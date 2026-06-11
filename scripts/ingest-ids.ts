/**
 * Ingest CLI for World Bank International Debt Statistics (Nepal)
 * — source_id: "wb-ids".
 *
 * IDS exposes debt by creditor via the counterpart-area route:
 *   api.worldbank.org/v2/sources/6/country/NPL/series/<CODE>/counterpart-area/all/time/all
 * (the standard /indicator/?source=6 route 404s for IDS series).
 *
 * This CLI fetches 6 series, extracts the World aggregate + the named creditors
 * (Japan/India/China/Korea bilateral; World-Bank-IDA/ADB multilateral) into
 * pre-resolved `ids-*` slugs, and writes the parser's combined JSON. The parser
 * (scrapers/wb_ids/parser.py) applies units + the period contract.
 *
 *   --input <path>   Use a pre-assembled combined JSON file.
 *   --download       Fetch from the IDS API, assemble, write to --output-dir.
 *
 * Both modes support --dry-run (no DB writes). Default --input: the test fixture.
 *
 * Usage:
 *   pnpm ingest:ids --dry-run
 *   pnpm ingest:ids --download
 *   pnpm ingest:ids --input /path/to/combined.json
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

const SOURCE_ID = 'wb-ids';
const PARSER_PATH = join(REPO_ROOT, 'scrapers', 'wb_ids', 'parser.py');
const DEFAULT_FIXTURE = join(REPO_ROOT, 'scrapers', 'wb_ids', 'tests', 'fixtures', 'ids_npl_2026.json');

const IDS_BASE = 'https://api.worldbank.org/v2/sources/6/country/NPL/series';
const WORLD = 'WLD';
const MAX_RETRIES = 4;
const PER_PAGE = 20000;

// slug → (IDS series code, counterpart-area id). WLD = aggregate.
const IDS_SERIES: ReadonlyArray<{ slug: string; code: string; cp: string }> = [
  { slug: 'ids-external-debt-total-usd', code: 'DT.DOD.DECT.CD', cp: WORLD },
  { slug: 'ids-external-debt-pct-gni', code: 'DT.DOD.DECT.GN.ZS', cp: WORLD },
  { slug: 'ids-debt-service-total-usd', code: 'DT.TDS.DECT.CD', cp: WORLD },
  { slug: 'ids-short-term-debt-usd', code: 'DT.DOD.DSTC.CD', cp: WORLD },
  { slug: 'ids-ppg-bilateral-total-usd', code: 'DT.DOD.BLAT.CD', cp: WORLD },
  { slug: 'ids-debt-bilateral-japan-usd', code: 'DT.DOD.BLAT.CD', cp: '701' },
  { slug: 'ids-debt-bilateral-india-usd', code: 'DT.DOD.BLAT.CD', cp: '646' },
  { slug: 'ids-debt-bilateral-china-usd', code: 'DT.DOD.BLAT.CD', cp: '730' },
  { slug: 'ids-debt-bilateral-korea-usd', code: 'DT.DOD.BLAT.CD', cp: '742' },
  { slug: 'ids-ppg-multilateral-total-usd', code: 'DT.DOD.MLAT.CD', cp: WORLD },
  { slug: 'ids-debt-multilateral-worldbank-ida-usd', code: 'DT.DOD.MLAT.CD', cp: '905' },
  { slug: 'ids-debt-multilateral-adb-usd', code: 'DT.DOD.MLAT.CD', cp: '915' },
];

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
  process.stdout.write(`[ingest-ids] ${msg}\n`);
}
function logErr(msg: string): void {
  process.stderr.write(`[ingest-ids] ${msg}\n`);
}

type DataPoint = { date: string; value: number | null };

/** Concept extractor for an IDS row's `variable` array. */
function conceptId(variable: unknown, concept: string): string | null {
  if (!Array.isArray(variable)) return null;
  for (const v of variable) {
    if (
      typeof v === 'object' &&
      v !== null &&
      (v as { concept?: unknown }).concept === concept &&
      typeof (v as { id?: unknown }).id === 'string'
    ) {
      return (v as { id: string }).id;
    }
  }
  return null;
}

