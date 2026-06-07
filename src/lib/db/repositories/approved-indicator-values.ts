/**
 * Approved Indicator Values repository.
 *
 * Production table the Pulse, Money Map, Fact Ledger and stories read.
 * Inserts happen exclusively through the validation job's promote path;
 * features never write here directly.
 */

import { and, desc, eq, gte } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import type { ReportingPeriodType } from '@/lib/db/schema/enums';
import {
  approvedIndicatorValues,
  type ApprovedIndicatorValueRow,
  type NewApprovedIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import { indicators } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';
import { sourceDocuments } from '@/lib/db/schema/source-documents';
import { err, ok, type Result } from '@/lib/errors';

export async function insertApprovedIndicatorValue(
  input: NewApprovedIndicatorValueRow,
): Promise<Result<ApprovedIndicatorValueRow>> {
  const inserted = await safeQuery(() =>
    db().insert(approvedIndicatorValues).values(input).returning(),
  );
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertApprovedIndicatorValue: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Find the latest approved row (highest revision_number) for an indicator
 * and a (periodType, periodBs). Returns ok(null) — not NotFound — when no
 * row matches: the validator's DuplicateCheck and RevisionFlowCheck treat
 * "no prior approved row" as a successful negative.
 */
export async function findLatestApprovedByPeriod(
  indicatorId: string,
  periodType: ReportingPeriodType,
  periodBs: string,
): Promise<Result<ApprovedIndicatorValueRow | null>> {
  const queried = await safeQuery(() =>
    db().query.approvedIndicatorValues.findFirst({
      where: and(
        eq(approvedIndicatorValues.indicatorId, indicatorId),
        eq(approvedIndicatorValues.reportingPeriodType, periodType),
        eq(approvedIndicatorValues.reportingPeriodBs, periodBs),
      ),
      orderBy: [desc(approvedIndicatorValues.revisionNumber)],
    }),
  );
  if (!queried.ok) return queried;
  return ok(queried.value ?? null);
}

/**
 * Trailing window of approved values for plausibility-band computation. The
 * validator computes mean/stdev across this window and warns rows that fall
 * outside ±5 stdev. Window is bounded by `since` (ad start) inclusive.
 */
export async function listApprovedTrailingForIndicator(
  indicatorId: string,
  since: Date,
): Promise<Result<ApprovedIndicatorValueRow[]>> {
  return safeQuery(() =>
    db().query.approvedIndicatorValues.findMany({
      where: and(
        eq(approvedIndicatorValues.indicatorId, indicatorId),
        gte(approvedIndicatorValues.reportingPeriodAdEnd, since),
      ),
      orderBy: [desc(approvedIndicatorValues.reportingPeriodAdEnd)],
    }),
  );
}

/**
 * Shape returned by listApprovedWithIndicator — one row per approved value
 * with the joined indicator metadata and source document metadata.
 */
export type ApprovedIndicatorWithMeta = {
  value: ApprovedIndicatorValueRow;
  indicator: IndicatorRow;
  sourceDocument: SourceDocumentRow;
};

/**
 * Read all approved indicator values joined to their indicator and source
 * document. Intended for the Pulse page; ordered by indicator category then
 * indicator slug for stable presentation.
 *
 * Returns ok([]) when the table is empty — callers render an empty state.
 * Only queries approved_indicator_values and indicators; does not touch
 * staging.
 */
export async function listApprovedWithIndicator(): Promise<Result<ApprovedIndicatorWithMeta[]>> {
  const queried = await safeQuery(() =>
    db()
      .select({
        value: approvedIndicatorValues,
        indicator: indicators,
        sourceDocument: sourceDocuments,
      })
      .from(approvedIndicatorValues)
      .innerJoin(indicators, eq(approvedIndicatorValues.indicatorId, indicators.id))
      .innerJoin(sourceDocuments, eq(approvedIndicatorValues.sourceDocumentId, sourceDocuments.id))
      .orderBy(indicators.category, indicators.slug),
  );
  if (!queried.ok) return queried;
  return ok(queried.value);
}
