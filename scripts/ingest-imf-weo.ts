/**
 * Ingest CLI for IMF World Economic Outlook (Nepal) — source_id: "imf-weo".
 *
 * The WEO parser reads a combined JSON blob (one file, 13 indicator time-series
 * with historical actuals + 5-year projections). This CLI has two modes:
 *
 *   --input <path>   Use a pre-assembled combined JSON file (a fixture or the
 *                    output of a previous --download run).
 *   --download       Fetch all 13 indicator codes from the IMF DataMapper API
 *                    (https://www.imf.org/external/datamapper/api/v1/<code>/NPL),
 *                    assemble the combined JSON, write it to --output-dir
 *                    (default: system temp), then hand off to the parser.
 *
 * Projections (ADR-0025): WEO mixes actuals and forecasts in one series, but
 * the DataMapper API does not flag which years are projections. The operator
 * supplies the published boundary via --projection-from-year <YEAR> (the first
 * forecast AD year for the vintage, e.g. 2025 for the Apr-2026 WEO). Years >=
 * that are emitted as observation_type='projection'. Omit it and every row is
 * 'actual' (the parser never fabricates the boundary).
 *
 * Both modes support --dry-run (no DB writes; parser output printed).
 *
 * Default --input: the checked-in fixture used by parser tests.
 *
 * Usage:
 *   pnpm ingest:imf-weo --dry-run
 *   pnpm ingest:imf-weo --input /path/to/combined.json
 *   pnpm ingest:imf-weo --download --projection-from-year 2025
 *   pnpm ingest:imf-weo --download --output-dir /tmp/weo --projection-from-year 2025
 *
 * Pipeline (ingestSource orchestrator):
 *   1. Read / download → combined JSON file on disk
 *   2. Archive to Supabase Storage (content-addressed; idempotent)
 *   3. Insert source_documents row
 *   4. Spawn scrapers/imf_weo/parser.py subprocess
 *   5. Persist parser_runs + staging_indicator_values
 *   6. Run validation (staging → approved promotion)
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

const SOURCE_ID = 'imf-weo';
const PARSER_PATH = join(REPO_ROOT, 'scrapers', 'imf_weo', 'parser.py');
const DEFAULT_FIXTURE = join(
  REPO_ROOT,
  'scrapers',
  'imf_weo',
  'tests',
  'fixtures',
  'weo_npl_2026-04.json',
);

const DATAMAPPER_BASE_URL = 'https://www.imf.org/external/datamapper/api/v1';
const WEO_INDICATOR_CODES = [
  'NGDPD',
  'NGDP_RPCH',
  'NGDPDPC',
  'PPPGDP',
  'PCPIPCH',
  'BCA_NGDPD',
  'GGR_NGDP',
  'GGXCNL_NGDP',
  'GGXWDG_NGDP',
  'NGSD_NGDP',
  'NID_NGDP',
  'LUR',
  'LP',
] as const;

type CliArgs = {
  inputPath: string | null;
  download: boolean;
  outputDir: string;
  dryRun: boolean;
  sourceId: string;
  projectionFromYear: number | null;
};

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath: string | null = null;
  let download = false;
  let outputDir = tmpdir();
  let dryRun = false;
  let sourceId = SOURCE_ID;
  let projectionFromYear: number | null = null;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--input') {
      if (!next) throw new Error('--input requires a value');
      inputPath = path.resolve(next);
      i += 1;
    } else if (arg === '--download') {
      download = true;
    } else if (arg === '--output-dir') {
      if (!next) throw new Error('--output-dir requires a value');
      outputDir = path.resolve(next);
      i += 1;
    } else if (arg === '--dry-run') {
      dryRun = true;
    } else if (arg === '--source-id') {
      if (!next) throw new Error('--source-id requires a value');
      sourceId = next;
      i += 1;
    } else if (arg === '--projection-from-year') {
      if (!next) throw new Error('--projection-from-year requires a value');
      const y = Number(next);
      if (!Number.isInteger(y) || y < 1960 || y > 2100) {
        throw new Error(`--projection-from-year must be an integer 1960–2100, got: ${next}`);
      }
      projectionFromYear = y;
      i += 1;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }

  return { inputPath, download, outputDir, dryRun, sourceId, projectionFromYear };
}

function log(msg: string): void {
  process.stdout.write(`[ingest-imf-weo] ${msg}\n`);
}
function logErr(msg: string): void {
  process.stderr.write(`[ingest-imf-weo] ${msg}\n`);
}

type WeoDataPoint = { date: string; value: number | null };

/**
 * Fetch one indicator from the IMF DataMapper API. Response shape:
 *   { "values": { "<code>": { "NPL": { "1980": 1.9, ..., "2031": 62.0 } } } }
 */
