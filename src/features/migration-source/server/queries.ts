/**
 * Migration-source server queries (census Hhld19 — View A).
 *
 * Reads the CBS National Population & Housing Census 2021 "Absent Population by
 * Destination Country" table (`census_facts` rows, source_table_id
 * `Hhld19_AbsentPopnByCountry`) and ranks Nepal's absent population (migrant
 * workers living abroad on census night) by destination region.
 *
 * CRITICAL SEMANTIC NOTE (see docs/research/DATA_BUILDOUT_PLAN.md §6):
 *   Hhld19 is a PERSON COUNT of the absent population by DESTINATION, NOT
 *   remittance NPR. The unit is people (count). This page is the census
 *   complement to the labour-migration / Money-OUT story; it must never be
 *   labelled "remittance" or imply a rupee flow.
 *
 * DESTINATION GRANULARITY: the census groups destinations by REGION (SAARC,
 *   ASEAN, Mid-East, EU, …) with India broken out on its own. Individual
 *   countries such as Saudi Arabia, Qatar and the UAE roll up into "Mid-East";
 *   Malaysia rolls up into "ASEAN". We surface the region labels honestly
 *   rather than implying a per-country breakdown the source does not provide.
 *
 * AGGREGATION (verified against live DB — no double-counting):
 *   The slug shape is
 *     hhld19-absentpopnbycountry-<sex>-<agegrp>-<countrycode>-<countryname>
 *   with sex ∈ {total, male, female}, agegrp ∈ {00-14 … 65, all-ages,
 *   not-stated}, and country ∈ {a-india … m-notstd, rowtotal}. To get one
 *   non-overlapping value per (palika × destination) we take the single
 *   marginal slice sex='total' AND agegrp='all-ages' AND country != 'rowtotal',
 *   then SUM over all 753 palikas per destination. This was checked three ways
 *   against the table's own marginals (the 13 country sums equal the
 *   `rowtotal` marginal; the age-band sums equal `all-ages`; male+female equals
 *   total) — all match exactly at 2,190,592, the published 2021 absent-
 *   population figure.
 *
 * SCOPE: only the migration-source feature. Reads from the DB directly; does
 * NOT edit any existing repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';

/** Census source table id for the absent-population-by-country table. */
export const ABSENT_POPN_SOURCE_TABLE_ID = 'Hhld19_AbsentPopnByCountry';

/** Slug prefix for the non-double-counting marginal slice we aggregate. */
const MARGINAL_SLICE_PREFIX = 'hhld19-absentpopnbycountry-total-all-ages-';

/** Country-code → human-readable destination-region label. */
const DESTINATION_LABELS: Record<string, string> = {
  'a-india': 'India',
  'b-saarc': 'Other SAARC',
  'c-asean': 'ASEAN (incl. Malaysia)',
  'd-midleast': 'Middle East (incl. Saudi Arabia, Qatar, UAE)',
  'e-othrasian': 'Other Asia',
  'f-eucntry': 'European Union',
  'g-othreuropn': 'Other Europe',
  'h-northamericn': 'North America',
  'i-southamericn': 'South America',
  'j-african': 'Africa',
  'k-pacific': 'Australia & Pacific',
  'l-other': 'Other countries',
  'm-notstd': 'Not stated',
};

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** One destination region with its national absent-population count. */
export type DestinationCount = {
  /** Census country-code key (e.g. 'd-midleast'), stable identifier. */
  code: string;
  /** Human-readable destination-region label. */
  label: string;
  /** Absent population (people) with this destination, summed over palikas. */
  people: number;
  /** Share of the total absent population, as a percentage (0–100). */
  sharePct: number;
};

export type MigrationByCountry = {
  /** Destinations ranked by absent-population count, descending. */
  destinations: DestinationCount[];
  /** Total absent population across all destinations (people). */
  totalPeople: number;
  /** Number of palikas (local levels) contributing — expected 753. */
  palikaCount: number;
  /** Census reference year (AD), e.g. '2021'. */
  censusYearAd: string;
};

