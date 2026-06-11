/**
 * Ingest CLI for the MoF White Book → `foreign_aid_facts` (ADR-0017).
 *
 * The White Book ("Source Book for Projects Financed with Foreign Assistance")
 * has two clean English summary tables — foreign aid by development partner
 * (donor) and by ministry (sector). The Python parser
 * (`scrapers/mof_whitebook/parser.py`) emits a `dimensional_rows` array (base
 * measure = `foreign-aid-grant` / `foreign-aid-loan`; dimension = donor or
 * sector) which this CLI routes directly into the `foreign_aid_facts` typed fact
 * table — exactly like `ingest:dne-yellowbook`, but with the White Book parser +
 * source id (`mof-whitebook-foreign-aid`). No indicator catalogue, no
 * validation-job resolution: base measure + dimension are self-describing.
 *
 * Source bytes are archived to Storage + a `source_documents` row created via the
 * shared helper. Idempotent: `foreign_aid_facts` has a unique index over
 * (base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs,
 * reporting_period_type, source_document_id) with ON CONFLICT DO NOTHING.
 *
 * Usage:
 *   pnpm ingest:whitebook --input "Financial Data/mof_documents/whitebook/Source Book White Book FY 2020-21_dkjqgrt.pdf"
 *   pnpm ingest:whitebook --input "..." --dry-run
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'mof_whitebook', 'parser.py');
const SOURCE_ID = 'mof-whitebook-foreign-aid';
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
  console.log(`[ingest-whitebook] ${msg}`);
}

function logErr(msg: string): void {
  console.error(`[ingest-whitebook] ${msg}`);
}

async function runParser(inputPath: string): Promise<z.infer<typeof ParserOutputSchema>> {
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolvePromise, reject) => {
    const child = nodeSpawn(python, [PARSER_PATH, inputPath, 'whitebook'], {
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
  for (const e of output.errors.slice(0, 5)) log(`  err ${e.error_class}: ${e.error_detail}`);
  if (output.dimensional_rows.length === 0) {
    logErr(
      'parser emitted 0 dimensional_rows — is this a supported White Book edition? ' +
        'Clean English and legacy Preeti/Siddhi editions are both parseable; CID-broken editions are not (ADR-0017).',
    );
    process.exit(1);
  }
  const byKey = new Map<string, number>();
  for (const r of output.dimensional_rows) {
    const k = `${r.dimension_kind}/${r.base_indicator_slug}`;
    byKey.set(k, (byKey.get(k) ?? 0) + 1);
  }
  log('by dimension_kind / base_indicator_slug:');
  for (const [k, n] of byKey) log(`  ${k.padEnd(40)} ${n}`);
  const units = new Set(output.dimensional_rows.map((r) => r.unit));
  log(`units = ${[...units].join(', ')}`);

  if (args.dryRun) {
    log('dry-run: first 3 dimensional rows:');
    for (const r of output.dimensional_rows.slice(0, 3)) {
      log(
        `  ${r.dimension_kind}:${r.base_indicator_slug} / ${r.dimension_value} = ${r.value} ${r.unit} (${r.reporting_period_bs})`,
      );
    }
    log('dry-run complete — no DB writes.');
    return;
  }

  const { archiveAndInsertSourceDocument } = await import('./_lib/archive-source-document');
  const { bulkInsertForeignAidFacts } = await import('@/lib/db/repositories/foreign-aid-facts');

  const sourceDocumentId = await archiveAndInsertSourceDocument({
    filePath: absoluteInput,
    sourceId: SOURCE_ID,
    contentType: 'application/pdf',
    reportingPeriodLabel: null,
    notes: 'White Book foreign-aid dimensional ingest (ADR-0017; donor + sector summary tables)',
  });
  log(`source_documents.id  = ${sourceDocumentId}`);

  const rows = output.dimensional_rows.map((r) => toFactRow(r, sourceDocumentId));
  const result = await bulkInsertForeignAidFacts(rows);
  if (!result.ok) {
    logErr(`bulkInsertForeignAidFacts failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }
  log(
    `foreign_aid_facts inserted = ${result.value.length} (of ${rows.length}; dupes skipped on conflict)`,
  );
  log('done.');
}

main().catch((e: unknown) => {
  logErr(`uncaught: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
