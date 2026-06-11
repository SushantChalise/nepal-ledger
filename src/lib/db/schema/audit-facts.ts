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
  aggregationRoleEnum,
  auditAmountBasisEnum,
  auditParagraphStatusEnum,
  auditStockTypeEnum,
  auditSubjectClassEnum,
  confidenceGradeEnum,
  extractionMethodEnum,
  reviewStatusEnum,
  valueOriginEnum,
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

// ─── beruju_categories (taxonomy lookup) ────────────────────────────────

/**
 * The OAG beruju taxonomy as a seeded lookup table, not a pgEnum (ADR-0027):
 * the Audit Act's 3 main categories × their leaves, carrying bilingual labels +
 * act references as data. `audit_beruju_lines` / `audit_findings` FK to `code`;
 * `mainCategory` drives main-level rollup/reconciliation.
 */
export const berujuCategories = pgTable('beruju_categories', {
  // Stable code, e.g. 'tbr_balance_not_brought_forward'. Prefix = main category
  // (rec_/tbr_/adv_) except the three bare main codes and 'other'.
  code: text('code').primaryKey(),
  // 'recoverable' | 'to_be_regularized' | 'advance' | 'other'.
  mainCategory: text('main_category').notNull(),
  nameEn: text('name_en').notNull(),
  nameNe: text('name_ne'),
  actReference: text('act_reference'),
  displayOrder: integer('display_order').notNull(),
});

export type BerujuCategoryRow = typeof berujuCategories.$inferSelect;
export type NewBerujuCategoryRow = typeof berujuCategories.$inferInsert;

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

    // Reconciliation gate (level-aware, ADR-0027): for a given (entity/scope,
    // FY, source_table), sum over `detail` rows within a basis equals the
    // printed `subtotal`/`grand_total` row; main-level rollup uses the lookup's
    // main_category. current_year_raised ↔ beruju_raised_npr, etc.
    amountBasis: auditAmountBasisEnum('amount_basis').notNull(),
    // FK → beruju_categories.code (the OAG taxonomy lookup). NOT NULL: every
    // line carries a taxonomy code; roll up via the lookup's main_category.
    berujuCategory: text('beruju_category')
      .notNull()
      .references(() => berujuCategories.code, { onDelete: 'restrict' }),
    // Exact printed labels the parser saw (fidelity).
    berujuCategoryLabelRaw: text('beruju_category_label_raw'),
    sourceRowLabel: text('source_row_label'),

    // Presentation + value provenance (ADR-0027). Parent/total rows are STORED
    // (role != 'detail'), not skipped; default analytical sums filter 'detail'.
    aggregationRole: aggregationRoleEnum('aggregation_role').notNull().default('detail'),
    valueOrigin: valueOriginEnum('value_origin').notNull().default('printed'),
    // Which source table the row came from (e.g. 'ch2_irregularity_classification',
    // 'ch2_settlement', 'ch_federal_by_ministry') — disambiguates the same
    // category appearing in multiple tables of one report.
    sourceTableCode: text('source_table_code').notNull(),

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
    // Collision-proof key (ADR-0027): source_document_id scopes a row to its
    // report, and aggregation_role + source_table_code separate the same
    // category appearing across the classification / settlement / ministry
    // tables. NULLS NOT DISTINCT so a re-parsed aggregate (NULL entity) is a
    // no-op, not a duplicate.
    unique('audit_beruju_lines_unique')
      .on(
        table.sourceDocumentId,
        table.auditSubjectClass,
        table.auditedEntityId,
        table.aggregateScope,
        table.fiscalYearBs,
        table.amountBasis,
        table.berujuCategory,
        table.aggregationRole,
        table.sourceTableCode,
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

    // FK → beruju_categories.code (nullable: a finding need not be a beruju).
    berujuCategory: text('beruju_category').references(() => berujuCategories.code, {
      onDelete: 'restrict',
    }),
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

// ─── audit_financial_stocks ─────────────────────────────────────────────

/**
 * OAG "amounts outstanding to be settled" stock table (ADR-0027) — a different
 * MEASURE from beruju classification. Revenue arrears, foreign-aid
 * reimbursables, audit backlogs, overdue principal/interest: each a balance
 * with a lifecycle (closing = opening + addition − settlement ± adjustment).
 */
export const auditFinancialStocks = pgTable(
  'audit_financial_stocks',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    auditedEntityId: uuid('audited_entity_id').references(() => entities.id, {
      onDelete: 'restrict',
    }),
    auditSubjectClass: auditSubjectClassEnum('audit_subject_class').notNull(),
    aggregateScope: text('aggregate_scope'),
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    stockType: auditStockTypeEnum('stock_type').notNull(),

    // Reconciliation identity: closing = opening + addition − settlement ±
    // adjustment. Each normalized NPR paired with its printed raw expression.
    openingNpr: numeric('opening_npr', { precision: 20, scale: 2 }),
    openingRaw: text('opening_raw'),
    additionNpr: numeric('addition_npr', { precision: 20, scale: 2 }),
    additionRaw: text('addition_raw'),
    settlementNpr: numeric('settlement_npr', { precision: 20, scale: 2 }),
    settlementRaw: text('settlement_raw'),
    adjustmentNpr: numeric('adjustment_npr', { precision: 20, scale: 2 }),
    adjustmentRaw: text('adjustment_raw'),
    closingNpr: numeric('closing_npr', { precision: 20, scale: 2 }),
    closingRaw: text('closing_raw'),

    sourceUnit: text('source_unit'),
    sourceScale: numeric('source_scale', { precision: 20, scale: 6 }),
    sourceTableCode: text('source_table_code').notNull(),
    sourceRowLabel: text('source_row_label'),
    sourcePage: integer('source_page'),
    sourceTableRef: text('source_table_ref'),
    sourceCellRef: text('source_cell_ref'),

    ...auditProvenanceColumns(),
  },
  (table) => [
    unique('audit_financial_stocks_unique')
      .on(
        table.sourceDocumentId,
        table.auditSubjectClass,
        table.auditedEntityId,
        table.aggregateScope,
        table.fiscalYearBs,
        table.stockType,
      )
      .nullsNotDistinct(),
    index('audit_financial_stocks_fy_idx').on(table.fiscalYearBs),
    index('audit_financial_stocks_type_idx').on(table.stockType),
    index('audit_financial_stocks_entity_idx').on(table.auditedEntityId),
  ],
);

