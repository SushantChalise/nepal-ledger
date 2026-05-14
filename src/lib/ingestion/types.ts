/**
 * Ingestion orchestrator types.
 *
 * The Node side mirrors the Python `_common.types` dataclasses exactly. Any
 * drift here is a coordinated-update bug — keep this file in sync with
 * `scrapers/_common/types.py`.
 *
 * The Zod schemas in this file are the boundary between the Python parser
 * subprocess (untrusted stdout) and the rest of the orchestrator (typed). All
 * date strings from Python are ISO 8601; `z.coerce.date()` accepts them and
 * yields `Date` instances, eliminating the only `as` cast that would
 * otherwise be needed at the Zod boundary.
 */

import { z } from 'zod';

import type { ValidationSummary } from '@/lib/validation';

// ─── Python ParserError ────────────────────────────────────────────────

const ParserErrorClassSchema = z.enum([
  'ColumnMissing',
  'RegexMismatch',
  'UnitAmbiguous',
  'PageLayoutChanged',
  'PeriodAmbiguous',
  'ValueUnparseable',
  'EncodingError',
  'Other',
]);

export const ParserErrorSchema = z.object({
  error_class: ParserErrorClassSchema,
  error_detail: z.string(),
  source_excerpt: z.string().nullable().optional(),
});

export type ParserErrorPayload = z.infer<typeof ParserErrorSchema>;

// ─── Python StagingRowDraft ────────────────────────────────────────────

const ReportingPeriodTypeSchema = z.enum([
  'monthly',
  'quarterly',
  'annual',
  'nine_months_cumulative',
  'year_to_date',
  'daily',
  'seasonal',
]);

const ConfidenceGradeSchema = z.enum(['A', 'B', 'C']);

export const StagingRowDraftSchema = z.object({
  indicator_slug_raw: z.string().min(1),
  value: z.number(),
  unit: z.string().min(1),
  reporting_period_type: ReportingPeriodTypeSchema,
  reporting_period_bs: z.string().min(1),
  reporting_period_ad_start: z.coerce.date(),
  reporting_period_ad_end: z.coerce.date(),
  publication_date_ad: z.coerce.date(),
  publication_date_bs: z.string().min(1),
  fiscal_year_bs: z.string().min(1),
  fiscal_year_ad_label: z.string().min(1),
  confidence_grade_proposed: ConfidenceGradeSchema,
  parser_notes: z.string().nullable().optional(),
});

export type StagingRowDraftPayload = z.infer<typeof StagingRowDraftSchema>;

// ─── Python ParserResult ───────────────────────────────────────────────

const ParserStatusSchema = z.enum(['success', 'partial', 'failure']);

export const ParserOutputSchema = z.object({
  status: ParserStatusSchema,
  parser_version: z.string().min(1),
  staging_rows: z.array(StagingRowDraftSchema),
  errors: z.array(ParserErrorSchema),
});

export type ParserOutput = z.infer<typeof ParserOutputSchema>;

// ─── Orchestrator surface ──────────────────────────────────────────────

/**
 * Where the file came from. The orchestrator either reads it directly from
 * disk (already-fetched by a scraper) or downloads it once via `fetch`.
 */
export type IngestionFileSource = { filePath: string } | { url: string };

export type IngestionInput = IngestionFileSource & {
  /** Registered `source_registry.source_id`. */
  sourceId: string;
  /** Filename to record + use as the storage key suffix. */
  fileName: string;
  /** MIME type, e.g. `application/pdf`, `text/csv`. */
  contentType: string;
  /** Path of the parser module relative to the repo root, e.g. `scrapers/nrb_ncpi/parser.py`. */
  parserPath: string;
  /** Best-guess label set at download time; the parser may refine. Optional. */
  reportingPeriodLabel?: string;
  /** Subprocess timeout in milliseconds. Default: 60_000. */
  parserTimeoutMs?: number;
};

export type IngestionSummary = {
  sourceDocumentId: string;
  parserRunId: string;
  parserStatus: ParserOutput['status'];
  stagingRowsWritten: number;
  validation: ValidationSummary;
};
