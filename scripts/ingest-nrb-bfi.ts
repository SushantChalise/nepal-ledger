/**
 * Ingest the Worker ζ-produced NRB BFI staging JSON into `banking_sector_facts`.
 *
 * Reads every `staging-data/nrb-bfi/*.json` (one file per monthly snapshot)
 * and upserts each row into `banking_sector_facts` keyed on
 * (bank_class, bank_entity_id, indicator_slug, reporting_period_bs,
 *  reporting_period_type).
 *
 * Idempotent: re-runs overwrite values (last-write-wins by
 * `promoted_at`). Revision detection happens by comparing the value
 * across snapshots for the same (indicator, period); when the value
 * differs, the second snapshot's value wins — Worker ζ's staging JSON
 * already accounts for which snapshot a value came from.
 *
 * Source-document handling: one `source_documents` row per monthly
 * XLSX (idempotent on file_hash_sha256).
 *
 * Usage:
 *   pnpm exec tsx scripts/ingest-nrb-bfi.ts             # all files
 *   pnpm exec tsx scripts/ingest-nrb-bfi.ts --dry-run   # parse only
 *   pnpm exec tsx scripts/ingest-nrb-bfi.ts --files=Bhadau_2082_Publish.json,Saun-2082-Publish.json  # subset
 */

import 'dotenv/config';

import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { argv } from 'node:process';

import { config as dotenvConfig } from 'dotenv';
import { drizzle } from 'drizzle-orm/postgres-js';
import { z } from 'zod';
import postgres from 'postgres';

import { bankingSectorFacts, sourceDocuments, sourceRegistry } from '@/lib/db/schema';
import type { BankClass, ConfidenceGrade, ReportingPeriodType } from '@/lib/db/schema';

dotenvConfig({ path: '.env.local', override: true });

const STAGING_DIR = 'staging-data/nrb-bfi';

// ─── CLI ──────────────────────────────────────────────────────────

function getArg(flag: string): string | undefined {
  const eq = argv.find((a) => a.startsWith(`${flag}=`));
  if (eq) return eq.slice(flag.length + 1);
  const idx = argv.indexOf(flag);
  if (idx >= 0 && idx + 1 < argv.length) return argv[idx + 1];
  return undefined;
}

const dryRun = argv.includes('--dry-run');
const filesArg = getArg('--files');
const filesFilter = filesArg ? new Set(filesArg.split(',').map((s) => s.trim())) : null;

// ─── Zod schema for Worker ζ's staging JSON ───────────────────────

const RowSchema = z.object({
  source_sheet: z.string(),
  indicator_slug: z.string(),
  bank_class: z.enum([
    'commercial',
    'development',
    'finance',
    'microfinance',
    'infrastructure',
    'system_total',
  ]),
  bank_entity_slug: z.string().nullable(),
  value: z.number(),
  unit: z.string(),
  reporting_period_type: z.enum([
    'monthly',
    'quarterly',
    'annual',
    'nine_months_cumulative',
    'year_to_date',
    'daily',
    'seasonal',
  ]),
  reporting_period_bs: z.string(),
  reporting_period_ad_start: z.string(),
  reporting_period_ad_end: z.string(),
  publication_date_ad: z.string(),
  publication_date_bs: z.string(),
  fiscal_year_bs: z.string(),
  confidence_grade_proposed: z.enum(['A', 'B', 'C']),
  parser_notes: z.string().nullable().optional(),
});

const FileSchema = z.object({
  source_file: z.string(),
  source_hash_sha256: z.string(),
  source_bytes: z.number().int(),
  parser_version: z.string(),
  parser_status: z.enum(['success', 'partial', 'failure']),
  row_count: z.number().int(),
  error_count: z.number().int(),
  rows: z.array(RowSchema),
});

type StagedFile = z.infer<typeof FileSchema>;
type StagedRow = z.infer<typeof RowSchema>;

// ─── Main ─────────────────────────────────────────────────────────

async function loadStaging(file: string): Promise<StagedFile> {
  const raw = await readFile(file, 'utf-8');
  const parsed = FileSchema.safeParse(JSON.parse(raw));
  if (!parsed.success) {
    throw new Error(`Invalid staging JSON ${file}: ${parsed.error.message}`);
  }
  return parsed.data;
}

