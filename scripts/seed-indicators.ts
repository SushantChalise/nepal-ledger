/**
 * Seed the indicator catalogue + controlled unit vocabulary.
 *
 * Three tables, in dependency order:
 *   1. `indicator_units`     — the controlled vocabulary the validator checks
 *                              a staging row's `unit` against (lowercase
 *                              snake_case, matching what the deterministic
 *                              Python parsers emit verbatim).
 *   2. `indicators`          — the canonical concepts (slug → name/category/
 *                              unit). The validator resolves a staging row's
 *                              `indicator_slug_raw` against this table.
 *   3. `indicator_source_map`— links each indicator to the source(s) that
 *                              feed it (here: nrb-cmefs-monthly).
 *
 * Without these rows the validation job blocks every CMEFs staging row with
 * IndicatorUnknown + UnitUnrecognized (see docs/DATA_PIPELINE.md §"The
 * Validation Job"). Seeding them unblocks promotion to
 * `approved_indicator_values`.
 *
 * Idempotent: units + indicators upsert on their natural keys; the
 * source-map link is read-then-write (repo handles existence).
 *
 * Usage:
 *   pnpm seed:indicators --dry-run    # no DB; prints what would be written
 *   pnpm seed:indicators              # requires DATABASE_URL (.env.local)
 */

import process from 'node:process';

import type { IndicatorCategory } from '@/lib/db/schema/enums';
import type { NewIndicatorRow } from '@/lib/db/schema/indicators';
import type { NewIndicatorUnitRow } from '@/lib/db/schema/indicators';

const CMEFS_SOURCE_ID = 'nrb-cmefs-monthly';

// ─── Controlled unit vocabulary ────────────────────────────────────────────
const UNITS: readonly NewIndicatorUnitRow[] = [
  { unit: 'npr_billion', displayEn: 'NPR billion', dimension: 'currency' },
  { unit: 'npr_million', displayEn: 'NPR million', dimension: 'currency' },
  { unit: 'npr_crore', displayEn: 'NPR crore', dimension: 'currency' },
  { unit: 'npr_lakh', displayEn: 'NPR lakh', dimension: 'currency' },
  { unit: 'npr', displayEn: 'NPR', dimension: 'currency' },
  { unit: 'usd_million', displayEn: 'USD million', dimension: 'currency' },
  { unit: 'usd', displayEn: 'USD', dimension: 'currency' },
  { unit: 'percent', displayEn: 'percent', dimension: 'ratio' },
  { unit: 'percent_yoy', displayEn: 'percent (year-on-year)', dimension: 'ratio' },
  { unit: 'index_points', displayEn: 'index points', dimension: 'index' },
  { unit: 'months', displayEn: 'months', dimension: 'duration' },
  { unit: 'count', displayEn: 'count', dimension: 'count' },
  { unit: 'ratio', displayEn: 'ratio', dimension: 'ratio' },
  { unit: 'metric_tonnes', displayEn: 'metric tonnes', dimension: 'mass' },
  { unit: 'kg_per_capita', displayEn: 'kg per capita', dimension: 'mass' },
  { unit: 'gigawatt_hours', displayEn: 'GWh', dimension: 'energy' },
  { unit: 'megawatt_hours', displayEn: 'MWh', dimension: 'energy' },
];

// ─── CMEFs headline indicators (parser nrb_cmefs v0.1.0) ────────────────────
type SeedIndicator = NewIndicatorRow & { category: IndicatorCategory };

const INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'cmefs-ncpi-yoy-overall',
    nameEn: 'Consumer Price Inflation (y-o-y)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-remittance-inflow-ytd',
    nameEn: 'Remittance Inflows (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-merchandise-imports-ytd',
    nameEn: 'Merchandise Imports (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-trade-deficit-ytd',
    nameEn: 'Trade Deficit (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-bop-surplus-ytd',
    nameEn: 'Balance of Payments Surplus (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-gross-forex-reserves',
    nameEn: 'Gross Foreign Exchange Reserves',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-forex-reserves-months-of-import-cover',
    nameEn: 'Foreign Exchange Reserves — Months of Import Cover',
    category: 'external_sector',
    unit: 'months',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
];

function log(msg: string): void {
  process.stdout.write(`[seed-indicators] ${msg}\n`);
}

async function persist(): Promise<void> {
  // Lazy imports so --dry-run runs without DATABASE_URL.
  const { db } = await import('@/lib/db/client');
  const { indicators } = await import('@/lib/db/schema/indicators');
  const { safeQuery } = await import('@/lib/db/safe-query');
  const { bulkUpsertIndicatorUnits } = await import('@/lib/db/repositories/indicator-units');
  const { findIndicatorBySlug, linkIndicatorToSource } =
    await import('@/lib/db/repositories/indicators');

  // 1. Units.
  const unitsResult = await bulkUpsertIndicatorUnits(UNITS);
  if (!unitsResult.ok) throw new Error(`units upsert failed: ${JSON.stringify(unitsResult.error)}`);
  log(`indicator_units: ${unitsResult.value} inserted (of ${UNITS.length}; existing skipped)`);

  // 2. Indicators.
  const insertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!insertResult.ok)
    throw new Error(`indicators insert failed: ${JSON.stringify(insertResult.error)}`);
  log(
    `indicators: ${insertResult.value.length} inserted (of ${INDICATORS.length}; existing skipped)`,
  );

  // 3. Source map — resolve every slug (incl. pre-existing) to its id, then link.
  let linked = 0;
  for (const ind of INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(found.value.id, CMEFS_SOURCE_ID, 'CMEFs headline set');
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    linked += 1;
  }
  log(`indicator_source_map: ${linked} links ensured → ${CMEFS_SOURCE_ID}`);
}

async function main(): Promise<void> {
  const dryRun = process.argv.slice(2).includes('--dry-run');
  log(`dry_run = ${dryRun}`);
  log(`units = ${UNITS.length}, indicators = ${INDICATORS.length}, source = ${CMEFS_SOURCE_ID}`);

  if (dryRun) {
    log('dry-run: would upsert the following indicator slugs:');
    for (const i of INDICATORS) log(`  - ${i.slug} (${i.category}, ${i.unit})`);
    log('dry-run complete — no DB writes performed');
    return;
  }

  await persist();
  log('done.');
}

main().catch((e: unknown) => {
  process.stderr.write(`[seed-indicators] fatal: ${e instanceof Error ? e.message : String(e)}\n`);
  process.exit(1);
});
