/**
 * Government audit fact-domain repository (ADR-0024).
 *
 * Typed data-access for the three OAG audit tables. Two upsert shapes:
 *
 *   - Summaries + beruju lines are **precedence-guarded**: a row only
 *     overwrites an existing one when `excluded.source_precedence >=` the
 *     existing row's precedence. So a local-body final report (precedence 2)
 *     overrides an annual-report local summary (precedence 1) — never the
 *     reverse, and a weaker source already present is never silently kept.
 *   - Findings are **document-scoped** (`source_document_id` is in their key),
 *     so re-parsing is idempotent via plain `ON CONFLICT DO NOTHING`.
 *
 * All calls go through `safeQuery`. Empty input is `ok(zeros)`, never an error.
 */

import { sql } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  auditBerujuLines,
  auditEntitySummaries,
  auditFinancialStocks,
  auditFindings,
  auditParagraphMetrics,
  type NewAuditBerujuLineRow,
  type NewAuditEntitySummaryRow,
  type NewAuditFinancialStockRow,
  type NewAuditFindingRow,
  type NewAuditParagraphMetricRow,
} from '@/lib/db/schema/audit-facts';
import { ok, type Result } from '@/lib/errors';

export type BulkUpsertSummary = {
  attempted: number;
  /** Rows inserted or updated (precedence won). */
  upserted: number;
  /** Rows skipped — conflict where the incoming precedence was lower. */
  skipped: number;
};

/**
 * Columns overwritten from `excluded` on a precedence-winning conflict.
 * Shared across summaries + lines because the provenance column names are
 * identical on every audit fact table. Natural-key columns are omitted (they
 * are equal under the conflict by definition).
 */
const provenanceUpdateSet = {
  sourceDocumentId: sql`excluded.source_document_id`,
  sourcePrecedence: sql`excluded.source_precedence`,
  extractionMethod: sql`excluded.extraction_method`,
  ocrCellExtractionId: sql`excluded.ocr_cell_extraction_id`,
  sourcePage: sql`excluded.source_page`,
  sourceTableRef: sql`excluded.source_table_ref`,
  sourceCellRef: sql`excluded.source_cell_ref`,
  reviewStatus: sql`excluded.review_status`,
  confidenceGrade: sql`excluded.confidence_grade`,
  promotedAt: sql`excluded.promoted_at`,
  promotedBy: sql`excluded.promoted_by`,
  notes: sql`excluded.notes`,
} as const;

/**
 * Precedence-guarded bulk upsert into `audit_entity_summaries`.
 */
export async function bulkUpsertAuditSummaries(
  rows: readonly NewAuditEntitySummaryRow[],
): Promise<Result<BulkUpsertSummary>> {
  if (rows.length === 0) return ok({ attempted: 0, upserted: 0, skipped: 0 });

  const upserted = await safeQuery(() =>
    db()
      .insert(auditEntitySummaries)
      .values([...rows])
      .onConflictDoUpdate({
        target: [
          auditEntitySummaries.auditSubjectClass,
          auditEntitySummaries.auditedEntityId,
          auditEntitySummaries.aggregateScope,
          auditEntitySummaries.fiscalYearBs,
        ],
        setWhere: sql`excluded.source_precedence >= ${auditEntitySummaries.sourcePrecedence}`,
        set: {
          aggregateLabelRaw: sql`excluded.aggregate_label_raw`,
          auditedAmountNpr: sql`excluded.audited_amount_npr`,
          auditedAmountRaw: sql`excluded.audited_amount_raw`,
          berujuRaisedNpr: sql`excluded.beruju_raised_npr`,
          berujuRaisedRaw: sql`excluded.beruju_raised_raw`,
          settledThisYearNpr: sql`excluded.settled_this_year_npr`,
          settledThisYearRaw: sql`excluded.settled_this_year_raw`,
          cumulativeOutstandingNpr: sql`excluded.cumulative_outstanding_npr`,
          cumulativeOutstandingRaw: sql`excluded.cumulative_outstanding_raw`,
          sourceUnit: sql`excluded.source_unit`,
          sourceScale: sql`excluded.source_scale`,
          ...provenanceUpdateSet,
        },
      })
      .returning({ id: auditEntitySummaries.id }),
  );
  if (!upserted.ok) return upserted;
  return ok(summarize(rows.length, upserted.value.length));
}

/**
 * Precedence-guarded bulk upsert into `audit_beruju_lines`.
 */
export async function bulkUpsertBerujuLines(
  rows: readonly NewAuditBerujuLineRow[],
): Promise<Result<BulkUpsertSummary>> {
  if (rows.length === 0) return ok({ attempted: 0, upserted: 0, skipped: 0 });

  const upserted = await safeQuery(() =>
    db()
      .insert(auditBerujuLines)
      .values([...rows])
      .onConflictDoUpdate({
        target: [
          auditBerujuLines.sourceDocumentId,
          auditBerujuLines.auditSubjectClass,
          auditBerujuLines.auditedEntityId,
          auditBerujuLines.aggregateScope,
          auditBerujuLines.fiscalYearBs,
          auditBerujuLines.amountBasis,
          auditBerujuLines.berujuCategory,
          auditBerujuLines.aggregationRole,
          auditBerujuLines.sourceTableCode,
        ],
        setWhere: sql`excluded.source_precedence >= ${auditBerujuLines.sourcePrecedence}`,
        set: {
          berujuCategoryLabelRaw: sql`excluded.beruju_category_label_raw`,
          sourceRowLabel: sql`excluded.source_row_label`,
          valueOrigin: sql`excluded.value_origin`,
          amountNpr: sql`excluded.amount_npr`,
          amountRaw: sql`excluded.amount_raw`,
          sourceUnit: sql`excluded.source_unit`,
          sourceScale: sql`excluded.source_scale`,
          ...provenanceUpdateSet,
        },
      })
      .returning({ id: auditBerujuLines.id }),
  );
  if (!upserted.ok) return upserted;
  return ok(summarize(rows.length, upserted.value.length));
}

