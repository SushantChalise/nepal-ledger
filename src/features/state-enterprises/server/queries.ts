/**
 * State-enterprises server queries (Public Enterprise X-Ray).
 *
 * Reads the MoF / DPM-Office Yellow Book Annex-1 (loan-investment-by-enterprise)
 * facts from `dne_facts` and pivots them to one row per public enterprise with
 * its government EQUITY (`soe-government-share`) and outstanding government LOAN
 * principal (`soe-loan-principal`) for the BS 2080/81 fiscal year.
 *
 * SEMANTIC NOTE (see scrapers/mof_yellowbook/parser.py + ADR-0015):
 *   - `soe-government-share` = paid-in government equity / share capital (शेयर).
 *   - `soe-loan-principal`   = outstanding government-loan principal (ऋण).
 *   These are two DISTINCT exposures of the state to each enterprise, NOT a
 *   revenue or profit figure. "Total exposure" here means equity + loan, the
 *   government's combined capital stake.
 *
 * UNIT (ADR-0011 — read the header, don't fuzzy-match):
 *   Every row is `unit = 'npr_thousand'` (the Annex-1 header states "(रु. हजारमा)"
 *   = NPR in thousand). Raw thousands are NEVER displayed; `format.ts` converts
 *   to NPR billion (value / 1e6). E.g. NEA government share 181,330,245 thousand
 *   → NPR 181.33 billion.
 *
 * DIMENSION: `dimension_kind = 'public_enterprise'`; `dimension_value` is the
 *   kebab slug of the enterprise name; `dimension_label` is the raw (mostly
 *   Devanagari) enterprise name, rendered faithfully (some carry known
 *   pdfplumber glyph-reorder artifacts — displayed as stored, never "fixed").
 *
 * CONFIDENCE: B — government-published annual review compiled from
 *   enterprise-submitted statements; figures are revised across editions.
 *
 * SCOPE: only the state-enterprises feature. Reads from the DB directly
 * (read-only); does NOT edit any existing repository in
 * src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';

/** Dimension kind for public-enterprise Yellow Book facts. */
export const PUBLIC_ENTERPRISE_DIMENSION_KIND = 'public_enterprise';
/** Base measure slug: paid-in government equity / share capital. */
export const SHARE_SLUG = 'soe-government-share';
/** Base measure slug: outstanding government-loan principal. */
export const LOAN_SLUG = 'soe-loan-principal';
/** BS fiscal year of the bundled Yellow Book edition (Annex-1 header). */
export const REPORTING_PERIOD_BS = '2080/81';

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** One public enterprise with its government equity vs loan exposure. */
export type EnterpriseExposure = {
  /** Kebab slug of the enterprise name (stable identifier / row key). */
  slug: string;
  /** Raw source enterprise name (mostly Devanagari), displayed faithfully. */
  label: string;
  /** Government equity / share capital, in NPR thousand. 0 if absent. */
  governmentShare: number;
  /** Outstanding government-loan principal, in NPR thousand. 0 if absent. */
  loanPrincipal: number;
  /** Combined government exposure (equity + loan), in NPR thousand. */
  total: number;
};

export type StateEnterprises = {
  /** Enterprises ranked by total government exposure, descending. */
  enterprises: EnterpriseExposure[];
  /** Number of distinct enterprises. */
  enterpriseCount: number;
  /** Sum of government equity across all enterprises, in NPR thousand. */
  totalShare: number;
  /** Sum of loan principal across all enterprises, in NPR thousand. */
  totalLoan: number;
  /** Combined government exposure across all enterprises, in NPR thousand. */
  grandTotal: number;
  /** BS fiscal year label (e.g. '2080/81'). */
  fiscalYearBs: string;
  /** Confidence grade for the source (Yellow Book → 'B'). */
  confidence: ConfidenceGrade;
};

// ---------------------------------------------------------------------------
// DB boundary
// ---------------------------------------------------------------------------

// Validated at the DB boundary with Zod — the sanctioned alternative to an
// `as` cast on the untyped postgres-js result (CONTEXT_RULES §"Cast Escape
// Hatches" (a)). The SQL column list below defines the shape. `share` / `loan`
// arrive as numeric strings (or null when an enterprise lacks that measure).
const EnterpriseRowSchema = z.object({
  slug: z.string(),
  label: z.string(),
  share: z.string().nullable(),
  loan: z.string().nullable(),
  fiscal_year_bs: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});
