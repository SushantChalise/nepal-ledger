/**
 * Ingest CLI for the MoF Economic Survey PDF.
 *
 * SOURCE_ID: "mof-economic-survey-annual" (the registered registry id — verified
 * against scripts/seed-source-registry.ts; status 'active', ingestionMode
 * 'reference_only'). Declared in scrapers/mof_economic_survey/parser.py as
 * SOURCE_ID = "mof-economic-survey-annual". NOT "mof-economic-survey".
 *
 * The parser (scrapers/mof_economic_survey/parser.py) scopes to the one cleanly
 * parseable high-value annex table — Annex 6.1 (Number of Workers having Foreign
 * Employment Permit) of the EN 2023/24 edition — and emits three annual
 * single-series indicators (Total/Female/Male, unit `count`). The headline MACRO
 * annex (GDP/prices/fiscal/trade) is RTL-mirrored and the two Nepali editions'
 * annex is CID-broken; both are DEFERRED with typed diagnostics (ADR-0016). So:
 *   - EN 2023/24 → status=partial (Annex-6.1 rows + deferral errors)
 *   - Nepali editions → status=failure (no clean Annex 6.1; documented infeasibility)
 *
 * Output contract mirrors ingest:fcgo-cfs — the parser emits the _common
 * ParserResult / staging_rows shape the orchestrator's ParserOutputSchema reads.
 *
 * Pipeline (live path, via ingestSource() orchestrator):
 *   1. Read the PDF from disk
 *   2. Archive to Supabase Storage (content-addressed; idempotent)
 *   3. Insert source_documents row
 *   4. Spawn scrapers/mof_economic_survey/parser.py subprocess
 *   5. Persist parser_runs + staging_indicator_values (Annex-6.1 rows)
 *   6. Validation job promotes rows once the three slugs are seeded
 *
 * NOTE: the three Annex-6.1 indicator slugs
 * (economic-survey-foreign-employment-permits-{total,female,male}) must be
 * seeded in seed-indicators.ts for rows to promote to approved_indicator_values;
 * Mother adds them at integration (this worker does not edit seed-indicators.ts).
 *
 * Usage:
 *   pnpm ingest:economic-survey --dry-run
 *   pnpm ingest:economic-survey --input "Financial Data/mof_documents/economic_survey/Economic_Survey_2023-24_EN.pdf" --dry-run
 *   pnpm ingest:economic-survey   (live path; archives the doc, persists Annex-6.1 rows)
 *
 * The script must be run from the repo root (where node_modules lives), e.g.:
 *   pnpm ingest:economic-survey --dry-run
 */

import { existsSync } from 'node:fs';
import { basename } from 'node:path';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

// REPO_ROOT is the worktree root — the scrapers and data files the parser
// reads live here (or at the project root for shared data files).
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

// SOURCE_ID from scrapers/mof_economic_survey/parser.py (registered id).
const DEFAULT_SOURCE_ID = 'mof-economic-survey-annual';

// The Economic Survey PDF — default to the English 2023/24 edition (the one
// with a non-CID annex; still RTL-mirrored, hence the documented failure).
// Data files live under the worktree root in `Financial Data/`.
const DEFAULT_INPUT_RELATIVE = path.join(
  'Financial Data',
  'mof_documents',
  'economic_survey',
  'Economic_Survey_2023-24_EN.pdf',
);
const DEFAULT_INPUT = path.join(REPO_ROOT, DEFAULT_INPUT_RELATIVE);

// Parser path — absolute so it resolves regardless of process.cwd().
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'mof_economic_survey', 'parser.py');

type CliArgs = {
  inputPath: string;
  dryRun: boolean;
  sourceId: string;
};

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath = DEFAULT_INPUT;
  let dryRun = false;
  let sourceId = DEFAULT_SOURCE_ID;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--input') {
      if (!next) throw new Error('--input requires a value');
      inputPath = path.resolve(next);
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

  return { inputPath, dryRun, sourceId };
}

function log(msg: string): void {
  process.stdout.write(`[ingest-economic-survey] ${msg}\n`);
}

