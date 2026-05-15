/**
 * Ingest CLI for the NRB BFI monthly XLSX (source id `nrb-bfi-monthly-xlsx`).
 *
 * Pipeline:
 *   1. spawn the Python parser (scrapers/nrb_bfi/parser.py)
 *   2. validate JSON output via a defensive Zod schema
 *   3. bulk-insert into `banking_sector_facts` via the typed repository
 *
 * Idempotency: relies on the natural-key unique index on
 * (bank_class, bank_entity_id, indicator_slug, reporting_period_bs,
 * reporting_period_type) + `onConflictDoNothing` in the repository. Re-running
 * the same XLSX is a no-op.
 *
 * Usage:
 *   pnpm ingest:bfi-monthly --input "Financial Data/nrb_monthly_statistics/Bhadau_2082_Publish.xlsx"
 *   pnpm ingest:bfi-monthly --dry-run        # uses the default canonical month, no DB writes
 *
 * Source-document row creation is intentionally deferred to the orchestrator
 * (Worker D pattern). This CLI accepts `--source-document-id <uuid>` so the
 * caller pre-creates the source_document row and threads the FK in.
 * In --dry-run mode the FK requirement is relaxed (placeholder UUID).
 */

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const DEFAULT_INPUT = path.join(
  REPO_ROOT,
  'Financial Data',
  'nrb_monthly_statistics',
  'Bhadau_2082_Publish.xlsx',
);
const PLACEHOLDER_SOURCE_DOC_ID = '00000000-0000-0000-0000-000000000000';

const FactRowSchema = z.object({
  bank_class: z.enum(['commercial', 'development', 'finance', 'system_total']),
  bank_entity_id: z.string().nullable(),
  source_sheet: z.string(),
  indicator_slug: z.string(),
  value: z.number(),
  unit: z.string(),
  reporting_period_type: z.literal('monthly'),
  reporting_period_bs: z.string(),
  reporting_period_ad_start: z.coerce.date(),
  reporting_period_ad_end: z.coerce.date(),
  publication_date_ad: z.coerce.date(),
  publication_date_bs: z.string(),
  fiscal_year_bs: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
  parser_notes: z.string().nullable(),
});

const ParserOutputSchema = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string(),
  fact_rows: z.array(FactRowSchema).default([]),
  errors: z
    .array(
      z.object({
        error_class: z.string(),
        error_detail: z.string(),
        source_excerpt: z.string().nullable().optional(),
      }),
    )
    .default([]),
});

type ParserOutput = z.infer<typeof ParserOutputSchema>;

function parseArgs(argv: readonly string[]): {
  input: string;
  dryRun: boolean;
  sourceDocumentId: string;
} {
  let input = DEFAULT_INPUT;
  let dryRun = false;
  let sourceDocumentId = PLACEHOLDER_SOURCE_DOC_ID;
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = argv[i + 1];
    if (a === '--input' && next) {
      input = path.resolve(next);
      i += 1;
    } else if (a === '--dry-run') {
      dryRun = true;
    } else if (a === '--source-document-id' && next) {
      sourceDocumentId = next;
      i += 1;
    } else {
      throw new Error(`unknown or malformed argument: ${a}`);
    }
  }
  return { input, dryRun, sourceDocumentId };
}

async function runParser(inputPath: string, sourceDocumentId: string): Promise<ParserOutput> {
  const scrapersDir = path.join(REPO_ROOT, 'scrapers');
  return new Promise((resolve, reject) => {
    const child = spawn('python', ['-m', 'nrb_bfi.parser', inputPath, sourceDocumentId], {
      cwd: scrapersDir,
      env: { ...process.env, PYTHONPATH: scrapersDir },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (c: Buffer) => (stdout += c.toString('utf8')));
    child.stderr.on('data', (c: Buffer) => (stderr += c.toString('utf8')));
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) return reject(new Error(`parser exited ${code}; stderr: ${stderr}`));
      try {
        resolve(ParserOutputSchema.parse(JSON.parse(stdout)));
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        reject(new Error(`parser stdout invalid: ${msg}\nstderr: ${stderr}`));
      }
    });
  });
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  if (!existsSync(args.input)) {
    throw new Error(`input file not found: ${args.input}`);
  }
  process.stdout.write(`[ingest-bfi-monthly] parsing ${args.input}\n`);
  const result = await runParser(args.input, args.sourceDocumentId);
  process.stdout.write(
    `[ingest-bfi-monthly] parser status=${result.status} rows=${result.fact_rows.length} errors=${result.errors.length}\n`,
  );
  for (const e of result.errors) {
    process.stdout.write(`  ! ${e.error_class}: ${e.error_detail}\n`);
  }
  if (args.dryRun) {
    process.stdout.write('[ingest-bfi-monthly] --dry-run: skipping DB write\n');
    return;
  }
  if (result.status === 'failure') {
    throw new Error('parser status=failure; refusing to write');
  }
  // Lazy import to keep --dry-run free of DATABASE_URL requirement.
  const { bulkInsertBankingSectorFacts } = await import('@/lib/db/repositories');
  const rows = result.fact_rows.map((r) => ({
    bankClass: r.bank_class,
    bankEntityId: r.bank_entity_id,
    sourceSheet: r.source_sheet,
    indicatorSlug: r.indicator_slug,
    value: String(r.value),
    unit: r.unit,
    reportingPeriodType: r.reporting_period_type,
    reportingPeriodBs: r.reporting_period_bs,
    reportingPeriodAdStart: r.reporting_period_ad_start,
    reportingPeriodAdEnd: r.reporting_period_ad_end,
    publicationDateAd: r.publication_date_ad,
    publicationDateBs: r.publication_date_bs,
    fiscalYearBs: r.fiscal_year_bs,
    sourceDocumentId: args.sourceDocumentId,
    confidenceGrade: r.confidence_grade,
    promotedBy: 'scripts/ingest-bfi-monthly.ts',
  }));
  const inserted = await bulkInsertBankingSectorFacts(rows);
  if (!inserted.ok) {
    throw new Error(`bulk insert failed: ${JSON.stringify(inserted.error)}`);
  }
  process.stdout.write(
    `[ingest-bfi-monthly] inserted=${inserted.value.length} (rest were duplicates skipped on conflict)\n`,
  );
}

main().catch((e: unknown) => {
  const msg = e instanceof Error ? e.message : String(e);
  process.stderr.write(`[ingest-bfi-monthly] ${msg}\n`);
  process.exit(1);
});
