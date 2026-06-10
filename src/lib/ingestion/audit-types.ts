/**
 * OAG audit parser-output contract (ADR-0024).
 *
 * The boundary between the (future) deterministic Python audit parser's stdout
 * and the typed ingest orchestrator. Mirrors `audit-facts.ts` row shapes in
 * snake_case (the orchestrator maps snake → Drizzle camelCase on insert).
 *
 * Two invariants are enforced here, at the boundary, not left to the DB:
 *   - every non-null normalized amount carries its raw printed expression;
 *   - `confidence_grade` is required (no default) so an OCR row can never
 *     silently become grade A.
 *
 * The `AuditValidationReport` schema is the Parser Ship Gate artifact every
 * parser run must emit before any row is promoted (see ADR-0024 + the plan's
 * "Parser Ship Gate" section).
 */

import { z } from 'zod';

// ─── Enums (mirror src/lib/db/schema/enums.ts) ──────────────────────────

const AuditSubjectClassSchema = z.enum([
  'federal_government',
  'provincial_government',
  'local_government',
  'public_corporation',
  'constitutional_body',
  'committee_board_authority',
  'other_institution',
]);

const BerujuCategorySchema = z.enum([
  'recoverable',
  'irregular',
  'evidence_not_submitted',
  'advance_outstanding',
  'revenue_arrears',
  'responsibility_not_transferred',
  'other',
]);

const AuditAmountBasisSchema = z.enum([
  'current_year_raised',
  'settled_this_year',
  'cumulative_outstanding',
  'opening_outstanding',
  'adjustment',
  'other',
]);

const ExtractionMethodSchema = z.enum(['text_layer', 'preeti_fix', 'surya_ocr', 'manual_review']);

const ReviewStatusSchema = z.enum(['unreviewed', 'auto_accepted', 'human_verified', 'flagged']);

const ConfidenceGradeSchema = z.enum(['A', 'B', 'C']);

/** Canonical decimal string for a numeric column — full NPR, no float drift. */
const DecimalStr = z.string().regex(/^-?\d+(\.\d+)?$/, 'must be a decimal string');

// ─── Shared provenance (the columns identical on every audit fact row) ──

const coreProvenanceShape = {
  source_document_id: z.string().uuid(),
  source_precedence: z.number().int().min(1), // annual_report=1, local_body_report=2
  extraction_method: ExtractionMethodSchema,
  ocr_cell_extraction_id: z.string().uuid().nullable().optional(),
  review_status: ReviewStatusSchema.default('unreviewed'),
  confidence_grade: ConfidenceGradeSchema, // REQUIRED — no default
  promoted_by: z.string().min(1),
  notes: z.string().nullable().optional(),
};

// ─── audit_entity_summaries draft ───────────────────────────────────────

export const AuditSummaryDraftSchema = z
  .object({
    audited_entity_id: z.string().uuid().nullable(), // null for class aggregates
    audit_subject_class: AuditSubjectClassSchema,
    aggregate_scope: z.string().nullable().optional(),
    aggregate_label_raw: z.string().nullable().optional(),
    fiscal_year_bs: z.string().min(1),

    audited_amount_npr: DecimalStr.nullable().optional(),
    audited_amount_raw: z.string().nullable().optional(),
    beruju_raised_npr: DecimalStr.nullable().optional(),
    beruju_raised_raw: z.string().nullable().optional(),
    settled_this_year_npr: DecimalStr.nullable().optional(),
    settled_this_year_raw: z.string().nullable().optional(),
    cumulative_outstanding_npr: DecimalStr.nullable().optional(),
    cumulative_outstanding_raw: z.string().nullable().optional(),

    source_unit: z.string().nullable().optional(),
    source_scale: DecimalStr.nullable().optional(),
    source_page: z.number().int().nullable().optional(),
    source_table_ref: z.string().nullable().optional(),
    source_cell_ref: z.string().nullable().optional(),

    ...coreProvenanceShape,
  })
  .superRefine((row, ctx) => {
    // Raw provenance is mandatory for every non-null normalized amount.
    const pairs = [
      ['audited_amount_npr', 'audited_amount_raw'],
      ['beruju_raised_npr', 'beruju_raised_raw'],
      ['settled_this_year_npr', 'settled_this_year_raw'],
      ['cumulative_outstanding_npr', 'cumulative_outstanding_raw'],
    ] as const;
    for (const [nprKey, rawKey] of pairs) {
      if (row[nprKey] != null && row[rawKey] == null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: [rawKey],
          message: `${rawKey} is required when ${nprKey} is present`,
        });
      }
    }
  });

export type AuditSummaryDraft = z.infer<typeof AuditSummaryDraftSchema>;

// ─── audit_beruju_lines draft ───────────────────────────────────────────

