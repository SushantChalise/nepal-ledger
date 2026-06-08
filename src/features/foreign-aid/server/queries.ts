/**
 * Foreign-aid server queries (MoF White Book — "Money In" external financing).
 *
 * Reads `foreign_aid_facts` (ADR-0017) and pivots it to a ranked breakdown of
 * foreign aid entering Nepal by development partner (donor) and by spending
 * ministry (sector), split into GRANT (need not be repaid) vs LOAN (must be
 * repaid), for one fiscal-year edition.
 *
 * SEMANTIC NOTE (see docs/sources/mof-whitebook-foreign-aid.md + ADR-0017):
 *   - `base_indicator_slug = 'foreign-aid-grant'` = the Total Grant column.
 *   - `base_indicator_slug = 'foreign-aid-loan'`  = the Total Loan column.
 *   A "donor" row is one development partner (e.g. ADB, IDA, India); a "sector"
 *   row is one recipient ministry. The grant/loan split is the headline story:
 *   loans add to Nepal's external debt, grants do not.
 *
 * UNIT (ADR-0011 / ADR-0017 — THE CRUX): the White Book money unit VARIES BY
 *   EDITION and is carried per-row in `unit` ('npr_lakh' for FY2020/21,
 *   'npr_thousand' for FY2015/16). Raw values are NEVER summed across editions.
 *   This layer converts every row to NPR billion via `toBillion(value, unit)`
 *   from `format.ts` BEFORE any addition, so the totals it returns are already
 *   in a single, safe-to-sum unit (billion). All values on the output types are
 *   NPR billion — downstream never sees a raw lakh/thousand figure.
 *
 * SCOPE: only the foreign-aid feature. Reads from the DB directly (read-only);
 * does NOT edit any repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';

import { toBillion, type ForeignAidUnit } from '../format';

/** Base-measure slug: the Total Grant column (aid that need not be repaid). */
export const GRANT_SLUG = 'foreign-aid-grant';
/** Base-measure slug: the Total Loan column (aid that must be repaid). */
export const LOAN_SLUG = 'foreign-aid-loan';

/** Latest White Book edition in the corpus (FY 2020/21). Headline ranking. */
export const LATEST_PERIOD_BS = '2077/78';
/** Earlier edition (FY 2015/16) — shown as a pre-COVID comparison point. */
export const PRIOR_PERIOD_BS = '2072/73';

// ---------------------------------------------------------------------------
// Output types — every monetary field is NPR BILLION (already converted).
// ---------------------------------------------------------------------------

/** One dimension member (a donor or a ministry) with its grant/loan split. */
export type AidMember = {
  /** Kebab slug of the member (stable row key), e.g. 'adb---general'. */
  slug: string;
  /** Raw source label (English donor/ministry name), shown faithfully. */
  label: string;
  /** Grant total for this member, in NPR billion. 0 if absent. */
  grant: number;
  /** Loan total for this member, in NPR billion. 0 if absent. */
  loan: number;
  /** Grant + loan for this member, in NPR billion. */
  total: number;
};

/** A complete ranked breakdown for one dimension (donor OR sector). */
export type AidBreakdown = {
  /** Members ranked by total aid (grant + loan), descending. */
  members: AidMember[];
  /** Number of distinct members. */
  memberCount: number;
  /** Sum of grants across members, in NPR billion. */
  totalGrant: number;
  /** Sum of loans across members, in NPR billion. */
  totalLoan: number;
  /** Sum of all aid (grant + loan) across members, in NPR billion. */
  grandTotal: number;
};

/** The headline edition plus a single comparison edition. */
export type ForeignAid = {
  /** BS fiscal-year label of the headline edition (e.g. '2077/78'). */
  fiscalYearBs: string;
  /** AD fiscal-year label of the headline edition (e.g. '2020/21'). */
  fiscalYearAd: string;
  /** Ranked breakdown by development partner (donor) — the headline ranking. */
  byDonor: AidBreakdown;
  /** Ranked breakdown by recipient ministry (sector). */
  bySector: AidBreakdown;
  /** Confidence grade for the source (White Book → 'B'). */
  confidence: ConfidenceGrade;
  /**
   * Compact donor-total comparison for the prior edition, already in NPR
   * billion. Null when the prior edition is not present (never fabricated).
   */
  priorDonor: {
    fiscalYearBs: string;
    fiscalYearAd: string;
    totalGrant: number;
    totalLoan: number;
    grandTotal: number;
  } | null;
};

