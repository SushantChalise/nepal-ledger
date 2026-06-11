/**
 * Government audit fact domain — OAG / महालेखापरीक्षक audit reports.
 *
 * Audit data is NOT a time series, so it does not live in
 * `approved_indicator_values`. It is entity-keyed, fiscal-year-keyed,
 * category-classified irregularity amounts (beruju) plus narrative findings.
 * Three tables (ADR-0024):
 *
 *   - `audit_entity_summaries` — headline scalars per (subject_class, entity
 *     or aggregate, FY): audited amount, beruju raised, settled, cumulative
 *     outstanding.
 *   - `audit_beruju_lines` — that beruju, broken down per (amount_basis,
 *     beruju_category). Reconciles to the summary scalar per basis.
 *   - `audit_findings` — individual structured narrative observations.
 *
 * Populated direct-to-fact-table (like `local_government_fiscal_transfers`):
 * a deterministic parser emits Zod-validated rows promoted only after the
 * reconciliation gate passes (ADR-0021). These tables add raw-amount,
 * OCR-locator, source-precedence, and review-status columns that the clean
 * XLSX fact tables didn't need — justified by OCR-heavy Nepali sources.
 *
 * Two feeds write here: the consolidated annual report (`oag-audit-reports`,
 * source_precedence 1) and the 753 local-body reports (`oag-lbl-local-audits`,
 * source_precedence 2). On overlap, higher precedence wins — repositories
 * upsert with a precedence-guarded ON CONFLICT, never blind DO NOTHING.
 */

import {
  index,
  integer,
  numeric,
  pgTable,
  smallint,
  text,
  timestamp,
  unique,
  uniqueIndex,
  uuid,
} from 'drizzle-orm/pg-core';

import {
  auditAmountBasisEnum,
  auditSubjectClassEnum,
  berujuCategoryEnum,
  confidenceGradeEnum,
  extractionMethodEnum,
  reviewStatusEnum,
} from './enums';
import { entities } from './entities';
import { ocrCellExtractions } from './ocr-tracking';
import { sourceDocuments } from './source-documents';

// ─── audit_entity_summaries ─────────────────────────────────────────────

export const auditEntitySummaries = pgTable(
  'audit_entity_summaries',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    // NULL when the row is a tier/class aggregate ("all federal offices");
    // populated for a specific ministry / province / local body / corporation.
    auditedEntityId: uuid('audited_entity_id').references(() => entities.id, {
      onDelete: 'restrict',
    }),
    auditSubjectClass: auditSubjectClassEnum('audit_subject_class').notNull(),

    // Distinguishes multiple aggregate rows within one class/FY
    // ('all_ministries' vs 'all_departments'). NULL for a specific entity.
    aggregateScope: text('aggregate_scope'),
    aggregateLabelRaw: text('aggregate_label_raw'),

    // Storage convention: 4-digit start year, slash, 2-digit end ("2079/80").
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    // Headline scalars: each normalized NPR is paired with the exact printed
    // expression (`*_raw`) for OCR auditability. Any may be NULL.
    auditedAmountNpr: numeric('audited_amount_npr', { precision: 20, scale: 2 }),
    auditedAmountRaw: text('audited_amount_raw'),
    berujuRaisedNpr: numeric('beruju_raised_npr', { precision: 20, scale: 2 }),
    berujuRaisedRaw: text('beruju_raised_raw'),
    settledThisYearNpr: numeric('settled_this_year_npr', { precision: 20, scale: 2 }),
    settledThisYearRaw: text('settled_this_year_raw'),
    cumulativeOutstandingNpr: numeric('cumulative_outstanding_npr', { precision: 20, scale: 2 }),
    cumulativeOutstandingRaw: text('cumulative_outstanding_raw'),

    // Source unit + the multiplier applied raw→NPR (e.g. 'रु. हजारमा' → 1000).
    sourceUnit: text('source_unit'),
    sourceScale: numeric('source_scale', { precision: 20, scale: 6 }),

    // OCR locators (nullable; populated when surya_ocr-sourced).
    sourcePage: integer('source_page'),
    sourceTableRef: text('source_table_ref'),
    sourceCellRef: text('source_cell_ref'),

    ...auditProvenanceColumns(),
  },
  (table) => [
    // NULLS NOT DISTINCT so re-ingesting a tier aggregate (NULL entity) is a
    // no-op instead of a silent duplicate.
    unique('audit_summaries_unique')
      .on(table.auditSubjectClass, table.auditedEntityId, table.aggregateScope, table.fiscalYearBs)
      .nullsNotDistinct(),
    index('audit_summaries_entity_idx').on(table.auditedEntityId),
    index('audit_summaries_fy_idx').on(table.fiscalYearBs),
    index('audit_summaries_class_idx').on(table.auditSubjectClass),
  ],
);

export type AuditEntitySummaryRow = typeof auditEntitySummaries.$inferSelect;
export type NewAuditEntitySummaryRow = typeof auditEntitySummaries.$inferInsert;

// ─── audit_beruju_lines ─────────────────────────────────────────────────

