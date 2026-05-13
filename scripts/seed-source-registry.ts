/**
 * Seed the Source Registry with Tier-1 starter sources.
 *
 * Per docs/SOURCE_REGISTRY.md, no scraper is written until the source is
 * registered. This script registers the two Tier-1 sources we already have
 * files for in the repo (NRB CMEFs monthly PDF + NRB NCPI Table 2(B) CSV).
 *
 * Usage:
 *   pnpm exec tsx scripts/seed-source-registry.ts --dry-run
 *   pnpm exec tsx scripts/seed-source-registry.ts        # requires DATABASE_URL
 *
 * Idempotent: composes `upsertSource`, which keys on `source_id`. Re-running
 * updates mutable fields without rewriting `registered_at`.
 *
 * `db` and `upsertSource` are imported lazily so `--dry-run` works without
 * `DATABASE_URL` set — useful for CI smoke checks and local validation.
 */

import type { NewSourceRegistryRow } from '@/lib/db/schema/source-registry';

const ROWS: readonly NewSourceRegistryRow[] = [
  {
    sourceId: 'nrb-cmefs-monthly',
    agency: 'Nepal Rastra Bank',
    agencyShort: 'NRB',
    datasetName: 'Current Macroeconomic and Financial Situation',
    sourceUrl: 'https://www.nrb.org.np/category/current-macroeconomic-situation/',
    publicationFrequency: 'monthly',
    expectedReleaseWindow: '25th–30th of the month following the reporting period',
    reportingPeriodType: 'monthly',
    fileFormat: 'pdf',
    requiresTableExtraction: true,
    historicalCoverage: 'FY 2073/74 onward (~2016)',
    licenseStatus: 'gov_open',
    parserOwner: 'scrapers/nrb-cmefs/parser.py',
    parserVersion: '0.0.0',
    revisionPolicy:
      'Provisional values revised in next release; historical values stable after 2 cycles',
    knownBreakageModes: ['url-changes-each-fy', 'pdf-format-shifts-at-fy-boundary'],
    confidenceDefault: 'A',
    status: 'active',
    notes:
      'Starter source — existing PDFs already in repo at Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf',
  },
  {
    sourceId: 'nrb-ncpi-table',
    agency: 'Nepal Rastra Bank',
    agencyShort: 'NRB',
    datasetName: 'NCPI Table 2(B)',
    sourceUrl: 'https://www.nrb.org.np/category/current-macroeconomic-situation/',
    publicationFrequency: 'monthly',
    expectedReleaseWindow: 'Bundled with CMEFs release',
    reportingPeriodType: 'nine_months_cumulative',
    fileFormat: 'csv',
    requiresTableExtraction: false,
    historicalCoverage: 'FY 2073/74 onward (table form available digitally; pre-2016 in PDF)',
    licenseStatus: 'gov_open',
    parserOwner: 'scrapers/nrb_ncpi/parser.py',
    parserVersion: '0.0.0',
    revisionPolicy: 'Aligned with CMEFs cycle',
    knownBreakageModes: ['header-row-position-shifts'],
    confidenceDefault: 'A',
    status: 'active',
    notes: 'Existing CSV in repo at NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv',
  },
];

export { ROWS };

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');

  if (dryRun) {
    console.log('[dry-run] would upsert the following source_registry rows:');
    console.log(JSON.stringify(ROWS, null, 2));
    console.log(`[dry-run] total: ${ROWS.length} rows`);
    process.exit(0);
  }

  // Lazy import: only require DATABASE_URL when we are actually hitting the DB.
  const { upsertSource } = await import('@/lib/db/repositories/source-registry');

  let failures = 0;
  for (const row of ROWS) {
    const result = await upsertSource(row);
    if (!result.ok) {
      failures += 1;
      console.error(`[seed] FAILED ${row.sourceId}:`, result.error);
      continue;
    }
    console.log(`[seed] upserted ${result.value.sourceId}`);
  }

  if (failures > 0) {
    console.error(`[seed] ${failures} of ${ROWS.length} rows failed`);
    process.exit(1);
  }

  console.log(`[seed] inserted/updated ${ROWS.length} source_registry rows`);
  process.exit(0);
}

main().catch((e: unknown) => {
  console.error('[seed] uncaught error:', e);
  process.exit(1);
});