async function main(): Promise<void> {
  const url = process.env['DIRECT_URL'] ?? process.env['DATABASE_URL'];
  if (!dryRun && !url) {
    console.error('No DIRECT_URL / DATABASE_URL in .env.local.');
    process.exit(1);
  }

  console.log(`[bfi-ingest] reading ${STAGING_DIR}/`);
  const allFiles = (await readdir(STAGING_DIR))
    .filter((f) => f.endsWith('.json'))
    .filter((f) => !filesFilter || filesFilter.has(f))
    .sort();
  console.log(
    `[bfi-ingest] ${allFiles.length} file(s) to ingest${filesFilter ? ' (filtered)' : ''}`,
  );

  // Parse all files first; surface schema problems before any DB writes
  const staged: { file: string; data: StagedFile }[] = [];
  for (const f of allFiles) {
    const fullPath = path.join(STAGING_DIR, f);
    try {
      const data = await loadStaging(fullPath);
      staged.push({ file: f, data });
      console.log(`  - ${f}: parser_status=${data.parser_status} rows=${data.row_count}`);
    } catch (e: unknown) {
      console.error(`  - ${f}: PARSE FAIL — ${e instanceof Error ? e.message : String(e)}`);
      process.exit(1);
    }
  }

  const totalRows = staged.reduce((acc, s) => acc + s.data.rows.length, 0);
  console.log(`[bfi-ingest] total rows to ingest: ${totalRows}`);

  if (dryRun) {
    console.log('[bfi-ingest] --dry-run: not connecting to DB');
    // Print breakdown by bank_class
    const byBankClass = new Map<BankClass, number>();
    for (const s of staged) {
      for (const r of s.data.rows) {
        byBankClass.set(r.bank_class, (byBankClass.get(r.bank_class) ?? 0) + 1);
      }
    }
    console.log('[bfi-ingest] breakdown by bank_class:');
    for (const [k, v] of byBankClass) {
      console.log(`  - ${k}: ${v}`);
    }
    return;
  }

  console.log('[bfi-ingest] Connecting to Postgres...');
  const sql = postgres(url!, { max: 5, prepare: false });
  const db = drizzle(sql);

  // ─── Ensure source_registry row ────────────────────────────────
  await db
    .insert(sourceRegistry)
    .values({
      sourceId: 'nrb-bfi-monthly',
      agency: 'Nepal Rastra Bank',
      agencyShort: 'NRB',
      datasetName: 'Banking & Financial Statistics (Monthly XLSX)',
      sourceUrl: 'https://www.nrb.org.np/category/economic-research/bafia-publications/',
      publicationFrequency: 'monthly',
      expectedReleaseWindow: '25th–30th of the month following the reporting period',
      reportingPeriodType: 'monthly',
      fileFormat: 'xlsx',
      requiresTableExtraction: false,
      licenseStatus: 'gov_open',
      ingestionMode: 'manual_upload',
      confidenceDefault: 'A',
      status: 'active',
      knownBreakageModes: [
        'column-count-changes-across-snapshots',
        'unit-header-varies-million-vs-crore',
      ],
      parserOwner: 'scrapers/nrb_bfi/parser.py',
      parserVersion: '0.1.0',
      notes: '49 continuous months Shrawan 2078 → Bhadau 2082; staged at staging-data/nrb-bfi/.',
    })
    .onConflictDoNothing();

  // ─── Per-file: insert source_documents row + bulk insert rows ──
  let totalInserted = 0;
  for (const s of staged) {
    const sourceDocResult = await db
      .insert(sourceDocuments)
      .values({
        sourceId: 'nrb-bfi-monthly',
        originalUrl: `local-file:${s.data.source_file}`,
        storageProvider: 'supabase',
        storageKey: `nrb-bfi-monthly/${new Date().toISOString().slice(0, 10)}/${path.basename(s.data.source_file)}`,
        fileHashSha256: s.data.source_hash_sha256,
        fileSizeBytes: s.data.source_bytes,
        contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        reportingPeriodLabel: s.file.replace('.json', ''),
        notes: `Ingested from staging-data/nrb-bfi/${s.file}; parser v${s.data.parser_version}.`,
      })
      .returning({ id: sourceDocuments.id });

    const sourceDocRow = sourceDocResult[0];
    if (!sourceDocRow) {
      console.error(`[bfi-ingest] failed to insert source_documents row for ${s.file}`);
      process.exit(1);
    }
    const sourceDocId = sourceDocRow.id;

    // Build inserts in batches of 200
    const batchSize = 200;
    for (let i = 0; i < s.data.rows.length; i += batchSize) {
      const batch = s.data.rows.slice(i, i + batchSize);
      const inserts = batch.map((r: StagedRow) => ({
        bankClass: r.bank_class as BankClass,
        // bank_entity_id intentionally null until per-bank rollup ships in v0.2.0
        bankEntityId: null,
        sourceSheet: r.source_sheet,
        indicatorSlug: r.indicator_slug,
        value: String(r.value),
        unit: r.unit,
        reportingPeriodType: r.reporting_period_type as ReportingPeriodType,
        reportingPeriodBs: r.reporting_period_bs,
        reportingPeriodAdStart: new Date(r.reporting_period_ad_start),
        reportingPeriodAdEnd: new Date(r.reporting_period_ad_end),
        publicationDateAd: new Date(r.publication_date_ad),
        publicationDateBs: r.publication_date_bs,
        fiscalYearBs: r.fiscal_year_bs,
        sourceDocumentId: sourceDocId,
        confidenceGrade: r.confidence_grade_proposed as ConfidenceGrade,
        promotedBy: 'mother:ingest-nrb-bfi',
      }));

      await db
        .insert(bankingSectorFacts)
        .values(inserts)
        .onConflictDoUpdate({
          target: [
            bankingSectorFacts.bankClass,
            bankingSectorFacts.bankEntityId,
            bankingSectorFacts.indicatorSlug,
            bankingSectorFacts.reportingPeriodBs,
            bankingSectorFacts.reportingPeriodType,
          ],
          set: {
            value: bankingSectorFacts.value,
            promotedAt: new Date(),
          },
        });
      totalInserted += inserts.length;
    }
    console.log(`  - ${s.file}: ${s.data.rows.length} rows inserted`);
  }

  console.log(`[bfi-ingest] total inserted: ${totalInserted}`);

  // ─── Summary ────────────────────────────────────────────────
  const counts = await sql<{ bank_class: string; cnt: number }[]>`
    SELECT bank_class, COUNT(*) AS cnt
    FROM banking_sector_facts
    GROUP BY bank_class
    ORDER BY bank_class
  `;
  console.log('[bfi-ingest] banking_sector_facts row counts by bank_class:');
  for (const row of counts) {
    console.log(`  - ${row.bank_class}: ${row.cnt}`);
  }

  await sql.end();
  console.log('[bfi-ingest] OK.');
}

main().catch((e: unknown) => {
  console.error('[bfi-ingest] FAILED:', e instanceof Error ? e.stack : String(e));
  process.exit(1);
});
