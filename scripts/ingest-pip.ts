/**
 * Ingest CLI for World Bank PIP (Poverty and Inequality Platform, Nepal)
 * — source_id: "wb-pip".
 *
 * PIP exposes one record per (country, year, poverty-line, reporting-level).
 * This CLI assembles the parser's combined JSON from four queries:
 *
 *   - survey anchors at $2.15 / $3.65 / $6.85 (no fill_gaps) → the 5 actual
 *     Nepal survey rounds, merged by reporting_year (headcount per line, plus
 *     line-independent gini / mean / median / deciles from the $3.65 query);
 *   - the $3.65 headcount filled across all years (fill_gaps=true) → the
 *     modelled poverty trend for NON-anchor years.
 *
 * The parser (scrapers/wb_pip/parser.py) does the rest deterministically.
 *
 *   --input <path>   Use a pre-assembled combined JSON file (fixture or a prior
 *                    --download output).
 *   --download       Fetch the four PIP queries, assemble, write to --output-dir.
 *
 * Both modes support --dry-run (no DB writes; parser output printed).
 * Default --input: the checked-in fixture used by parser tests.
 *
 * Usage:
 *   pnpm ingest:pip --dry-run
 *   pnpm ingest:pip --download
 *   pnpm ingest:pip --download --output-dir /tmp/pip
 *   pnpm ingest:pip --input /path/to/combined.json
 *
 * PIP API note: the endpoint is intermittently flaky (transient empty / 000
 * responses). Each query retries a few times before failing.
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

const SOURCE_ID = 'wb-pip';
const PARSER_PATH = join(REPO_ROOT, 'scrapers', 'wb_pip', 'parser.py');
const DEFAULT_FIXTURE = join(REPO_ROOT, 'scrapers', 'wb_pip', 'tests', 'fixtures', 'pip_npl_2026.json');

const PIP_BASE_URL = 'https://api.worldbank.org/pip/v1/pip';
const POVERTY_LINES = { '215': 2.15, '365': 3.65, '685': 6.85 } as const;
const REPORTING_LEVEL = 'national';
const MAX_RETRIES = 4;

type CliArgs = {
  inputPath: string | null;
  download: boolean;
  outputDir: string;
  dryRun: boolean;
  sourceId: string;
};

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath: string | null = null;
  let download = false;
  let outputDir = tmpdir();
  let dryRun = false;
  let sourceId = SOURCE_ID;

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
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return { inputPath, download, outputDir, dryRun, sourceId };
}

function log(msg: string): void {
  process.stdout.write(`[ingest-pip] ${msg}\n`);
}
function logErr(msg: string): void {
  process.stderr.write(`[ingest-pip] ${msg}\n`);
}

/** One raw PIP record — only the fields the parser's combined JSON needs. */
type PipRecord = {
  reporting_year: number;
  reporting_level: string;
  survey_year: number | null;
  survey_acronym: string | null;
  welfare_type: string | null;
  headcount: number | null;
  poverty_gap: number | null;
  poverty_severity: number | null;
  gini: number | null;
  mean: number | null;
  median: number | null;
  decile1: number | null;
  decile10: number | null;
  estimation_type: string | null;
  estimate_type: string | null;
};

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}
function str(v: unknown): string | null {
  return typeof v === 'string' ? v : null;
}

