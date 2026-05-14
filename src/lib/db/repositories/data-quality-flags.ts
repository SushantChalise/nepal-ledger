/**
 * Data Quality Flags repository.
 *
 * Validation issues recorded by the staging→approved promotion job. Blocking
 * flags hold a staging row out of production until resolved; warnings
 * annotate a row that was promoted anyway. Resolution is a human-review step
 * surfaced in the (future) `/admin/quality` page.
 */

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  dataQualityFlags,
  type DataQualityFlagRow,
  type NewDataQualityFlagRow,
} from '@/lib/db/schema/indicator-values';
import { err, ok, type Result } from '@/lib/errors';

export async function insertDataQualityFlag(
  input: NewDataQualityFlagRow,
): Promise<Result<DataQualityFlagRow>> {
  const inserted = await safeQuery(() => db().insert(dataQualityFlags).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertDataQualityFlag: insert...returning produced no row',
    });
  }
  return ok(row);
}
