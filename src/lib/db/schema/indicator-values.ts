/**
 * Indicator values pipeline: staging → validation → approved.
 *
 * Every row carries the FULL calendar/period contract from CALENDAR_AND_PERIODS.md:
 * reporting-period (BS + AD start + AD end) AND publication-date (BS + AD) AND
 * fiscal-year label AND revision number. Feature code reads ONLY from
 * `approved_indicator_values`.
 */

import { sql } from 'drizzle-orm';
import {
  index,
  integer,
  numeric,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from 'drizzle-orm/pg-core';

import {
  confidenceGradeEnum,
  dataQualityFlagTypeEnum,
  flagSeverityEnum,
  reportingPeriodTypeEnum,
} from './enums';
import { indicators } from './indicators';
import { parserRuns } from './parser-runs';
import { sourceDocuments } from './source-documents';

/**
 * Untrusted parser output. Cleared after promotion or rejection.
 * No FK constraints on `indicatorId` because the parser may emit a value for
 * an unresolved slug; resolution happens during validation.
 */
export const stagingIndicatorValues = pgTable(
  'staging_indicator_values',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    parserRunId: uuid('parser_run_id')
      .notNull()
      .references(() => parserRuns.id, { onDelete: 'cascade' }),
    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    // Resolved if the parser could map the raw slug to a known indicator.
    indicatorId: uuid('indicator_id').references(() => indicators.id, { onDelete: 'set null' }),
    indicatorSlugRaw: text('indicator_slug_raw').notNull(),

    value: numeric('value', { precision: 24, scale: 6 }).notNull(),
    unit: text('unit').notNull(),

    // Calendar/period contract (CALENDAR_AND_PERIODS.md).
    reportingPeriodType: reportingPeriodTypeEnum('reporting_period_type').notNull(),
    reportingPeriodBs: text('reporting_period_bs').notNull(),
    reportingPeriodAdStart: timestamp('reporting_period_ad_start', {
      withTimezone: true,
    }).notNull(),
    reportingPeriodAdEnd: timestamp('reporting_period_ad_end', { withTimezone: true }).notNull(),

    publicationDateAd: timestamp('publication_date_ad', { withTimezone: true }).notNull(),
    publicationDateBs: text('publication_date_bs').notNull(),

    fiscalYearBs: text('fiscal_year_bs').notNull(),
    fiscalYearAdLabel: text('fiscal_year_ad_label').notNull(),

    confidenceGradeProposed: confidenceGradeEnum('confidence_grade_proposed').notNull(),
    parserNotes: text('parser_notes'),

    insertedAt: timestamp('inserted_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index('staging_run_idx').on(table.parserRunId),
    index('staging_indicator_idx').on(table.indicatorId),
    index('staging_period_idx').on(table.reportingPeriodBs, table.reportingPeriodType),
  ],
);

export type StagingIndicatorValueRow = typeof stagingIndicatorValues.$inferSelect;
export type NewStagingIndicatorValueRow = typeof stagingIndicatorValues.$inferInsert;

/**
 * Production — what the Pulse, Money Map, calculators, and stories read.
 * Same shape as staging minus the parser_run/proposed fields, plus revision
 * tracking. Revisions are append-only; see DATA_PIPELINE.md §"Revisions".
 */
export const approvedIndicatorValues = pgTable(
  'approved_indicator_values',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),
    indicatorId: uuid('indicator_id')
      .notNull()
      .references(() => indicators.id, { onDelete: 'restrict' }),

    value: numeric('value', { precision: 24, scale: 6 }).notNull(),
    unit: text('unit').notNull(),

    reportingPeriodType: reportingPeriodTypeEnum('reporting_period_type').notNull(),
    reportingPeriodBs: text('reporting_period_bs').notNull(),
    reportingPeriodAdStart: timestamp('reporting_period_ad_start', {
      withTimezone: true,
    }).notNull(),
    reportingPeriodAdEnd: timestamp('reporting_period_ad_end', { withTimezone: true }).notNull(),

    publicationDateAd: timestamp('publication_date_ad', { withTimezone: true }).notNull(),
    publicationDateBs: text('publication_date_bs').notNull(),

    fiscalYearBs: text('fiscal_year_bs').notNull(),
    fiscalYearAdLabel: text('fiscal_year_ad_label').notNull(),

    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull(),
    revisionNumber: integer('revision_number').notNull().default(0),

    promotedAt: timestamp('promoted_at', { withTimezone: true }).notNull().defaultNow(),
    // Free-form attribution (script name, agent label, or human handle).
    promotedBy: text('promoted_by').notNull(),

    notes: text('notes'),
  },
  (table) => [
    // One row per (indicator, period, revision). Revisions append new rows
    // with incremented revisionNumber rather than updating in place.
    uniqueIndex('approved_unique_period_revision').on(
      table.indicatorId,
      table.reportingPeriodType,
      table.reportingPeriodBs,
      table.revisionNumber,
    ),
    index('approved_indicator_idx').on(table.indicatorId),
    index('approved_period_idx').on(table.reportingPeriodAdEnd),
    index('approved_fy_idx').on(table.fiscalYearBs),
  ],
);

export type ApprovedIndicatorValueRow = typeof approvedIndicatorValues.$inferSelect;
export type NewApprovedIndicatorValueRow = typeof approvedIndicatorValues.$inferInsert;

/**
 * Validation issues found during promotion. Blocking flags hold a staging
 * row out of production until resolved; warnings annotate a promoted row.
 */
export const dataQualityFlags = pgTable(
  'data_quality_flags',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    stagingRowId: uuid('staging_row_id')
      .notNull()
      .references(() => stagingIndicatorValues.id, { onDelete: 'cascade' }),

    flagType: dataQualityFlagTypeEnum('flag_type').notNull(),
    severity: flagSeverityEnum('severity').notNull(),
    detail: text('detail').notNull(),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    resolvedAt: timestamp('resolved_at', { withTimezone: true }),
    resolutionNote: text('resolution_note'),
  },
  (table) => [
    index('flags_staging_row_idx').on(table.stagingRowId),
    index('flags_unresolved_idx')
      .on(table.severity, table.createdAt)
      .where(sql`resolved_at IS NULL`),
  ],
);

export type DataQualityFlagRow = typeof dataQualityFlags.$inferSelect;
export type NewDataQualityFlagRow = typeof dataQualityFlags.$inferInsert;