export const auditBerujuLines = pgTable(
  'audit_beruju_lines',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    auditedEntityId: uuid('audited_entity_id').references(() => entities.id, {
      onDelete: 'restrict',
    }),
    auditSubjectClass: auditSubjectClassEnum('audit_subject_class').notNull(),
    aggregateScope: text('aggregate_scope'),
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    // For a given (entity/scope, FY), sum(amount_npr) over categories within a
    // basis must equal the matching summary scalar (reconciliation gate):
    //   current_year_raised    ↔ beruju_raised_npr
    //   settled_this_year      ↔ settled_this_year_npr
    //   cumulative_outstanding ↔ cumulative_outstanding_npr
    amountBasis: auditAmountBasisEnum('amount_basis').notNull(),
    berujuCategory: berujuCategoryEnum('beruju_category').notNull(),
    // Exact Nepali/English label the parser saw — fidelity for `other`.
    berujuCategoryLabelRaw: text('beruju_category_label_raw'),

    amountNpr: numeric('amount_npr', { precision: 20, scale: 2 }).notNull(),
    amountRaw: text('amount_raw'),
    sourceUnit: text('source_unit'),
    sourceScale: numeric('source_scale', { precision: 20, scale: 6 }),

    // OCR locators (nullable; populated when surya_ocr-sourced).
    sourcePage: integer('source_page'),
    sourceTableRef: text('source_table_ref'),
    sourceCellRef: text('source_cell_ref'),

    ...auditProvenanceColumns(),
  },
  (table) => [
    unique('audit_beruju_lines_unique')
      .on(
        table.auditSubjectClass,
        table.auditedEntityId,
        table.aggregateScope,
        table.fiscalYearBs,
        table.amountBasis,
        table.berujuCategory,
      )
      .nullsNotDistinct(),
    index('audit_beruju_lines_entity_idx').on(table.auditedEntityId),
    index('audit_beruju_lines_fy_idx').on(table.fiscalYearBs),
    index('audit_beruju_lines_category_idx').on(table.berujuCategory),
    index('audit_beruju_lines_basis_idx').on(table.amountBasis),
  ],
);

export type AuditBerujuLineRow = typeof auditBerujuLines.$inferSelect;
export type NewAuditBerujuLineRow = typeof auditBerujuLines.$inferInsert;

// ─── audit_findings ─────────────────────────────────────────────────────

export const auditFindings = pgTable(
  'audit_findings',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    auditedEntityId: uuid('audited_entity_id').references(() => entities.id, {
      onDelete: 'restrict',
    }),
    auditSubjectClass: auditSubjectClassEnum('audit_subject_class').notNull(),
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    berujuCategory: berujuCategoryEnum('beruju_category'),
    amountBasis: auditAmountBasisEnum('amount_basis'),

    // Stable parser ordering within (document, entity). Identity, NOT para_ref,
    // because local reports have repeated/missing/OCR-damaged paragraph numbers.
    findingOrdinal: integer('finding_ordinal').notNull(),
    paraRef: text('para_ref'),
    sourceSectionPath: text('source_section_path'),
    sourcePageStart: integer('source_page_start'),
    sourcePageEnd: integer('source_page_end'),
    // Stable hash(doc, page-span, section, normalized title) — re-parse dedup.
    sourceLocatorHash: text('source_locator_hash').notNull(),
    sourceTableRef: text('source_table_ref'),

    titleEn: text('title_en'),
    titleNe: text('title_ne'),
    narrativeEn: text('narrative_en'),
    narrativeNe: text('narrative_ne'),

    amountNpr: numeric('amount_npr', { precision: 20, scale: 2 }),
    amountRaw: text('amount_raw'),
    sourceUnit: text('source_unit'),

    recommendationEn: text('recommendation_en'),
    recommendationNe: text('recommendation_ne'),

    ...auditProvenanceColumns(),
  },
  (table) => [
    unique('audit_findings_ordinal_unique')
      .on(table.sourceDocumentId, table.auditedEntityId, table.fiscalYearBs, table.findingOrdinal)
      .nullsNotDistinct(),
    // Both columns NOT NULL — a plain unique index suffices for re-parse dedup.
    uniqueIndex('audit_findings_locator_unique').on(
      table.sourceDocumentId,
      table.sourceLocatorHash,
    ),
    index('audit_findings_entity_idx').on(table.auditedEntityId),
    index('audit_findings_fy_idx').on(table.fiscalYearBs),
    index('audit_findings_category_idx').on(table.berujuCategory),
  ],
);

export type AuditFindingRow = typeof auditFindings.$inferSelect;
export type NewAuditFindingRow = typeof auditFindings.$inferInsert;

// ─── Shared provenance ──────────────────────────────────────────────────

/**
 * Provenance columns every audit fact row carries. Inlined into each table
 * (Drizzle has no column mixins) — the column set is identical across the
 * three tables by design.
 *
 * `confidenceGrade` has NO default: the parser must state it explicitly so an
 * OCR row can never silently inherit grade A. `sourcePrecedence` (annual=1,
 * local_body=2) drives the precedence-guarded upsert.
 */
function auditProvenanceColumns() {
  return {
    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),
    sourcePrecedence: smallint('source_precedence').notNull(),
    extractionMethod: extractionMethodEnum('extraction_method').notNull(),
    // Links a fact back to the OCR cell it came from, when surya_ocr-sourced.
    ocrCellExtractionId: uuid('ocr_cell_extraction_id').references(() => ocrCellExtractions.id, {
      onDelete: 'set null',
    }),
    reviewStatus: reviewStatusEnum('review_status').notNull().default('unreviewed'),
    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull(),
    promotedAt: timestamp('promoted_at', { withTimezone: true }).notNull().defaultNow(),
    promotedBy: text('promoted_by').notNull(),
    notes: text('notes'),
  };
}