/**
 * Fetch one IDS series across all counterparts/years, returning
 * counterpartId → (year → value). Handles pagination + transient failures.
 */
async function fetchIdsSeries(code: string): Promise<Map<string, Map<string, number>>> {
  const out = new Map<string, Map<string, number>>();
  let page = 1;
  let pages = 1;

  do {
    const url = `${IDS_BASE}/${code}/counterpart-area/all/time/all?format=json&per_page=${PER_PAGE}&page=${page}`;
    let ok = false;
    for (let attempt = 1; attempt <= MAX_RETRIES && !ok; attempt += 1) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as unknown;
        if (typeof body !== 'object' || body === null || !('source' in body)) {
          throw new Error('missing "source" key (IDS error response?)');
        }
        const src = (body as { source: unknown }).source;
        const data = (src as { data?: unknown })?.data;
        if (!Array.isArray(data)) throw new Error('source.data is not an array');
        pages = Number((body as { pages?: unknown }).pages ?? 1) || 1;

        for (const row of data as Array<{ variable?: unknown; value?: unknown }>) {
          if (typeof row.value !== 'number') continue;
          const cp = conceptId(row.variable, 'Counterpart-Area');
          const time = conceptId(row.variable, 'Time');
          if (cp === null || time === null) continue;
          const year = time.replace(/^YR/, '');
          if (!out.has(cp)) out.set(cp, new Map());
          out.get(cp)!.set(year, row.value);
        }
        ok = true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        log(`  retry ${attempt}/${MAX_RETRIES} (${code} p${page}): ${msg}`);
        if (attempt === MAX_RETRIES) throw new Error(`IDS ${code} page ${page} failed: ${msg}`);
      }
    }
    page += 1;
  } while (page <= pages);

  return out;
}

async function downloadCombined(outputDir: string): Promise<string> {
  log('downloading IDS Nepal — 6 debt series across creditors …');
  mkdirSync(outputDir, { recursive: true });

  const codes = [...new Set(IDS_SERIES.map((s) => s.code))];
  const byCode = new Map<string, Map<string, Map<string, number>>>();
  for (const code of codes) {
    log(`  fetching ${code} …`);
    byCode.set(code, await fetchIdsSeries(code));
  }

  const series: Record<string, DataPoint[]> = {};
  for (const { slug, code, cp } of IDS_SERIES) {
    const yearMap = byCode.get(code)?.get(cp);
    const points: DataPoint[] = yearMap
      ? [...yearMap.entries()]
          .map(([date, value]) => ({ date, value }))
          .sort((a, b) => Number(b.date) - Number(a.date))
      : [];
    series[slug] = points;
    log(`    ${slug}: ${points.length} years`);
  }

  const fetchedAt = new Date().toISOString();
  const combined = { fetched_at: fetchedAt, country_code: 'NPL', series };
  const fileName = `ids_npl_${fetchedAt.slice(0, 10)}.json`;
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
    log(`parser_status        = ${output.status}`);
    log(`staging_rows_count   = ${output.staging_rows.length}`);
    log(`distinct_indicators  = ${new Set(output.staging_rows.map((r) => r.indicator_slug_raw)).size}`);
    log(`parser_errors_count  = ${output.errors.length}`);
    for (const e of output.errors) log(`  ! ${e.error_class}: ${e.error_detail}`);
    log('latest-year creditor stocks (usd_million):');
    for (const row of output.staging_rows.filter((r) => r.indicator_slug_raw.includes('bilateral-') || r.indicator_slug_raw.includes('multilateral-')).slice(0, 8)) {
      log(`  ${row.indicator_slug_raw}: ${row.value} (${row.reporting_period_bs})`);
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
    reportingPeriodLabel: 'WB IDS external debt by creditor (annual)',
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
