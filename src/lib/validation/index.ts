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
import { listKnownUnits } from '@/lib/db/repositories/indicator-units';
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
 * Starter unit vocabulary — the floor. The authoritative set lives in the
 * `indicator_units` table (loaded via `listKnownUnits`); we union the two so
 * that (a) a freshly-migrated DB with no seeded units still recognizes the
 * core vocabulary, and (b) seeded units extend it without code changes.
 * Order doesn't matter — membership is set-semantics.
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

function runChecks(ctx: RowContext, knownUnits: ReadonlySet<string>): CheckOutcome[] {
  return [
    schemaCheck(ctx.row),
    indicatorResolutionCheck(ctx.row, ctx.indicator),
    periodParseCheck(ctx.row),
    unitRecognitionCheck(ctx.row, knownUnits),
    plausibilityCheck(ctx.row, ctx.trailing),
    duplicateCheck(ctx.row, ctx.existing),
    revisionFlowCheck(ctx.row, ctx.existing),
    sourceIntegrityCheck(ctx.row, ctx.doc),
  ];
}

/**
 * Load the recognized-unit set: the seeded `indicator_units` table unioned
 * with the in-code starter floor. A DB error degrades gracefully to the
 * starter set rather than failing the whole run (units are one check of
 * eight; a transient read failure shouldn't block promotion of otherwise
 * valid rows whose units are in the floor).
 */
async function loadKnownUnits(): Promise<ReadonlySet<string>> {
  const fromDb = await listKnownUnits();
  if (!fromDb.ok) return STARTER_KNOWN_UNITS;
  return new Set([...STARTER_KNOWN_UNITS, ...fromDb.value]);
}

export type { ValidationSummary, CheckContext, CheckOutcome } from './types';

type BlockingFlag = { stagingRowId: string; flagType: DataQualityFlagType; detail: string };

async function processRow(
  row: StagingIndicatorValueRow,
  knownUnits: ReadonlySet<string>,
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

  const outcomes = runChecks(ctx, knownUnits);
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

/**
 * Bounded retry wrapper around `processRow` for transient connection failures.
 *
 * Live observation: Supabase's pooler resets the socket on roughly 0.1% of
 * queries (ECONNRESET). The validation loop does several hundred sequential
 * round-trips per file, so an un-retried run hit at least one reset ~70% of
 * the time and aborted wholesale. We retry ONLY `DatabaseUnavailable` (the
 * connection-class AppError) with exponential backoff; any other error (bad
 * SQL, constraint violation, validation block) returns immediately and is
 * never retried.
 *
 * Retry safety: `processRow`'s context loads are idempotent reads, and the
 * promote is a single transaction (no partial state). The one at-least-once
 * hazard — a reset AFTER a promote commit — causes the retry to write a higher
 * revision of identical data; read queries take `revision_number DESC LIMIT 1`,
 * so it is read-harmless and retained as a revision (Data Continuity Protocol).
 */
const MAX_TRANSIENT_RETRIES = 5;
const RETRY_BASE_DELAY_MS = 150;

async function processRowWithRetry(
  row: StagingIndicatorValueRow,
  knownUnits: ReadonlySet<string>,
  summary: {
    promoted: number;
    promotedWithWarnings: number;
    blocked: number;
    blockingFlags: BlockingFlag[];
  },
): Promise<Result<void>> {
  let last = await processRow(row, knownUnits, summary);
  for (let attempt = 1; attempt <= MAX_TRANSIENT_RETRIES; attempt += 1) {
    if (last.ok || last.error.kind !== 'DatabaseUnavailable') return last;
    await delay(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
    last = await processRow(row, knownUnits, summary);
  }
  return last;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function validateParserRun(parserRunId: string): Promise<Result<ValidationSummary>> {
  const stagingResult = await listStagingRowsForParserRun(parserRunId);
  if (!stagingResult.ok) return stagingResult;
  const stagingRows = stagingResult.value;

  // No rows → nothing to check; skip the units read entirely.
  const knownUnits = stagingRows.length > 0 ? await loadKnownUnits() : STARTER_KNOWN_UNITS;

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
    const result = await processRowWithRetry(row, knownUnits, summary);
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
