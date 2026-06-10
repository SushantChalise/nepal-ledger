/**
 * Ingest CLI for the MoF / DPM-Office Yellow Book → `dne_facts` (ADR-0015).
 *
 * The Yellow Book (Annual Performance Review of Public Enterprises) is a
 * Devanagari PDF whose one deterministically parseable per-enterprise matrix
 * is Annex-1 (loan-investment-by-enterprise). The Python parser
 * (`scrapers/mof_yellowbook/parser.py`) emits a `dimensional_rows` array
 * (dimension = public enterprise) which this CLI routes directly into the
 * `dne_facts` typed fact table — exactly like `ingest:dne-dimensional`, but
 * with the Yellow Book parser + source id (`dpm-public-enterprises-annual`).
 * No indicator catalogue, no validation-job resolution: base measure
 * (`soe-government-share` / `soe-loan-principal`) + enterprise dimension are
 * self-describing.
 *
 * Source bytes are archived to Storage + a `source_documents` row created via
 * the shared helper. Idempotent: `dne_facts` has a unique index over
 * (base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs,
 * reporting_period_type, source_document_id) with ON CONFLICT DO NOTHING.
 *
 * Usage:
 *   pnpm ingest:dne-yellowbook --input "Financial Data/mof_documents/yellowbook/Webiste Uploaded Yellow_sdwyi9v.pdf"
 *   pnpm ingest:dne-yellowbook --input "..." --dry-run
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'mof_yellowbook', 'parser.py');
const SOURCE_ID = 'dpm-public-enterprises-annual';
const PARSER_TIMEOUT_MS = 300_000;

const DimensionalRowSchema = z.object({
  base_indicator_slug: z.string().min(1),
  base_indicator_name: z.string().min(1),
  dimension_kind: z.string().min(1),
  dimension_value: z.string().min(1),
  dimension_label: z.string().min(1),
  value: z.number(),
  unit: z.string().min(1),
  reporting_period_type: z.enum([
    'monthly',
    'quarterly',
    'annual',
    'daily',
    'seasonal',
    'nine_months_cumulative',
    'year_to_date',
  ]),
  reporting_period_bs: z.string().min(1),
  reporting_period_ad_start: z.coerce.date().nullable(),
  reporting_period_ad_end: z.coerce.date().nullable(),
  fiscal_year_bs: z.string().nullable(),
  fiscal_year_ad_label: z.string().nullable(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});
type DimensionalRow = z.infer<typeof DimensionalRowSchema>;

const ParserOutputSchema = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string().min(1),
  dimensional_rows: z.array(DimensionalRowSchema).default([]),
  errors: z.array(z.object({ error_class: z.string(), error_detail: z.string() })).default([]),
});

type CliArgs = { inputPath: string; dryRun: boolean };

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath = '';
  let dryRun = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') dryRun = true;
    else if (arg === '--input') {
      const next = argv[i + 1];
      if (!next) throw new Error('--input requires a value');
      inputPath = next;
      i += 1;
    } else if (arg?.startsWith('--input=')) inputPath = arg.slice('--input='.length);
  }
  if (!inputPath) throw new Error('--input <path> is required');
  return { inputPath, dryRun };
}

function log(msg: string): void {
  console.log(`[ingest-dne-yellowbook] ${msg}`);
}

async function runParser(inputPath: string): Promise<z.infer<typeof ParserOutputSchema>> {
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolvePromise, reject) => {
    const child = nodeSpawn(python, [PARSER_PATH, inputPath, 'yellowbook'], { shell: false });
    const out: Buffer[] = [];
    const err: Buffer[] = [];
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`parser timeout after ${PARSER_TIMEOUT_MS}ms`));
    }, PARSER_TIMEOUT_MS);
    child.stdout.on('data', (c: Buffer) => out.push(c));
    child.stderr.on('data', (c: Buffer) => err.push(c));
    child.on('error', (e) => {
      clearTimeout(timer);
      reject(e);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        reject(
          new Error(`parser exit ${code}: ${Buffer.concat(err).toString('utf8').slice(0, 400)}`),
        );
        return;
      }
      const parsed = ParserOutputSchema.safeParse(JSON.parse(Buffer.concat(out).toString('utf8')));
      if (!parsed.success) {
        reject(new Error(`parser output failed schema: ${parsed.error.message}`));
        return;
      }
      resolvePromise(parsed.data);
    });
  });
}

function toFactRow(row: DimensionalRow, sourceDocumentId: string) {
  return {
    sourceDocumentId,
    baseIndicatorSlug: row.base_indicator_slug,
    baseIndicatorName: row.base_indicator_name,
    dimensionKind: row.dimension_kind,
    dimensionValue: row.dimension_value,
    dimensionLabel: row.dimension_label,
    value: row.value.toString(),
    unit: row.unit,
    reportingPeriodType: row.reporting_period_type,
    reportingPeriodBs: row.reporting_period_bs,
    reportingPeriodAdStart: row.reporting_period_ad_start,
    reportingPeriodAdEnd: row.reporting_period_ad_end,
    fiscalYearBs: row.fiscal_year_bs,
    fiscalYearAdLabel: row.fiscal_year_ad_label,
    confidenceGrade: row.confidence_grade,
  };
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const absoluteInput = path.isAbsolute(args.inputPath)
    ? args.inputPath
    : path.join(REPO_ROOT, args.inputPath);
  log(`input   = ${absoluteInput}`);
  log(`dry_run = ${args.dryRun}`);
  if (!existsSync(absoluteInput)) {
    logErr(`input file not found: ${absoluteInput}`);
    process.exit(2);
  }
  if (!existsSync(PARSER_PATH)) {
    logErr(`parser not found: ${PARSER_PATH}`);
    process.exit(2);
  }

  const output = await runParser(absoluteInput);
  log(`parser_status        = ${output.status}`);
  log(`dimensional_rows     = ${output.dimensional_rows.length}`);
  log(`parser_errors        = ${output.errors.length}`);
  if (output.dimensional_rows.length === 0) {
    logErr('parser emitted 0 dimensional_rows — is this the FY2080/81 Yellow Book edition?');
    process.exit(1);
  }
  const bySlug = new Map<string, number>();
  for (const r of output.dimensional_rows)
    bySlug.set(r.base_indicator_slug, (bySlug.get(r.base_indicator_slug) ?? 0) + 1);
  log('by base_indicator_slug:');
  for (const [slug, n] of bySlug) log(`  ${slug.padEnd(40)} ${n}`);

  if (args.dryRun) {
    log('dry-run: first 3 dimensional rows:');
    for (const r of output.dimensional_rows.slice(0, 3)) {
      log(
        `  ${r.base_indicator_slug} / ${r.dimension_value} = ${r.value} ${r.unit} (${r.reporting_period_bs})`,
      );
    }
    log('dry-run complete — no DB writes.');
    return;
  }

  const { archiveAndInsertSourceDocument } = await import('./_lib/archive-source-document');
  const { bulkInsertDneFacts } = await import('@/lib/db/repositories/dne-facts');

  const sourceDocumentId = await archiveAndInsertSourceDocument({
    filePath: absoluteInput,
    sourceId: SOURCE_ID,
    contentType: 'application/pdf',
    reportingPeriodLabel: null,
    notes: 'Yellow Book public-enterprise dimensional ingest (ADR-0015; Annex-1)',
  });
  log(`source_documents.id  = ${sourceDocumentId}`);

  const rows = output.dimensional_rows.map((r) => toFactRow(r, sourceDocumentId));
  const result = await bulkInsertDneFacts(rows);
  if (!result.ok) {
    logErr(`bulkInsertDneFacts failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }
  log(
    `dne_facts inserted   = ${result.value.length} (of ${rows.length}; dupes skipped on conflict)`,
  );
  log('done.');
}

function logErr(msg: string): void {
  console.error(`[ingest-dne-yellowbook] ${msg}`);
}

main().catch((e: unknown) => {
  logErr(`uncaught: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
