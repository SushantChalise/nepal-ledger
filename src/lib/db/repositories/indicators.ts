/**
 * Indicators repository.
 *
 * Typed accessors for `indicators` and the `indicator_source_map` join table.
 * `linkIndicatorToSource` has upsert-on-conflict semantics so callers may
 * re-link without first checking existence (no `Conflict` surface for the
 * common case).
 */

import { and, eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import type { IndicatorCategory } from '@/lib/db/schema/enums';
import {
  indicatorSourceMap,
  indicators,
  type IndicatorRow,
  type IndicatorSourceMapRow,
} from '@/lib/db/schema/indicators';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'indicators';

export async function findIndicatorBySlug(slug: string): Promise<Result<IndicatorRow>> {
  const queried = await safeQuery(() =>
    db().query.indicators.findFirst({ where: eq(indicators.slug, slug) }),
  );
  if (!queried.ok) return queried;
  if (!queried.value) return err({ kind: 'NotFound', resource: RESOURCE, id: slug });
  return ok(queried.value);
}

export async function listIndicatorsByCategory(
  category: IndicatorCategory,
): Promise<Result<IndicatorRow[]>> {
  return safeQuery(() =>
    db().query.indicators.findMany({ where: eq(indicators.category, category) }),
  );
}

/**
 * Idempotent link. If the (indicator_id, source_id) pair already exists we
 * return the existing row rather than throwing — the join table has no
 * composite unique index declared in schema today, so we emulate set
 * semantics in the repo by checking first.
 *
 * Note: when the composite unique constraint is added (planned), this can
 * be tightened to `.onConflictDoUpdate(...)` against that constraint. For
 * now the read-then-write race is acceptable because callers are the
 * single-writer parser pipeline.
 */
export async function linkIndicatorToSource(
  indicatorId: string,
  sourceId: string,
  notes?: string,
): Promise<Result<IndicatorSourceMapRow>> {
  const existing = await safeQuery(() =>
    db().query.indicatorSourceMap.findFirst({
      where: and(
        eq(indicatorSourceMap.indicatorId, indicatorId),
        eq(indicatorSourceMap.sourceId, sourceId),
      ),
    }),
  );
  if (!existing.ok) return existing;
  if (existing.value) return ok(existing.value);

  const inserted = await safeQuery(() =>
    db()
      .insert(indicatorSourceMap)
      .values({
        indicatorId,
        sourceId,
        notes: notes ?? null,
      })
      .returning(),
  );
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'linkIndicatorToSource: insert...returning produced no row',
    });
  }
  return ok(row);
}
