/**
 * Migration permit fact domain — DoFE labour-permit corpus (ADR-0026).
 *
 * The Department of Foreign Employment issues labour permits cut by
 * destination country, origin district, skill class (Atlas Fig 11), permit
 * category (Atlas Fig 8), sex, and fiscal year / month. None of those
 * dimensions fit the time-series `approved_indicator_values` pipeline (they
 * would explode the indicator-slug namespace) and they are not census facts.
 * They are a distinct dimensional fact domain — exactly like `dne_facts`
 * (ADR-0015), `banking_sector_facts`, and `audit_facts` (ADR-0024) — populated
 * direct-to-fact-table, entity-keyed for origin.
 *
 * One row = one `(period × destination × origin × skill × category × sex)`
 * cell. A NULL in any nullable dimension means "marginal / aggregate over that
 * dimension" (the census + DNE convention). `sex` is NOT NULL: its both-sexes
 * aggregate is the explicit `total` value, not a NULL.
 *
 * Foundation only (ADR-0026) — no corpus parsed, no data ingested. The
 * deterministic Python parser (ADR-0003) and the activation of source
 * `dofe-labour-migration` (currently paused) are follow-up work.
 */

import {
  index,
  integer,
  numeric,
  pgTable,
  text,
  timestamp,
  unique,
  uuid,
} from 'drizzle-orm/pg-core';

import {
  confidenceGradeEnum,
  migrationDestinationRegionEnum,
  migrationPermitCategoryEnum,
  migrationSexEnum,
  migrationSkillClassEnum,
} from './enums';
import { entities } from './entities';
import { sourceDocuments } from './source-documents';

export const migrationPermitFacts = pgTable(
  'migration_permit_facts',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    // BS fiscal-year dating (ADR-0013), e.g. '2080/81'.
    fiscalYearBs: text('fiscal_year_bs').notNull(),

    // Nepali month 1–12; NULL = annual aggregate over months.
    monthNum: integer('month_num'),

    // Country name; NULL = all-countries marginal.
    destinationCountry: text('destination_country'),
    // Region bucket (aligned with census Hhld19); NULL = marginal over region.
    destinationRegion: migrationDestinationRegionEnum('destination_region'),

    // Origin district (or local level) entity; NULL = all-Nepal marginal.
    originEntityId: uuid('origin_entity_id').references(() => entities.id, {
      onDelete: 'set null',
    }),

    // NULL = marginal over the respective dimension.
    skillClass: migrationSkillClassEnum('skill_class'),
    permitCategory: migrationPermitCategoryEnum('permit_category'),

    // NOT NULL — 'total' is the explicit both-sexes aggregate.
    sex: migrationSexEnum('sex').notNull(),

    // Permit count: integers (no fractional permits), so scale 0.
    permits: numeric('permits', { precision: 20, scale: 0 }).notNull(),
    unit: text('unit').notNull().default('permits'),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),
    // DoFE permits are administrative records → grade A by default.
    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull().default('A'),

    promotedAt: timestamp('promoted_at', { withTimezone: true }).notNull().defaultNow(),
    promotedBy: text('promoted_by').notNull(),
  },
  (table) => [
    // Single unique constraint over the full dimension tuple, declared with
    // NULLS NOT DISTINCT so marginal rows (carrying NULLs) collide instead of
    // duplicating on re-ingest. This expresses the intent directly — no
    // coalesce-sentinel index needed (cf. banking_sector_facts) — and mirrors
    // the audit_facts aggregate-row pattern (ADR-0024 / ADR-0026).
    unique('migration_permit_facts_unique')
      .on(
        table.fiscalYearBs,
        table.monthNum,
        table.destinationCountry,
        table.destinationRegion,
        table.originEntityId,
        table.skillClass,
        table.permitCategory,
        table.sex,
      )
      .nullsNotDistinct(),
    index('migration_permit_facts_fy_idx').on(table.fiscalYearBs),
    index('migration_permit_facts_origin_idx').on(table.originEntityId),
    index('migration_permit_facts_region_idx').on(table.destinationRegion),
    index('migration_permit_facts_country_idx').on(table.destinationCountry),
  ],
);

export type MigrationPermitFactRow = typeof migrationPermitFacts.$inferSelect;
export type NewMigrationPermitFactRow = typeof migrationPermitFacts.$inferInsert;
