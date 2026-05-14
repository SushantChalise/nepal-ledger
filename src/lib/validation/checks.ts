/**
 * Validation checks — pure functions, one per check, no DB calls.
 *
 * Per docs/DATA_PIPELINE.md §"The Validation Job", checks fire in this
 * order: schema → indicator-resolution → period-parse → unit-recognition →
 * plausibility → duplicate → revision-flow → source-integrity. The driver
 * (index.ts) decides whether to short-circuit after the first block or
 * surface every issue — we surface every issue (preferred for ops
 * visibility, see brief §"Outcomes").
 */

import { parseReportingPeriod } from '@/lib/dates';
import { confidenceGradeEnum, reportingPeriodTypeEnum } from '@/lib/db/schema/enums';
import type {
  ApprovedIndicatorValueRow,
  StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';

import type { CheckOutcome } from './types';

/** Helpers: a numeric column comes off Drizzle as a string — coerce safely. */
function toNumber(s: string): number {
  return Number(s);
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string' && v.length > 0;
}

function isValidDate(v: unknown): v is Date {
  return v instanceof Date && !Number.isNaN(v.getTime());
}

const REPORTING_PERIOD_TYPES = new Set<string>(reportingPeriodTypeEnum.enumValues);
const CONFIDENCE_GRADES = new Set<string>(confidenceGradeEnum.enumValues);

function blockSchema(field: string, why: string): CheckOutcome {
  return {
    kind: 'block',
    flagType: 'SchemaInvalid',
    detail: `staging row failed shape check at ${field}: ${why}`,
  };
}

/**
 * Belt-and-braces re-validation of the staging row shape. The TS type
 * already has compile-time guarantees — this catches runtime drift from
 * the DB layer (empty strings, invalid dates, enum drift).
 */
export function schemaCheck(row: StagingIndicatorValueRow): CheckOutcome {
  const stringFields: ReadonlyArray<readonly [string, string | null]> = [
    ['id', row.id],
    ['parserRunId', row.parserRunId],
    ['sourceDocumentId', row.sourceDocumentId],
    ['indicatorSlugRaw', row.indicatorSlugRaw],
    ['value', row.value],
    ['unit', row.unit],
    ['reportingPeriodBs', row.reportingPeriodBs],
    ['publicationDateBs', row.publicationDateBs],
    ['fiscalYearBs', row.fiscalYearBs],
    ['fiscalYearAdLabel', row.fiscalYearAdLabel],
  ];
  for (const [name, v] of stringFields) {
    if (!isNonEmptyString(v)) return blockSchema(name, 'missing or empty');
  }
  if (row.indicatorId !== null && !isNonEmptyString(row.indicatorId)) {
    return blockSchema('indicatorId', 'must be uuid string or null');
  }
  if (!Number.isFinite(toNumber(row.value))) {
    return blockSchema('value', `"${row.value}" is not a finite number`);
  }
  const dateFields: ReadonlyArray<readonly [string, Date]> = [
    ['reportingPeriodAdStart', row.reportingPeriodAdStart],
    ['reportingPeriodAdEnd', row.reportingPeriodAdEnd],
    ['publicationDateAd', row.publicationDateAd],
  ];
  for (const [name, v] of dateFields) {
    if (!isValidDate(v)) return blockSchema(name, 'invalid date');
  }
  if (!REPORTING_PERIOD_TYPES.has(row.reportingPeriodType)) {
    return blockSchema('reportingPeriodType', `unknown "${row.reportingPeriodType}"`);
  }
  if (!CONFIDENCE_GRADES.has(row.confidenceGradeProposed)) {
    return blockSchema('confidenceGradeProposed', `unknown "${row.confidenceGradeProposed}"`);
  }
  return { kind: 'pass' };
}

export function indicatorResolutionCheck(
  row: StagingIndicatorValueRow,
  indicator: IndicatorRow | null,
): CheckOutcome {
  if (indicator) return { kind: 'pass' };
  if (row.indicatorId) {
    return {
      kind: 'block',
      flagType: 'IndicatorUnknown',
      detail: `indicatorId ${row.indicatorId} did not resolve to a row in indicators`,
    };
  }
  return {
    kind: 'block',
    flagType: 'IndicatorUnknown',
    detail: `indicatorSlugRaw "${row.indicatorSlugRaw}" did not resolve to a known indicator`,
  };
}

const PERIOD_AD_TOLERANCE_MS = 2 * 24 * 60 * 60 * 1000;

export function periodParseCheck(row: StagingIndicatorValueRow): CheckOutcome {
  const parsed = parseReportingPeriod(row.reportingPeriodBs);
  if (!parsed.ok) {
    return {
      kind: 'block',
      flagType: 'PeriodAmbiguous',
      detail: `reportingPeriodBs "${row.reportingPeriodBs}" did not parse: ${parsed.error.kind === 'ParseFailed' ? parsed.error.reason : parsed.error.kind}`,
    };
  }
  const startDelta = Math.abs(
    parsed.value.adStart.getTime() - row.reportingPeriodAdStart.getTime(),
  );
  const endDelta = Math.abs(parsed.value.adEnd.getTime() - row.reportingPeriodAdEnd.getTime());
  if (startDelta > PERIOD_AD_TOLERANCE_MS || endDelta > PERIOD_AD_TOLERANCE_MS) {
    return {
      kind: 'warn',
      flagType: 'PeriodAmbiguous',
      detail: `parsed BS period AD range disagrees with row AD range by >2d (startΔ=${startDelta}ms, endΔ=${endDelta}ms)`,
    };
  }
  return { kind: 'pass' };
}

export function unitRecognitionCheck(
  row: StagingIndicatorValueRow,
  knownUnits: ReadonlySet<string>,
): CheckOutcome {
  if (knownUnits.has(row.unit)) return { kind: 'pass' };
  return {
    kind: 'block',
    flagType: 'UnitUnrecognized',
    detail: `unit "${row.unit}" is not in the known unit registry`,
  };
}

/** Minimum trailing rows needed before we even compute mean/stdev. */
const PLAUSIBILITY_MIN_TRAILING = 3;
/** Wide-on-purpose band — catches order-of-magnitude errors, not noise. */
const PLAUSIBILITY_STDEV_LIMIT = 5;

export function plausibilityCheck(
  row: StagingIndicatorValueRow,
  trailing: readonly ApprovedIndicatorValueRow[],
): CheckOutcome {
  if (trailing.length < PLAUSIBILITY_MIN_TRAILING) return { kind: 'pass' };
  const values = trailing.map((r) => toNumber(r.value)).filter((n) => Number.isFinite(n));
  if (values.length < PLAUSIBILITY_MIN_TRAILING) return { kind: 'pass' };
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / values.length;
  const stdev = Math.sqrt(variance);
  // Degenerate: all trailing values identical → only block exact-match
  // outliers (i.e. a different value when historical variance is zero is
  // still treated as plausible at warn level).
  if (stdev === 0) return { kind: 'pass' };
  const value = toNumber(row.value);
  const zAbs = Math.abs((value - mean) / stdev);
  if (zAbs > PLAUSIBILITY_STDEV_LIMIT) {
    return {
      kind: 'warn',
      flagType: 'ValueOutOfPlausibleRange',
      detail: `value ${value} is ${zAbs.toFixed(2)} stdev from trailing mean ${mean.toFixed(3)} (n=${values.length}, σ=${stdev.toFixed(3)})`,
    };
  }
  return { kind: 'pass' };
}

export function duplicateCheck(
  row: StagingIndicatorValueRow,
  existing: ApprovedIndicatorValueRow | null,
): CheckOutcome {
  if (!existing) return { kind: 'pass' };
  if (existing.sourceDocumentId === row.sourceDocumentId) {
    return {
      kind: 'block',
      flagType: 'DuplicateOfApproved',
      detail: `an approved row already exists for this (indicator, period) from the same source document ${row.sourceDocumentId}`,
    };
  }
  // Different doc → defer to RevisionFlowCheck.
  return { kind: 'pass' };
}

export function revisionFlowCheck(
  row: StagingIndicatorValueRow,
  existing: ApprovedIndicatorValueRow | null,
): CheckOutcome {
  if (!existing) return { kind: 'pass' };
  if (existing.sourceDocumentId === row.sourceDocumentId) {
    // DuplicateCheck handled this case; nothing for revision flow to do.
    return { kind: 'pass' };
  }
  const incoming = toNumber(row.value);
  const prior = toNumber(existing.value);
  if (Number.isFinite(incoming) && Number.isFinite(prior) && incoming === prior) {
    return {
      kind: 'block',
      flagType: 'DuplicateOfApproved',
      detail: `revision candidate matches prior approved value (${prior}); not a real revision`,
    };
  }
  // The driver computes the next revision number as prior+1. If the prior's
  // revisionNumber is corrupted (negative or non-integer), flag.
  if (!Number.isInteger(existing.revisionNumber) || existing.revisionNumber < 0) {
    return {
      kind: 'block',
      flagType: 'RevisionMismatch',
      detail: `prior approved row has invalid revisionNumber ${existing.revisionNumber}`,
    };
  }
  return { kind: 'pass' };
}

export function sourceIntegrityCheck(
  row: StagingIndicatorValueRow,
  doc: SourceDocumentRow,
): CheckOutcome {
  if (doc.id !== row.sourceDocumentId) {
    return {
      kind: 'block',
      flagType: 'SourceHashCollision',
      detail: `source document id mismatch: row=${row.sourceDocumentId} doc=${doc.id}`,
    };
  }
  if (!doc.fileHashSha256 || doc.fileHashSha256.length === 0) {
    return {
      kind: 'block',
      flagType: 'SourceHashCollision',
      detail: `source document ${doc.id} has empty file_hash_sha256`,
    };
  }
  return { kind: 'pass' };
}