/**
 * Idempotent bulk insert into `audit_findings`. Findings are document-scoped
 * (`source_document_id` is in the natural key), so re-parsing the same report
 * is a no-op rather than a precedence question.
 */
export async function bulkInsertAuditFindings(
  rows: readonly NewAuditFindingRow[],
): Promise<Result<BulkUpsertSummary>> {
  if (rows.length === 0) return ok({ attempted: 0, upserted: 0, skipped: 0 });

  const inserted = await safeQuery(() =>
    db()
      .insert(auditFindings)
      .values([...rows])
      .onConflictDoNothing({
        target: [
          auditFindings.sourceDocumentId,
          auditFindings.auditedEntityId,
          auditFindings.fiscalYearBs,
          auditFindings.findingOrdinal,
        ],
      })
      .returning({ id: auditFindings.id }),
  );
  if (!inserted.ok) return inserted;
  return ok(summarize(rows.length, inserted.value.length));
}

/**
 * Precedence-guarded bulk upsert into `audit_financial_stocks` (ADR-0027 stock
 * balances — arrears, reimbursables, backlogs). Document-scoped key.
 */
export async function bulkUpsertFinancialStocks(
  rows: readonly NewAuditFinancialStockRow[],
): Promise<Result<BulkUpsertSummary>> {
  if (rows.length === 0) return ok({ attempted: 0, upserted: 0, skipped: 0 });

  const upserted = await safeQuery(() =>
    db()
      .insert(auditFinancialStocks)
      .values([...rows])
      .onConflictDoUpdate({
        target: [
          auditFinancialStocks.sourceDocumentId,
          auditFinancialStocks.auditSubjectClass,
          auditFinancialStocks.auditedEntityId,
          auditFinancialStocks.aggregateScope,
          auditFinancialStocks.fiscalYearBs,
          auditFinancialStocks.stockType,
        ],
        setWhere: sql`excluded.source_precedence >= ${auditFinancialStocks.sourcePrecedence}`,
        set: {
          openingNpr: sql`excluded.opening_npr`,
          openingRaw: sql`excluded.opening_raw`,
          additionNpr: sql`excluded.addition_npr`,
          additionRaw: sql`excluded.addition_raw`,
          settlementNpr: sql`excluded.settlement_npr`,
          settlementRaw: sql`excluded.settlement_raw`,
          adjustmentNpr: sql`excluded.adjustment_npr`,
          adjustmentRaw: sql`excluded.adjustment_raw`,
          closingNpr: sql`excluded.closing_npr`,
          closingRaw: sql`excluded.closing_raw`,
          sourceUnit: sql`excluded.source_unit`,
          sourceScale: sql`excluded.source_scale`,
          sourceRowLabel: sql`excluded.source_row_label`,
          ...provenanceUpdateSet,
        },
      })
      .returning({ id: auditFinancialStocks.id }),
  );
  if (!upserted.ok) return upserted;
  return ok(summarize(rows.length, upserted.value.length));
}

/**
 * Precedence-guarded bulk upsert into `audit_paragraph_metrics` (ADR-0027
 * Section-38 paragraph counts). Document-scoped key.
 */
export async function bulkUpsertParagraphMetrics(
  rows: readonly NewAuditParagraphMetricRow[],
): Promise<Result<BulkUpsertSummary>> {
  if (rows.length === 0) return ok({ attempted: 0, upserted: 0, skipped: 0 });

  const upserted = await safeQuery(() =>
    db()
      .insert(auditParagraphMetrics)
      .values([...rows])
      .onConflictDoUpdate({
        target: [
          auditParagraphMetrics.sourceDocumentId,
          auditParagraphMetrics.auditSubjectClass,
          auditParagraphMetrics.auditedEntityId,
          auditParagraphMetrics.aggregateScope,
          auditParagraphMetrics.fiscalYearBs,
          auditParagraphMetrics.paragraphStatus,
        ],
        setWhere: sql`excluded.source_precedence >= ${auditParagraphMetrics.sourcePrecedence}`,
        set: {
          paragraphCount: sql`excluded.paragraph_count`,
          amountNpr: sql`excluded.amount_npr`,
          amountRaw: sql`excluded.amount_raw`,
          sourceUnit: sql`excluded.source_unit`,
          sourceScale: sql`excluded.source_scale`,
          sourceRowLabel: sql`excluded.source_row_label`,
          ...provenanceUpdateSet,
        },
      })
      .returning({ id: auditParagraphMetrics.id }),
  );
  if (!upserted.ok) return upserted;
  return ok(summarize(rows.length, upserted.value.length));
}

function summarize(attempted: number, affected: number): BulkUpsertSummary {
  return { attempted, upserted: affected, skipped: attempted - affected };
}
