/**
 * Entities — the master dimension table for everything that's NOT a macro
 * indicator concept. Banks, public enterprises, local levels, cooperatives,
 * business groups, ministries, donors, constituencies, wards all live here.
 *
 * Indicators that are entity-scoped (e.g. NOC Net Profit; NEA Generation MWh)
 * carry an `entity_id` FK on `indicators`. Macro indicators (NCPI inflation,
 * NEPSE index) leave it NULL.
 *
 * Reference: docs/FINANCIAL_DATA_STRATEGY.md §"Schema impact" (ADR-0009).
 */

import {
  foreignKey,
  index,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from 'drizzle-orm/pg-core';

import { entityKindEnum } from './enums';

export const entities = pgTable(
  'entities',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    kind: entityKindEnum('kind').notNull(),

    // Stable kebab-case identifier. Examples:
    //   bank: 'rastriya-banijya-bank', 'global-ime-bank'
    //   public_enterprise: 'noc', 'nea', 'nac', 'ntc'
    //   local_level: '80101101' (8-digit federal code; not kebab)
    //   district: '801' (3-digit federal code)
    //   donor: 'adb', 'wb', 'jica', 'china-exim'
    slug: text('slug').notNull(),

    nameEn: text('name_en').notNull(),
    nameNe: text('name_ne'),

    // Self-referential hierarchy: local_level → district → province; ward → local_level.
    parentEntityId: uuid('parent_entity_id'),

    // Type-specific structured extras: e.g. for local_level rows we store
    // { local_level_type, federal_code, constituency_no, voter_count, ward_count }.
    // For bank entities: { license_class, license_date }.
    metadata: jsonb('metadata'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    foreignKey({
      columns: [table.parentEntityId],
      foreignColumns: [table.id],
      name: 'entities_parent_fk',
    }).onDelete('set null'),
    uniqueIndex('entities_kind_slug_idx').on(table.kind, table.slug),
    index('entities_parent_idx').on(table.parentEntityId),
    index('entities_kind_idx').on(table.kind),
  ],
);

export type EntityRow = typeof entities.$inferSelect;
export type NewEntityRow = typeof entities.$inferInsert;
