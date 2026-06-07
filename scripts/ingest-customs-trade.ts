/**
 * Ingest CLI for the Department of Customs Foreign Trade Statistics → `dne_facts`
 * (ADR-0015).
 *
 * The Department of Customs publishes machine-readable XLSX workbooks of monthly
 * (cumulative-to-date) and annual foreign-trade statistics compiled from the
 * ASYCUDA World system. The Python parser (`scrapers/customs_trade/parser.py`)
 * emits a `dimensional_rows` array (dimension = commodity HS-code / country /
 * customs office) which this CLI routes directly into the typed `dne_facts` fact
 * table — exactly like `ingest:dne-yellowbook`, but with the customs parser +
 * source id (`customs-monthly-trade`). No indicator catalogue, no validation-job
 * resolution: base measure (`customs-merchandise-imports` /
 * `customs-merchandise-exports`) + dimension are self-describing.
 *
 * Source bytes are archived to Storage + a `source_documents` row created via
 * the shared helper. Idempotent: `dne_facts` has a unique index over
 * (base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs,
 * reporting_period_type, source_document_id) with ON CONFLICT DO NOTHING — so the
 * same workbook re-ingested never double-counts, and distinct periods (Shrawan
 * vs. up-to-Bhadra vs. annual) coexist because the period label differs.
 *
 * Usage:
 *   pnpm ingest:customs-trade --input "Financial Data/customs/FTS_Annual_2081_82.xlsx" --dry-run
 *   pnpm ingest:customs-trade --input "Financial Data/customs/FTS_Annual_2081_82.xlsx"
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'customs_trade', 'parser.py');
const SOURCE_ID = 'customs-monthly-trade';
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
  console.log(`[ingest-customs-trade] ${msg}`);
}

function logErr(msg: string): void {
  console.error(`[ingest-customs-trade] ${msg}`);
}

async function runParser(inputPath: string): Promise<z.infer<typeof ParserOutputSchema>> {
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolvePromise, reject) => {
    const child = nodeSpawn(python, [PARSER_PATH, inputPath, 'customs-fts'], { shell: false });
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
    logErr('parser emitted 0 dimensional_rows — is this a Customs FTS workbook?');
    process.exit(1);
  }

  // Period sanity: every fact in one workbook shares one period label.
  const periods = new Set(output.dimensional_rows.map((r) => r.reporting_period_bs));
  log(`reporting_period(s)  = ${[...periods].join(', ')}`);

  const byDim = new Map<string, number>();
  for (const r of output.dimensional_rows) {
    const key = `${r.base_indicator_slug} / ${r.dimension_kind}`;
    byDim.set(key, (byDim.get(key) ?? 0) + 1);
  }
  log('by base_indicator_slug / dimension_kind:');
  for (const [key, n] of byDim) log(`  ${key.padEnd(48)} ${n}`);

  if (args.dryRun) {
    log('dry-run: first 3 dimensional rows:');
    for (const r of output.dimensional_rows.slice(0, 3)) {
      log(
        `  ${r.base_indicator_slug} / ${r.dimension_kind}=${r.dimension_value} = ${r.value} ${r.unit} (${r.reporting_period_bs})`,
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
    contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    reportingPeriodLabel: null,
    notes:
      'Customs Foreign Trade Statistics dimensional ingest (ADR-0015; commodity/country/customs-office)',
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

main().catch((e: unknown) => {
  logErr(`uncaught: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
