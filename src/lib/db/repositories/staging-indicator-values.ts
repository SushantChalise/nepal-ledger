/**
 * Staging Indicator Values repository.
 *
 * Typed data-access for `staging_indicator_values`. Staging rows are
 * untrusted parser output; the validation job walks them, decides
 * promote-vs-flag, and deletes the row when promoted. Feature code MUST
 * NOT read from staging — only `approved_indicator_values`.
 */

import { eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  stagingIndicatorValues,
  type NewStagingIndicatorValueRow,
  type StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'staging_indicator_values';

export async function findStagingRowById(id: string): Promise<Result<StagingIndicatorValueRow>> {
  const queried = await safeQuery(() =>
    db().query.stagingIndicatorValues.findFirst({
      where: eq(stagingIndicatorValues.id, id),
    }),
  );
  if (!queried.ok) return queried;
  if (!queried.value) return err({ kind: 'NotFound', resource: RESOURCE, id });
  return ok(queried.value);
}

export async function listStagingRowsForParserRun(
  parserRunId: string,
): Promise<Result<StagingIndicatorValueRow[]>> {
  return safeQuery(() =>
    db().query.stagingIndicatorValues.findMany({
      where: eq(stagingIndicatorValues.parserRunId, parserRunId),
    }),
  );
}

/**
 * Bulk-insert staging rows from a single parser run. No-op (returns ok([]))
 * when given an empty list — the ingestion orchestrator may legitimately call
 * this with zero rows when a parser returns status='failure' but we still want
 * the parser_runs row written.
 */
export async function bulkInsertStagingRows(
  rows: readonly NewStagingIndicatorValueRow[],
): Promise<Result<StagingIndicatorValueRow[]>> {
  if (rows.length === 0) return ok([]);
  const values: NewStagingIndicatorValueRow[] = [...rows];
  return safeQuery(() => db().insert(stagingIndicatorValues).values(values).returning());
}

export async function deleteStagingRowById(id: string): Promise<Result<{ id: string }>> {
  const deleted = await safeQuery(() =>
    db()
      .delete(stagingIndicatorValues)
      .where(eq(stagingIndicatorValues.id, id))
      .returning({ id: stagingIndicatorValues.id }),
  );
  if (!deleted.ok) return deleted;
  const row = deleted.value[0];
  if (!row) return err({ kind: 'NotFound', resource: RESOURCE, id });
  return ok(row);
}
