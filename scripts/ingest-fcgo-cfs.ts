/**
 * Ingest CLI for the FCGO Consolidated Financial Statements PDF.
 *
 * SOURCE_ID: "fcgo-consolidated-financial-statements" (declared in
 * scrapers/fcgo_consolidated/parser.py as
 * SOURCE_ID = "fcgo-consolidated-financial-statements"). The parser is a
 * deterministic pymupdf narrative-prose parser: it scans all pages of the
 * CFS, anchors on the clean forward-text Executive Summary / Treasury-Position
 * prose, and lifts 9 indicators (7 extracted + 2 derived: total
 * revenue/expenditure, recurrent/capital/financing expenditure, provincial &
 * local expenditure, federal expenditure, fiscal balance). All values are
 * npr_million; reporting_period_type is annual; fiscal year is BS 2079/80
 * (AD 2022/23) for the bundled FY 2022/23 publication.
 *
 * The parser (v1.0.0) auto-detects the fiscal year from "FY YYYY/YY" in the
 * Executive Summary prose, so no --period flag is needed — the correct BS
 * period is stamped on every staging row regardless of which edition PDF is
 * provided (FY 2018/19 through FY 2023/24 all work).
 *
 * Pipeline (via ingestSource() orchestrator):
 *   1. Read the PDF from disk
 *   2. Archive to Supabase Storage (content-addressed; idempotent)
 *   3. Insert source_documents row
 *   4. Spawn scrapers/fcgo_consolidated/parser.py subprocess
 *   5. Persist parser_runs + staging_indicator_values
 *   6. Run validation job (staging → approved promotion)
 *
 * NOTE: the 9 FCGO indicator slugs must be seeded in the indicators table
 * (seed-indicators.ts) for rows to promote to approved_indicator_values;
 * Mother adds them at integration (this worker does not edit seed-indicators.ts).
 *
 * Usage:
 *   pnpm ingest:fcgo-cfs
 *   pnpm ingest:fcgo-cfs --dry-run
 *   pnpm ingest:fcgo-cfs --input "Financial Data/fcgo_consolidated/FCGO_CFS_2023-24.pdf"
 *   pnpm ingest:fcgo-cfs --input "Financial Data/fcgo_consolidated/FCGO_CFS_2022-23.pdf"
 *   pnpm ingest:fcgo-cfs --source-id fcgo-consolidated-financial-statements
 *
 * The script must be run from the repo root (where node_modules lives):
 *   cd /path/to/Economy && node_modules/.bin/tsx .claude/worktrees/.../scripts/ingest-fcgo-cfs.ts
 * OR via the worktree package.json script (pnpm resolves tsx from the root):
 *   pnpm ingest:fcgo-cfs
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

// SOURCE_ID from scrapers/fcgo_consolidated/parser.py.
const DEFAULT_SOURCE_ID = 'fcgo-consolidated-financial-statements';

// The FCGO CFS PDF — the narrative prose parser (pymupdf) reads this.
// Data files live under the worktree root in `Financial Data/`.
const DEFAULT_INPUT_RELATIVE = path.join(
  'Financial Data',
  'fcgo_consolidated',
  'FCGO_CFS_2022-23.pdf',
);
const DEFAULT_INPUT = path.join(REPO_ROOT, DEFAULT_INPUT_RELATIVE);

// Parser path — absolute so it resolves regardless of process.cwd().
const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'fcgo_consolidated', 'parser.py');

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
  process.stdout.write(`[ingest-fcgo-cfs] ${msg}\n`);
}

function logErr(msg: string): void {
  process.stderr.write(`[ingest-fcgo-cfs] ${msg}\n`);
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

    log('staging rows:');
    for (const row of output.staging_rows) {
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
  const { ingestSource } = await import('@/lib/ingestion');

  log('starting full pipeline via ingestSource() orchestrator ...');

  const result = await ingestSource({
    filePath: args.inputPath,
    sourceId: args.sourceId,
    fileName: basename(args.inputPath),
    contentType: 'application/pdf',
    parserPath: PARSER_PATH,
    // reportingPeriodLabel omitted: parser v0.2.0 auto-detects FY from prose.
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

  // Query the approved rows for this source document and print them.
  // Direct DB query because there is no repository function for "list by
  // sourceDocumentId" in approved-indicator-values.ts (scope fence: cannot
  // add one). We use the Drizzle client directly, which is sanctioned for
  // scripts per existing patterns (ingest-cmefs.ts §persist).
  if (approvedTotal > 0) {
    log('');
    log('=== Approved Rows (sanity check) ===');

    const { db } = await import('@/lib/db/client');
    const { approvedIndicatorValues } = await import('@/lib/db/schema/indicator-values');
    const { eq, desc } = await import('drizzle-orm');

    const rows = await db()
      .select()
      .from(approvedIndicatorValues)
      .where(eq(approvedIndicatorValues.sourceDocumentId, summary.sourceDocumentId))
      .orderBy(desc(approvedIndicatorValues.promotedAt))
      .limit(10);

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
    log(
      'This may indicate that the FCGO indicator slugs are not yet seeded in the indicators table.',
    );
  }

  log('');
  log('done.');
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  logErr(`uncaught error: ${msg}`);
  process.exit(1);
});
