/**
 * Indicator-units repository.
 *
 * `indicator_units` is the controlled vocabulary the validation layer checks
 * a staging row's `unit` against (docs/DATA_PIPELINE.md §"The Validation Job",
 * check 4 — UnitUnrecognized). The parser must emit a unit string that exists
 * in this table verbatim.
 *
 * `listKnownUnits` returns a Set for O(1) membership in the validator;
 * `bulkUpsertIndicatorUnits` is the seed-time writer (idempotent on the
 * `unit` primary key).
 */

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { indicatorUnits, type NewIndicatorUnitRow } from '@/lib/db/schema/indicators';
import { ok, type Result } from '@/lib/errors';

export async function listKnownUnits(): Promise<Result<Set<string>>> {
  const queried = await safeQuery(() =>
    db().select({ unit: indicatorUnits.unit }).from(indicatorUnits),
  );
  if (!queried.ok) return queried;
  return ok(new Set(queried.value.map((r) => r.unit)));
}

export async function bulkUpsertIndicatorUnits(
  rows: readonly NewIndicatorUnitRow[],
): Promise<Result<number>> {
  if (rows.length === 0) return ok(0);
  const inserted = await safeQuery(() =>
    db()
      .insert(indicatorUnits)
      .values([...rows])
      .onConflictDoNothing({ target: indicatorUnits.unit })
      .returning({ unit: indicatorUnits.unit }),
  );
  if (!inserted.ok) return inserted;
  return ok(inserted.value.length);
}
