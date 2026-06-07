/**
 * District MRI server queries.
 *
 * Rolls palika-grain `census_facts` and `local_government_fiscal_transfers` up
 * to the district level for the 5 Year-1 launch districts, reading LIVE
 * production data. Pure render path — no scraper, no migration, no staging.
 *
 * JOIN INVARIANT (the load-bearing correction — verified against the live DB):
 *   The ONLY way to roll palika → district is `entities.metadata->>'district_en'`
 *   (a NAME string). The 8-digit `federal_code` does NOT encode district, and
 *   there are NO `kind='district'` entities. Every aggregation below joins
 *   census_facts / fiscal_transfers → entities (kind='local_level') and filters
 *   `e.metadata->>'district_en' = $1`.
 *
 * CENSUS DENOMINATOR RULE:
 *   Each census ratio derives its denominator from THAT table's own `rowtotal`
 *   slug (the per-palika household/person total), summed across the district —
 *   never from another table and never hard-coded. Slugs are matched via an
 *   explicit ALLOWLIST (see `CENSUS_METRICS`); we never LIKE-match indicator
 *   slugs (a stray dimensional slug would silently corrupt the aggregate).
 *
 * All four census metrics here come from SINGLE-row-per-palika tables
 * (Hhld01/10/11/12 — absent from the parser's `_TABLE_DIMENSION_COLUMNS`), so
 * no `sexname='Total'` filter is required. If a future metric uses a multi-row
 * table (Hhld18/19/20), its allowlist entry MUST pin the `sexname='Total'`
 * dimension slugs explicitly.
 *
 * SCOPE: only the district-mri feature. Reads from DB directly; does NOT edit
 * any repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { GrantType } from '@/lib/db/schema/enums';

// ---------------------------------------------------------------------------
// Grant-type labels (kept in sync with the GrantType enum, mirrors money-map)
// ---------------------------------------------------------------------------

export const GRANT_TYPE_LABELS: Record<GrantType, string> = {
  equalization_minimum: 'Equalization (Minimum)',
  equalization_formula: 'Equalization (Formula)',
  equalization_performance: 'Equalization (Performance)',
  conditional_current: 'Conditional (Current)',
  conditional_capital: 'Conditional (Capital)',
  special_current: 'Special (Current)',
  special_capital: 'Special (Capital)',
  complementary_capital: 'Complementary (Capital)',
};

// ---------------------------------------------------------------------------
// Census metric allowlist — explicit numerator + denominator slugs per metric.
// ---------------------------------------------------------------------------

/**
 * One census-derived ratio. `numeratorSlugs` are summed across the district;
 * `denominatorSlug` is the table's own `rowtotal`. Pillar tags the mission area.
 */
export type CensusMetricSpec = {
  id: string;
  label: string;
  /** Plain-language description of what the ratio measures. */
  description: string;
  /** Slugs whose values sum to the numerator (district roll-up). */
  numeratorSlugs: readonly string[];
  /** The table's own per-palika total slug (the denominator). */
  denominatorSlug: string;
  /** Which of the 5 Public Pillars this serves (display only). */
  pillar: string;
};

/**
 * The allowlist. Every slug here was verified to exist with data for all 5
 * launch districts. All are from single-row-per-palika tables.
 */
export const CENSUS_METRICS: readonly CensusMetricSpec[] = [
  {
    id: 'home-ownership',
    label: 'Home ownership',
    description: 'Share of households that own the house they live in.',
    numeratorSlugs: ['hhld01-ownershipofhouse-a-own'],
    denominatorSlug: 'hhld01-ownershipofhouse-rowtotal',
    pillar: 'Money Becomes Wealth',
  },
  {
    id: 'internet-access',
    label: 'Internet access',
    description: 'Share of households with an internet connection at home.',
    numeratorSlugs: ['hhld10-householdfacility-g-internet'],
    denominatorSlug: 'hhld10-householdfacility-rowtotal',
    pillar: 'Money Becomes Wealth',
  },
  {
    id: 'female-house-and-land',
    label: 'Female house & land ownership',
    description:
      'Share of households where a female member owns both house and land — the strongest asset-ownership signal.',
    numeratorSlugs: ['hhld11-femaleownershipoffixedasset-c-houseandland'],
    denominatorSlug: 'hhld11-femaleownershipoffixedasset-rowtotal',
    pillar: 'Money Becomes Wealth',
  },
  {
    id: 'household-entrepreneurship',
    label: 'Household entrepreneurship',
    description: 'Share of households operating at least one small-scale business.',
    // Derived as (rowtotal − no-business): every household either runs a
    // business or is counted in the explicit `nobusiness` column.
    numeratorSlugs: ['hhld12-smallscalebusiness-rowtotal', 'hhld12-smallscalebusiness-nobusiness'],
    denominatorSlug: 'hhld12-smallscalebusiness-rowtotal',
    pillar: 'Money Becomes Wealth',
  },
];

