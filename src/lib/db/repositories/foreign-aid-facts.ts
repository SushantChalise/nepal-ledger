/**
 * Foreign-aid Facts repository.
 *
 * Typed data-access for `foreign_aid_facts` — the White Book dimensional fact
 * table (ADR-0017). A row is one base aid measure (`base_indicator_slug`) sliced
 * by one dimension member (`dimension_kind` + `dimension_value`) for one fiscal
 * year.
 *
 * Inserts are intentionally idempotent: re-running the White Book ingest for the
 * same edition must not double-count. The bulk insert uses `ON CONFLICT DO
 * NOTHING` against `foreign_aid_facts_unique_idx`
 *   (base_indicator_slug, dimension_kind, dimension_value,
 *    reporting_period_bs, reporting_period_type, source_document_id)
 * so a partial re-run picks up exactly the rows that were missing.
 *
 * Mirrors the `dne_facts` repository field-for-field (ADR-0015 precedent).
 */

import { and, eq, sql } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  foreignAidFacts,
  type ForeignAidFactRow,
  type NewForeignAidFactRow,
} from '@/lib/db/schema/foreign-aid-facts';
import { err, ok, type Result } from '@/lib/errors';

export async function insertForeignAidFact(
  input: NewForeignAidFactRow,
): Promise<Result<ForeignAidFactRow>> {
  const inserted = await safeQuery(() => db().insert(foreignAidFacts).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertForeignAidFact: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Bulk insert with `ON CONFLICT DO NOTHING` against
 * `foreign_aid_facts_unique_idx`. Returns only the rows actually inserted —
 * callers compute `inputs.length - returned.length` to learn the dedup count.
 *
 * The natural key is a plain composite of NOT NULL columns, so an explicit
 * `target` column list correctly names it.
 *
 * Chunked: Postgres caps a statement at 65,535 bind parameters. A foreign-aid
 * fact has ~14 columns; an edition emits up to a few hundred rows (donors +
 * ministries × 2 measures), so a single chunk usually suffices — but we batch in
 * CHUNK_ROWS to stay safely under the limit and match the DNE repo. No-op
 * (returns ok([])) when given zero rows.
 */
const CHUNK_ROWS = 2000;

export async function bulkInsertForeignAidFacts(
  inputs: ReadonlyArray<NewForeignAidFactRow>,
): Promise<Result<ForeignAidFactRow[]>> {
  if (inputs.length === 0) return ok([]);
  const inserted: ForeignAidFactRow[] = [];
  for (let i = 0; i < inputs.length; i += CHUNK_ROWS) {
    const chunk = inputs.slice(i, i + CHUNK_ROWS);
    const result = await safeQuery(() =>
      db()
        .insert(foreignAidFacts)
        .values([...chunk])
        .onConflictDoNothing({
          target: [
            foreignAidFacts.baseIndicatorSlug,
            foreignAidFacts.dimensionKind,
            foreignAidFacts.dimensionValue,
            foreignAidFacts.reportingPeriodBs,
            foreignAidFacts.reportingPeriodType,
            foreignAidFacts.sourceDocumentId,
          ],
        })
        .returning(),
    );
    if (!result.ok) return result;
    inserted.push(...result.value);
  }
  return ok(inserted);
}

/**
 * All facts for a base measure (e.g. every donor row of `foreign-aid-grant`).
 * Returns ok([]) for the empty-match case — "no rows" is a successful negative.
 *
 * Uses the query-builder form (`select().from()`) rather than the relational
 * `db().query.foreignAidFacts` accessor on purpose: the relational accessor only
 * exists once this table is re-exported from the schema barrel
 * (`src/lib/db/schema/index.ts`), which Mother wires up with the migration. The
 * query-builder form compiles against the table object directly, so this repo
 * typechecks BEFORE the barrel/migration land (per the task contract).
 */
export async function listByBaseIndicator(
  baseIndicatorSlug: string,
): Promise<Result<ForeignAidFactRow[]>> {
  return safeQuery(() =>
    db()
      .select()
      .from(foreignAidFacts)
      .where(eq(foreignAidFacts.baseIndicatorSlug, baseIndicatorSlug)),
  );
}

/**
 * Count facts for a base measure, optionally scoped to one source document.
 * Used by the White Book ingest to report dedup metrics after a re-run.
 */
export async function countByBaseIndicator(
  baseIndicatorSlug: string,
  sourceDocumentId?: string,
): Promise<Result<number>> {
  const conds = [eq(foreignAidFacts.baseIndicatorSlug, baseIndicatorSlug)];
  if (sourceDocumentId !== undefined) {
    conds.push(eq(foreignAidFacts.sourceDocumentId, sourceDocumentId));
  }
  const queried = await safeQuery(() =>
    db()
      .select({ count: sql<number>`count(*)::int` })
      .from(foreignAidFacts)
      .where(and(...conds)),
  );
  if (!queried.ok) return queried;
  return ok(queried.value[0]?.count ?? 0);
}
