/**
 * Growth (headline macro) server queries.
 *
 * Loads Nepal's six core annual macro series from approved_indicator_values
 * joined to indicators, in a single round-trip, and shapes each into a full
 * fiscal-year history plus its latest observation:
 *
 *   - `dne-gdp-nominal`         Nominal GDP            (npr_billion)
 *   - `dne-gdp-real`            Real GDP              (npr_billion)
 *   - `dne-gdp-real-growth`     Real GDP growth rate  (percent)
 *   - `dne-gdp-per-capita-usd`  Per-capita GDP        (usd)
 *   - `dne-cpi`                 National CPI — overall (index_points)
 *   - `dne-inflation-rate`      CPI inflation — overall (percent)
 *
 * TIME AXIS: these are ANNUAL fiscal-year series (unlike the monthly tourism
 * series, the BS fiscal-year label is the canonical period here). We still
 * order chronologically by `reporting_period_ad_end` so a later edition's
 * appended years sort correctly, and carry the BS label (e.g. "2081/82") for
 * display on the axis and in the accessible table.
 *
 * WHY A LOCAL QUERY (not a shared repo helper): the existing repository
 * exposes `findLatestApprovedByPeriod` (one period) and
 * `listApprovedTrailingForIndicator` (a date-bounded window by indicator UUID,
 * descending — built for the validator's plausibility band). Neither fetches a
 * full ascending history *by slug*, and this page needs six such series in one
 * shot. Per the scope fence ("do NOT add a repo function unless necessary"),
 * we mirror the tourism-rupee feature's local `db().execute(sql\`…\`)` +
 * Zod-at-boundary pattern rather than widening the shared repository.
 *
 * SCOPE: only the growth feature. Reads from the DB directly (read-only); does
 * NOT edit any existing repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';

// ---------------------------------------------------------------------------
// Slugs
// ---------------------------------------------------------------------------

export const GDP_NOMINAL_SLUG = 'dne-gdp-nominal';
export const GDP_REAL_SLUG = 'dne-gdp-real';
export const GDP_REAL_GROWTH_SLUG = 'dne-gdp-real-growth';
export const GDP_PER_CAPITA_USD_SLUG = 'dne-gdp-per-capita-usd';
export const CPI_SLUG = 'dne-cpi';
export const INFLATION_RATE_SLUG = 'dne-inflation-rate';

/** Every slug this page loads, in one query. */
export const GROWTH_SLUGS = [
  GDP_NOMINAL_SLUG,
  GDP_REAL_SLUG,
  GDP_REAL_GROWTH_SLUG,
  GDP_PER_CAPITA_USD_SLUG,
  CPI_SLUG,
  INFLATION_RATE_SLUG,
] as const;

export type GrowthSlug = (typeof GROWTH_SLUGS)[number];

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** One annual observation of a single series, keyed on the BS fiscal year. */
export type SeriesPoint = {
  /** BS fiscal-year label (e.g. "2081/82") — the canonical annual period. */
  fiscalYearBs: string;
  /** Real Gregorian period-end (reporting_period_ad_end), ISO string. */
  adEnd: string;
  /** The numeric value (already coerced from the postgres numeric string). */
  value: number;
};

/** A full annual series for one indicator, ascending by fiscal year. */
export type IndicatorSeries = {
  slug: GrowthSlug;
  /** Indicator display name (indicators.name_en). */
  name: string;
  /** Canonical unit string (indicators.unit), e.g. "npr_billion" / "percent". */
  unit: string;
  /** Confidence grade of the latest observation (A/B/C). */
  confidence: ConfidenceGrade;
  /** Source agency label (indicators.source_agency). */
  sourceAgency: string;
  /** Chronological points, ascending by fiscal year / adEnd. */
  points: SeriesPoint[];
  /** Most-recent point (highest adEnd), or null when the series has no rows. */
  latest: SeriesPoint | null;
};

/**
 * The six headline series the /growth page renders. Each field is the full
 * history for one slug; a series with no approved rows comes back with an
 * empty `points` array and null `latest` (NOT an error — a single missing
 * series must not blank the whole page).
 */
export type GrowthData = {
  gdpNominal: IndicatorSeries;
  gdpReal: IndicatorSeries;
  gdpRealGrowth: IndicatorSeries;
  perCapitaUsd: IndicatorSeries;
  cpi: IndicatorSeries;
  inflationRate: IndicatorSeries;
};

// ---------------------------------------------------------------------------
// DB boundary
// ---------------------------------------------------------------------------