export const AuditBerujuLineDraftSchema = z.object({
  audited_entity_id: z.string().uuid().nullable(),
  audit_subject_class: AuditSubjectClassSchema,
  aggregate_scope: z.string().nullable().optional(),
  fiscal_year_bs: z.string().min(1),

  amount_basis: AuditAmountBasisSchema,
  beruju_category: BerujuCategorySchema,
  beruju_category_label_raw: z.string().nullable().optional(),

  amount_npr: DecimalStr, // NOT NULL in the DB
  amount_raw: z.string().min(1), // always present — amount_npr is always present
  source_unit: z.string().nullable().optional(),
  source_scale: DecimalStr.nullable().optional(),
  source_page: z.number().int().nullable().optional(),
  source_table_ref: z.string().nullable().optional(),
  source_cell_ref: z.string().nullable().optional(),

  ...coreProvenanceShape,
});

export type AuditBerujuLineDraft = z.infer<typeof AuditBerujuLineDraftSchema>;

// ─── audit_findings draft ───────────────────────────────────────────────

export const AuditFindingDraftSchema = z
  .object({
    audited_entity_id: z.string().uuid().nullable(),
    audit_subject_class: AuditSubjectClassSchema,
    fiscal_year_bs: z.string().min(1),

    beruju_category: BerujuCategorySchema.nullable().optional(),
    amount_basis: AuditAmountBasisSchema.nullable().optional(),

    finding_ordinal: z.number().int().nonnegative(),
    para_ref: z.string().nullable().optional(),
    source_section_path: z.string().nullable().optional(),
    source_page_start: z.number().int().nullable().optional(),
    source_page_end: z.number().int().nullable().optional(),
    source_locator_hash: z.string().min(1),
    source_table_ref: z.string().nullable().optional(),

    title_en: z.string().nullable().optional(),
    title_ne: z.string().nullable().optional(),
    narrative_en: z.string().nullable().optional(),
    narrative_ne: z.string().nullable().optional(),

    amount_npr: DecimalStr.nullable().optional(),
    amount_raw: z.string().nullable().optional(),
    source_unit: z.string().nullable().optional(),

    recommendation_en: z.string().nullable().optional(),
    recommendation_ne: z.string().nullable().optional(),

    ...coreProvenanceShape,
  })
  .superRefine((row, ctx) => {
    if (row.amount_npr != null && row.amount_raw == null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['amount_raw'],
        message: 'amount_raw is required when amount_npr is present',
      });
    }
  });

export type AuditFindingDraft = z.infer<typeof AuditFindingDraftSchema>;

// ─── Parser output envelope ─────────────────────────────────────────────

const AuditParserErrorSchema = z.object({
  error_class: z.enum([
    'ColumnMissing',
    'RegexMismatch',
    'UnitAmbiguous',
    'PageLayoutChanged',
    'PeriodAmbiguous',
    'ValueUnparseable',
    'EncodingError',
    'EntityUnresolved',
    'ReconciliationFailed',
    'Other',
  ]),
  error_detail: z.string(),
  source_excerpt: z.string().nullable().optional(),
});

export const AuditParserOutputSchema = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string().min(1),
  source_id: z.string().min(1),
  source_document_id: z.string().uuid(),
  fiscal_year_bs: z.string().min(1),
  summaries: z.array(AuditSummaryDraftSchema),
  beruju_lines: z.array(AuditBerujuLineDraftSchema),
  findings: z.array(AuditFindingDraftSchema),
  errors: z.array(AuditParserErrorSchema),
});

export type AuditParserOutput = z.infer<typeof AuditParserOutputSchema>;

// ─── Parser Ship Gate validation report (ADR-0024) ──────────────────────

const ReconciliationResultSchema = z.object({
  scope: z.string(), // what is being reconciled, e.g. "beruju by category → summary"
  raw_printed_total: DecimalStr.nullable(),
  computed_extracted_total: DecimalStr.nullable(),
  variance_npr: DecimalStr,
  passed: z.boolean(),
});

/**
 * The artifact every parser run must emit (`audit_validation_report.json`).
 * `decision` is `PASS` only when every reconciliation passes and no hard-fail
 * condition is hit; otherwise `DEFER` — no rows are promoted.
 */
export const AuditValidationReportSchema = z.object({
  document_id: z.string().uuid(),
  source_id: z.string().min(1),
  fiscal_year_bs: z.string().min(1),
  // Sparse count maps keyed by extraction_method / confidence_grade values.
  extraction_method_distribution: z.record(z.string(), z.number().int()),
  confidence_grade_distribution: z.record(z.string(), z.number().int()),
  rows_extracted: z.object({
    summaries: z.number().int(),
    beruju_lines: z.number().int(),
    findings: z.number().int(),
  }),
  unresolved_entity_count: z.number().int(),
  parked_entity_count: z.number().int(),
  flagged_ocr_disagreement_count: z.number().int(),
  category_to_summary: z.array(ReconciliationResultSchema),
  entity_to_aggregate: z.array(ReconciliationResultSchema),
  aggregate_to_grand_total: z.array(ReconciliationResultSchema),
  decision: z.enum(['PASS', 'DEFER']),
});

export type AuditValidationReport = z.infer<typeof AuditValidationReportSchema>;
