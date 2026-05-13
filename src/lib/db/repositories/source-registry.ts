/**
 * Source Registry repository.
 *
 * Typed data-access for `source_registry`. Every public function composes
 * `safeQuery` so Drizzle/Postgres exceptions become typed `AppError` variants.
 * Feature code imports from this module; raw `db.*` calls in features are
 * rejected at review (see docs/CONVENTIONS.md §"Repository pattern").
 */

import { eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  sourceRegistry,
  type NewSourceRegistryRow,
  type SourceRegistryRow,
} from '@/lib/db/schema/source-registry';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'source_registry';

export async function findSourceById(sourceId: string): Promise<Result<SourceRegistryRow>> {
  const queried = await safeQuery(() =>
    db().query.sourceRegistry.findFirst({ where: eq(sourceRegistry.sourceId, sourceId) }),
  );
  if (!queried.ok) return queried;
  if (!queried.value) return err({ kind: 'NotFound', resource: RESOURCE, id: sourceId });
  return ok(queried.value);
}

export async function listActiveSources(): Promise<Result<SourceRegistryRow[]>> {
  return safeQuery(() =>
    db().query.sourceRegistry.findMany({ where: eq(sourceRegistry.status, 'active') }),
  );
}

/**
 * Insert-or-update by `source_id`. Returns the row as persisted after the
 * upsert (input fields override; columns not present in the input are left
 * as-is on conflict — Drizzle's `set` is built from the supplied keys).
 */
export async function upsertSource(
  input: NewSourceRegistryRow,
): Promise<Result<SourceRegistryRow>> {
  // Build the `set` payload from the input, excluding the primary key.
  // We deliberately exclude `registeredAt` so an upsert never rewrites the
  // original registration timestamp.
  const { sourceId: _id, registeredAt: _registered, ...rest } = input;
  void _id;
  void _registered;

  const inserted = await safeQuery(() =>
    db()
      .insert(sourceRegistry)
      .values(input)
      .onConflictDoUpdate({ target: sourceRegistry.sourceId, set: rest })
      .returning(),
  );
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'upsertSource: insert...returning produced no row',
    });
  }
  return ok(row);
}

export async function markVerified(
  sourceId: string,
  atIso: string,
): Promise<Result<SourceRegistryRow>> {
  const updated = await safeQuery(() =>
    db()
      .update(sourceRegistry)
      .set({ lastVerifiedAt: new Date(atIso) })
      .where(eq(sourceRegistry.sourceId, sourceId))
      .returning(),
  );
  if (!updated.ok) return updated;
  const row = updated.value[0];
  if (!row) return err({ kind: 'NotFound', resource: RESOURCE, id: sourceId });
  return ok(row);
}
