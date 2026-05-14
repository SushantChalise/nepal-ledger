/**
 * Parser Runs repository.
 *
 * One row per parser execution. The ingestion orchestrator inserts a parser_runs
 * row before persisting staging rows so every staging row has an FK target.
 * Parser errors (granular per-row diagnostics) are inserted in a separate
 * bulk call after the run row exists.
 */

import { eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  parserErrors,
  parserRuns,
  type NewParserErrorRow,
  type NewParserRunRow,
  type ParserErrorRow,
  type ParserRunRow,
} from '@/lib/db/schema/parser-runs';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'parser_runs';

export async function insertParserRun(input: NewParserRunRow): Promise<Result<ParserRunRow>> {
  const inserted = await safeQuery(() => db().insert(parserRuns).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertParserRun: insert...returning produced no row',
    });
  }
  return ok(row);
}

export async function findParserRunById(id: string): Promise<Result<ParserRunRow>> {
  const queried = await safeQuery(() =>
    db().query.parserRuns.findFirst({ where: eq(parserRuns.id, id) }),
  );
  if (!queried.ok) return queried;
  if (!queried.value) return err({ kind: 'NotFound', resource: RESOURCE, id });
  return ok(queried.value);
}

/**
 * Bulk-insert granular parser errors. No-op (returns ok([])) when given an
 * empty list — avoids round-tripping an empty INSERT.
 */
export async function bulkInsertParserErrors(
  rows: readonly NewParserErrorRow[],
): Promise<Result<ParserErrorRow[]>> {
  if (rows.length === 0) return ok([]);
  const values: NewParserErrorRow[] = [...rows];
  return safeQuery(() => db().insert(parserErrors).values(values).returning());
}