async function fetchPip(povline: number, fillGaps: boolean): Promise<PipRecord[]> {
  const url =
    `${PIP_BASE_URL}?country=NPL&povline=${povline}&format=json` +
    (fillGaps ? '&fill_gaps=true' : '');

  let lastErr = '';
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt += 1) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = (await res.json()) as unknown;
      if (!Array.isArray(body)) throw new Error('response is not an array');
      const out: PipRecord[] = [];
      for (const r of body as Record<string, unknown>[]) {
        if (str(r['reporting_level']) !== REPORTING_LEVEL) continue;
        const year = num(r['reporting_year']);
        if (year === null) continue;
        out.push({
          reporting_year: year,
          reporting_level: REPORTING_LEVEL,
          survey_year: num(r['survey_year']),
          survey_acronym: str(r['survey_acronym']),
          welfare_type: str(r['welfare_type']),
          headcount: num(r['headcount']),
          poverty_gap: num(r['poverty_gap']),
          poverty_severity: num(r['poverty_severity']),
          gini: num(r['gini']),
          mean: num(r['mean']),
          median: num(r['median']),
          decile1: num(r['decile1']),
          decile10: num(r['decile10']),
          estimation_type: str(r['estimation_type']),
          estimate_type: str(r['estimate_type']),
        });
      }
      if (out.length === 0) throw new Error('no national rows returned');
      return out;
    } catch (e) {
      lastErr = e instanceof Error ? e.message : String(e);
      log(`  retry ${attempt}/${MAX_RETRIES} (povline=${povline} fill_gaps=${fillGaps}): ${lastErr}`);
    }
  }
  throw new Error(`PIP query failed after ${MAX_RETRIES} attempts (povline=${povline}): ${lastErr}`);
}

type AnchorRecord = {
  reporting_year: number;
  survey_year: number | null;
  survey_acronym: string | null;
  welfare_type: string | null;
  headcount_215: number | null;
  headcount_365: number | null;
  headcount_685: number | null;
  poverty_gap_365: number | null;
  poverty_severity_365: number | null;
  gini: number | null;
  mean: number | null;
  median: number | null;
  decile1: number | null;
  decile10: number | null;
};

async function downloadCombined(outputDir: string): Promise<string> {
  log('downloading PIP Nepal — 3 survey-anchor lines + $3.65 filled series …');
  mkdirSync(outputDir, { recursive: true });

  const a365 = await fetchPip(POVERTY_LINES['365'], false);
  const a215 = await fetchPip(POVERTY_LINES['215'], false);
  const a685 = await fetchPip(POVERTY_LINES['685'], false);
  const series = await fetchPip(POVERTY_LINES['365'], true);

  const hc215 = new Map(a215.map((r) => [r.reporting_year, r.headcount]));
  const hc685 = new Map(a685.map((r) => [r.reporting_year, r.headcount]));

  const anchors: AnchorRecord[] = a365.map((r) => ({
    reporting_year: r.reporting_year,
    survey_year: r.survey_year,
    survey_acronym: r.survey_acronym,
    welfare_type: r.welfare_type,
    headcount_215: hc215.get(r.reporting_year) ?? null,
    headcount_365: r.headcount,
    headcount_685: hc685.get(r.reporting_year) ?? null,
    poverty_gap_365: r.poverty_gap,
    poverty_severity_365: r.poverty_severity,
    gini: r.gini,
    mean: r.mean,
    median: r.median,
    decile1: r.decile1,
    decile10: r.decile10,
  }));

  const series_365 = series.map((r) => ({
    reporting_year: r.reporting_year,
    headcount: r.headcount,
    estimation_type: r.estimation_type,
    estimate_type: r.estimate_type,
  }));

  log(`  ${anchors.length} survey anchors, ${series_365.length} filled-series years`);

  const fetchedAt = new Date().toISOString();
  const combined = {
    fetched_at: fetchedAt,
    country_code: 'NPL',
    reporting_level: REPORTING_LEVEL,
    anchors,
    series_365,
  };
  const fileName = `pip_npl_${fetchedAt.slice(0, 10)}.json`;
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
    resolvedInput = await downloadCombined(args.outputDir);
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
    const byType = new Map<string, number>();
    for (const r of output.staging_rows) {
      byType.set(r.observation_type, (byType.get(r.observation_type) ?? 0) + 1);
    }
    log(`parser_status        = ${output.status}`);
    log(`staging_rows_count   = ${output.staging_rows.length}`);
    log(`  by observation_type= ${[...byType].map(([k, v]) => `${k}:${v}`).join(', ')}`);
    log(`parser_errors_count  = ${output.errors.length}`);
    for (const e of output.errors) log(`  ! ${e.error_class}: ${e.error_detail}`);
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
    reportingPeriodLabel: 'WB PIP poverty (survey anchors + filled series)',
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
