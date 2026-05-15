/**
 * Census Facts repository.
 *
 * Typed data-access for `census_facts` — the long-format CBS NPHC 2021
 * fact table. Census facts have no time dimension and no fiscal-year
 * period; the unique key is `(entity_id, indicator_slug, census_year_ad)`.
 *
 * Inserts are intentionally idempotent: re-running the ingestion script
 * for the same CSV must not double-count rows. The bulk insert uses
 * `ON CONFLICT DO NOTHING` against the `census_facts_unique_idx` index
 * so a partial re-run picks up exactly the rows that were missing.
 */

import { and, eq, sql } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  censusFacts,
  type CensusFactRow,
  type NewCensusFactRow,
} from '@/lib/db/schema/census-facts';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'census_facts';

export async function insertOne(input: NewCensusFactRow): Promise<Result<CensusFactRow>> {
  const inserted = await safeQuery(() => db().insert(censusFacts).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({ kind: 'QueryFailed', detail: 'insertOne: insert...returning produced no row' });
  }
  return ok(row);
}

/**
 * Bulk insert with `ON CONFLICT DO NOTHING` against the unique index
 * `(entity_id, indicator_slug, census_year_ad)`. Returns only the rows
 * that were actually inserted — callers compute `input.length - returned`
 * to learn the dedup count.
 *
 * No-op (returns ok([])) when given zero rows — symmetric with the
 * staging-indicator-values bulk insert convention.
 */
export async function bulkInsert(
  rows: readonly NewCensusFactRow[],
): Promise<Result<CensusFactRow[]>> {
  if (rows.length === 0) return ok([]);
  const values: NewCensusFactRow[] = [...rows];
  return safeQuery(() =>
    db()
      .insert(censusFacts)
      .values(values)
      .onConflictDoNothing({
        target: [censusFacts.entityId, censusFacts.indicatorSlug, censusFacts.censusYearAd],
      })
      .returning(),
  );
}

/**
 * Look up a single fact by its natural key. Returns `NotFound` when no
 * row matches — callers that want a presence-check should branch on
 * `result.ok` and `result.error.kind === 'NotFound'`.
 */
export async function findByEntityAndIndicator(
  entityId: string,
  indicatorSlug: string,
  censusYearAd: string = '2021',
): Promise<Result<CensusFactRow>> {
  const queried = await safeQuery(() =>
    db().query.censusFacts.findFirst({
      where: and(
        eq(censusFacts.entityId, entityId),
        eq(censusFacts.indicatorSlug, indicatorSlug),
        eq(censusFacts.censusYearAd, censusYearAd),
      ),
    }),
  );
  if (!queried.ok) return queried;
  if (!queried.value) {
    return err({
      kind: 'NotFound',
      resource: RESOURCE,
      id: `${entityId}/${indicatorSlug}/${censusYearAd}`,
    });
  }
  return ok(queried.value);
}

/**
 * Count facts for a given (source_table_id, census_year_ad). Used by the
 * ingest script to report dedup metrics after a re-run.
 */
export async function countBySourceTable(
  sourceTableId: string,
  censusYearAd: string = '2021',
): Promise<Result<number>> {
  const queried = await safeQuery(() =>
    db()
      .select({ count: sql<number>`count(*)::int` })
      .from(censusFacts)
      .where(
        and(
          eq(censusFacts.sourceTableId, sourceTableId),
          eq(censusFacts.censusYearAd, censusYearAd),
        ),
      ),
  );
  if (!queried.ok) return queried;
  return ok(queried.value[0]?.count ?? 0);
}
