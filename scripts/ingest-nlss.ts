/**
 * Ingest CLI for the NSO NLSS-IV Summary Report PDF.
 *
 * SOURCE_ID: "nlss-survey" (declared in scrapers/nso_nlss/parser.py).
 *
 * Pipeline (via ingestSource() orchestrator):
 *   1. Read the PDF from disk
 *   2. Archive to local filesystem storage (ADR-0006; content-addressed)
 *   3. Insert source_documents row
 *   4. Spawn scrapers/nso_nlss/parser.py subprocess
 *   5. Persist parser_runs + staging_indicator_values
 *   6. Run validation job (staging → approved promotion)
 *
 * Expected output: 20 staging rows (14 NLSS-IV + 6 NLSS-III comparison).
 * All rows carry confidence_grade_proposed = 'A'.
 *
 * Usage:
 *   pnpm ingest:nlss
 *   pnpm ingest:nlss --dry-run
 *   pnpm ingest:nlss --input "Financial Data/nso_nlss/NLSS_IV_Summary_2022-23.pdf"
 *
 * The script must be run from the repo root (where node_modules lives).
 * Seed prerequisites (run once before the first live ingest):
 *   pnpm seed:source-registry
 *   pnpm seed:indicators
 */

import { existsSync } from 'node:fs';
import { basename } from 'node:path';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');

const DEFAULT_SOURCE_ID = 'nlss-survey';

// Data files live in "Financial Data/" at the project root (parent of
// .claude/worktrees/<worktree>). The summary report is ~3 MB.
const PROJECT_ROOT = path.resolve(REPO_ROOT, '..', '..', '..');
const DEFAULT_INPUT_RELATIVE = path.join(
  'Financial Data',
  'nso_nlss',
  'NLSS_IV_Summary_2022-23.pdf',
);
const DEFAULT_INPUT = path.join(PROJECT_ROOT, DEFAULT_INPUT_RELATIVE);

const PARSER_PATH = path.join(REPO_ROOT, 'scrapers', 'nso_nlss', 'parser.py');

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
  process.stdout.write(`[ingest-nlss] ${msg}\n`);
}

function logErr(msg: string): void {
  process.stderr.write(`[ingest-nlss] ${msg}\n`);
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  log(`input      = ${args.inputPath}`);
  log(`source_id  = ${args.sourceId}`);
  log(`dry_run    = ${args.dryRun}`);
  log(`parser     = ${PARSER_PATH}`);

  if (!existsSync(args.inputPath)) {
    logErr(`input file not found: ${args.inputPath}`);
    logErr(`Download the NLSS-IV Summary Report PDF and archive it at:`);
    logErr(`  ${DEFAULT_INPUT}`);
    logErr(`Official portal: https://data.nsonepal.gov.np/dataset/poverty-status-2023`);
    process.exit(2);
  }

  if (!existsSync(PARSER_PATH)) {
    logErr(`parser not found: ${PARSER_PATH}`);
    process.exit(2);
  }

  if (args.dryRun) {
    // Dry-run: spawn the parser, validate output shape, print summary. No DB writes.
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
      for (const e of output.errors) {
        log(`  ! ${e.error_class}: ${e.error_detail}`);
      }
    }

    log('first 5 staging rows:');
    for (const row of output.staging_rows.slice(0, 5)) {
      log(
        `  ${row.indicator_slug_raw}: ${row.value} ${row.unit} ` +
          `(${row.fiscal_year_bs} / ${row.fiscal_year_ad_label})`,
      );
    }

    log('dry-run complete — no DB writes performed');
    return;
  }

  // Live path: use the full ingestSource() orchestrator.
  const { ingestSource } = await import('@/lib/ingestion');

  log('starting full pipeline via ingestSource() orchestrator ...');

  const result = await ingestSource({
    filePath: args.inputPath,
    sourceId: args.sourceId,
    fileName: basename(args.inputPath),
    contentType: 'application/pdf',
    parserPath: PARSER_PATH,
    reportingPeriodLabel: 'NLSS-IV 2022/23',
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
    log('Run: pnpm seed:indicators');
  }

  log('');
  log('done.');
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  logErr(`uncaught error: ${msg}`);
  process.exit(1);
});
