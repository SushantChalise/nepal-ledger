/**
 * Federal-to-local-level fiscal transfers.
 *
 * One row per (local_level, fiscal_year, grant_type, amount). Sourced from
 * MoF/NNRFC intergovernmental fiscal transfer tables — for FY 2082/83 from
 * the pre-cleaned XLSX in `Financial Data/mof_documents/Cleaned/`, for
 * prior FYs from OCR'd intergovernmental PDFs.
 *
 * The four grant types per Nepal's fiscal-federalism law:
 *   1. Equalization Grant (3 sub-types: Minimum, Formula-Based, Performance-Based) — budget head 26331
 *   2. Conditional Grant (Current 26332 + Capital 26336)
 *   3. Special Grant (Current 26333 + Capital 26337)
 *   4. Complementary Grant (Capital only 26334)
 */

import { index, numeric, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { confidenceGradeEnum, grantTypeEnum } from './enums';
import { entities } from './entities';
import { sourceDocuments } from './source-documents';

export const localGovernmentFiscalTransfers = pgTable(
  'local_government_fiscal_transfers',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    // entity.kind = 'local_level'
    localLevelEntityId: uuid('local_level_entity_id')
      .notNull()
      .references(() => entities.id, { onDelete: 'restrict' }),

    // Storage convention: 4-digit start year, slash, 2-digit end (e.g. "2082/83").
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    grantType: grantTypeEnum('grant_type').notNull(),

    // NPR — Numeric with precision for full-rupee sums; unit captured separately.
    amountNpr: numeric('amount_npr', { precision: 20, scale: 2 }).notNull(),
    unit: text('unit').notNull().default('NPR_thousand'),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull(),
    promotedAt: timestamp('promoted_at', { withTimezone: true }).notNull().defaultNow(),
    promotedBy: text('promoted_by').notNull(),
    notes: text('notes'),
  },
  (table) => [
    uniqueIndex('fiscal_transfers_unique_idx').on(
      table.localLevelEntityId,
      table.fiscalYearBs,
      table.grantType,
    ),
    index('fiscal_transfers_local_idx').on(table.localLevelEntityId),
    index('fiscal_transfers_fy_idx').on(table.fiscalYearBs),
  ],
);

export type LocalGovernmentFiscalTransferRow = typeof localGovernmentFiscalTransfers.$inferSelect;
export type NewLocalGovernmentFiscalTransferRow =
  typeof localGovernmentFiscalTransfers.$inferInsert;
