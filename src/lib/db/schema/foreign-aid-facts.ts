/**
 * Foreign-aid dimensional facts — a base aid measure sliced by exactly one
 * dimension (development partner OR spending sector).
 *
 * Source: Ministry of Finance "Source Book for Projects Financed with Foreign
 * Assistance" (the *White Book*). Its two clean English summary tables —
 * "Development Partnerwise Summary" (by donor) and "Summary of Ministrywise
 * Development Partners" (by ministry/sector) — are matrices of (member × measure)
 * that don't fit the single-series (indicator, period, value) shape of
 * `approved_indicator_values`. Registering each donor/ministry as an `indicator`
 * would wreck the catalogue, so these live in a dedicated dimensional table
 * (same precedent as `dne_facts`, ADR-0015; this table's own model is ADR-0017).
 *
 * A row is one `(base_indicator_slug, dimension_kind, dimension_value, period)`
 * data point. `base_indicator_slug` is the MEASURE (`foreign-aid-grant` /
 * `foreign-aid-loan`), NOT the donor; `dimension_value` is the kebab slug of the
 * dimension member (e.g. `adb-general`, `ministry-of-finance`). Members are
 * intentionally NOT registered in `indicators`.
 *
 * Unit varies by White Book edition and is carried per-row VERBATIM from the
 * table's own annotation (`npr_lakh` for "(Rs. in '00000')"; `npr_thousand` for
 * "(NRs'000s)") — never normalised at ingest (ADR-0011 / ADR-0017). Downstream
 * consumers must read `unit` before summing across editions.
 *
 * Mirrors `dne_facts` field-for-field so the migration is mechanical.
 */

import { index, numeric, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { confidenceGradeEnum, reportingPeriodTypeEnum } from './enums';
import { sourceDocuments } from './source-documents';

export const foreignAidFacts = pgTable(
  'foreign_aid_facts',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    // The MEASURE: 'foreign-aid-grant' (Total Grant column) or
    // 'foreign-aid-loan' (Total Loan column). NOT the donor/ministry.
    // Documented in scrapers/mof_whitebook/parser.py.
    baseIndicatorSlug: text('base_indicator_slug').notNull(),
    baseIndicatorName: text('base_indicator_name').notNull(),

    // 'donor' | 'sector'. Free-text rather than a pgEnum: the dimension
    // vocabulary (donors, ministries) is open and grows per edition; the parser
    // is the controlled-vocabulary authority (mirrors dne_facts, ADR-0015/0017).
    dimensionKind: text('dimension_kind').notNull(),
    // Kebab slug of the dimension member, e.g. 'adb-general', 'ministry-of-finance'.
    dimensionValue: text('dimension_value').notNull(),
    // Raw source label (English donor/ministry name) for the dimension member.
    dimensionLabel: text('dimension_label').notNull(),

    value: numeric('value', { precision: 20, scale: 4 }).notNull(),
    // 'npr_lakh' | 'npr_thousand' — verbatim from the White Book edition's unit
    // annotation (ADR-0011). NOT normalised; consumers must read this column.
    unit: text('unit').notNull(),

    // Calendar/period contract — same fields as approved_indicator_values.
    // White Book figures are reported per fiscal year (ADR-0013/0017).
    reportingPeriodType: reportingPeriodTypeEnum('reporting_period_type').notNull(),
    reportingPeriodBs: text('reporting_period_bs').notNull(),
    // Nullable for parity with dne_facts; the White Book parser always fills the
    // AD span (the annual fiscal-year bounds), but the column stays nullable so
    // the table shape matches the dimensional precedent exactly.
    reportingPeriodAdStart: timestamp('reporting_period_ad_start', { withTimezone: true }),
    reportingPeriodAdEnd: timestamp('reporting_period_ad_end', { withTimezone: true }),

    // White Book rows are annual, so both fiscal-year fields are populated;
    // nullable for parity with dne_facts (whose monthly rows have no FY context).
    fiscalYearBs: text('fiscal_year_bs'),
    fiscalYearAdLabel: text('fiscal_year_ad_label'),

    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull().default('B'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    // Natural key for idempotent re-ingest via ON CONFLICT DO NOTHING. Plain
    // composite (no COALESCE): every keyed column is NOT NULL, so Postgres treats
    // the tuple as a normal unique key — re-ingesting the same edition is a no-op.
    // source_document_id is part of the key so a revised edition (new document)
    // can coexist with the prior one. dimension_kind is in the key so the donor
    // and sector cuts of the same measure/period never collide.
    uniqueIndex('foreign_aid_facts_unique_idx').on(
      table.baseIndicatorSlug,
      table.dimensionKind,
      table.dimensionValue,
      table.reportingPeriodBs,
      table.reportingPeriodType,
      table.sourceDocumentId,
    ),
    index('foreign_aid_facts_base_indicator_idx').on(table.baseIndicatorSlug),
    index('foreign_aid_facts_dimension_idx').on(table.dimensionKind, table.dimensionValue),
    index('foreign_aid_facts_period_idx').on(table.reportingPeriodBs),
  ],
);

export type ForeignAidFactRow = typeof foreignAidFacts.$inferSelect;
export type NewForeignAidFactRow = typeof foreignAidFacts.$inferInsert;