/**
 * For the entrepreneurship metric the numerator is (rowtotal − nobusiness).
 * We encode the subtractive term here rather than inventing a generic
 * arithmetic DSL — it is the only metric that needs it, and being explicit
 * keeps the aggregation auditable.
 */
const SUBTRACTIVE_NUMERATOR_SLUGS: ReadonlySet<string> = new Set([
  'hhld12-smallscalebusiness-nobusiness',
]);

// ---------------------------------------------------------------------------
// Pillar fields NOT yet ingested — surfaced via MissingDataPanel, never faked.
// ---------------------------------------------------------------------------

/** A Pillar field we deliberately do NOT render because the data is not ingested. */
export type MissingPillarField = {
  label: string;
  pillar: string;
  /** Why it is absent / what would unblock it. */
  reason: string;
};

/**
 * These are part of the District MRI vision but have no ingested source yet.
 * We list them honestly instead of zero-filling (Data Continuity Protocol).
 */
export const MISSING_PILLAR_FIELDS: readonly MissingPillarField[] = [
  {
    label: 'Remittance received (NPR)',
    pillar: 'Money In',
    reason: 'No remittance-by-recipient-district series exists in the NRB DNE catalog yet.',
  },
  {
    label: 'Capital-expenditure execution rate',
    pillar: 'Money Becomes Wealth',
    reason: 'Local-government capex-vs-budget actuals are not yet ingested (FCGO/MoF pipeline).',
  },
  {
    label: 'Agricultural production',
    pillar: 'Money Becomes Wealth',
    reason: 'District-level crop/livestock statistics (MoALD) are not yet parsed.',
  },
  {
    label: 'Disaster & climate loss',
    pillar: 'Money Wasted',
    reason: 'District disaster-loss data has no registered source yet.',
  },
];

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

export type GrantTotal = {
  grantType: GrantType;
  label: string;
  totalNprCrore: number;
};

export type FiscalSummary = {
  fiscalYearBs: string;
  unit: string;
  grandTotalNprCrore: number;
  byGrantType: GrantTotal[];
};

export type CensusMetric = {
  id: string;
  label: string;
  description: string;
  pillar: string;
  /** Ratio in [0,1]; null when the denominator is zero / data absent. */
  ratio: number | null;
  /** Numerator household/person count (already net of subtractive terms). */
  numerator: number;
  /** Denominator household/person count (the table rowtotal). */
  denominator: number;
};

export type DistrictMriData = {
  districtEn: string;
  /** Number of local levels (palikas) that contributed rows. */
  palikaCount: number;
  fiscal: FiscalSummary | null;
  censusMetrics: CensusMetric[];
  /** Census reference year, if any census data is present. */
  censusYearAd: string | null;
};

// ---------------------------------------------------------------------------
// DB-boundary row schemas (Zod-validated — sanctioned post-Zod pattern)
// ---------------------------------------------------------------------------

const FiscalRowSchema = z.object({
  grant_type: z.string(),
  total_amount: z.string(),
  unit: z.string(),
  fiscal_year_bs: z.string(),
});

const CensusRowSchema = z.object({
  indicator_slug: z.string(),
  total_value: z.string(),
});

const PalikaCountRowSchema = z.object({
  palika_count: z.string(),
  census_year_ad: z.string().nullable(),
});

// Keep the GRANT_TYPE_LABELS map as the canonical set of known grant types.
const KNOWN_GRANT_TYPES = new Set<string>(Object.keys(GRANT_TYPE_LABELS));

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Aggregate one district's fiscal transfers + census ratios.
 *
 * @param districtEn EXACT `entities.metadata->>'district_en'` string. Callers
 *   pass `LaunchDistrict.districtEn`; the value is parameterised ($1) — never
 *   interpolated — so it is injection-safe.
 */
