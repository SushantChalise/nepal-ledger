/**
 * Local Government Fiscal Transfers repository.
 *
 * Typed data-access for `local_government_fiscal_transfers` — the
 * federal-to-local-level transfer fact table. Inserts are idempotent: the
 * `(local_level_entity_id, fiscal_year_bs, grant_type)` unique index
 * guarantees re-ingestion is a no-op when paired with
 * `ON CONFLICT DO NOTHING`.
 *
 * Companion entity-lookup helper `findLocalLevelEntityBySlug` is colocated
 * here because the fiscal-transfer ingest is currently the only consumer of
 * a stable-by-federal-code lookup. If a second consumer appears, lift it
 * into a standalone `entities.ts` repository.
 */

import { and, eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { entities, type EntityRow } from '@/lib/db/schema/entities';
import {
  localGovernmentFiscalTransfers,
  type LocalGovernmentFiscalTransferRow,
  type NewLocalGovernmentFiscalTransferRow,
} from '@/lib/db/schema/fiscal-transfers';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'local_government_fiscal_transfers';

export type BulkInsertSummary = {
  attempted: number;
  inserted: number;
  skippedDuplicate: number;
};

/**
 * Insert a single fiscal-transfer row. Returns ok(row) on success or err(...)
 * on ConstraintViolation (unique / fk). Callers that want idempotency should
 * use `bulkInsertIdempotent` instead.
 */
export async function insertOne(
  input: NewLocalGovernmentFiscalTransferRow,
): Promise<Result<LocalGovernmentFiscalTransferRow>> {
  const inserted = await safeQuery(() =>
    db().insert(localGovernmentFiscalTransfers).values(input).returning(),
  );
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertOne: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Bulk-insert with `ON CONFLICT DO NOTHING` on the unique index
 * `(local_level_entity_id, fiscal_year_bs, grant_type)`. Returns a summary
 * with attempted / inserted / skippedDuplicate counts.
 *
 * No-op (returns zeros) when given an empty array — keeps the orchestrator
 * code path straight when a parser legitimately emits zero rows.
 */
export async function bulkInsertIdempotent(
  rows: readonly NewLocalGovernmentFiscalTransferRow[],
): Promise<Result<BulkInsertSummary>> {
  if (rows.length === 0) {
    return ok({ attempted: 0, inserted: 0, skippedDuplicate: 0 });
  }
  const values: NewLocalGovernmentFiscalTransferRow[] = [...rows];
  const inserted = await safeQuery(() =>
    db()
      .insert(localGovernmentFiscalTransfers)
      .values(values)
      .onConflictDoNothing({
        target: [
          localGovernmentFiscalTransfers.localLevelEntityId,
          localGovernmentFiscalTransfers.fiscalYearBs,
          localGovernmentFiscalTransfers.grantType,
        ],
      })
      .returning({ id: localGovernmentFiscalTransfers.id }),
  );
  if (!inserted.ok) return inserted;
  const insertedCount = inserted.value.length;
  return ok({
    attempted: rows.length,
    inserted: insertedCount,
    skippedDuplicate: rows.length - insertedCount,
  });
}

export async function findByMunicipalityAndFY(
  localLevelEntityId: string,
  fiscalYearBs: string,
): Promise<Result<LocalGovernmentFiscalTransferRow[]>> {
  return safeQuery(() =>
    db().query.localGovernmentFiscalTransfers.findMany({
      where: and(
        eq(localGovernmentFiscalTransfers.localLevelEntityId, localLevelEntityId),
        eq(localGovernmentFiscalTransfers.fiscalYearBs, fiscalYearBs),
      ),
    }),
  );
}

/**
 * Resolve an 8-digit federal local-level code to its `entities.id`. Returns
 * `ok(null)` — not `NotFound` — when no entity matches, because the ingest
 * CLI's "skip unresolved" path treats absence as a successful negative and
 * we want a cheap branch on `.value === null`.
 */
export async function findLocalLevelEntityBySlug(slug: string): Promise<Result<EntityRow | null>> {
  const queried = await safeQuery(() =>
    db().query.entities.findFirst({
      where: and(eq(entities.kind, 'local_level'), eq(entities.slug, slug)),
    }),
  );
  if (!queried.ok) return queried;
  return ok(queried.value ?? null);
}

void RESOURCE; // reserved for future NotFound branches; quiets the linter
