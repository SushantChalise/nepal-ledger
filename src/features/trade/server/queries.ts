/**
 * Trade server queries (customs foreign-trade detail — "Money Out" on goods).
 *
 * Reads the Department of Customs Foreign Trade Statistics facts from
 * `dne_facts` (ADR-0015) and assembles Nepal's merchandise-trade picture for one
 * reporting period: total imports, total exports, the trade deficit, and the
 * top-ranked commodities (by HS code) and partner countries on each side.
 *
 * SEMANTIC NOTE (see docs/sources/customs-monthly-trade.md + ADR-0015):
 *   - `customs-merchandise-imports` / `customs-merchandise-exports` are the two
 *     base MEASURES. The DIMENSION member is the HS-code commodity
 *     (`dimension_kind = 'commodity'`; `dimension_value` = HS code,
 *     `dimension_label` = description), the partner country
 *     (`dimension_kind = 'country'`), or the customs office
 *     (`dimension_kind = 'customs_office'`, not surfaced here).
 *   - Within one period the commodity-dimension total and the country-dimension
 *     total are the SAME aggregate trade value (verified against the live DB:
 *     both sum to 1,804,122,731 thousand for imports, 277,030,201 for exports in
 *     FY 2081/82). We take the commodity-dimension sum as the canonical total.
 *
 * UNIT (ADR-0011 — read the sheet header, don't fuzzy-match):
 *   Every row is `unit = 'npr_thousand'`. Raw thousands are NEVER displayed;
 *   `format.ts` converts to NPR billion / trillion. The import/export gap IS the
 *   story — Nepal's structural merchandise deficit (~6.5× in FY 2081/82).
 *
 * TOP-N HONESTY: there are 5,264 import commodities and 1,236 export commodities
 *   in the annual file. We rank and return only the top N (default 15) per list,
 *   and carry the FULL distinct count alongside so the page can state "top 15 of
 *   5,264" — never implying it rendered them all (Data Continuity Protocol).
 *
 * SCOPE: only the trade feature. Reads from the DB directly (read-only); does
 * NOT edit any existing repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';

/** Base measure slug: merchandise imports (customs). */
export const IMPORTS_SLUG = 'customs-merchandise-imports';
/** Base measure slug: merchandise exports (customs). */
export const EXPORTS_SLUG = 'customs-merchandise-exports';
/** Dimension kind: an HS-code commodity. */
export const COMMODITY_DIMENSION_KIND = 'commodity';
/** Dimension kind: a trading-partner country. */
export const COUNTRY_DIMENSION_KIND = 'country';
/** Default reporting period — the FY 2081/82 annual file (the headline floor). */
export const DEFAULT_PERIOD_BS = '2081/82';
/** Default number of ranked members returned per list. */
export const DEFAULT_TOP_N = 15;

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** One ranked dimension member (commodity or country) with its trade value. */
export type TradeMember = {
  /** Stable identifier: HS code (commodity) or country slug. */
  value: string;
  /** Faithful source label: commodity description or country name. */
  label: string;
  /** Trade value for this member, in NPR thousand. */
  amount: number;
  /** Share of the side's total (imports or exports), as a percentage (0–100). */
  sharePct: number;
};

/** A ranked breakdown plus the full member count behind it (top-N honesty). */
export type TradeBreakdown = {
  /** The top-N members, ranked by value descending. */
  members: TradeMember[];
  /** Total distinct members in the period (e.g. 5,264) — NOT just the shown N. */
  totalMembers: number;
};

/** One available reporting period in the customs data, for the period note. */
export type TradePeriod = {
  /** BS period label, e.g. '2081/82' or 'Jestha 2082'. */
  periodBs: string;
  /** reporting_period_type, e.g. 'annual' | 'year_to_date' | 'monthly'. */
  periodType: string;
};

export type TradeOverview = {
  /** The reporting period these figures describe (BS label). */
  periodBs: string;
  /** reporting_period_type of the selected period. */
  periodType: string;
  /** Human-readable measure description for the selected period (from the data). */
  importsName: string;
  /** Total merchandise imports for the period, in NPR thousand. */
  totalImports: number;
  /** Total merchandise exports for the period, in NPR thousand. */
  totalExports: number;
  /** Trade balance = exports − imports (negative = deficit), in NPR thousand. */
  tradeBalance: number;
  /** Top import commodities (by value) + the full commodity count. */
  importCommodities: TradeBreakdown;
  /** Top export commodities (by value) + the full commodity count. */
  exportCommodities: TradeBreakdown;
  /** Top import partner countries (by value) + the full country count. */
  importCountries: TradeBreakdown;
  /** Top export partner countries (by value) + the full country count. */
  exportCountries: TradeBreakdown;
  /** All reporting periods present in the customs data, newest-annual first. */
  availablePeriods: TradePeriod[];
  /** Confidence grade for the source (customs FTS → 'A'). */
  confidence: ConfidenceGrade;
};