export type AuditFinancialStockRow = typeof auditFinancialStocks.$inferSelect;
export type NewAuditFinancialStockRow = typeof auditFinancialStocks.$inferInsert;

// ─── audit_paragraph_metrics ────────────────────────────────────────────

/**
 * Section-38 record reconciliation (ADR-0027) — COUNTS of audit paragraphs by
 * lifecycle status (issued / settled-on-response / carried-forward / remaining)
 * per subject class, with an optional amount. Not money classified by type, so
 * it is neither a beruju line nor a stock balance.
 */
export const auditParagraphMetrics = pgTable(
  'audit_paragraph_metrics',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    auditedEntityId: uuid('audited_entity_id').references(() => entities.id, {
      onDelete: 'restrict',
    }),
    auditSubjectClass: auditSubjectClassEnum('audit_subject_class').notNull(),
    aggregateScope: text('aggregate_scope'),
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    paragraphStatus: auditParagraphStatusEnum('paragraph_status').notNull(),
    paragraphCount: integer('paragraph_count'),
    amountNpr: numeric('amount_npr', { precision: 20, scale: 2 }),
    amountRaw: text('amount_raw'),

    sourceUnit: text('source_unit'),
    sourceScale: numeric('source_scale', { precision: 20, scale: 6 }),
    sourceTableCode: text('source_table_code').notNull(),
    sourceRowLabel: text('source_row_label'),
    sourcePage: integer('source_page'),
    sourceTableRef: text('source_table_ref'),
    sourceCellRef: text('source_cell_ref'),

    ...auditProvenanceColumns(),
  },
  (table) => [
    unique('audit_paragraph_metrics_unique')
      .on(
        table.sourceDocumentId,
        table.auditSubjectClass,
        table.auditedEntityId,
        table.aggregateScope,
        table.fiscalYearBs,
        table.paragraphStatus,
      )
      .nullsNotDistinct(),
    index('audit_paragraph_metrics_fy_idx').on(table.fiscalYearBs),
    index('audit_paragraph_metrics_entity_idx').on(table.auditedEntityId),
  ],
);

export type AuditParagraphMetricRow = typeof auditParagraphMetrics.$inferSelect;
export type NewAuditParagraphMetricRow = typeof auditParagraphMetrics.$inferInsert;

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