function logErr(msg: string): void {
  process.stderr.write(`[ingest-economic-survey] ${msg}\n`);
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  log(`input      = ${args.inputPath}`);
  log(`source_id  = ${args.sourceId}`);
  log(`dry_run    = ${args.dryRun}`);
  log(`parser     = ${PARSER_PATH}`);

  if (!existsSync(args.inputPath)) {
    logErr(`input file not found: ${args.inputPath}`);
    process.exit(2);
  }

  if (!existsSync(PARSER_PATH)) {
    logErr(`parser not found: ${PARSER_PATH}`);
    process.exit(2);
  }

  if (args.dryRun) {
    // Dry-run: spawn the parser directly, validate output shape, print summary.
    // No DB writes. Lazy import of ingestSource is skipped entirely so
    // DATABASE_URL is not required.
    log('dry-run mode: spawning parser to verify output shape (no DB writes)');

    const { ParserOutputSchema } = await import('@/lib/ingestion/types');
    const { spawn } = await import('node:child_process');

    const placeholderDocId = '00000000-0000-0000-0000-000000000000';
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');

    await new Promise<void>((resolve, reject) => {
      const child = spawn(python, [PARSER_PATH, args.inputPath, placeholderDocId], {
        cwd: process.cwd(),
        shell: false,
      });
      child.stdout.on('data', (c: Buffer) => stdoutChunks.push(c));
      child.stderr.on('data', (c: Buffer) => stderrChunks.push(c));
      child.on('error', reject);
      child.on('close', (code) => {
        if (code !== 0) {
          const stderr = Buffer.concat(stderrChunks).toString('utf8');
          reject(new Error(`parser exit ${code}: ${stderr.trim() || '<no stderr>'}`));
          return;
        }
        resolve();
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
      log('typed errors (deferred breakage modes — ADR-0016):');
      for (const e of output.errors) {
        log(`  ! ${e.error_class}: ${e.error_detail}`);
      }
    }

    if (output.status === 'failure' && output.staging_rows.length === 0) {
      log('');
      log(
        'NOTE: this edition has no clean Annex 6.1 (its annex is CID-broken — the ' +
          'Nepali editions). The headline macro annex is RTL-mirrored. Zero rows is ' +
          'a documented infeasibility for this edition (ADR-0016), not a bug. Use the ' +
          'EN 2023/24 edition for the Annex-6.1 foreign-employment series.',
      );
    }

    const bySlug = new Map<string, number>();
    for (const row of output.staging_rows)
      bySlug.set(row.indicator_slug_raw, (bySlug.get(row.indicator_slug_raw) ?? 0) + 1);
    log('staging rows by slug:');
    for (const [slug, n] of bySlug) log(`  ${slug.padEnd(48)} ${n}`);

    log('first staging rows:');
    for (const row of output.staging_rows.slice(0, 6)) {
      log(
        `  ${row.indicator_slug_raw}: ${row.value} ${row.unit} ` +
          `(${row.reporting_period_type}, ${row.reporting_period_bs})`,
      );
    }

    log('dry-run complete — no DB writes performed');
    return;
  }

  // Live path: use the full ingestSource() orchestrator. For the EN edition the
  // parser returns status=partial with the Annex-6.1 staging rows (the macro
  // annex / CID pages are deferred as typed errors); rows promote once the three
  // slugs are seeded. For the Nepali editions it returns status=failure with no
  // rows (documented infeasibility). Lazy import so --dry-run does not require
  // DATABASE_URL / Supabase creds.
  const { ingestSource } = await import('@/lib/ingestion');

  log('starting full pipeline via ingestSource() orchestrator ...');
  log(
    'note: status=partial is expected for the EN edition (Annex-6.1 rows + ' +
      'deferred macro/CID pages); the Nepali editions yield status=failure ' +
      '(no clean Annex 6.1). See ADR-0016.',
  );

  const result = await ingestSource({
    filePath: args.inputPath,
    sourceId: args.sourceId,
    fileName: basename(args.inputPath),
    contentType: 'application/pdf',
    parserPath: PARSER_PATH,
    // reportingPeriodLabel intentionally omitted (optional): Annex 6.1 spans many
    // fiscal years, so there is no single label; the parser sets per-row periods.
    parserTimeoutMs: 300_000,
  });

  if (!result.ok) {
    logErr(`ingestSource failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }

  const summary = result.value;

  log('');
  log('=== Ingest Summary ===');
  log(`source_documents.id  = ${summary.sourceDocumentId}`);
  log(`parser_runs.id       = ${summary.parserRunId}`);
  log(`parser_runs.status   = ${summary.parserStatus}`);
  log(`staging_rows_written = ${summary.stagingRowsWritten}`);
  log(`validation.promoted  = ${summary.validation.promoted}`);
  log(`validation.blocked   = ${summary.validation.blocked}`);
  log('');
  log(
    'done. If promoted=0 but staging_rows>0, the three ' +
      'economic-survey-foreign-employment-permits-* slugs are not yet seeded ' +
      '(seed-indicators.ts — pending Mother). See ADR-0016 / the source profile.',
  );
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  logErr(`uncaught error: ${msg}`);
  process.exit(1);
});
