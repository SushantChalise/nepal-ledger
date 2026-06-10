/**
 * NRB Banking & Financial Statistics monthly facts.
 *
 * Sourced from the NRB BFI Monthly XLSX series (50 files Aug 2021 → Sept 2025,
 * one file = one snapshot, 25 sheets per file). Each row here represents one
 * (bank_class, indicator, period) data point — the long-format equivalent of
 * the C5–C25 sheet tables.
 *
 * Separate from `approved_indicator_values` because:
 *   - Bank-class dimension would explode the indicator slug namespace
 *   - Sheet-specific provenance (which C-sheet → which indicator slug) matters
 *     for revision detection across monthly snapshots
 */

import { sql } from 'drizzle-orm';
import { index, numeric, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { bankClassEnum, confidenceGradeEnum, reportingPeriodTypeEnum } from './enums';
import { entities } from './entities';
import { sourceDocuments } from './source-documents';

/**
 * Sentinel UUID standing in for "no bank entity" (system-aggregate rows where
 * `bank_entity_id IS NULL`). Postgres treats NULLs as DISTINCT in unique
 * indexes, so a plain unique index over `bank_entity_id` never matches NULL
 * rows on `ON CONFLICT DO NOTHING` — re-ingesting a month would duplicate every
 * aggregate row. Coalescing NULL to this fixed UUID inside the unique index
 * makes those rows collide, restoring idempotent re-ingest. The value is the
 * all-zeros UUID, which entities.id (a random v4 UUID) can never take.
 */
export const BANK_ENTITY_NULL_SENTINEL = '00000000-0000-0000-0000-000000000000';

export const bankingSectorFacts = pgTable(
  'banking_sector_facts',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    bankClass: bankClassEnum('bank_class').notNull(),

    // NULL when the fact is at the bank-class aggregate level (e.g. "all
    // commercial banks paid-up capital"). Populated when the row is per
    // bank (entity.kind = 'bank').
    bankEntityId: uuid('bank_entity_id').references(() => entities.id, {
      onDelete: 'set null',
    }),

    // Source sheet inside the NRB BFI XLSX: 'C5' (Assets & Liabilities),
    // 'C6' (P&L), 'C7' (Sector-wise lending), etc.
    sourceSheet: text('source_sheet').notNull(),

    // E.g. 'paid-up-capital', 'capital-fund', 'sector-credit-real-estate',
    // 'sector-credit-hydropower', 'npl-by-sector-agriculture'. Documented in
    // scrapers/nrb_bfi/parser.py.
    indicatorSlug: text('indicator_slug').notNull(),

    value: numeric('value', { precision: 24, scale: 6 }).notNull(),
    unit: text('unit').notNull(),

    // Calendar/period contract — same fields as approved_indicator_values.
    reportingPeriodType: reportingPeriodTypeEnum('reporting_period_type').notNull(),
    reportingPeriodBs: text('reporting_period_bs').notNull(),
    reportingPeriodAdStart: timestamp('reporting_period_ad_start', {
      withTimezone: true,
    }).notNull(),
    reportingPeriodAdEnd: timestamp('reporting_period_ad_end', { withTimezone: true }).notNull(),

    publicationDateAd: timestamp('publication_date_ad', { withTimezone: true }).notNull(),
    publicationDateBs: text('publication_date_bs').notNull(),

    fiscalYearBs: text('fiscal_year_bs').notNull(),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),
    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull().default('A'),

    promotedAt: timestamp('promoted_at', { withTimezone: true }).notNull().defaultNow(),
    promotedBy: text('promoted_by').notNull(),
  },
  (table) => [
    // NULL bank_entity_id is coalesced to BANK_ENTITY_NULL_SENTINEL so that
    // system-aggregate rows (NULL entity) collide on re-ingest. A plain unique
    // index over bank_entity_id would treat each NULL as DISTINCT, letting
    // onConflictDoNothing re-insert the ~36 aggregate rows per month. See the
    // BANK_ENTITY_NULL_SENTINEL doc-comment above for the full rationale.
    uniqueIndex('banking_facts_unique_idx').on(
      table.bankClass,
      sql`coalesce(${table.bankEntityId}, ${sql.raw(`'${BANK_ENTITY_NULL_SENTINEL}'`)}::uuid)`,
      table.indicatorSlug,
      table.reportingPeriodBs,
      table.reportingPeriodType,
    ),
    index('banking_facts_class_idx').on(table.bankClass),
    index('banking_facts_indicator_idx').on(table.indicatorSlug),
    index('banking_facts_period_idx').on(table.reportingPeriodAdEnd),
  ],
);

export type BankingSectorFactRow = typeof bankingSectorFacts.$inferSelect;
export type NewBankingSectorFactRow = typeof bankingSectorFacts.$inferInsert;
