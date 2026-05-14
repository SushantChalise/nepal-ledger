/**
 * Write parser output to the database.
 *
 * Order matters:
 *   1. Insert one `parser_runs` row (status, version, counts, error_summary).
 *   2. Bulk-insert `staging_indicator_values` rows, all referencing that run.
 *   3. Bulk-insert `parser_errors` for granular diagnostics (optional; the
 *      run-row already carries an `error_summary` text field).
 *
 * The function is NOT transactional across all three steps: a parser_runs row
 * exists even if the staging insert fails — by design, so failed runs remain
 * visible for debugging. The staging + errors inserts use Drizzle's batched
 * `values(rows[])` so each is one round-trip.
 */

import { bulkInsertParserErrors, insertParserRun } from '@/lib/db/repositories/parser-runs';
import { bulkInsertStagingRows } from '@/lib/db/repositories/staging-indicator-values';
import type { NewStagingIndicatorValueRow } from '@/lib/db/schema/indicator-values';
import type { NewParserErrorRow } from '@/lib/db/schema/parser-runs';
import { ok, type Result } from '@/lib/errors';

import type { ParserOutput, StagingRowDraftPayload } from './types';

const STDOUT_TAIL_BYTES = 2048;

export type PersistStagingInput = {
  parserOutput: ParserOutput;
  sourceDocumentId: string;
  parserPath: string;
  startedAt: Date;
  endedAt: Date;
  stdoutTail: string;
};

export type PersistStagingResult = {
  parserRunId: string;
  stagingRowsWritten: number;
};

export async function persistStaging(
  input: PersistStagingInput,
): Promise<Result<PersistStagingResult>> {
  const { parserOutput, sourceDocumentId, parserPath, startedAt, endedAt, stdoutTail } = input;

  const errorSummary =
    parserOutput.errors.length === 0
      ? null
      : `${parserOutput.errors.length} error(s); first: ${parserOutput.errors[0]?.error_class}: ${parserOutput.errors[0]?.error_detail}`;

  const tail =
    stdoutTail.length <= STDOUT_TAIL_BYTES ? stdoutTail : stdoutTail.slice(-STDOUT_TAIL_BYTES);

  const runResult = await insertParserRun({
    sourceDocumentId,
    parserPath,
    parserVersion: parserOutput.parser_version,
    startedAt,
    endedAt,
    status: parserOutput.status,
    stagingRowsWritten: parserOutput.staging_rows.length,
    errorSummary,
    stdoutTail: tail,
  });
  if (!runResult.ok) return runResult;
  const parserRunId = runResult.value.id;

  if (parserOutput.staging_rows.length > 0) {
    const stagingRows: NewStagingIndicatorValueRow[] = parserOutput.staging_rows.map((row) =>
      toStagingInsert(row, parserRunId, sourceDocumentId),
    );
    const stagingResult = await bulkInsertStagingRows(stagingRows);
    if (!stagingResult.ok) return stagingResult;
  }

  if (parserOutput.errors.length > 0) {
    const errorRows: NewParserErrorRow[] = parserOutput.errors.map((e) => ({
      parserRunId,
      errorClass: e.error_class,
      errorDetail: e.error_detail,
      sourceExcerpt: e.source_excerpt ?? null,
    }));
    const errorsResult = await bulkInsertParserErrors(errorRows);
    if (!errorsResult.ok) return errorsResult;
  }

  return ok({ parserRunId, stagingRowsWritten: parserOutput.staging_rows.length });
}

function toStagingInsert(
  draft: StagingRowDraftPayload,
  parserRunId: string,
  sourceDocumentId: string,
): NewStagingIndicatorValueRow {
  return {
    parserRunId,
    sourceDocumentId,
    indicatorSlugRaw: draft.indicator_slug_raw,
    value: String(draft.value),
    unit: draft.unit,
    reportingPeriodType: draft.reporting_period_type,
    reportingPeriodBs: draft.reporting_period_bs,
    reportingPeriodAdStart: draft.reporting_period_ad_start,
    reportingPeriodAdEnd: draft.reporting_period_ad_end,
    publicationDateAd: draft.publication_date_ad,
    publicationDateBs: draft.publication_date_bs,
    fiscalYearBs: draft.fiscal_year_bs,
    fiscalYearAdLabel: draft.fiscal_year_ad_label,
    confidenceGradeProposed: draft.confidence_grade_proposed,
    parserNotes: draft.parser_notes ?? null,
  };
}