// ---------------------------------------------------------------------------
// DB boundary schemas (Zod — sanctioned alternative to an `as` cast on the
// untyped postgres-js result; CONTEXT_RULES §"Cast Escape Hatches" (a)).
// ---------------------------------------------------------------------------

const TotalsRowSchema = z.object({
  slug: z.string(),
  total: z.string().nullable(),
  member_count: z.coerce.number(),
  base_name: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});

const MemberRowSchema = z.object({
  dim_value: z.string(),
  label: z.string(),
  amount: z.string(),
});

const PeriodRowSchema = z.object({
  period_bs: z.string(),
  period_type: z.string(),
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Fetch the top-N members of one (measure, dimension) slice for a period,
 * ranked by value descending. Pure read; returns a typed Result. The numeric
 * `value` column comes back from postgres-js as a string, validated by
 * `MemberRowSchema` and coerced with a finite guard at the call site.
 */
async function fetchTopMembers(
  baseSlug: string,
  dimensionKind: string,
  periodBs: string,
  topN: number,
): Promise<Result<Array<{ value: string; label: string; amount: number }>>> {
  // NOTE: do NOT alias `dimension_value AS value` — that would shadow the
  // numeric `value` column and make `ORDER BY value` sort the text dimension
  // slug (alphabetically), not the trade amount. The alias is `dim_value` so
  // `ORDER BY value DESC` unambiguously ranks by the numeric measure.
  const raw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          dimension_value    AS dim_value,
          dimension_label    AS label,
          value::text        AS amount
        FROM dne_facts
        WHERE base_indicator_slug = ${baseSlug}
          AND dimension_kind = ${dimensionKind}
          AND reporting_period_bs = ${periodBs}
        ORDER BY value DESC, dimension_value ASC
        LIMIT ${topN}
      `,
    ),
  );
  if (!raw.ok) return raw;

  const parsed = z.array(MemberRowSchema).safeParse(raw.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `trade top-members query (${baseSlug}/${dimensionKind}) returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const members = parsed.data
    .map((r) => ({ value: r.dim_value, label: r.label, amount: Number(r.amount) }))
    .filter((m) => Number.isFinite(m.amount));
  return ok(members);
}

/** Attach per-member shares (of the side total) to ranked members. */
function withShares(
  members: ReadonlyArray<{ value: string; label: string; amount: number }>,
  sideTotal: number,
): TradeMember[] {
  return members.map((m) => ({
    value: m.value,
    label: m.label,
    amount: m.amount,
    sharePct: sideTotal > 0 ? (m.amount / sideTotal) * 100 : 0,
  }));
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Assemble the full trade overview for `periodBs` (default the FY 2081/82
 * annual file): import / export totals, the deficit, and the top-`topN`
 * commodities and partner countries on each side, with the full member counts
 * for honest "top N of M" labelling.
 *
 * Totals + distinct member counts are derived in one GROUP BY over the
 * commodity dimension (the canonical aggregate). Each ranked list is a separate
 * scoped LIMIT query. Returns NotFound when the period has no customs facts;
 * never throws — callers render typed states.
 */
export async function getTradeOverview(
  periodBs: string = DEFAULT_PERIOD_BS,
  topN: number = DEFAULT_TOP_N,
): Promise<Result<TradeOverview>> {
  const safeTopN = Number.isFinite(topN) && topN > 0 ? Math.floor(topN) : DEFAULT_TOP_N;

  // 1. Totals + distinct commodity counts for both measures, one period. The
  //    commodity-dimension sum is the canonical period total (it equals the
  //    country-dimension sum — verified against the live DB).
  const totalsRaw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          base_indicator_slug              AS slug,
          SUM(value)::text                 AS total,
          COUNT(DISTINCT dimension_value)  AS member_count,
          MIN(base_indicator_name)         AS base_name,
          MIN(confidence_grade)            AS confidence_grade
        FROM dne_facts
        WHERE base_indicator_slug IN (${IMPORTS_SLUG}, ${EXPORTS_SLUG})
          AND dimension_kind = ${COMMODITY_DIMENSION_KIND}
          AND reporting_period_bs = ${periodBs}
        GROUP BY base_indicator_slug
      `,
    ),
  );
  if (!totalsRaw.ok) return totalsRaw;

  const totalsParsed = z.array(TotalsRowSchema).safeParse(totalsRaw.value);
  if (!totalsParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `trade totals query returned unexpected row shape: ${totalsParsed.error.message}`,
    });
  }
  if (totalsParsed.data.length === 0) {
    return err({
      kind: 'NotFound',
      resource: 'dne_facts',
      id: `customs trade, reporting_period_bs=${periodBs}`,
    });
  }

  const importsRow = totalsParsed.data.find((r) => r.slug === IMPORTS_SLUG);
  const exportsRow = totalsParsed.data.find((r) => r.slug === EXPORTS_SLUG);

  const toFinite = (s: string | null): number => {
    if (s === null) return 0;
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  };
  const totalImports = toFinite(importsRow?.total ?? null);
  const totalExports = toFinite(exportsRow?.total ?? null);
  const importCommodityCount = importsRow?.member_count ?? 0;
  const exportCommodityCount = exportsRow?.member_count ?? 0;

  // 2. Distinct country counts (separate dimension). Cheap aggregate.
  const countryCountsRaw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          base_indicator_slug              AS slug,
          NULL::text                       AS total,
          COUNT(DISTINCT dimension_value)  AS member_count,
          MIN(base_indicator_name)         AS base_name,
          MIN(confidence_grade)            AS confidence_grade
        FROM dne_facts
        WHERE base_indicator_slug IN (${IMPORTS_SLUG}, ${EXPORTS_SLUG})
          AND dimension_kind = ${COUNTRY_DIMENSION_KIND}
          AND reporting_period_bs = ${periodBs}
        GROUP BY base_indicator_slug
      `,
    ),
  );
  if (!countryCountsRaw.ok) return countryCountsRaw;
  const countryCountsParsed = z.array(TotalsRowSchema).safeParse(countryCountsRaw.value);
  if (!countryCountsParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `trade country-count query returned unexpected row shape: ${countryCountsParsed.error.message}`,
    });
  }
  const importCountryCount =
    countryCountsParsed.data.find((r) => r.slug === IMPORTS_SLUG)?.member_count ?? 0;
  const exportCountryCount =
    countryCountsParsed.data.find((r) => r.slug === EXPORTS_SLUG)?.member_count ?? 0;

  // 3. The four ranked lists (top-N each).
  const [impComm, expComm, impCtry, expCtry] = await Promise.all([
    fetchTopMembers(IMPORTS_SLUG, COMMODITY_DIMENSION_KIND, periodBs, safeTopN),
    fetchTopMembers(EXPORTS_SLUG, COMMODITY_DIMENSION_KIND, periodBs, safeTopN),
    fetchTopMembers(IMPORTS_SLUG, COUNTRY_DIMENSION_KIND, periodBs, safeTopN),
    fetchTopMembers(EXPORTS_SLUG, COUNTRY_DIMENSION_KIND, periodBs, safeTopN),
  ]);
  if (!impComm.ok) return impComm;
  if (!expComm.ok) return expComm;
  if (!impCtry.ok) return impCtry;
  if (!expCtry.ok) return expCtry;

  // 4. Available periods (for the period note / selector). Annual sorts first.
  //    GROUP BY (not SELECT DISTINCT) so the ORDER BY can reference the
  //    annual-first CASE expression — Postgres rejects an ORDER BY expression
  //    that is not in the select list under SELECT DISTINCT.
  const periodsRaw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          reporting_period_bs   AS period_bs,
          reporting_period_type AS period_type
        FROM dne_facts
        WHERE base_indicator_slug IN (${IMPORTS_SLUG}, ${EXPORTS_SLUG})
        GROUP BY reporting_period_bs, reporting_period_type
        ORDER BY
          CASE WHEN reporting_period_type = 'annual' THEN 0 ELSE 1 END,
          reporting_period_bs DESC
      `,
    ),
  );
  if (!periodsRaw.ok) return periodsRaw;
  const periodsParsed = z.array(PeriodRowSchema).safeParse(periodsRaw.value);
  if (!periodsParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `trade periods query returned unexpected row shape: ${periodsParsed.error.message}`,
    });
  }
  const availablePeriods: TradePeriod[] = periodsParsed.data.map((r) => ({
    periodBs: r.period_bs,
    periodType: r.period_type,
  }));

  // The period type / name come from whichever measure row is present.
  const selected = importsRow ?? exportsRow;
  const periodType = availablePeriods.find((p) => p.periodBs === periodBs)?.periodType ?? 'annual';

  return ok({
    periodBs,
    periodType,
    importsName: selected?.base_name ?? 'Merchandise imports (customs)',
    totalImports,
    totalExports,
    tradeBalance: totalExports - totalImports,
    importCommodities: {
      members: withShares(impComm.value, totalImports),
      totalMembers: importCommodityCount,
    },
    exportCommodities: {
      members: withShares(expComm.value, totalExports),
      totalMembers: exportCommodityCount,
    },
    importCountries: {
      members: withShares(impCtry.value, totalImports),
      totalMembers: importCountryCount,
    },
    exportCountries: {
      members: withShares(expCtry.value, totalExports),
      totalMembers: exportCountryCount,
    },
    availablePeriods,
    confidence: selected?.confidence_grade ?? 'A',
  });
}
