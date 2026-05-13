/**
 * Administrative units — Nepal's federal political hierarchy.
 *
 * Joined hierarchy: province → district → local_level → ward → polling_station.
 * Each row is its own `entities` row PLUS this specialized row capturing
 * federal codes and topology that don't belong in the generic entity metadata.
 *
 * Source: `administrative_hierarchy_FINAL.csv` (10,263 rows derived from the
 * voter database). Constitutional totals: 7 provinces, 77 districts, 753
 * local levels (6 metro + 11 sub-metro + 276 muni + 460 rural municipality),
 * ~6,176 wards, ~10,203 polling stations.
 */

import { index, integer, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { entities } from './entities';
import { localLevelTypeEnum } from './enums';

export const administrativeUnits = pgTable(
  'administrative_units',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    // 1:1 with an entities row. Every administrative unit also appears in
    // the entities dimension so cross-domain queries work uniformly.
    entityId: uuid('entity_id')
      .notNull()
      .references(() => entities.id, { onDelete: 'cascade' }),

    // Federal Ministry of Federal Affairs and General Administration code.
    // - Province: 1-digit
    // - District: 3-digit (province + 2-digit district)
    // - Local level: 8-digit (province + district + 5-digit local code)
    // - Ward: 11-digit (local level + ward number)
    // - Polling station: free-form (provided by EC, may include letters)
    federalCode: text('federal_code'),

    // Local-level type only for local-level rows; NULL for province/district/ward.
    localLevelType: localLevelTypeEnum('local_level_type'),

    // For local-level rows: federal-parliament constituency number (1..165
    // in the current districting, prefixed with district name).
    constituencyNo: text('constituency_no'),

    // For ward rows: ward number within the local level (1..varies).
    wardNo: integer('ward_no'),

    // Whether classified urban or rural by the federal scheme. Mostly
    // determined by local-level-type but the source CSV carries both.
    ruralUrban: text('rural_urban'),

    // For polling-station rows: voter count from the EC source. Populated
    // by the admin-hierarchy ingest from the voter DB derivative.
    voterCount: integer('voter_count'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex('admin_units_entity_idx').on(table.entityId),
    index('admin_units_federal_code_idx').on(table.federalCode),
    index('admin_units_constituency_idx').on(table.constituencyNo),
  ],
);

export type AdministrativeUnitRow = typeof administrativeUnits.$inferSelect;
export type NewAdministrativeUnitRow = typeof administrativeUnits.$inferInsert;
