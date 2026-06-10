/**
 * Ingest CLI for the NRB Database on Nepalese Economy (DNE) XLSX.
 *
 * SOURCE_ID: "nrb-dne-xlsx" (declared in scrapers/nrb_dne/parser.py
 * as SOURCE_ID = "nrb-dne-xlsx").
 *
 * NOTE — Source Registry reconciliation required before a live run:
 *   The parser's SOURCE_ID is "nrb-dne-xlsx", but the current source_registry
 *   rows use the pattern "nrb-db-<sector>" (e.g. "nrb-db-external-sector").
 *   Mother must decide before a live ingest whether to:
 *     (a) Register "nrb-dne-xlsx" as a single umbrella source covering all
 *         DNE XLSX files, OR
 *     (b) Map individual DNE XLSX downloads to specific "nrb-db-<sector>" ids
 *         and pass the matching --source-id on the CLI per-file.
 *   Until that FK exists in source_registry, any live run will fail the
 *   source_documents FK constraint. Dry-run is safe (no DB writes).
 *
 * Pipeline (via ingestSource() orchestrator):
 *   1. Read the XLSX from disk
 *   2. Archive to Supabase Storage (content-addressed; idempotent)
 *   3. Insert source_documents row
 *   4. Spawn scrapers/nrb_dne/parser.py subprocess
 *   5. Persist parser_runs + staging_indicator_values
 *   6. Run validation job (staging → approved promotion)
 *
 * Usage:
 *   pnpm ingest:dne --dry-run --input "scrapers/nrb_dne/tests/fixtures/happy_path.xlsx"
 *   pnpm ingest:dne --input "/path/to/real/DNE.xlsx"
 *   pnpm ingest:dne --input "/path/to/real/DNE.xlsx" --source-id nrb-db-external-sector
 *
 * The script must be run from the repo root (where node_modules lives):
 *   cd /path/to/Economy && node_modules/.bin/tsx .claude/worktrees/.../scripts/ingest-dne.ts
 * OR via the worktree package.json script (pnpm resolves tsx from the root):
 *   pnpm ingest:dne
 */

import { existsSync } from 'node:fs';
import { basename } from 'node:path';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

// REPO_ROOT is the worktree root — the scrapers and fixture files live here.
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

// SOURCE_ID from scrapers/nrb_dne/parser.py: SOURCE_ID = "nrb-dne-xlsx"
const DEFAULT_SOURCE_ID = 'nrb-dne-xlsx';

// Default input: real NRB DNE External Sector — Foreign Exchange Reserves
// (downloaded 2026-06-07 from https://nrb.org.np/contents/uploads/2026/01/Foreign-exchange-reserves.xlsx).
// This file uses AD-year column headers (2001–2025 AD), which the parser
// correctly classifies as PeriodUnparseable. A BS-year file (e.g. one from
// the Fiscal or Financial sector that uses BS FY headers) would produce rows.
// Override with --input to point at a different DNE XLSX.
const DEFAULT_INPUT = path.join(
  REPO_ROOT,
  'Financial Data',
  'nrb_dne',
  'Foreign-exchange-reserves.xlsx',
);

// Parser path — absolute so it resolves regardless of process.cwd().
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'nrb_dne', 'parser.py');

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
  process.stdout.write(`[ingest-dne] ${msg}\n`);
}

function logErr(msg: string): void {
  process.stderr.write(`[ingest-dne] ${msg}\n`);
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

    // Lazy import to confirm types without the server-only import chain.
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
      for (const e of output.errors) {
        log(`  ! ${e.error_class}: ${e.error_detail}`);
      }
    }

    log('first 3 staging rows:');
    for (const row of output.staging_rows.slice(0, 3)) {
      log(
        `  ${row.indicator_slug_raw}: ${row.value} ${row.unit} ` +
          `(${row.reporting_period_type}, ${row.reporting_period_bs})`,
      );
    }

    log('dry-run complete — no DB writes performed');
    return;
  }

  // Live path: use the full ingestSource() orchestrator.
  // Lazy import so --dry-run does not require DATABASE_URL / Supabase creds.
  //
  // IMPORTANT: before running a live ingest, Mother must register the source_id
  // in source_registry. See the NOTE at the top of this file.
  const { ingestSource } = await import('@/lib/ingestion');

  log('starting full pipeline via ingestSource() orchestrator ...');

  const result = await ingestSource({
    filePath: args.inputPath,
    sourceId: args.sourceId,
    fileName: basename(args.inputPath),
    contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    parserPath: PARSER_PATH,
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

  const approvedTotal = summary.validation.promoted + summary.validation.promotedWithWarnings;
  log(`approved_indicator_values total  = ${approvedTotal}`);

  if (summary.validation.blockingFlags.length > 0) {
    log('');
    log('=== Data Quality Flags (blocking) ===');
    for (const flag of summary.validation.blockingFlags) {
      log(`  staging_row_id=${flag.stagingRowId}`);
      log(`    flag_type=${flag.flagType}`);
      log(`    detail=${flag.detail}`);
    }
  }

  // Query the approved rows for this source document and print the first 5.
  // Direct DB query via the Drizzle client, matching the pattern in
  // ingest-cmefs.ts (sanctioned for scripts).
  if (approvedTotal > 0) {
    log('');
    log('=== First 5 Approved Rows (sanity check) ===');

    const { db } = await import('@/lib/db/client');
    const { approvedIndicatorValues } = await import('@/lib/db/schema/indicator-values');
    const { eq, desc } = await import('drizzle-orm');

    const rows = await db()
      .select()
      .from(approvedIndicatorValues)
      .where(eq(approvedIndicatorValues.sourceDocumentId, summary.sourceDocumentId))
      .orderBy(desc(approvedIndicatorValues.promotedAt))
      .limit(5);

    for (const row of rows) {
      log(
        `  id=${row.id}` +
          ` indicator_id=${row.indicatorId}` +
          ` value=${row.value} ${row.unit}` +
          ` period=${row.reportingPeriodBs} (${row.reportingPeriodType})` +
          ` grade=${row.confidenceGrade}`,
      );
    }
  } else {
    log('');
    log('No rows promoted to approved_indicator_values (all blocked or zero staging rows).');
    log('Check blockingFlags above for data_quality_flag details.');
    log('This may indicate that the indicator slugs are not yet seeded in the indicators table.');
  }

  log('');
  log('done.');
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  logErr(`uncaught error: ${msg}`);
  process.exit(1);
});
