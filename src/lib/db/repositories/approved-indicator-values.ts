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
