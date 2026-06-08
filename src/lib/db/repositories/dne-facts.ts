/**
 * DNE Facts repository.
 *
 * Typed data-access for `dne_facts` — the DNE dimensional fact table
 * (ADR-0015). A row is one base measure (`base_indicator_slug`) sliced by one
 * dimension member (`dimension_kind` + `dimension_value`) for one period.
 *
 * Inserts are intentionally idempotent: re-running the DNE ingest for the same
 * matrix file must not double-count. The bulk insert uses `ON CONFLICT DO
 * NOTHING` against `dne_facts_unique_idx`
 *   (base_indicator_slug, dimension_kind, dimension_value,
 *    reporting_period_bs, reporting_period_type, source_document_id)
 * so a partial re-run picks up exactly the rows that were missing.
 */

import { and, eq, sql } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery, safeQueryWithRetry } from '@/lib/db/safe-query';
import { dneFacts, type DneFactRow, type NewDneFactRow } from '@/lib/db/schema/dne-facts';
import { err, ok, type Result } from '@/lib/errors';

export async function insertDneFact(input: NewDneFactRow): Promise<Result<DneFactRow>> {
  const inserted = await safeQuery(() => db().insert(dneFacts).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertDneFact: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Bulk insert with `ON CONFLICT DO NOTHING` against `dne_facts_unique_idx`.
 * Returns only the rows actually inserted — callers compute
 * `inputs.length - returned.length` to learn the dedup count.
 *
 * The natural key is a plain composite of NOT NULL columns, so an explicit
 * `target` column list correctly names it (unlike the banking table's COALESCE
 * expression index, which requires the bare `onConflictDoNothing()` form).
 *
 * Chunked: Postgres caps a statement at 65,535 bind parameters. A DNE fact has
 * ~14 columns; dimensional matrices (~745 commodities × periods) emit large
 * row counts, so we insert in batches of CHUNK_ROWS to stay well under the
 * limit. No-op (returns ok([])) when given zero rows.
 */
const CHUNK_ROWS = 2000;

export async function bulkInsertDneFacts(
  inputs: ReadonlyArray<NewDneFactRow>,
): Promise<Result<DneFactRow[]>> {
  if (inputs.length === 0) return ok([]);
  const inserted: DneFactRow[] = [];
  for (let i = 0; i < inputs.length; i += CHUNK_ROWS) {
    const chunk = inputs.slice(i, i + CHUNK_ROWS);
    // safeQueryWithRetry: a transient ECONNRESET on one chunk of a large
    // multi-chunk insert would otherwise abort the whole ingest. The insert is
    // onConflictDoNothing (conflict-guarded), so retrying a chunk is safe.
    const result = await safeQueryWithRetry(() =>
      db()
        .insert(dneFacts)
        .values([...chunk])
        .onConflictDoNothing({
          target: [
            dneFacts.baseIndicatorSlug,
            dneFacts.dimensionKind,
            dneFacts.dimensionValue,
            dneFacts.reportingPeriodBs,
            dneFacts.reportingPeriodType,
            dneFacts.sourceDocumentId,
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
 * All facts for a base measure (e.g. every commodity row of
 * `dne-merchandise-exports`). Returns ok([]) for the empty-match case —
 * "no rows" is a successful negative.
 */
export async function listByBaseIndicator(
  baseIndicatorSlug: string,
): Promise<Result<DneFactRow[]>> {
  return safeQuery(() =>
    db().query.dneFacts.findMany({
      where: eq(dneFacts.baseIndicatorSlug, baseIndicatorSlug),
    }),
  );
}

/**
 * Count facts for a base measure, optionally scoped to one source document.
 * Used by the DNE ingest to report dedup metrics after a re-run.
 */
export async function countByBaseIndicator(
  baseIndicatorSlug: string,
  sourceDocumentId?: string,
): Promise<Result<number>> {
  const conds = [eq(dneFacts.baseIndicatorSlug, baseIndicatorSlug)];
  if (sourceDocumentId !== undefined) {
    conds.push(eq(dneFacts.sourceDocumentId, sourceDocumentId));
  }
  const queried = await safeQuery(() =>
    db()
      .select({ count: sql<number>`count(*)::int` })
      .from(dneFacts)
      .where(and(...conds)),
  );
  if (!queried.ok) return queried;
  return ok(queried.value[0]?.count ?? 0);
}
