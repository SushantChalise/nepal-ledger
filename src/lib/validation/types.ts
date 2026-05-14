/**
 * Validation job types.
 *
 * Per docs/DATA_PIPELINE.md §"The Validation Job": each staging row runs
 * through eight ordered checks. Each check returns a `CheckOutcome`. The
 * driver collects outcomes for a row, then decides promote / promote-with-
 * warning / block. The aggregate report is `ValidationSummary`.
 */

import type { DataQualityFlagType } from '@/lib/db/schema/enums';
import type {
  ApprovedIndicatorValueRow,
  StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';

export type CheckOutcome =
  | { kind: 'pass' }
  | { kind: 'warn'; flagType: DataQualityFlagType; detail: string }
  | { kind: 'block'; flagType: DataQualityFlagType; detail: string };

export type CheckContext = {
  stagingRow: StagingIndicatorValueRow;
  sourceDocument: SourceDocumentRow;
  /** null when IndicatorResolutionCheck has nothing to match. */
  indicator: IndicatorRow | null;
  /** Trailing 24-month approved values for this indicator (any periodType). */
  approvedTrailing24m: readonly ApprovedIndicatorValueRow[];
  /** Existing latest approved row for (indicatorId, periodType, periodBs). */
  existingApprovedForPeriod: ApprovedIndicatorValueRow | null;
  /** Controlled vocabulary of recognized units. */
  knownUnits: ReadonlySet<string>;
};

export type ValidationSummary = {
  parserRunId: string;
  totalStagingRows: number;
  promoted: number;
  promotedWithWarnings: number;
  blocked: number;
  blockingFlags: ReadonlyArray<{
    stagingRowId: string;
    flagType: DataQualityFlagType;
    detail: string;
  }>;
};