// ---------------------------------------------------------------------------
// DB boundary — Zod over the untyped postgres-js result (CONTEXT_RULES (a)).
// ---------------------------------------------------------------------------

// One pivoted member row. `grant` / `loan` arrive as numeric strings (or null
// when a member lacks that measure). `unit` is constrained to the two known
// White Book units so a row carrying anything else is rejected here rather than
// silently mis-scaled downstream.
const MemberRowSchema = z.object({
  slug: z.string(),
  label: z.string(),
  grant: z.string().nullable(),
  loan: z.string().nullable(),
  unit: z.enum(['npr_lakh', 'npr_thousand']),
});
type MemberRow = z.infer<typeof MemberRowSchema>;

const EditionMetaSchema = z.object({
  reporting_period_bs: z.string(),
  fiscal_year_ad_label: z.string().nullable(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});

const PriorTotalsSchema = z.object({
  reporting_period_bs: z.string(),
  fiscal_year_ad_label: z.string().nullable(),
  grant: z.string().nullable(),
  loan: z.string().nullable(),
  unit: z.enum(['npr_lakh', 'npr_thousand']),
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Pivot the two measure rows of each member into one row, ranked by total
 * (grant + loan) descending in SQL. `unit` is homogeneous within an edition, so
 * MIN(unit) is a safe marginal pick; a member's grant and loan share the same
 * `dimension_value`, so MAX(value) FILTER collapses them. Sorting by the raw
 * summed value is correct WITHIN one edition (a single unit), which this query
 * always is — the conversion to billion happens after, in TS.
 */
function memberPivotSql(dimensionKind: 'donor' | 'sector', periodBs: string) {
  return sql`
    SELECT
      dimension_value                                            AS slug,
      MIN(dimension_label)                                       AS label,
      MAX(value) FILTER (WHERE base_indicator_slug = ${GRANT_SLUG})::text AS grant,
      MAX(value) FILTER (WHERE base_indicator_slug = ${LOAN_SLUG})::text  AS loan,
      MIN(unit)                                                  AS unit
    FROM foreign_aid_facts
    WHERE dimension_kind = ${dimensionKind}
      AND reporting_period_bs = ${periodBs}
      AND base_indicator_slug IN (${GRANT_SLUG}, ${LOAN_SLUG})
    GROUP BY dimension_value
    ORDER BY
      COALESCE(MAX(value) FILTER (WHERE base_indicator_slug = ${GRANT_SLUG}), 0)
      + COALESCE(MAX(value) FILTER (WHERE base_indicator_slug = ${LOAN_SLUG}), 0) DESC,
      label ASC
  `;
}

/**
 * Build a ranked breakdown from validated member rows, converting each row's
 * grant/loan to NPR billion with ITS OWN unit before any addition. A null
 * measure is a genuine 0 (the member has no grant or no loan), never a
 * fabricated fill.
 */
function buildBreakdown(rows: readonly MemberRow[]): AidBreakdown {
  const members: AidMember[] = [];
  let totalGrant = 0;
  let totalLoan = 0;

  for (const row of rows) {
    const unit: ForeignAidUnit = row.unit;
    const grant = row.grant === null ? 0 : toBillion(Number(row.grant), unit);
    const loan = row.loan === null ? 0 : toBillion(Number(row.loan), unit);
    totalGrant += grant;
    totalLoan += loan;
    members.push({ slug: row.slug, label: row.label, grant, loan, total: grant + loan });
  }

  return {
    members,
    memberCount: members.length,
    totalGrant,
    totalLoan,
    grandTotal: totalGrant + totalLoan,
  };
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Fetch the foreign-aid breakdown for the latest White Book edition (donor +
 * sector), plus a compact donor-total comparison for the prior edition.
 *
 * Returns NotFound when the latest edition has no facts; never throws — callers
 * render typed states. All monetary fields on the result are NPR billion.
 */
export async function getForeignAidBreakdown(): Promise<Result<ForeignAid>> {
  // 1. Edition metadata (period AD label + confidence) for the latest edition.
  const metaResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          reporting_period_bs,
          MIN(fiscal_year_ad_label) AS fiscal_year_ad_label,
          MIN(confidence_grade)     AS confidence_grade
        FROM foreign_aid_facts
        WHERE reporting_period_bs = ${LATEST_PERIOD_BS}
        GROUP BY reporting_period_bs
      `,
    ),
  );
  if (!metaResult.ok) return metaResult;

  const metaParsed = z.array(EditionMetaSchema).safeParse(metaResult.value);
  if (!metaParsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `foreign-aid edition-meta query returned unexpected shape: ${metaParsed.error.message}`,
    });
  }
  const meta = metaParsed.data[0];
  if (!meta) {
    return err({
      kind: 'NotFound',
      resource: 'foreign_aid_facts',
      id: `reporting_period_bs=${LATEST_PERIOD_BS}`,
    });
  }

  // 2. Donor + sector pivots for the latest edition.
  const donorResult = await safeQuery(() =>
    db().execute(memberPivotSql('donor', LATEST_PERIOD_BS)),
  );
  if (!donorResult.ok) return donorResult;
  const sectorResult = await safeQuery(() =>
    db().execute(memberPivotSql('sector', LATEST_PERIOD_BS)),
  );
  if (!sectorResult.ok) return sectorResult;

  const donorParsed = z.array(MemberRowSchema).safeParse(donorResult.value);
  const sectorParsed = z.array(MemberRowSchema).safeParse(sectorResult.value);
  if (!donorParsed.success || !sectorParsed.success) {
    const detail = !donorParsed.success ? donorParsed.error.message : sectorParsed.error!.message;
    return err({
      kind: 'QueryFailed',
      detail: `foreign-aid pivot query returned unexpected row shape: ${detail}`,
    });
  }

  const byDonor = buildBreakdown(donorParsed.data);
  const bySector = buildBreakdown(sectorParsed.data);

  if (byDonor.members.length === 0 || byDonor.grandTotal <= 0) {
    return err({
      kind: 'NotFound',
      resource: 'foreign_aid_facts',
      id: `dimension_kind=donor, reporting_period_bs=${LATEST_PERIOD_BS}`,
    });
  }

  // 3. Prior-edition donor totals for a comparison row. Absent → null (never
  //    fabricated). A failed query degrades to null rather than failing the page.
  const priorDonor = await getPriorDonorTotals();

  return ok({
    fiscalYearBs: meta.reporting_period_bs,
    fiscalYearAd: meta.fiscal_year_ad_label ?? meta.reporting_period_bs,
    byDonor,
    bySector,
    confidence: meta.confidence_grade,
    priorDonor,
  });
}

/**
 * Compact donor grand-totals for the prior edition (FY2015/16), already in NPR
 * billion. A single aggregate row per measure; converted with the edition's own
 * unit. Returns null on absence or query failure — the comparison is optional
 * context, not load-bearing, and must never block or fabricate the headline.
 */
async function getPriorDonorTotals(): Promise<ForeignAid['priorDonor']> {
  const result = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          reporting_period_bs,
          MIN(fiscal_year_ad_label) AS fiscal_year_ad_label,
          SUM(value) FILTER (WHERE base_indicator_slug = ${GRANT_SLUG})::text AS grant,
          SUM(value) FILTER (WHERE base_indicator_slug = ${LOAN_SLUG})::text  AS loan,
          MIN(unit)                                                  AS unit
        FROM foreign_aid_facts
        WHERE dimension_kind = 'donor'
          AND reporting_period_bs = ${PRIOR_PERIOD_BS}
          AND base_indicator_slug IN (${GRANT_SLUG}, ${LOAN_SLUG})
        GROUP BY reporting_period_bs
      `,
    ),
  );
  if (!result.ok) return null;

  const parsed = z.array(PriorTotalsSchema).safeParse(result.value);
  if (!parsed.success) return null;
  const row = parsed.data[0];
  if (!row) return null;

  const unit: ForeignAidUnit = row.unit;
  const totalGrant = row.grant === null ? 0 : toBillion(Number(row.grant), unit);
  const totalLoan = row.loan === null ? 0 : toBillion(Number(row.loan), unit);
  if (totalGrant + totalLoan <= 0) return null;

  return {
    fiscalYearBs: row.reporting_period_bs,
    fiscalYearAd: row.fiscal_year_ad_label ?? row.reporting_period_bs,
    totalGrant,
    totalLoan,
    grandTotal: totalGrant + totalLoan,
  };
}
