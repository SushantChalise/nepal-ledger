/**
 * One-shot ingest CLI for MoF Intergovernmental Fiscal Transfers (historical
 * FYs). Phase B1. Routes per-local-level transfer rows from the historical
 * intergovernmental PDFs into `local_government_fiscal_transfers` — the SAME
 * table the FY2082/83 XLSX feeds, extending that series backward.
 *
 * Two data channels (see scrapers/surya_ocr/parsers/intergovernmental.py):
 *   - VALUES come from the PDF text layer (deterministic, exact, self-
 *     reconciling). The Python parser refuses to emit a FY whose per-row and
 *     document totals don't reconcile (ADR-0021 gate enforced parser-side).
 *   - With `--surya`, the Surya OCR harness ALSO runs over the detail pages
 *     and its `ocr_tracking` trio (tiles / cell extractions / stitch
 *     disagreements) is persisted for inspectability + independent
 *     confirmation. Confidence is B; method `surya-ocr+textlayer-xcheck`.
 *
 * Usage:
 *   pnpm ingest:intergovernmental --input "Financial Data/mof_documents/intergovernmental/207980.pdf" --dry-run
 *   pnpm ingest:intergovernmental --input "Financial Data/mof_documents/intergovernmental/207980.pdf"
 *   pnpm ingest:intergovernmental --input "...207980.pdf" --surya          # also persist ocr_tracking
 *
 * Idempotency: `bulkInsertIdempotent` uses ON CONFLICT DO NOTHING on
 * `(local_level_entity_id, fiscal_year_bs, grant_type)`.
 *
 * Subprocess contract mirrors scripts/ingest-fiscal-transfers.ts:
 *   - argv: <pdf_path> <source_document_id> [--surya]
 *   - stdout: ParserOutput JSON (rows + reconciliation [+ surya])
 *   - exit 0 → consumer parses stdout; exit 2 → usage error; exit 1 → crash
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { stat } from 'node:fs/promises';
import { resolve } from 'node:path';

import { z } from 'zod';

const PARSER_PATH = 'scrapers/surya_ocr/parsers/intergovernmental.py';
const SOURCE_ID = 'mof-intergovernmental';
// Surya model load + tile-OCR over ~30 detail pages on GPU is minutes, not
// seconds — generous timeout when --surya is set.
const PARSER_TIMEOUT_TEXT_MS = 120_000;
const PARSER_TIMEOUT_SURYA_MS = 1_800_000;

// ─── Parser output schema (mirrors the Python parser) ─────────────────────

const ParserErrorSchema = z.object({
  error_class: z.string(),
  error_detail: z.string(),
  source_excerpt: z.string().nullable().optional(),
});

const TransferRowSchema = z.object({
  federal_code: z.string().regex(/^\d{8}$/),
  municipality_name_en: z.string(),
  municipality_name_ne: z.string(),
  local_level_type: z.string(),
  district_en: z.string(),
  fiscal_year_bs: z.string().min(1),
  grant_type: z.enum([
    'equalization_minimum',
    'equalization_formula',
    'equalization_performance',
    'conditional_current',
    'conditional_capital',
    'special_current',
    'special_capital',
    'complementary_capital',
  ]),
  amount_npr: z.number(),
  unit: z.string().min(1),
  confidence_grade: z.enum(['A', 'B', 'C']),
  notes: z.string().nullable().optional(),
});

type TransferRowPayload = z.infer<typeof TransferRowSchema>;

const ReconciliationSchema = z
  .object({
    fiscal_year_bs: z.string(),
    local_level_count: z.number(),
    rows_reconciled: z.number(),
    rows_failed: z.number(),
    row_grand_total_sum_lakh: z.number(),
    printed_local_total_lakh: z.number().nullable(),
    document_total_reconciles: z.boolean(),
  })
  .nullable();

const StitchResolutionSchema = z.enum([
  'kept_higher_confidence',
  'kept_left_tile',
  'kept_right_tile',
  'flagged_for_review',
]);

const OcrPageSchema = z.object({
  page_number: z.number(),
  tiles: z.array(
    z.object({
      page_number: z.number(),
      tile_index: z.number(),
      offset_x_px: z.number(),
      offset_y_px: z.number(),
      width_px: z.number(),
      height_px: z.number(),
      dpi: z.number(),
      model_name: z.string(),
      model_version: z.string(),
    }),
  ),
  cells: z.array(
    z.object({
      page_number: z.number(),
      tile_index: z.number(),
      table_region_id: z.string().nullable(),
      tile_bbox_x: z.number(),
      tile_bbox_y: z.number(),
      tile_bbox_w: z.number(),
      tile_bbox_h: z.number(),
      page_bbox_x: z.number(),
      page_bbox_y: z.number(),
      page_bbox_w: z.number(),
      page_bbox_h: z.number(),
      near_tile_seam_px: z.number().nullable(),
      text_raw: z.string(),
      text_normalized: z.string().nullable(),
      numeral_arabic: z.string().nullable(),
      numeral_devanagari: z.string().nullable(),
      confidence: z.number().nullable(),
    }),
  ),
  disagreements: z.array(
    z.object({
      cell_a_index: z.number(),
      cell_b_index: z.number(),
      iou: z.number(),
      resolution: StitchResolutionSchema,
      resolution_reason: z.string(),
    }),
  ),
  kept_cell_indices: z.array(z.number()),
});

const SuryaSchema = z
  .object({
    ocr_pages: z.array(OcrPageSchema),
    cross_validation: z.object({
      fiscal_year_bs: z.string(),
      pages_ocred: z.number(),
      tile_count: z.number(),
      cell_count: z.number(),
      disagreement_count: z.number(),
      value_cells_compared: z.number(),
      value_cells_agreeing: z.number(),
      mean_line_confidence: z.number(),
    }),
    low_confidence_samples: z.array(z.unknown()),
  })
  .optional();

const ParserOutputSchema = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string().min(1),
  rows: z.array(TransferRowSchema),
  errors: z.array(ParserErrorSchema),
  reconciliation: ReconciliationSchema,
  surya: SuryaSchema,
});

type ParserOutput = z.infer<typeof ParserOutputSchema>;

// ─── CLI ──────────────────────────────────────────────────────────────────

type CliArgs = { inputPath: string; dryRun: boolean; surya: boolean };

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath = '';
  let dryRun = false;
  let surya = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') dryRun = true;
    else if (arg === '--surya') surya = true;
    else if (arg === '--input') {
      const next = argv[i + 1];
      if (!next) throw new Error('--input requires a value');
      inputPath = next;
      i += 1;
    } else if (arg?.startsWith('--input=')) {
      inputPath = arg.slice('--input='.length);
    }
  }
  return { inputPath, dryRun, surya };
}

function log(msg: string): void {
  console.log(`[ingest-intergovernmental] ${msg}`);
}
function logErr(msg: string): void {
  console.error(`[ingest-intergovernmental] ${msg}`);
}

// ─── Python parser subprocess ───────────────────────────────────────────

async function runParser(
  inputPath: string,
  sourceDocumentId: string,
  surya: boolean,
): Promise<ParserOutput> {
  // Surya needs the base py312 GPU interpreter; the text-only path runs on the
  // scrapers venv too. PYTHON env var (per ADR-0010) selects the interpreter.
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  const args = [PARSER_PATH, inputPath, sourceDocumentId];
  if (surya) args.push('--surya');
  const timeoutMs = surya ? PARSER_TIMEOUT_SURYA_MS : PARSER_TIMEOUT_TEXT_MS;
  return new Promise((resolvePromise, reject) => {
    const child = nodeSpawn(python, args, { cwd: process.cwd(), shell: false });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`python parser timeout after ${timeoutMs}ms`));
    }, timeoutMs);
    child.stdout.on('data', (c: Buffer) => stdoutChunks.push(c));
    child.stderr.on('data', (c: Buffer) => stderrChunks.push(c));
    child.on('error', (e) => {
      clearTimeout(timer);
      reject(e);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      const stdout = Buffer.concat(stdoutChunks).toString('utf8');
      const stderr = Buffer.concat(stderrChunks).toString('utf8');
      if (code !== 0) {
        reject(new Error(`python parser exit ${code}: ${stderr.trim() || '<no stderr>'}`));
        return;
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(stdout);
      } catch (e) {
        reject(new Error(`parser stdout was not JSON: ${e instanceof Error ? e.message : e}`));
        return;
      }
      const validated = ParserOutputSchema.safeParse(parsed);
      if (!validated.success) {
        reject(new Error(`parser stdout failed schema validation: ${validated.error.message}`));
        return;
      }
      resolvePromise(validated.data);
    });
  });
}

// ─── Summary ────────────────────────────────────────────────────────────

function printSummary(output: ParserOutput): void {
  log(`parser_status   = ${output.status}`);
  log(`parsed_rows     = ${output.rows.length}`);
  log(`parser_errors   = ${output.errors.length}`);
  const r = output.reconciliation;
  if (r) {
    log(`fiscal_year_bs  = ${r.fiscal_year_bs}`);
    log(`local_levels    = ${r.local_level_count}`);
    log(`rows_reconciled = ${r.rows_reconciled}  rows_failed = ${r.rows_failed}`);
    log(
      `doc_total       = ${r.document_total_reconciles ? 'RECONCILES' : 'MISMATCH'} ` +
        `(sum ${r.row_grand_total_sum_lakh} lakh vs printed ${r.printed_local_total_lakh})`,
    );
  }
  const byGrant: Record<string, number> = {};
  let totalCrore = 0;
  const codes = new Set<string>();
  for (const row of output.rows) {
    byGrant[row.grant_type] = (byGrant[row.grant_type] ?? 0) + 1;
    totalCrore += row.amount_npr;
    codes.add(row.federal_code);
  }
  log(`unique_local_levels = ${codes.size}`);
  log(`total_npr_crore     = ${totalCrore.toLocaleString('en-US')}`);
  log('by_grant_type:');
  for (const [k, v] of Object.entries(byGrant)) log(`  ${k.padEnd(28)} ${v}`);
  if (output.surya) {
    const cv = output.surya.cross_validation;
    log(
      `surya: pages=${cv.pages_ocred} tiles=${cv.tile_count} cells=${cv.cell_count} ` +
        `disagreements=${cv.disagreement_count} mean_conf=${cv.mean_line_confidence}`,
    );
  }
  if (output.errors.length > 0) {
    log(`first errors:`);
    for (const e of output.errors.slice(0, 5)) log(`  ${e.error_class}: ${e.error_detail}`);
    if (output.errors.length > 5) log(`  … (${output.errors.length - 5} more)`);
  }
}

// ─── DB write path ──────────────────────────────────────────────────────

async function persist(
  output: ParserOutput,
  inputPath: string,
): Promise<{ wrote: number; skipped: number; unresolved: number; ocr: string }> {
  const { archiveAndInsertSourceDocument } = await import('./_lib/archive-source-document');
  const { findLocalLevelEntitiesBySlugs, bulkInsertIdempotent } =
    await import('@/lib/db/repositories/local-government-fiscal-transfers');

  const fy = output.reconciliation?.fiscal_year_bs ?? 'unknown';
  const absoluteInput = resolve(inputPath);
  const sourceDocumentId = await archiveAndInsertSourceDocument({
    filePath: absoluteInput,
    sourceId: SOURCE_ID,
    contentType: 'application/pdf',
    reportingPeriodLabel: `FY ${fy}`,
    notes: 'One-shot ingest via scripts/ingest-intergovernmental.ts (Phase B1)',
  });
  log(`source_documents.id = ${sourceDocumentId}`);

  // Resolve all federal codes in ONE query.
  const entityMap = await findLocalLevelEntitiesBySlugs(output.rows.map((r) => r.federal_code));
  if (!entityMap.ok) {
    throw new Error(`findLocalLevelEntitiesBySlugs failed: ${JSON.stringify(entityMap.error)}`);
  }
  const entityBySlug = entityMap.value;

  let unresolved = 0;
  const inserts: Array<{
    localLevelEntityId: string;
    fiscalYearBs: string;
    grantType: TransferRowPayload['grant_type'];
    amountNpr: string;
    unit: string;
    sourceDocumentId: string;
    confidenceGrade: TransferRowPayload['confidence_grade'];
    promotedBy: string;
    notes: string | null;
  }> = [];
  for (const row of output.rows) {
    const entity = entityBySlug.get(row.federal_code);
    if (entity === undefined) {
      unresolved += 1;
      continue;
    }
    inserts.push({
      localLevelEntityId: entity.id,
      fiscalYearBs: row.fiscal_year_bs,
      grantType: row.grant_type,
      amountNpr: row.amount_npr.toFixed(2),
      unit: row.unit,
      sourceDocumentId,
      confidenceGrade: row.confidence_grade,
      promotedBy: 'scripts/ingest-intergovernmental.ts',
      notes: row.notes ?? null,
    });
  }

  const writeResult = await bulkInsertIdempotent(inserts);
  if (!writeResult.ok) {
    throw new Error(`bulkInsertIdempotent failed: ${JSON.stringify(writeResult.error)}`);
  }

  // Persist the Surya ocr_tracking trio (provenance), if present.
  let ocr = 'not-run';
  if (output.surya) {
    const { insertParserRun } = await import('@/lib/db/repositories/parser-runs');
    const { persistOcrTracking } = await import('@/lib/db/repositories/ocr-tracking');
    const run = await insertParserRun({
      sourceDocumentId,
      parserPath: PARSER_PATH,
      parserVersion: output.parser_version,
      status: output.status,
      stagingRowsWritten: 0,
      errorSummary: `Surya cross-check: ${output.surya.cross_validation.cell_count} cells`,
    });
    if (!run.ok) throw new Error(`insertParserRun failed: ${JSON.stringify(run.error)}`);
    const pages = output.surya.ocr_pages.map((p) => ({
      pageNumber: p.page_number,
      tiles: p.tiles.map((t) => ({
        pageNumber: t.page_number,
        tileIndex: t.tile_index,
        offsetXPx: t.offset_x_px,
        offsetYPx: t.offset_y_px,
        widthPx: t.width_px,
        heightPx: t.height_px,
        dpi: t.dpi,
        modelName: t.model_name,
        modelVersion: t.model_version,
      })),
      cells: p.cells.map((c) => ({
        pageNumber: c.page_number,
        tileIndex: c.tile_index,
        tableRegionId: c.table_region_id,
        tileBboxX: c.tile_bbox_x,
        tileBboxY: c.tile_bbox_y,
        tileBboxW: c.tile_bbox_w,
        tileBboxH: c.tile_bbox_h,
        pageBboxX: c.page_bbox_x,
        pageBboxY: c.page_bbox_y,
        pageBboxW: c.page_bbox_w,
        pageBboxH: c.page_bbox_h,
        nearTileSeamPx: c.near_tile_seam_px,
        textRaw: c.text_raw,
        textNormalized: c.text_normalized,
        numeralArabic: c.numeral_arabic,
        numeralDevanagari: c.numeral_devanagari,
        confidence: c.confidence,
      })),
      disagreements: p.disagreements.map((d) => ({
        cellAIndex: d.cell_a_index,
        cellBIndex: d.cell_b_index,
        iou: d.iou,
        resolution: d.resolution,
        resolutionReason: d.resolution_reason,
      })),
    }));
    const tracked = await persistOcrTracking(run.value.id, sourceDocumentId, pages);
    if (!tracked.ok) throw new Error(`persistOcrTracking failed: ${JSON.stringify(tracked.error)}`);
    ocr =
      `parser_run=${run.value.id} tiles=${tracked.value.tilesInserted} ` +
      `cells=${tracked.value.cellsInserted} disagreements=${tracked.value.disagreementsInserted}`;
  }

  return {
    wrote: writeResult.value.inserted,
    skipped: writeResult.value.skippedDuplicate,
    unresolved,
    ocr,
  };
}

// ─── Main ───────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  if (!args.inputPath) {
    logErr('missing --input <pdf path>');
    process.exit(2);
  }
  const absoluteInput = resolve(args.inputPath);
  log(`input    = ${absoluteInput}`);
  log(`dry_run  = ${args.dryRun}`);
  log(`surya    = ${args.surya}`);

  try {
    await stat(absoluteInput);
  } catch {
    logErr(`input file not found: ${absoluteInput}`);
    process.exit(2);
  }

  const placeholderDocId = 'dry-run-placeholder';
  const output = await runParser(absoluteInput, placeholderDocId, args.surya);
  printSummary(output);

  // ADR-0021 gate: refuse to persist a FY that doesn't reconcile.
  if (output.status === 'failure') {
    logErr('parser returned status=failure — refusing to persist (unreconciled/scanned FY).');
    process.exit(args.dryRun ? 0 : 1);
  }
  if (output.reconciliation && !output.reconciliation.document_total_reconciles) {
    logErr('document total does not reconcile — refusing to persist (ADR-0021).');
    process.exit(args.dryRun ? 0 : 1);
  }

  if (args.dryRun) {
    log('dry-run mode: no DB writes performed');
    process.exit(0);
  }

  const writeSummary = await persist(output, absoluteInput);
  log(`db_inserted    = ${writeSummary.wrote}`);
  log(`db_skipped_dup = ${writeSummary.skipped}`);
  log(`unresolved     = ${writeSummary.unresolved}`);
  log(`ocr_tracking   = ${writeSummary.ocr}`);
  if (writeSummary.unresolved > 0) {
    log(
      `note: ${writeSummary.unresolved} rows skipped — no entities row with ` +
        `kind=local_level + slug=<federal_code>. Run seed:local-levels first.`,
    );
  }
  process.exit(0);
}

main().catch((e: unknown) => {
  logErr(`uncaught error: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
