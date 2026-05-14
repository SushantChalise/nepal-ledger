/**
 * Promote a staging row into `approved_indicator_values` atomically.
 *
 * The insert into approved AND the delete of staging happen inside a single
 * Drizzle transaction wrapped by `safeQuery`. If either statement fails the
 * transaction aborts, no partial state lands, and the returned `AppError`
 * propagates to the validation driver.
 *
 * See docs/DATA_PIPELINE.md §"The Validation Job" §"Outcomes".
 */

import { eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  approvedIndicatorValues,
  stagingIndicatorValues,
  type ApprovedIndicatorValueRow,
  type StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import { err, ok, type Result } from '@/lib/errors';

export type PromoteInput = {
  stagingRow: StagingIndicatorValueRow;
  /** Required: validation has guaranteed indicator resolution by this point. */
  indicatorId: string;
  /** revision_number = (prior approved row revisionNumber + 1) OR 0 for first. */
  revisionNumber: number;
  /** Free-form attribution: validator name, agent label, or human handle. */
  promotedBy: string;
};

export async function promoteStagingRow(
  input: PromoteInput,
): Promise<Result<ApprovedIndicatorValueRow>> {
  const { stagingRow, indicatorId, revisionNumber, promotedBy } = input;

  const result = await safeQuery(() =>
    db().transaction(async (tx) => {
      const inserted = await tx
        .insert(approvedIndicatorValues)
        .values({
          sourceDocumentId: stagingRow.sourceDocumentId,
          indicatorId,
          value: stagingRow.value,
          unit: stagingRow.unit,
          reportingPeriodType: stagingRow.reportingPeriodType,
          reportingPeriodBs: stagingRow.reportingPeriodBs,
          reportingPeriodAdStart: stagingRow.reportingPeriodAdStart,
          reportingPeriodAdEnd: stagingRow.reportingPeriodAdEnd,
          publicationDateAd: stagingRow.publicationDateAd,
          publicationDateBs: stagingRow.publicationDateBs,
          fiscalYearBs: stagingRow.fiscalYearBs,
          fiscalYearAdLabel: stagingRow.fiscalYearAdLabel,
          confidenceGrade: stagingRow.confidenceGradeProposed,
          revisionNumber,
          promotedBy,
          notes: stagingRow.parserNotes,
        })
        .returning();

      await tx.delete(stagingIndicatorValues).where(eq(stagingIndicatorValues.id, stagingRow.id));

      return inserted;
    }),
  );

  if (!result.ok) return result;
  const row = result.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'promoteStagingRow: transaction returned no inserted row',
    });
  }
  return ok(row);
}
