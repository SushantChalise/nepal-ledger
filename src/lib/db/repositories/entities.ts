/**
 * Entities repository — the canonical DB path for the `entities` dimension.
 *
 * Created when a second consumer (the OAG audit parsers, ADR-0024) needed
 * entity resolution beyond the local-level lookup that previously lived in
 * `local-government-fiscal-transfers.ts`. Provides:
 *   - `bulkUpsertEntities` — idempotent seed write (keyed on the unique index
 *     `(kind, slug)`), used by `scripts/seed-audit-entities.ts`.
 *   - `findEntityByKindAndSlug` / `findProvinceByNo` — exact-slug resolution
 *     seams the audit ingest uses to attach per-entity rows.
 *
 * Fuzzy Devanagari name resolution (for matching report labels to entities)
 * stays in the Python `scrapers/_common/municipality_resolver.py` at parse
 * time; this module is exact-key lookup only.
 */

import { and, eq, sql } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { entities, type EntityRow, type NewEntityRow } from '@/lib/db/schema/entities';
import { type EntityKind } from '@/lib/db/schema/enums';
import { ok, type Result } from '@/lib/errors';

export type BulkUpsertEntitiesSummary = { attempted: number; upserted: number };

/**
 * Idempotent bulk upsert keyed on `(kind, slug)`. Refreshes name/metadata on
 * conflict; never touches `id` or `createdAt`. Empty input → `ok(zeros)`.
 */
export async function bulkUpsertEntities(
  rows: readonly NewEntityRow[],
): Promise<Result<BulkUpsertEntitiesSummary>> {
  if (rows.length === 0) return ok({ attempted: 0, upserted: 0 });

  const upserted = await safeQuery(() =>
    db()
      .insert(entities)
      .values([...rows])
      .onConflictDoUpdate({
        target: [entities.kind, entities.slug],
        set: {
          nameEn: sql`excluded.name_en`,
          nameNe: sql`excluded.name_ne`,
          parentEntityId: sql`excluded.parent_entity_id`,
          metadata: sql`excluded.metadata`,
          updatedAt: new Date(),
        },
      })
      .returning({ id: entities.id }),
  );
  if (!upserted.ok) return upserted;
  return ok({ attempted: rows.length, upserted: upserted.value.length });
}

/**
 * Resolve an entity by its `(kind, slug)` natural key. Returns `ok(null)` —
 * not `NotFound` — when absent, so callers can branch cheaply on a miss
 * (the ingest "park unresolved" path treats absence as a successful negative).
 */
export async function findEntityByKindAndSlug(
  kind: EntityKind,
  slug: string,
): Promise<Result<EntityRow | null>> {
  const queried = await safeQuery(() =>
    db().query.entities.findFirst({
      where: and(eq(entities.kind, kind), eq(entities.slug, slug)),
    }),
  );
  if (!queried.ok) return queried;
  return ok(queried.value ?? null);
}

/** Resolve a province entity by its federal province number (1–7). */
export async function findProvinceByNo(provinceNo: number): Promise<Result<EntityRow | null>> {
  return findEntityByKindAndSlug('province', String(provinceNo));
}
