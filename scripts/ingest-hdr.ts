/**
 * Ingest CLI for UNDP HDR Composite Indices (Nepal) — source_id: "hdr-composite".
 *
 * Unlike the JSON sources, the HDR parser reads the UNDP "complete time series"
 * CSV DIRECTLY (one wide row per country). This CLI just fetches that CSV to
 * disk and hands the path to the parser; no assembly step.
 *
 *   --input <path>   Use a local CSV (fixture or a prior --download output).
 *   --download       Fetch the HDR 2025 CSV to --output-dir, then ingest.
 *
 * Both modes support --dry-run (no DB writes; parser output printed).
 * Default --input: the checked-in fixture used by parser tests.
 *
 * Usage:
 *   pnpm ingest:hdr --dry-run
 *   pnpm ingest:hdr --download
 *   pnpm ingest:hdr --download --output-dir /tmp/hdr
 *   pnpm ingest:hdr --input /path/to/HDR25_Composite_indices_complete_time_series.csv
 *
 * Note: the CSV is Latin-1 (cp1252) encoded — the parser handles that; this CLI
 * streams the bytes verbatim and never re-encodes them.
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

const SOURCE_ID = 'hdr-composite';
const PARSER_PATH = join(REPO_ROOT, 'scrapers', 'hdr_composite', 'parser.py');
const DEFAULT_FIXTURE = join(
  REPO_ROOT,
  'scrapers',
  'hdr_composite',
  'tests',
  'fixtures',
  'hdr_composite_npl.csv',
);

const HDR_CSV_URL =
  'https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv';
const MAX_RETRIES = 3;

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
  process.stdout.write(`[ingest-hdr] ${msg}\n`);
}
function logErr(msg: string): void {
  process.stderr.write(`[ingest-hdr] ${msg}\n`);
}

async function downloadCsv(outputDir: string): Promise<string> {
  log(`downloading HDR composite-indices CSV …`);
  mkdirSync(outputDir, { recursive: true });

  let lastErr = '';
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt += 1) {
    try {
      const res = await fetch(HDR_CSV_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Latin-1 bytes — preserve verbatim, do NOT decode as UTF-8.
      const bytes = Buffer.from(await res.arrayBuffer());
      if (bytes.length < 1000) throw new Error(`suspiciously small (${bytes.length} bytes)`);
      const fileName = `HDR25_Composite_indices_${new Date().toISOString().slice(0, 10)}.csv`;
      const filePath = join(outputDir, fileName);
      writeFileSync(filePath, bytes);
      log(`saved ${bytes.length} bytes → ${filePath}`);
      return filePath;
    } catch (e) {
      lastErr = e instanceof Error ? e.message : String(e);
      log(`  retry ${attempt}/${MAX_RETRIES}: ${lastErr}`);
    }
  }
  throw new Error(`HDR CSV download failed after ${MAX_RETRIES} attempts: ${lastErr}`);
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  if (!existsSync(PARSER_PATH)) {
    logErr(`parser not found: ${PARSER_PATH}`);
    process.exit(2);
  }

  let resolvedInput: string;
  if (args.download) {
    resolvedInput = await downloadCsv(args.outputDir);
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
    const slugs = new Set(output.staging_rows.map((r) => r.indicator_slug_raw));
    log(`parser_status        = ${output.status}`);
    log(`staging_rows_count   = ${output.staging_rows.length}`);
    log(`distinct_indicators  = ${slugs.size}`);
    log(`parser_errors_count  = ${output.errors.length}`);
    for (const e of output.errors) log(`  ! ${e.error_class}: ${e.error_detail}`);
    log('first 5 staging rows:');
    for (const row of output.staging_rows.slice(0, 5)) {
      log(`  ${row.indicator_slug_raw}: ${row.value} ${row.unit} (${row.reporting_period_bs})`);
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
    contentType: 'text/csv',
    parserPath: PARSER_PATH,
    reportingPeriodLabel: 'UNDP HDR composite indices (1990–latest)',
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
