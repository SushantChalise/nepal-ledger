/**
 * Tourism Rupee server queries.
 *
 * Reads the monthly tourist-arrivals series (indicator slug
 * `dne-tourist-arrival`, ~407 rows, 1992–2025) from approved_indicator_values
 * joined to indicators, and shapes it for a line chart.
 *
 * GOTCHA (verified — see docs/research/DATA_BUILDOUT_PLAN.md §#27):
 *   Plot on `reporting_period_ad_end` (the real Gregorian month-end), NOT
 *   `reporting_period_bs`. The BS labels skew near COVID because the DNE
 *   transposed-layout parser approximates them mid-month; the AD end date is
 *   the trustworthy time axis. Every point's `x` is `reporting_period_ad_end`.
 *
 * SCOPE: only the tourism-rupee feature. Reads from the DB directly; does NOT
 * edit any existing repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';

/** Indicator slug for the NRB DNE monthly tourist-arrivals series. */
export const TOURIST_ARRIVAL_SLUG = 'dne-tourist-arrival';

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** One monthly observation, keyed on the AD month-end (the trustworthy axis). */
export type ArrivalsPoint = {
  /** Real Gregorian month-end (reporting_period_ad_end), ISO string. */
  adEnd: string;
  /** BS reporting-period label (display only — NOT used for the time axis). */
  periodBs: string;
  /** Tourist arrivals in that month (count). */
  arrivals: number;
};

export type ArrivalsSeries = {
  /** Chronological points, ascending by adEnd. */
  points: ArrivalsPoint[];
  /** Most-recent point (highest adEnd), or null when the series is empty. */
  latest: ArrivalsPoint | null;
  /**
   * Year-over-year change of the latest month vs. the same month one year
   * earlier, as a percentage. null when no ~12-months-prior row exists.
   */
  yoyPct: number | null;
  /** Indicator display name (indicators.name_en). */
  indicatorName: string;
  /** Canonical unit string (indicators.unit). */
  unit: string;
  /** Confidence grade of the latest observation (A/B/C). */
  confidence: ConfidenceGrade;
  /** Source agency label (indicators.source_agency). */
  sourceAgency: string;
};

// ---------------------------------------------------------------------------
// DB boundary
// ---------------------------------------------------------------------------

// Validated at the DB boundary with Zod — the sanctioned alternative to an
// `as` cast on the untyped postgres-js result (CONTEXT_RULES §"Cast Escape
// Hatches" (a)). The SQL column list below defines the shape.
const ArrivalsRowSchema = z.object({
  ad_end: z.coerce.date(),
  period_bs: z.string(),
  value: z.string(),
  unit: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
  name_en: z.string(),
  source_agency: z.string(),
});
type ArrivalsRow = z.infer<typeof ArrivalsRowSchema>;

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Fetch the full monthly tourist-arrivals series, ascending by the AD
 * month-end. Returns ok with an empty `points` array (and null `latest`) when
 * the indicator exists but has no rows; NotFound only when the slug or its
 * rows are entirely absent. Never throws — callers render typed states.
 */
export async function getTouristArrivalsSeries(): Promise<Result<ArrivalsSeries>> {
  const rawResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          v.reporting_period_ad_end AS ad_end,
          v.reporting_period_bs      AS period_bs,
          v.value::text              AS value,
          v.unit                     AS unit,
          v.confidence_grade         AS confidence_grade,
          i.name_en                  AS name_en,
          i.source_agency            AS source_agency
        FROM approved_indicator_values v
        JOIN indicators i ON i.id = v.indicator_id
        WHERE i.slug = ${TOURIST_ARRIVAL_SLUG}
        ORDER BY v.reporting_period_ad_end ASC
      `,
    ),
  );

  if (!rawResult.ok) return rawResult;

  const parsed = z.array(ArrivalsRowSchema).safeParse(rawResult.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `tourist-arrivals query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const rows: ArrivalsRow[] = parsed.data;

  if (rows.length === 0) {
    return err({
      kind: 'NotFound',
      resource: 'approved_indicator_values',
      id: `indicator slug=${TOURIST_ARRIVAL_SLUG}`,
    });
  }

  const points: ArrivalsPoint[] = [];
  for (const row of rows) {
    const arrivals = Number(row.value);
    if (!Number.isFinite(arrivals)) continue;
    points.push({
      adEnd: row.ad_end.toISOString(),
      periodBs: row.period_bs,
      arrivals,
    });
  }

  if (points.length === 0) {
    return err({
      kind: 'QueryFailed',
      detail: 'getTouristArrivalsSeries: all rows had non-finite values',
    });
  }

  // Metadata is taken from the most-recent row (rows are ascending, so last).
  const lastRow = rows[rows.length - 1];
  if (!lastRow) {
    return err({
      kind: 'QueryFailed',
      detail: 'getTouristArrivalsSeries: non-empty rows but no final row',
    });
  }

  const latest = points[points.length - 1] ?? null;

  return ok({
    points,
    latest,
    yoyPct: computeYoyPct(points),
    indicatorName: lastRow.name_en,
    unit: lastRow.unit,
    confidence: lastRow.confidence_grade,
    sourceAgency: lastRow.source_agency,
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Year-over-year percentage change of the final point vs. the observation
 * closest to exactly 12 months earlier. Returns null when no suitable
 * prior-year point exists, or when the prior-year value is zero (division
 * would be undefined — we never fabricate a band).
 *
 * "Closest to 12 months earlier" tolerates the irregular BS→AD month-end
 * spacing: we search for the point whose adEnd is nearest to (latest − 1yr)
 * within a ±45-day window.
 */
function computeYoyPct(points: readonly ArrivalsPoint[]): number | null {
  const latest = points[points.length - 1];
  if (!latest) return null;

  const latestMs = new Date(latest.adEnd).getTime();
  const targetMs = latestMs - 365.25 * 24 * 60 * 60 * 1000;
  const toleranceMs = 45 * 24 * 60 * 60 * 1000;

  let best: ArrivalsPoint | null = null;
  let bestDelta = Number.POSITIVE_INFINITY;
  for (const p of points) {
    const delta = Math.abs(new Date(p.adEnd).getTime() - targetMs);
    if (delta < bestDelta) {
      bestDelta = delta;
      best = p;
    }
  }

  if (best === null || bestDelta > toleranceMs) return null;
  if (best.arrivals === 0) return null;

  return ((latest.arrivals - best.arrivals) / best.arrivals) * 100;
}
