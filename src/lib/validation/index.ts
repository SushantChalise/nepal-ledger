/**
 * Validation job — staging → approved promoter.
 *
 * Given a `parser_run_id`, walks every staging row produced by that run,
 * resolves the row's indicator + source document + plausibility window +
 * existing approved row, then runs the 8 ordered checks (see ./checks.ts).
 * Outcomes are collected per row (we surface every issue rather than
 * short-circuiting at the first block — per the brief's preference for ops
 * visibility). Per row:
 *
 *   - no warn, no block  → promote, increment `promoted`
 *   - warn(s) but no block → promote AND write each warn flag,
 *                            increment `promotedWithWarnings`
 *   - any block           → do NOT promote, write all flags (block + warn),
 *                           increment `blocked`
 *
 * Promote-and-delete-staging is atomic via `db.transaction` inside
 * `promote.ts`. Every DB op composes `safeQuery` — this function NEVER
 * throws; it always returns `Result<ValidationSummary>`.
 *
 * See docs/DATA_PIPELINE.md §"The Validation Job".
 */

import { findIndicatorBySlug } from '@/lib/db/repositories/indicators';
import {
  findLatestApprovedByPeriod,
  listApprovedTrailingForIndicator,
} from '@/lib/db/repositories/approved-indicator-values';
import { findSourceDocumentById } from '@/lib/db/repositories/source-documents';
import { listStagingRowsForParserRun } from '@/lib/db/repositories/staging-indicator-values';
import type {
  ApprovedIndicatorValueRow,
  StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';
import type { DataQualityFlagType } from '@/lib/db/schema/enums';
import { err, ok, type AppError, type Result } from '@/lib/errors';

import {
  duplicateCheck,
  indicatorResolutionCheck,
  periodParseCheck,
  plausibilityCheck,
  revisionFlowCheck,
  schemaCheck,
  sourceIntegrityCheck,
  unitRecognitionCheck,
} from './checks';
import { writeFlag } from './flag';
import { promoteStagingRow } from './promote';
import type { CheckOutcome, ValidationSummary } from './types';

/**
 * Starter unit vocabulary. Used until `indicator_units` is seeded; the
 * orchestrator (Worker H) will swap this for a DB-backed set. Order
 * doesn't matter — membership is set-semantics.
 */
const STARTER_KNOWN_UNITS: ReadonlySet<string> = new Set([
  'NPR_billion',
  'NPR_million',
  'NPR_crore',
  'NPR_lakh',
  'NPR',
  'USD_million',
  'USD',
  'percent',
  'percent_yoy',
  'index_points',
  'months_of_imports',
  'count',
  'kg_per_capita',
  'metric_tonnes',
  'megawatt_hours',
  'gigawatt_hours',
]);

const PROMOTED_BY = 'validation-job/v1';

/** 24-month trailing window in milliseconds — wide on purpose. */
const TRAILING_24M_MS = 24 * 30 * 24 * 60 * 60 * 1000;

type RowContext = {
  row: StagingIndicatorValueRow;
  doc: SourceDocumentRow;
  indicator: IndicatorRow | null;
  trailing: readonly ApprovedIndicatorValueRow[];
  existing: ApprovedIndicatorValueRow | null;
};

async function loadRowContext(row: StagingIndicatorValueRow): Promise<Result<RowContext>> {
  const docResult = await findSourceDocumentById(row.sourceDocumentId);
  if (!docResult.ok) return docResult;
  const doc = docResult.value;

  // Resolve via slug — `indicators` is keyed on slug. IndicatorUnknown
  // surfaces only when both the slug AND any pre-set FK fail to resolve.
  let indicator: IndicatorRow | null = null;
  const bySlug = await findIndicatorBySlug(row.indicatorSlugRaw);
  if (bySlug.ok) indicator = bySlug.value;
  else if (bySlug.error.kind !== 'NotFound') return bySlug;

  let trailing: readonly ApprovedIndicatorValueRow[] = [];
  let existing: ApprovedIndicatorValueRow | null = null;
  if (indicator) {
    const since = new Date(row.reportingPeriodAdEnd.getTime() - TRAILING_24M_MS);
    const trailingResult = await listApprovedTrailingForIndicator(indicator.id, since);
    if (!trailingResult.ok) return trailingResult;
    trailing = trailingResult.value;

    const existingResult = await findLatestApprovedByPeriod(
      indicator.id,
      row.reportingPeriodType,
      row.reportingPeriodBs,
    );
    if (!existingResult.ok) return existingResult;
    existing = existingResult.value;
  }

  return ok({ row, doc, indicator, trailing, existing });
}

function runChecks(ctx: RowContext): CheckOutcome[] {
  return [
    schemaCheck(ctx.row),
    indicatorResolutionCheck(ctx.row, ctx.indicator),
    periodParseCheck(ctx.row),
    unitRecognitionCheck(ctx.row, STARTER_KNOWN_UNITS),
    plausibilityCheck(ctx.row, ctx.trailing),
    duplicateCheck(ctx.row, ctx.existing),
    revisionFlowCheck(ctx.row, ctx.existing),
    sourceIntegrityCheck(ctx.row, ctx.doc),
  ];
}

export type { ValidationSummary, CheckContext, CheckOutcome } from './types';

type BlockingFlag = { stagingRowId: string; flagType: DataQualityFlagType; detail: string };

async function processRow(
  row: StagingIndicatorValueRow,
  summary: {
    promoted: number;
    promotedWithWarnings: number;
    blocked: number;
    blockingFlags: BlockingFlag[];
  },
): Promise<Result<void>> {
  const ctxResult = await loadRowContext(row);
  if (!ctxResult.ok) return ctxResult;
  const ctx = ctxResult.value;

  const outcomes = runChecks(ctx);
  const blocks = outcomes.filter(
    (o): o is Extract<CheckOutcome, { kind: 'block' }> => o.kind === 'block',
  );
  const warns = outcomes.filter(
    (o): o is Extract<CheckOutcome, { kind: 'warn' }> => o.kind === 'warn',
  );

  // Write every blocking + warning flag found, then decide outcome.
  for (const block of blocks) {
    const flagged = await writeFlag({
      stagingRowId: row.id,
      flagType: block.flagType,
      severity: 'blocking',
      detail: block.detail,
    });
    if (!flagged.ok) return flagged;
    summary.blockingFlags.push({
      stagingRowId: row.id,
      flagType: block.flagType,
      detail: block.detail,
    });
  }
  for (const warn of warns) {
    const flagged = await writeFlag({
      stagingRowId: row.id,
      flagType: warn.flagType,
      severity: 'warning',
      detail: warn.detail,
    });
    if (!flagged.ok) return flagged;
  }

  if (blocks.length > 0) {
    summary.blocked += 1;
    return ok(undefined);
  }

  // Promote path. IndicatorResolutionCheck would have blocked above if null.
  if (!ctx.indicator) {
    const e: AppError = {
      kind: 'QueryFailed',
      detail: 'validateParserRun: promote path reached with null indicator (logic bug)',
    };
    return err(e);
  }

  const revisionNumber = ctx.existing ? ctx.existing.revisionNumber + 1 : 0;
  const promoted = await promoteStagingRow({
    stagingRow: row,
    indicatorId: ctx.indicator.id,
    revisionNumber,
    promotedBy: PROMOTED_BY,
  });
  if (!promoted.ok) return promoted;

  if (warns.length > 0) summary.promotedWithWarnings += 1;
  else summary.promoted += 1;
  return ok(undefined);
}

export async function validateParserRun(parserRunId: string): Promise<Result<ValidationSummary>> {
  const stagingResult = await listStagingRowsForParserRun(parserRunId);
  if (!stagingResult.ok) return stagingResult;
  const stagingRows = stagingResult.value;

  const summary: {
    promoted: number;
    promotedWithWarnings: number;
    blocked: number;
    blockingFlags: BlockingFlag[];
  } = {
    promoted: 0,
    promotedWithWarnings: 0,
    blocked: 0,
    blockingFlags: [],
  };

  for (const row of stagingRows) {
    const result = await processRow(row, summary);
    if (!result.ok) return result;
  }

  return ok({
    parserRunId,
    totalStagingRows: stagingRows.length,
    promoted: summary.promoted,
    promotedWithWarnings: summary.promotedWithWarnings,
    blocked: summary.blocked,
    blockingFlags: summary.blockingFlags,
  });
}
