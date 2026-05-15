/**
 * One-shot ingest CLI for MoF Local Fiscal Transfers (FY 2082/83).
 *
 * Unlike the general indicator-orchestrator pipeline, this script writes
 * directly to the `local_government_fiscal_transfers` domain-fact table —
 * no staging-validation step. Confidence is A by default because the
 * cleaned XLSX is authoritative MoF data.
 *
 * Usage:
 *   pnpm ingest:fiscal-transfers --dry-run
 *   pnpm ingest:fiscal-transfers --input "Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx"
 *   pnpm ingest:fiscal-transfers                        # uses default path
 *
 * Idempotency: re-running is safe. The repository's `bulkInsertIdempotent`
 * uses `ON CONFLICT DO NOTHING` against the unique index
 * `(local_level_entity_id, fiscal_year_bs, grant_type)`.
 *
 * Subprocess contract mirrors `src/lib/ingestion/run-parser.ts`:
 *   - argv: <source_document_path> <source_document_id>
 *   - stdout: ParserResult JSON
 *   - exit 0  → consumer parses stdout
 *   - exit 1  → catastrophic crash
 *   - exit 2  → usage error
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import { basename, resolve } from 'node:path';

import { z } from 'zod';

const DEFAULT_INPUT = 'Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx';
const PARSER_PATH = 'scrapers/mof_fiscal_transfers/parser.py';
const SOURCE_ID = 'local-fiscal-transfers-cleaned';
const PARSER_TIMEOUT_MS = 120_000;

// ─── Parser output schema (mirrors scrapers/mof_fiscal_transfers/parser.py) ─

const ParserErrorSchema = z.object({
  error_class: z.string(),
  error_detail: z.string(),
  source_excerpt: z.string().nullable().optional(),
});

const FiscalTransferRowSchema = z.object({
  federal_code: z.string().regex(/^\d{8}$/),
  municipality_name_en: z.string().min(1),
  municipality_name_ne: z.string().min(1),
  local_level_type: z.string().min(1),
  district_en: z.string().min(1),
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

type FiscalTransferRowPayload = z.infer<typeof FiscalTransferRowSchema>;

const ParserOutputSchema = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string().min(1),
  rows: z.array(FiscalTransferRowSchema),
  errors: z.array(ParserErrorSchema),
});

type ParserOutput = z.infer<typeof ParserOutputSchema>;

// ─── CLI ────────────────────────────────────────────────────────────────

type CliArgs = {
  inputPath: string;
  dryRun: boolean;
};

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath = DEFAULT_INPUT;
  let dryRun = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') {
      dryRun = true;
    } else if (arg === '--input') {
      const next = argv[i + 1];
      if (!next) throw new Error('--input requires a value');
      inputPath = next;
      i += 1;
    } else if (arg?.startsWith('--input=')) {
      inputPath = arg.slice('--input='.length);
    }
  }
  return { inputPath, dryRun };
}

function log(msg: string): void {
  console.log(`[ingest-fiscal-transfers] ${msg}`);
}

function logErr(msg: string): void {
  console.error(`[ingest-fiscal-transfers] ${msg}`);
}

// ─── Python parser subprocess ───────────────────────────────────────────

async function runParser(inputPath: string, sourceDocumentId: string): Promise<ParserOutput> {
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolvePromise, reject) => {
    const child = nodeSpawn(python, [PARSER_PATH, inputPath, sourceDocumentId], {
      cwd: process.cwd(),
      shell: false,
    });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`python parser timeout after ${PARSER_TIMEOUT_MS}ms`));
    }, PARSER_TIMEOUT_MS);
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

type Summary = {
  parserStatus: ParserOutput['status'];
  parsedRows: number;
  parserErrors: number;
  byGrantType: Record<string, number>;
  byLocalLevelType: Record<string, number>;
  totalNprThousand: number;
  uniqueMunicipalities: number;
};

function summarise(rows: readonly FiscalTransferRowPayload[], output: ParserOutput): Summary {
  const byGrantType: Record<string, number> = {};
  const byLocalLevelType: Record<string, number> = {};
  const seenMunicipalities = new Set<string>();
  let totalNprThousand = 0;
  for (const row of rows) {
    byGrantType[row.grant_type] = (byGrantType[row.grant_type] ?? 0) + 1;
    byLocalLevelType[row.local_level_type] = (byLocalLevelType[row.local_level_type] ?? 0) + 1;
    totalNprThousand += row.amount_npr;
    seenMunicipalities.add(row.federal_code);
  }
  return {
    parserStatus: output.status,
    parsedRows: rows.length,
    parserErrors: output.errors.length,
    byGrantType,
    byLocalLevelType,
    totalNprThousand,
    uniqueMunicipalities: seenMunicipalities.size,
  };
}

function printSummary(s: Summary): void {
  log(`parser_status         = ${s.parserStatus}`);
  log(`parsed_rows           = ${s.parsedRows}`);
  log(`parser_errors         = ${s.parserErrors}`);
  log(`unique_municipalities = ${s.uniqueMunicipalities}`);
  log(`total_npr_thousand    = ${s.totalNprThousand.toLocaleString('en-US')}`);
  log('by_grant_type:');
  for (const [k, v] of Object.entries(s.byGrantType)) log(`  ${k.padEnd(28)} ${v}`);
  log('by_local_level_type:');
  for (const [k, v] of Object.entries(s.byLocalLevelType)) log(`  ${k.padEnd(28)} ${v}`);
}

// ─── DB write path ──────────────────────────────────────────────────────

async function persist(
  rows: readonly FiscalTransferRowPayload[],
  inputPath: string,
): Promise<{ wrote: number; skipped: number; unresolved: number }> {
  // Lazy import so --dry-run doesn't need DATABASE_URL set.
  const { insertSourceDocument } = await import('@/lib/db/repositories/source-documents');
  const { findLocalLevelEntityBySlug, bulkInsertIdempotent } =
    await import('@/lib/db/repositories/local-government-fiscal-transfers');

  // 1. Record the source document (append-only).
  const absoluteInput = resolve(inputPath);
  const fileBuf = await readFile(absoluteInput);
  const fileHash = createHash('sha256').update(fileBuf).digest('hex');
  const fileStat = await stat(absoluteInput);
  const today = new Date().toISOString().slice(0, 10);
  const docResult = await insertSourceDocument({
    sourceId: SOURCE_ID,
    originalUrl: `file://${absoluteInput}`,
    storageProvider: 'supabase',
    storageKey: `${SOURCE_ID}/${today}/${basename(absoluteInput)}`,
    fileHashSha256: fileHash,
    fileSizeBytes: fileStat.size,
    contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    reportingPeriodLabel: 'FY 2082/83',
    notes: 'One-shot ingest via scripts/ingest-fiscal-transfers.ts',
  });
  if (!docResult.ok) {
    throw new Error(`insertSourceDocument failed: ${JSON.stringify(docResult.error)}`);
  }
  const sourceDocumentId = docResult.value.id;
  log(`source_documents.id = ${sourceDocumentId}`);

  // 2. Resolve entities + build typed inserts.
  const inserts: Array<{
    localLevelEntityId: string;
    fiscalYearBs: string;
    grantType: FiscalTransferRowPayload['grant_type'];
    amountNpr: string;
    unit: string;
    sourceDocumentId: string;
    confidenceGrade: FiscalTransferRowPayload['confidence_grade'];
    promotedBy: string;
    notes: string | null;
  }> = [];
  let unresolved = 0;
  for (const row of rows) {
    const entityResult = await findLocalLevelEntityBySlug(row.federal_code);
    if (!entityResult.ok) {
      throw new Error(
        `findLocalLevelEntityBySlug(${row.federal_code}) failed: ${JSON.stringify(entityResult.error)}`,
      );
    }
    if (entityResult.value === null) {
      unresolved += 1;
      continue;
    }
    inserts.push({
      localLevelEntityId: entityResult.value.id,
      fiscalYearBs: row.fiscal_year_bs,
      grantType: row.grant_type,
      // numeric(20,2) — pass as string per Drizzle convention.
      amountNpr: row.amount_npr.toFixed(2),
      unit: row.unit,
      sourceDocumentId,
      confidenceGrade: row.confidence_grade,
      promotedBy: 'scripts/ingest-fiscal-transfers.ts',
      notes: row.notes ?? null,
    });
  }

  // 3. Bulk-insert with ON CONFLICT DO NOTHING.
  const writeResult = await bulkInsertIdempotent(inserts);
  if (!writeResult.ok) {
    throw new Error(`bulkInsertIdempotent failed: ${JSON.stringify(writeResult.error)}`);
  }
  return {
    wrote: writeResult.value.inserted,
    skipped: writeResult.value.skippedDuplicate,
    unresolved,
  };
}

// ─── Main ───────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const absoluteInput = resolve(args.inputPath);
  log(`input          = ${absoluteInput}`);
  log(`dry_run        = ${args.dryRun}`);

  try {
    await stat(absoluteInput);
  } catch {
    logErr(`input file not found: ${absoluteInput}`);
    process.exit(2);
  }

  // The python parser is the source of truth for parsing; we pass a
  // placeholder source_document_id during dry-run, and the real UUID when
  // we actually persist.
  const placeholderDocId = 'dry-run-placeholder';
  const parserOutput = await runParser(absoluteInput, placeholderDocId);
  const summary = summarise(parserOutput.rows, parserOutput);
  printSummary(summary);

  if (parserOutput.errors.length > 0) {
    log(`parser surfaced ${parserOutput.errors.length} warning(s):`);
    for (const e of parserOutput.errors.slice(0, 10)) {
      log(`  ${e.error_class}: ${e.error_detail}`);
    }
    if (parserOutput.errors.length > 10) {
      log(`  … (${parserOutput.errors.length - 10} more suppressed)`);
    }
  }

  if (args.dryRun) {
    log('dry-run mode: no DB writes performed');
    process.exit(0);
  }

  if (parserOutput.status === 'failure') {
    logErr('parser returned status=failure — refusing to persist');
    process.exit(1);
  }

  const writeSummary = await persist(parserOutput.rows, absoluteInput);
  log(`db_inserted    = ${writeSummary.wrote}`);
  log(`db_skipped_dup = ${writeSummary.skipped}`);
  log(`unresolved_entities = ${writeSummary.unresolved}`);
  if (writeSummary.unresolved > 0) {
    log(
      `note: ${writeSummary.unresolved} rows were skipped because no entities ` +
        `row exists with kind=local_level + slug=<federal_code>. Run the ` +
        `entity-seed step before re-ingesting to capture these.`,
    );
  }
  process.exit(0);
}

main().catch((e: unknown) => {
  logErr(`uncaught error: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
