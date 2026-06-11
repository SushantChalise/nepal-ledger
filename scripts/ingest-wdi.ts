/**
 * Ingest CLI for World Bank WDI (Nepal) — source_id: "wb-wdi".
 *
 * The WDI parser reads a combined JSON blob (one file, 15 indicator time-series).
 * This CLI has two modes:
 *
 *   --input <path>   Use a pre-assembled combined JSON file (e.g. a fixture or a
 *                    file produced by a previous --download run).
 *   --download       Fetch all 15 indicator codes from the WB API, assemble the
 *                    combined JSON, write to a temp file, then hand off to the
 *                    parser. The assembled file is kept at --output-dir (default:
 *                    system temp) so it can be inspected / re-ingested.
 *
 * Both modes support --dry-run (no DB writes; parser output printed to stdout).
 *
 * Default --input: the checked-in fixture used by parser tests.
 *
 * Usage:
 *   pnpm ingest:wdi --dry-run                               # validate fixture
 *   pnpm ingest:wdi --input /path/to/combined.json          # live ingest from file
 *   pnpm ingest:wdi --download                              # live: fetch + ingest
 *   pnpm ingest:wdi --download --output-dir /tmp/wdi        # save fetched file here
 *
 * Pipeline (ingestSource orchestrator):
 *   1. Read / download → combined JSON file on disk
 *   2. Archive to Supabase Storage (content-addressed; idempotent)
 *   3. Insert source_documents row
 *   4. Spawn scrapers/wb_wdi/parser.py subprocess
 *   5. Persist parser_runs + staging_indicator_values
 *   6. Run validation (staging → approved promotion)
 *   7. Run WDI-vs-DNE cross-source divergence check (warnings only)
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

const SOURCE_ID = 'wb-wdi';
const PARSER_PATH = join(REPO_ROOT, 'scrapers', 'wb_wdi', 'parser.py');
const DEFAULT_FIXTURE = join(
  REPO_ROOT,
  'scrapers',
  'wb_wdi',
  'tests',
  'fixtures',
  'wdi_npl_2024.json',
);

const WB_BASE_URL = 'https://api.worldbank.org/v2/country/NPL/indicator';
const WB_INDICATOR_CODES = [
  'NY.GDP.MKTP.CD',
  'NY.GDP.MKTP.KD',
  'NY.GDP.MKTP.KD.ZG',
  'NY.GDP.PCAP.CD',
  'NY.GDP.PCAP.KD.ZG',
  'FP.CPI.TOTL.ZG',
  'BX.TRF.PWKR.CD.DT',
  'BX.TRF.PWKR.DT.GD.ZS',
  'NY.GNP.MKTP.CD',
  'NY.GNP.PCAP.CD',
  'SI.POV.NAHC',
  'SI.POV.GINI',
  'NE.GDI.TOTL.ZS',
  'GC.DOD.TOTL.GD.ZS',
  'BN.CAB.XOKA.GD.ZS',
] as const;

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
  process.stdout.write(`[ingest-wdi] ${msg}\n`);
}
function logErr(msg: string): void {
  process.stderr.write(`[ingest-wdi] ${msg}\n`);
}

type WbDataPoint = { date: string; value: number | null };

async function fetchIndicator(code: string): Promise<WbDataPoint[]> {
  const url = `${WB_BASE_URL}/${code}?format=json&per_page=100&mrv=60`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`WB API ${code}: HTTP ${res.status}`);
  const body = (await res.json()) as unknown;
  if (!Array.isArray(body) || body.length < 2 || !Array.isArray(body[1])) {
    throw new Error(`WB API ${code}: unexpected response shape`);
  }
  const points: WbDataPoint[] = [];
  for (const dp of body[1] as unknown[]) {
    if (
      typeof dp === 'object' &&
      dp !== null &&
      'date' in dp &&
      'value' in dp
    ) {
      const d = dp as { date: unknown; value: unknown };
      points.push({
        date: String(d.date),
        value: typeof d.value === 'number' ? d.value : null,
      });
    }
  }
  return points;
}

async function downloadCombined(outputDir: string): Promise<string> {
  log(`downloading ${WB_INDICATOR_CODES.length} indicators from World Bank API …`);
  mkdirSync(outputDir, { recursive: true });

  const indicators: Record<string, WbDataPoint[]> = {};
  for (const code of WB_INDICATOR_CODES) {
    log(`  fetching ${code} …`);
    const points = await fetchIndicator(code);
    indicators[code] = points.sort((a, b) => Number(b.date) - Number(a.date));
    log(`    ${points.filter((p) => p.value !== null).length} non-null observations`);
  }

  const fetchedAt = new Date().toISOString();
  const combined = { fetched_at: fetchedAt, country_code: 'NPL', indicators };
  const fileName = `wdi_npl_${fetchedAt.slice(0, 10)}.json`;
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

  // Resolve the input file: download, override, or default fixture.
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
    log(`parser_status       = ${output.status}`);
    log(`staging_rows_count  = ${output.staging_rows.length}`);
    log(`parser_errors_count = ${output.errors.length}`);
    if (output.errors.length > 0) {
      for (const e of output.errors) log(`  ! ${e.error_class}: ${e.error_detail}`);
    }
    log('first 5 staging rows:');
    for (const row of output.staging_rows.slice(0, 5)) {
      log(
        `  ${row.indicator_slug_raw}: ${row.value} ${row.unit} (${row.reporting_period_bs})`,
      );
    }
    log('dry-run complete — no DB writes performed');
    return;
  }

  // Live path.
  const { ingestSource } = await import('@/lib/ingestion');

  log('starting full pipeline via ingestSource() orchestrator …');

  const result = await ingestSource({
    filePath: resolvedInput,
    sourceId: args.sourceId,
    fileName: basename(resolvedInput),
    contentType: 'application/json',
    parserPath: PARSER_PATH,
    reportingPeriodLabel: 'WDI annual (multi-year)',
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

  // Cross-source divergence check (WDI vs DNE — non-blocking, warning only).
  const { checkWdiDneDivergence } = await import('@/lib/validation/benchmark');
  log('');
  log('=== WDI-vs-DNE Divergence Check ===');
  const divergences = await checkWdiDneDivergence();
  if (!divergences.ok) {
    log(`  divergence check failed: ${JSON.stringify(divergences.error)} (non-fatal)`);
  } else if (divergences.value.length === 0) {
    log('  all comparable pairs within tolerance ✓');
  } else {
    for (const d of divergences.value) {
      log(`  ${d.wdiSlug} vs ${d.dneSlug} (${d.fiscalYearBs}): divergence ${d.pct.toFixed(1)}% — ${d.detail}`);
    }
  }

  log('');
  log('done.');
}

main().catch((e: unknown) => {
  logErr(`uncaught error: ${e instanceof Error ? e.message : String(e)}`);
  process.exit(1);
});
