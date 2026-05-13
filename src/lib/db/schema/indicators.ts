/**
 * Indicators — the canonical catalogue of what Nepal Ledger tracks.
 *
 * Examples: `inflation-yoy`, `nrb-reserves`, `nrb-credit-to-private-sector`,
 * `kalimati-tomato-wholesale`, `nepse-index`, `tourism-arrivals-monthly`.
 *
 * An indicator is a *concept* (the thing measured); its time-series values
 * live in `approved_indicator_values`; its sources are joined via
 * `indicator_source_map`.
 */

import { foreignKey, index, pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';

import { indicatorCategoryEnum } from './enums';
import { sourceRegistry } from './source-registry';

export const indicators = pgTable(
  'indicators',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    slug: text('slug').notNull().unique(),

    nameEn: text('name_en').notNull(),
    nameNe: text('name_ne'),

    category: indicatorCategoryEnum('category').notNull(),

    // Canonical unit string (e.g. "NPR_billion", "percent", "months_of_imports",
    // "kg_per_capita", "index_points"). Resolved via `indicator_units`.
    unit: text('unit').notNull(),

    // Native cadence — does not constrain stored values (a monthly indicator
    // can also be stored quarterly aggregated), but provides a default.
    nativeFrequency: text('native_frequency').notNull(),

    sourceAgency: text('source_agency').notNull(),
    parentIndicatorId: uuid('parent_indicator_id'),

    descriptionEn: text('description_en'),
    descriptionNe: text('description_ne'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    foreignKey({
      columns: [table.parentIndicatorId],
      foreignColumns: [table.id],
      name: 'indicators_parent_fk',
    }).onDelete('set null'),
    index('indicators_category_idx').on(table.category),
  ],
);

export type IndicatorRow = typeof indicators.$inferSelect;
export type NewIndicatorRow = typeof indicators.$inferInsert;

/**
 * Indicator ↔ Source mapping. An indicator may have multiple feeding sources
 * (e.g. NCPI inflation is fed by both the CMEFs PDF and the standalone NCPI
 * table CSV — same numbers, two sources of record).
 */
export const indicatorSourceMap = pgTable(
  'indicator_source_map',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    indicatorId: uuid('indicator_id')
      .notNull()
      .references(() => indicators.id, { onDelete: 'cascade' }),
    sourceId: text('source_id')
      .notNull()
      .references(() => sourceRegistry.sourceId, { onDelete: 'restrict' }),
    notes: text('notes'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index('indicator_source_map_indicator_idx').on(table.indicatorId),
    index('indicator_source_map_source_idx').on(table.sourceId),
  ],
);

export type IndicatorSourceMapRow = typeof indicatorSourceMap.$inferSelect;
export type NewIndicatorSourceMapRow = typeof indicatorSourceMap.$inferInsert;

/**
 * Canonical unit registry. A controlled vocabulary the parser must hit
 * exactly. Validation rejects values whose unit string isn't in this table.
 */
export const indicatorUnits = pgTable('indicator_units', {
  unit: text('unit').primaryKey(),
  displayEn: text('display_en').notNull(),
  displayNe: text('display_ne'),
  dimension: text('dimension').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

export type IndicatorUnitRow = typeof indicatorUnits.$inferSelect;
export type NewIndicatorUnitRow = typeof indicatorUnits.$inferInsert;