async function fetchIndicator(code: string): Promise<WeoDataPoint[]> {
  const url = `${DATAMAPPER_BASE_URL}/${code}/NPL`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`DataMapper ${code}: HTTP ${res.status}`);
  const body = (await res.json()) as unknown;

  if (typeof body !== 'object' || body === null || !('values' in body)) {
    throw new Error(`DataMapper ${code}: missing "values" key`);
  }
  const values = (body as { values: unknown }).values;
  if (typeof values !== 'object' || values === null || !(code in values)) {
    // No data for this code/country — return empty (parser skips nothing).
    return [];
  }
  const byCountry = (values as Record<string, unknown>)[code];
  if (typeof byCountry !== 'object' || byCountry === null || !('NPL' in byCountry)) {
    return [];
  }
  const series = (byCountry as Record<string, unknown>)['NPL'];
  if (typeof series !== 'object' || series === null) return [];

  const points: WeoDataPoint[] = [];
  for (const [year, raw] of Object.entries(series as Record<string, unknown>)) {
    points.push({ date: year, value: typeof raw === 'number' ? raw : null });
  }
  return points;
}

async function downloadCombined(
  outputDir: string,
  projectionFromYear: number | null,
): Promise<string> {
  log(`downloading ${WEO_INDICATOR_CODES.length} indicators from IMF DataMapper …`);
  mkdirSync(outputDir, { recursive: true });

  const indicators: Record<string, WeoDataPoint[]> = {};
  for (const code of WEO_INDICATOR_CODES) {
    log(`  fetching ${code} …`);
    const points = await fetchIndicator(code);
    indicators[code] = points.sort((a, b) => Number(b.date) - Number(a.date));
    log(`    ${points.filter((p) => p.value !== null).length} non-null observations`);
  }

  if (projectionFromYear === null) {
    logErr(
      'WARNING: no --projection-from-year supplied — every value will be stored as ' +
        "observation_type='actual'. WEO forecast years will NOT be marked as projections. " +
        'Re-run with --projection-from-year <YEAR> (the vintage\'s first forecast year).',
    );
  }

  const fetchedAt = new Date().toISOString();
  const combined = {
    fetched_at: fetchedAt,
    country_code: 'NPL',
    vintage: fetchedAt.slice(0, 7),
    projection_from_year: projectionFromYear,
    indicators,
  };
  const fileName = `weo_npl_${fetchedAt.slice(0, 10)}.json`;
  const filePath = join(outputDir, fileName);
  writeFileSync(filePath, JSON.stringify(combined, null, 2), 'utf8');
  log(`saved combined fixture → ${filePath}`);
  return filePath;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  if (!existsSync(PARSER_PATH)) {
    logErr(`parser not found: ${PARSER_PATH}`);
    process.exit(2);
  }

  let resolvedInput: string;
  if (args.download) {
    resolvedInput = await downloadCombined(args.outputDir, args.projectionFromYear);
  } else if (args.inputPath !== null) {
    resolvedInput = args.inputPath;
  } else {
    resolvedInput = DEFAULT_FIXTURE;
    log(`no --input supplied; using default fixture: ${resolvedInput}`);
  }

  if (!existsSync(resolvedInput)) {
    logErr(`input file not found: ${resolvedInput}`);
    process.exit(2);
  }

  log(`input      = ${resolvedInput}`);
  log(`source_id  = ${args.sourceId}`);
  log(`dry_run    = ${args.dryRun}`);
  log(`parser     = ${PARSER_PATH}`);

  if (args.dryRun) {
    log('dry-run mode: spawning parser to verify output shape (no DB writes)');
    const { ParserOutputSchema } = await import('@/lib/ingestion/types');
    const { spawn } = await import('node:child_process');

    const placeholder = '00000000-0000-0000-0000-000000000000';
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');

    await new Promise<void>((resolve, reject) => {
      const child = spawn(python, [PARSER_PATH, resolvedInput, placeholder], { shell: false });
      child.stdout.on('data', (c: Buffer) => stdoutChunks.push(c));
      child.stderr.on('data', (c: Buffer) => stderrChunks.push(c));
      child.on('error', reject);
      child.on('close', (code) => {
        if (code !== 0) {
          const stderr = Buffer.concat(stderrChunks).toString('utf8');
          reject(new Error(`parser exit ${code}: ${stderr.trim() || '<no stderr>'}`));
        } else {
          resolve();
        }
      });
    });

    const stdout = Buffer.concat(stdoutChunks).toString('utf8');
    const parsed = ParserOutputSchema.safeParse(JSON.parse(stdout));
    if (!parsed.success) {
      logErr(`parser output failed schema validation: ${parsed.error.message}`);
      process.exit(1);
    }

    const output = parsed.data;
    const projections = output.staging_rows.filter((r) => r.observation_type === 'projection');
    log(`parser_status        = ${output.status}`);
    log(`staging_rows_count   = ${output.staging_rows.length}`);
    log(`  of which projection= ${projections.length}`);
    log(`parser_errors_count  = ${output.errors.length}`);
    if (output.errors.length > 0) {
      for (const e of output.errors) log(`  ! ${e.error_class}: ${e.error_detail}`);
    }
    log('first 5 staging rows:');
    for (const row of output.staging_rows.slice(0, 5)) {
      log(
        `  ${row.indicator_slug_raw}: ${row.value} ${row.unit} (${row.reporting_period_bs}) [${row.observation_type}]`,
      );
    }
    log('dry-run complete — no DB writes performed');
    return;
  }

  const { ingestSource } = await import('@/lib/ingestion');

  log('starting full pipeline via ingestSource() orchestrator …');

  const result = await ingestSource({
    filePath: resolvedInput,
    sourceId: args.sourceId,
    fileName: basename(resolvedInput),
    contentType: 'application/json',
    parserPath: PARSER_PATH,
    reportingPeriodLabel: 'IMF WEO annual (actuals + projections)',
    parserTimeoutMs: 120_000,
  });

  if (!result.ok) {
    logErr(`ingestSource failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }

  const summary = result.value;
  log('');
  log('=== Ingest Summary ===');
  log(`source_documents.id              = ${summary.sourceDocumentId}`);
  log(`parser_runs.id                   = ${summary.parserRunId}`);
  log(`parser_runs.status               = ${summary.parserStatus}`);
  log(`staging_rows_written             = ${summary.stagingRowsWritten}`);
  log(`validation.promoted              = ${summary.validation.promoted}`);
  log(`validation.promoted_with_warnings= ${summary.validation.promotedWithWarnings}`);
  log(`validation.blocked               = ${summary.validation.blocked}`);

  if (summary.validation.blockingFlags.length > 0) {
    log('');
    log('=== Data Quality Flags (blocking) ===');
    for (const flag of summary.validation.blockingFlags) {
      log(`  staging_row_id=${flag.stagingRowId} flag=${flag.flagType}: ${flag.detail}`);
    }
  }

  log('');
  log('done.');
}

main().catch((e: unknown) => {
  logErr(`uncaught error: ${e instanceof Error ? e.message : String(e)}`);
  process.exit(1);
});