// ---------------------------------------------------------------------------
// DB boundary
// ---------------------------------------------------------------------------

// Validated at the DB boundary with Zod — the sanctioned alternative to an
// `as` cast on the untyped postgres-js result (CONTEXT_RULES §"Cast Escape
// Hatches" (a)). The SQL column list below defines the shape.
const CountryRowSchema = z.object({
  code: z.string(),
  total_people: z.string(),
  palika_count: z.coerce.number(),
  census_year_ad: z.string(),
});
type CountryRow = z.infer<typeof CountryRowSchema>;

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Fetch the absent population by destination region, ranked descending.
 *
 * Aggregates the single non-double-counting marginal slice (sex=total,
 * age=all-ages, per destination region, excluding the across-country
 * `rowtotal` marginal) summed over all palikas. Returns NotFound when the
 * census table has no matching rows; never throws — callers render typed
 * states.
 *
 * @param topN cap on the number of ranked destinations returned (default 15).
 *             The census has 13 destination regions, so the default returns
 *             them all; the parameter keeps the contract explicit and future-
 *             proof.
 */
export async function getMigrationByCountrySeries(topN = 15): Promise<Result<MigrationByCountry>> {
  // `LIKE prefix%` AND `NOT LIKE prefix||'rowtotal'` isolates the per-country
  // marginals of the (sex=total, age=all-ages) slice. The trailing country
  // segment is recovered by stripping the fixed prefix.
  const rowtotalSlug = `${MARGINAL_SLICE_PREFIX}rowtotal`;
  const likePattern = `${MARGINAL_SLICE_PREFIX}%`;

  const rawResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          replace(indicator_slug, ${MARGINAL_SLICE_PREFIX}, '') AS code,
          SUM(value)::text                                       AS total_people,
          COUNT(DISTINCT entity_id)                              AS palika_count,
          MIN(census_year_ad)                                    AS census_year_ad
        FROM census_facts
        WHERE source_table_id = ${ABSENT_POPN_SOURCE_TABLE_ID}
          AND indicator_slug LIKE ${likePattern}
          AND indicator_slug <> ${rowtotalSlug}
        GROUP BY code
        ORDER BY SUM(value) DESC
      `,
    ),
  );

  if (!rawResult.ok) return rawResult;

  const parsed = z.array(CountryRowSchema).safeParse(rawResult.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `migration-by-country query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const rows: CountryRow[] = parsed.data;

  if (rows.length === 0) {
    return err({
      kind: 'NotFound',
      resource: 'census_facts',
      id: `source_table_id=${ABSENT_POPN_SOURCE_TABLE_ID}`,
    });
  }

  // Sum to the national total first (the denominator for shares) over every
  // finite destination, then build the ranked rows.
  let totalPeople = 0;
  let palikaCount = 0;
  const censusYearAd = rows[0]?.census_year_ad ?? '2021';
  const counted: Array<{ code: string; people: number }> = [];

  for (const row of rows) {
    const people = Number(row.total_people);
    if (!Number.isFinite(people)) continue;
    totalPeople += people;
    palikaCount = Math.max(palikaCount, row.palika_count);
    counted.push({ code: row.code, people });
  }

  if (counted.length === 0 || totalPeople <= 0) {
    return err({
      kind: 'QueryFailed',
      detail: 'getMigrationByCountrySeries: no finite destination counts found',
    });
  }

  const destinations: DestinationCount[] = counted
    .slice(0, Math.max(0, topN))
    .map(({ code, people }) => ({
      code,
      label: DESTINATION_LABELS[code] ?? code,
      people,
      sharePct: (people / totalPeople) * 100,
    }));

  return ok({
    destinations,
    totalPeople,
    palikaCount,
    censusYearAd,
  });
}
