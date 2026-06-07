/**
 * Shared helper for direct-fact-table ingest CLIs.
 *
 * Reads file bytes from disk, uploads them to Supabase Storage via
 * `uploadSourceDocument` (content-addressed + idempotent — same bytes → same
 * key, no error), then inserts a `source_documents` row using the real
 * storageKey/hash/size returned by the upload.
 *
 * Reference pattern: `src/lib/ingestion/index.ts` §steps 2–3.
 *
 * Used by:
 *   - scripts/ingest-bfi-monthly.ts
 *   - scripts/ingest-census-2021.ts
 *   - scripts/ingest-fiscal-transfers.ts
 *
 * NOT used by the orchestrator-based CLIs (ingest-cmefs, ingest-ncpi,
 * ingest-dne) which already go through `ingestSource()`.
 */

import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';

import { uploadSourceDocument } from '@/lib/storage';
import { insertSourceDocument } from '@/lib/db/repositories/source-documents';

export type ArchiveSourceDocumentInput = {
  /** Absolute path to the file on disk. */
  filePath: string;
  /** Must match a row in source_registry.source_id (FK enforced). */
  sourceId: string;
  /**
   * MIME type for the file.
   *   XLSX: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
   *   CSV:  'text/csv'
   */
  contentType: string;
  /** Human-readable label for the reporting period, e.g. "FY 2082/83". */
  reportingPeriodLabel: string | null;
  /** Optional free-text notes stored on the source_documents row. */
  notes?: string | null;
};

/**
 * Upload file bytes to Supabase Storage then insert a `source_documents` row.
 *
 * Returns the new row's `id` (UUID string) on success; throws on any error so
 * callers can propagate with a simple `await archiveAndInsertSourceDocument(...)`.
 *
 * Idempotency: `uploadSourceDocument` is content-addressed — re-running with
 * the same file returns the existing storage object without error. A new
 * `source_documents` row is always appended (append-only design, matching the
 * orchestrator pattern in `ingestSource`).
 */
export async function archiveAndInsertSourceDocument(
  input: ArchiveSourceDocumentInput,
): Promise<string> {
  const { filePath, sourceId, contentType, reportingPeriodLabel, notes } = input;

  // 1. Read file bytes from disk.
  const body = await readFile(filePath);

  // 2. Upload to Supabase Storage (content-addressed; idempotent on same bytes).
  const downloadedAtIso = new Date().toISOString();
  const uploadResult = await uploadSourceDocument({
    sourceId,
    downloadedAtIso,
    fileName: basename(filePath),
    body,
    contentType,
  });
  if (!uploadResult.ok) {
    throw new Error(
      `archiveAndInsertSourceDocument: storage upload failed: ${JSON.stringify(uploadResult.error)}`,
    );
  }
  const stored = uploadResult.value;

  // 3. Insert source_documents row using real storage metadata from the upload.
  const docResult = await insertSourceDocument({
    sourceId,
    originalUrl: `file://${filePath}`,
    storageProvider: stored.storageProvider,
    storageKey: stored.storageKey,
    fileHashSha256: stored.fileHashSha256,
    fileSizeBytes: stored.fileSizeBytes,
    contentType: stored.contentType,
    reportingPeriodLabel: reportingPeriodLabel ?? null,
    notes: notes ?? null,
  });
  if (!docResult.ok) {
    throw new Error(
      `archiveAndInsertSourceDocument: insertSourceDocument failed: ${JSON.stringify(docResult.error)}`,
    );
  }

  return docResult.value.id;
}