export async function getDistrictMriData(districtEn: string): Promise<Result<DistrictMriData>> {
  // --- (0) Palika count + census reference year for this district ---------
  const countResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          COUNT(DISTINCT e.id)::text AS palika_count,
          MIN(c.census_year_ad)      AS census_year_ad
        FROM entities e
        LEFT JOIN census_facts c ON c.entity_id = e.id
        WHERE e.kind = 'local_level'
          AND e.metadata->>'district_en' = ${districtEn}
      `,
    ),
  );
  if (!countResult.ok) return countResult;
  const countParsed = z.array(PalikaCountRowSchema).safeParse(countResult.value);
  if (!countParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `district-mri palika-count returned unexpected shape: ${countParsed.error.message}`,
    });
  }
  const countRow = countParsed.data[0];
  const palikaCount = countRow ? Number(countRow.palika_count) : 0;
  if (palikaCount === 0) {
    // Unknown district name → no local levels matched. Typed NotFound; the page
    // renders an empty state rather than throwing.
    return err({ kind: 'NotFound', resource: 'district', id: districtEn });
  }
  const censusYearAd = countRow?.census_year_ad ?? null;

  // --- (1) Fiscal transfers grouped by grant_type ------------------------
  const fiscalResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          t.grant_type,
          SUM(t.amount_npr)::text AS total_amount,
          MIN(t.unit)             AS unit,
          MIN(t.fiscal_year_bs)   AS fiscal_year_bs
        FROM local_government_fiscal_transfers t
        JOIN entities e
          ON e.id = t.local_level_entity_id
         AND e.kind = 'local_level'
        WHERE e.metadata->>'district_en' = ${districtEn}
        GROUP BY t.grant_type
        ORDER BY t.grant_type
      `,
    ),
  );
  if (!fiscalResult.ok) return fiscalResult;
  const fiscalParsed = z.array(FiscalRowSchema).safeParse(fiscalResult.value);
  if (!fiscalParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `district-mri fiscal aggregation returned unexpected shape: ${fiscalParsed.error.message}`,
    });
  }
  const fiscal = buildFiscalSummary(fiscalParsed.data);

  // --- (2) Census facts for the allowlisted slugs only -------------------
  // Build a parameterised IN list. Each slug is its own bind param (via
  // sql.join), so this stays injection-safe and avoids the postgres-js
  // tuple-vs-array pitfall that `= ANY(<js array>)` hits inside a sql template.
  const allowlistSlugs = collectAllowlistSlugs();
  const slugList = sql.join(
    allowlistSlugs.map((s) => sql`${s}`),
    sql`, `,
  );
  const censusResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          c.indicator_slug,
          SUM(c.value)::text AS total_value
        FROM census_facts c
        JOIN entities e
          ON e.id = c.entity_id
         AND e.kind = 'local_level'
        WHERE e.metadata->>'district_en' = ${districtEn}
          AND c.indicator_slug IN (${slugList})
        GROUP BY c.indicator_slug
      `,
    ),
  );
  if (!censusResult.ok) return censusResult;
  const censusParsed = z.array(CensusRowSchema).safeParse(censusResult.value);
  if (!censusParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `district-mri census aggregation returned unexpected shape: ${censusParsed.error.message}`,
    });
  }
  const censusMetrics = buildCensusMetrics(censusParsed.data);

  return ok({
    districtEn,
    palikaCount,
    fiscal,
    censusMetrics,
    censusYearAd,
  });
}

// ---------------------------------------------------------------------------
// Pure builders (testable, no I/O)
// ---------------------------------------------------------------------------

function buildFiscalSummary(
  rows: readonly z.infer<typeof FiscalRowSchema>[],
): FiscalSummary | null {
  if (rows.length === 0) return null;
  const first = rows[0];
  if (!first) return null;

  const byGrantType: GrantTotal[] = [];
  let grandTotal = 0;
  for (const row of rows) {
    const amount = Number(row.total_amount);
    if (!isFinite(amount)) continue;
    grandTotal += amount;
    // Only surface grant types we have a label for; unknowns are summed into
    // the grand total but not given a mislabeled row.
    if (KNOWN_GRANT_TYPES.has(row.grant_type)) {
      const gt = row.grant_type as GrantType;
      byGrantType.push({ grantType: gt, label: GRANT_TYPE_LABELS[gt], totalNprCrore: amount });
    }
  }
  // Sort descending by amount so the dominant grant leads.
  byGrantType.sort((a, b) => b.totalNprCrore - a.totalNprCrore);

  return {
    fiscalYearBs: first.fiscal_year_bs,
    unit: first.unit,
    grandTotalNprCrore: grandTotal,
    byGrantType,
  };
}

function collectAllowlistSlugs(): string[] {
  const set = new Set<string>();
  for (const metric of CENSUS_METRICS) {
    set.add(metric.denominatorSlug);
    for (const s of metric.numeratorSlugs) set.add(s);
  }
  return [...set];
}

function buildCensusMetrics(rows: readonly z.infer<typeof CensusRowSchema>[]): CensusMetric[] {
  const byslug = new Map<string, number>();
  for (const row of rows) {
    const v = Number(row.total_value);
    if (isFinite(v)) byslug.set(row.indicator_slug, v);
  }

  const out: CensusMetric[] = [];
  for (const metric of CENSUS_METRICS) {
    const denominator = byslug.get(metric.denominatorSlug) ?? 0;
    // Sum the numerator slugs, subtracting any flagged subtractive terms
    // (only the entrepreneurship `nobusiness` column today).
    let numerator = 0;
    for (const s of metric.numeratorSlugs) {
      const v = byslug.get(s) ?? 0;
      numerator += SUBTRACTIVE_NUMERATOR_SLUGS.has(s) ? -v : v;
    }
    const ratio = denominator > 0 ? numerator / denominator : null;
    out.push({
      id: metric.id,
      label: metric.label,
      description: metric.description,
      pillar: metric.pillar,
      ratio,
      numerator,
      denominator,
    });
  }
  return out;
}
