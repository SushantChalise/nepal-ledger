/**
 * Source Documents repository.
 *
 * Append-only archive of downloaded source files. `findSourceDocumentByHash`
 * returns `Result<SourceDocumentRow | null>` because hash-based lookups treat
 * "no match" as a successful negative — content-addressed dedup needs to
 * distinguish "not present" from "DB threw".
 */

import { desc, eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  sourceDocuments,
  type NewSourceDocumentRow,
  type SourceDocumentRow,
} from '@/lib/db/schema/source-documents';
import { err, ok, type Result } from '@/lib/errors';

const RESOURCE = 'source_documents';

export async function insertSourceDocument(
  input: NewSourceDocumentRow,
): Promise<Result<SourceDocumentRow>> {
  const inserted = await safeQuery(() => db().insert(sourceDocuments).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertSourceDocument: insert...returning produced no row',
    });
  }
  return ok(row);
}

export async function findSourceDocumentById(id: string): Promise<Result<SourceDocumentRow>> {
  const queried = await safeQuery(() =>
    db().query.sourceDocuments.findFirst({ where: eq(sourceDocuments.id, id) }),
  );
  if (!queried.ok) return queried;
  if (!queried.value) return err({ kind: 'NotFound', resource: RESOURCE, id });
  return ok(queried.value);
}

/**
 * Hash-based lookup. Null is a successful "no match", not an error — used
 * for content-addressed dedup in the storage layer.
 */
export async function findSourceDocumentByHash(
  sha256: string,
): Promise<Result<SourceDocumentRow | null>> {
  const queried = await safeQuery(() =>
    db().query.sourceDocuments.findFirst({
      where: eq(sourceDocuments.fileHashSha256, sha256),
    }),
  );
  if (!queried.ok) return queried;
  return ok(queried.value ?? null);
}

export async function listSourceDocumentsForSource(
  sourceId: string,
  limit: number,
): Promise<Result<SourceDocumentRow[]>> {
  return safeQuery(() =>
    db().query.sourceDocuments.findMany({
      where: eq(sourceDocuments.sourceId, sourceId),
      orderBy: [desc(sourceDocuments.downloadedAt)],
      limit,
    }),
  );
}