type EnterpriseRow = z.infer<typeof EnterpriseRowSchema>;

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Fetch the public enterprises with both government-capital measures for BS
 * 2080/81, pivoted to one row per enterprise and ranked by total exposure
 * (equity + loan) descending.
 *
 * The pivot is a GROUP BY `dimension_value` with conditional aggregates: each
 * enterprise has at most one `soe-government-share` row and one
 * `soe-loan-principal` row for the period, so `MAX(value) FILTER (WHERE …)`
 * collapses the two measure rows into one output row. `dimension_label` /
 * `fiscal_year_bs` / `confidence_grade` are homogeneous per enterprise, so
 * MAX/MIN over them is a safe marginal pick. Sorting by the summed exposure is
 * done in SQL; ties fall back to the label for a stable order.
 *
 * Returns NotFound when no public-enterprise facts exist; never throws —
 * callers render typed states.
 */
export async function getStateEnterpriseExposure(): Promise<Result<StateEnterprises>> {
  const rawResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          dimension_value                                            AS slug,
          MIN(dimension_label)                                       AS label,
          MAX(value) FILTER (WHERE base_indicator_slug = ${SHARE_SLUG})::text AS share,
          MAX(value) FILTER (WHERE base_indicator_slug = ${LOAN_SLUG})::text  AS loan,
          MIN(reporting_period_bs)                                   AS fiscal_year_bs,
          MIN(confidence_grade)                                      AS confidence_grade
        FROM dne_facts
        WHERE dimension_kind = ${PUBLIC_ENTERPRISE_DIMENSION_KIND}
          AND reporting_period_bs = ${REPORTING_PERIOD_BS}
          AND base_indicator_slug IN (${SHARE_SLUG}, ${LOAN_SLUG})
        GROUP BY dimension_value
        ORDER BY
          COALESCE(MAX(value) FILTER (WHERE base_indicator_slug = ${SHARE_SLUG}), 0)
          + COALESCE(MAX(value) FILTER (WHERE base_indicator_slug = ${LOAN_SLUG}), 0) DESC,
          label ASC
      `,
    ),
  );

  if (!rawResult.ok) return rawResult;

  const parsed = z.array(EnterpriseRowSchema).safeParse(rawResult.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `state-enterprise query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const rows: EnterpriseRow[] = parsed.data;

  if (rows.length === 0) {
    return err({
      kind: 'NotFound',
      resource: 'dne_facts',
      id: `dimension_kind=${PUBLIC_ENTERPRISE_DIMENSION_KIND}, reporting_period_bs=${REPORTING_PERIOD_BS}`,
    });
  }

  const enterprises: EnterpriseExposure[] = [];
  let totalShare = 0;
  let totalLoan = 0;

  for (const row of rows) {
    // numeric → number after a finite guard; a missing measure (null) is a
    // genuine 0 here (the enterprise carries no equity or no loan), never a
    // fabricated fill of a present-but-unreadable value.
    const share = row.share === null ? 0 : Number(row.share);
    const loan = row.loan === null ? 0 : Number(row.loan);
    const safeShare = Number.isFinite(share) ? share : 0;
    const safeLoan = Number.isFinite(loan) ? loan : 0;
    totalShare += safeShare;
    totalLoan += safeLoan;
    enterprises.push({
      slug: row.slug,
      label: row.label,
      governmentShare: safeShare,
      loanPrincipal: safeLoan,
      total: safeShare + safeLoan,
    });
  }

  const firstRow = rows[0];
  if (!firstRow) {
    return err({
      kind: 'QueryFailed',
      detail: 'getStateEnterpriseExposure: query returned empty rows array',
    });
  }

  return ok({
    enterprises,
    enterpriseCount: enterprises.length,
    totalShare,
    totalLoan,
    grandTotal: totalShare + totalLoan,
    fiscalYearBs: firstRow.fiscal_year_bs,
    confidence: firstRow.confidence_grade,
  });
}
