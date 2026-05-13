/**
 * Source Registry — every external data feed registered before any scraper is
 * written. Per docs/SOURCE_REGISTRY.md, a scraper merged without a registry
 * entry is reverted on sight.
 */

import { sql } from 'drizzle-orm';
import { boolean, pgTable, text, timestamp } from 'drizzle-orm/pg-core';

import {
  confidenceGradeEnum,
  fileFormatEnum,
  licenseStatusEnum,
  publicationFrequencyEnum,
  reportingPeriodTypeEnum,
  sourceStatusEnum,
} from './enums';

export const sourceRegistry = pgTable('source_registry', {
  // Stable kebab-case slug. Used in storage keys, parser paths, FKs.
  sourceId: text('source_id').primaryKey(),

  agency: text('agency').notNull(),
  agencyShort: text('agency_short').notNull(),
  datasetName: text('dataset_name').notNull(),
  sourceUrl: text('source_url').notNull(),

  publicationFrequency: publicationFrequencyEnum('publication_frequency').notNull(),
  expectedReleaseWindow: text('expected_release_window'),
  reportingPeriodType: reportingPeriodTypeEnum('reporting_period_type').notNull(),

  fileFormat: fileFormatEnum('file_format').notNull(),
  requiresTableExtraction: boolean('requires_table_extraction').notNull().default(false),
  historicalCoverage: text('historical_coverage'),
  licenseStatus: licenseStatusEnum('license_status').notNull().default('gov_open'),

  parserOwner: text('parser_owner'),
  parserVersion: text('parser_version'),
  revisionPolicy: text('revision_policy'),

  // text[] — Postgres array. Parser bumps version when it learns a new mode.
  knownBreakageModes: text('known_breakage_modes')
    .array()
    .notNull()
    .default(sql`ARRAY[]::text[]`),

  confidenceDefault: confidenceGradeEnum('confidence_default').notNull().default('A'),
  status: sourceStatusEnum('status').notNull().default('active'),
  notes: text('notes'),

  registeredAt: timestamp('registered_at', { withTimezone: true }).notNull().defaultNow(),
  lastVerifiedAt: timestamp('last_verified_at', { withTimezone: true }),
});

export type SourceRegistryRow = typeof sourceRegistry.$inferSelect;
export type NewSourceRegistryRow = typeof sourceRegistry.$inferInsert;