// Validated at the DB boundary with Zod — the sanctioned alternative to an
// `as` cast on the untyped postgres-js result (CONTEXT_RULES §"Cast Escape
// Hatches" (a)). The SQL column list below defines the shape. `value` arrives
// as a numeric string (e.g. "6107.000000").
const SeriesRowSchema = z.object({
  slug: z.string(),
  name_en: z.string(),
  unit: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
  source_agency: z.string(),
  fiscal_year_bs: z.string(),
  ad_end: z.coerce.date(),
  value: z.string(),
});
type SeriesRow = z.infer<typeof SeriesRowSchema>;

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Fetch all six headline macro series in a single query, ascending by fiscal
 * year within each slug, and group them into {@link GrowthData}.
 *
 * Returns NotFound only when NONE of the six slugs has any approved row (the
 * page then renders its empty state). When at least one series has data, the
 * others may legitimately be empty (`points: []`, `latest: null`) and the page
 * renders what exists — a single missing series never errors the page. Never
 * throws; callers render typed states.
 */
export async function getGrowthData(): Promise<Result<GrowthData>> {
  const rawResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          i.slug                     AS slug,
          i.name_en                  AS name_en,
          v.unit                     AS unit,
          v.confidence_grade         AS confidence_grade,
          i.source_agency            AS source_agency,
          v.fiscal_year_bs           AS fiscal_year_bs,
          v.reporting_period_ad_end  AS ad_end,
          v.value::text              AS value
        FROM approved_indicator_values v
        JOIN indicators i ON i.id = v.indicator_id
        WHERE i.slug IN (
          ${GDP_NOMINAL_SLUG},
          ${GDP_REAL_SLUG},
          ${GDP_REAL_GROWTH_SLUG},
          ${GDP_PER_CAPITA_USD_SLUG},
          ${CPI_SLUG},
          ${INFLATION_RATE_SLUG}
        )
        ORDER BY i.slug ASC, v.reporting_period_ad_end ASC
      `,
    ),
  );

  if (!rawResult.ok) return rawResult;

  const parsed = z.array(SeriesRowSchema).safeParse(rawResult.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `growth query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const rows: SeriesRow[] = parsed.data;

  if (rows.length === 0) {
    return err({
      kind: 'NotFound',
      resource: 'approved_indicator_values',
      id: `indicator slugs=${GROWTH_SLUGS.join(',')}`,
    });
  }

  return ok({
    gdpNominal: buildSeries(GDP_NOMINAL_SLUG, rows),
    gdpReal: buildSeries(GDP_REAL_SLUG, rows),
    gdpRealGrowth: buildSeries(GDP_REAL_GROWTH_SLUG, rows),
    perCapitaUsd: buildSeries(GDP_PER_CAPITA_USD_SLUG, rows),
    cpi: buildSeries(CPI_SLUG, rows),
    inflationRate: buildSeries(INFLATION_RATE_SLUG, rows),
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Collect every row for `slug` (rows are pre-sorted ascending by ad_end) into
 * an {@link IndicatorSeries}. Non-finite values are skipped (never zero-filled
 * — Data Continuity Protocol). Metadata (name/unit/confidence/source) is taken
 * from the slug's most-recent row; an empty series falls back to the seeded
 * indicator metadata so the unit label is never blank.
 */
function buildSeries(slug: GrowthSlug, rows: readonly SeriesRow[]): IndicatorSeries {
  const slugRows = rows.filter((r) => r.slug === slug);

  const points: SeriesPoint[] = [];
  for (const row of slugRows) {
    const value = Number(row.value);
    if (!Number.isFinite(value)) continue;
    points.push({
      fiscalYearBs: row.fiscal_year_bs,
      adEnd: row.ad_end.toISOString(),
      value,
    });
  }

  const lastRow = slugRows[slugRows.length - 1];
  const meta = SLUG_FALLBACK_META[slug];

  return {
    slug,
    name: lastRow?.name_en ?? meta.name,
    unit: lastRow?.unit ?? meta.unit,
    confidence: lastRow?.confidence_grade ?? 'B',
    sourceAgency: lastRow?.source_agency ?? 'Nepal Rastra Bank',
    points,
    latest: points[points.length - 1] ?? null,
  };
}

/**
 * Seeded metadata fallback for a series that returns zero rows, so the empty
 * state still carries the correct name + unit label. Mirrors
 * `scripts/seed-indicators.ts`; the values come from the DB when rows exist.
 */
const SLUG_FALLBACK_META: Record<GrowthSlug, { name: string; unit: string }> = {
  [GDP_NOMINAL_SLUG]: { name: "Nominal GDP (at producers' price)", unit: 'npr_billion' },
  [GDP_REAL_SLUG]: { name: "Real GDP (at purchasers' price)", unit: 'npr_billion' },
  [GDP_REAL_GROWTH_SLUG]: {
    name: "Real GDP Growth Rate (at purchasers' price)",
    unit: 'percent',
  },
  [GDP_PER_CAPITA_USD_SLUG]: { name: 'Per Capita GDP (USD)', unit: 'usd' },
  [CPI_SLUG]: { name: 'National Consumer Price Index — Overall', unit: 'index_points' },
  [INFLATION_RATE_SLUG]: { name: 'Consumer Price Inflation — Overall', unit: 'percent' },
};
