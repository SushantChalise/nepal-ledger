/**
 * Census 2021 (NPHC) facts — long-format per municipality × indicator.
 *
 * Source: CBS National Population & Housing Census 2021. 89 CSVs + 8 Excel
 * files at municipality (gapa) granularity; ward-level only in the DEGURBA
 * Excel. The 7 provinces × 77 districts × 753 local levels × ~6,176 wards
 * referenced via `entity_id`.
 *
 * Census schema = single fact table because the indicator dimension is wide
 * (hundreds of named columns across the 89 CSVs) and stable. Each CSV row
 * becomes many fact rows after column-explode.
 */

import { index, numeric, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { censusIndicatorFamilyEnum, confidenceGradeEnum } from './enums';
import { entities } from './entities';
import { sourceDocuments } from './source-documents';

export const censusFacts = pgTable(
  'census_facts',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    // Either a local_level entity (most CSVs) or a ward entity (DEGURBA).
    entityId: uuid('entity_id')
      .notNull()
      .references(() => entities.id, { onDelete: 'restrict' }),

    indicatorFamily: censusIndicatorFamilyEnum('indicator_family').notNull(),

    // Source filename without extension: 'Hhld01_OwnershipOfHouse' etc.
    // Keeps a stable provenance handle independent of the indicator slug.
    sourceTableId: text('source_table_id').notNull(),

    // E.g. 'household-owned', 'cooking-fuel-lpg', 'population-female',
    // 'literate-female-15-plus'. Derived from CSV column name + categorical
    // breakdown. Documented in scrapers/census/<table>/parser.py.
    indicatorSlug: text('indicator_slug').notNull(),

    // Categorical breakdown captured in jsonb-of-strings form via the slug
    // (sex / age-group / urban-rural / literacy-status / etc.). Avoids
    // explosion of one column per breakdown axis.

    value: numeric('value', { precision: 24, scale: 6 }).notNull(),
    unit: text('unit').notNull(),

    // The census reference year — currently always 2021 / BS 2078 — but
    // kept as a column so the table extends cleanly to the next census.
    censusYearAd: text('census_year_ad').notNull().default('2021'),
    censusYearBs: text('census_year_bs').notNull().default('2078'),

    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),
    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull().default('A'),

    promotedAt: timestamp('promoted_at', { withTimezone: true }).notNull().defaultNow(),
    promotedBy: text('promoted_by').notNull(),
  },
  (table) => [
    uniqueIndex('census_facts_unique_idx').on(
      table.entityId,
      table.indicatorSlug,
      table.censusYearAd,
    ),
    index('census_facts_entity_idx').on(table.entityId),
    index('census_facts_family_idx').on(table.indicatorFamily),
    index('census_facts_slug_idx').on(table.indicatorSlug),
  ],
);

export type CensusFactRow = typeof censusFacts.$inferSelect;
export type NewCensusFactRow = typeof censusFacts.$inferInsert;
