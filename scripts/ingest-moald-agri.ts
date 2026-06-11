/**
 * Ingest CLI for MoALD Statistical Information on Nepalese Agriculture → `dne_facts`
 * (ADR-0015).
 *
 * The Python parser (`scrapers/moald_agri_stats/parser.py`) emits
 * `dimensional_rows` covering:
 *   - Table 1.1: 10-year cereal area/production/yield × crop_type (paddy/maize/…)
 *   - Summary §1.4: 3-year cash crop area/production × crop_type
 *   - Summary §1.5: 3-year pulse area/production × crop_type
 *   - Summary §2.2: 3-year livestock production × livestock_product
 *   - Summary §3:   3-year fertilizer sales × fertilizer_type
 *
 * Source bytes are archived and a `source_documents` row created via
 * `scripts/_lib/archive-source-document.ts`. Idempotent: `dne_facts` unique index
 * (base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs,
 * reporting_period_type, source_document_id) with ON CONFLICT DO NOTHING.
 *
 * Usage:
 *   pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf" --dry-run
 *   pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf"
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'moald_agri_stats', 'parser.py');
const SOURCE_ID = 'moald-agri-stats';
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
  console.log(`[ingest-moald-agri] ${msg}`);
}
function logErr(msg: string): void {
  console.error(`[ingest-moald-agri] ${msg}`);
}

async function runParser(inputPath: string): Promise<z.infer<typeof ParserOutputSchema>> {
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolve, reject) => {
    const child = nodeSpawn(python, [PARSER_PATH, inputPath], {
      shell: false,
      env: { ...process.env, PYTHONPATH: path.join(REPO_ROOT, 'scrapers') },
    });
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
        reject(new Error(`parser output schema mismatch: ${parsed.error.message}`));
        return;
      }
      resolve(parsed.data);
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
  log(`parser_status    = ${output.status}`);
  log(`dimensional_rows = ${output.dimensional_rows.length}`);
  log(`parser_errors    = ${output.errors.length}`);
  for (const e of output.errors) logErr(`  parser error: ${e.error_class} — ${e.error_detail}`);

  if (output.dimensional_rows.length === 0) {
    logErr('parser emitted 0 dimensional_rows');
    process.exit(1);
  }

  const byDim = new Map<string, number>();
  for (const r of output.dimensional_rows) {
    const key = `${r.base_indicator_slug} / ${r.dimension_kind}`;
    byDim.set(key, (byDim.get(key) ?? 0) + 1);
  }
  log('by base_indicator_slug / dimension_kind:');
  for (const [key, n] of byDim) log(`  ${key.padEnd(44)} ${n}`);

  if (args.dryRun) {
    log('dry-run: first 3 rows:');
    for (const r of output.dimensional_rows.slice(0, 3)) {
      log(`  ${r.base_indicator_slug}/${r.dimension_value} ${r.reporting_period_bs} = ${r.value} ${r.unit}`);
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
    reportingPeriodLabel: 'FY 2080/81 (2023/24 AD)',
    notes:
      'MoALD Statistical Information on Nepalese Agriculture FY 2080/81; ' +
      'cereal 10yr series + cash/pulse/livestock/fertilizer 3yr summary → dne_facts (ADR-0015)',
  });
  log(`source_documents.id = ${sourceDocumentId}`);

  const rows = output.dimensional_rows.map((r) => toFactRow(r, sourceDocumentId));
  const result = await bulkInsertDneFacts(rows);
  if (!result.ok) {
    logErr(`bulkInsertDneFacts failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }
  log(`inserted ${rows.length} dne_facts rows (ON CONFLICT DO NOTHING)`);
  log('ingest complete.');
}

main().catch((err: unknown) => {
  logErr(String(err));
  process.exit(1);
});
