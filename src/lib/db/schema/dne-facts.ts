/**
 * DNE dimensional facts — a base measure sliced by exactly one dimension.
 *
 * Source: NRB "Current Macroeconomic & Financial Situation" (DNE) matrix
 * tables that don't fit the single-series (indicator, period, value) shape of
 * `approved_indicator_values` — Foreign Trade by commodity (~745 commodities)
 * and Remittance by source country / recipient district. Registering each
 * commodity/country/district as an `indicator` would wreck the catalogue, so
 * these live in a dedicated dimensional table (see ADR-0015).
 *
 * A row is one `(base_indicator_slug, dimension_value, period)` data point.
 * `base_indicator_slug` is the MEASURE (e.g. `dne-merchandise-exports`), NOT
 * the commodity; `dimension_value` is the kebab slug of the dimension member
 * (e.g. `agarbatti`). Members are intentionally NOT registered in `indicators`.
 *
 * Separate from `banking_sector_facts` / `census_facts` because the dimension
 * here is an open vocabulary (commodities/countries/districts) keyed by an
 * explicit `dimension_kind` + `dimension_value` pair rather than a fixed enum.
 */

import { index, numeric, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { confidenceGradeEnum, reportingPeriodTypeEnum } from './enums';
import { sourceDocuments } from './source-documents';

export const dneFacts = pgTable(
  'dne_facts',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    // The MEASURE, e.g. 'dne-merchandise-exports', 'dne-merchandise-imports',
    // 'dne-remittance-inflow'. NOT the commodity/country/district. Documented
    // in scrapers/nrb_dne/parser.py.
    baseIndicatorSlug: text('base_indicator_slug').notNull(),
    baseIndicatorName: text('base_indicator_name').notNull(),

    // 'commodity' | 'country' | 'district' | 'currency'. Free-text rather than
    // a pgEnum: the dimension vocabulary is open and grows per matrix file; the
    // parser is the controlled-vocabulary authority (ADR-0015).
    dimensionKind: text('dimension_kind').notNull(),
    // Kebab slug of the dimension member, e.g. 'agarbatti', 'qatar', 'baglung'.
    dimensionValue: text('dimension_value').notNull(),
    // Raw source label (Devanagari/English) for the dimension member.
    dimensionLabel: text('dimension_label').notNull(),

    value: numeric('value', { precision: 20, scale: 4 }).notNull(),
    unit: text('unit').notNull(),

    // Calendar/period contract — same fields as approved_indicator_values.
    // DNE matrices are reported annually or monthly (ADR-0013/0015).
    reportingPeriodType: reportingPeriodTypeEnum('reporting_period_type').notNull(),
    reportingPeriodBs: text('reporting_period_bs').notNull(),
    // Nullable: some DNE matrix periods are BS-only at parse time; the AD span
    // is filled when the parser can derive it (ADR-0013 AD fiscal-year labels).
    reportingPeriodAdStart: timestamp('reporting_period_ad_start', { withTimezone: true }),
    reportingPeriodAdEnd: timestamp('reporting_period_ad_end', { withTimezone: true }),

    // Nullable: monthly rows have no fiscal-year context; annual rows do.
    fiscalYearBs: text('fiscal_year_bs'),
    fiscalYearAdLabel: text('fiscal_year_ad_label'),

    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull().default('A'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    // Natural key for idempotent re-ingest via ON CONFLICT DO NOTHING. Plain
    // composite (no COALESCE): every column is NOT NULL, so Postgres treats the
    // tuple as a normal unique key — re-ingesting the same matrix file is a
    // no-op. source_document_id is part of the key so a revised release (new
    // document) can coexist with the prior one.
    uniqueIndex('dne_facts_unique_idx').on(
      table.baseIndicatorSlug,
      table.dimensionKind,
      table.dimensionValue,
      table.reportingPeriodBs,
      table.reportingPeriodType,
      table.sourceDocumentId,
    ),
    index('dne_facts_base_indicator_idx').on(table.baseIndicatorSlug),
    index('dne_facts_dimension_idx').on(table.dimensionKind, table.dimensionValue),
    index('dne_facts_period_idx').on(table.reportingPeriodBs),
  ],
);

export type DneFactRow = typeof dneFacts.$inferSelect;
export type NewDneFactRow = typeof dneFacts.$inferInsert;
