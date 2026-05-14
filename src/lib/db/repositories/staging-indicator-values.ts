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
