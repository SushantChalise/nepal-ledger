/**
 * Local filesystem archive for source documents (ADR-0006).
 *
 * Used when SOURCE_ARCHIVE_DIR is set in the environment instead of
 * Supabase Storage credentials. Storage key convention is identical to the
 * Supabase path: `<source-id>/<yyyy-mm-dd>/<sanitized-filename>`.
 */

import * as fs from 'node:fs/promises';
import * as nodePath from 'node:path';

import { err, ok, type Result } from '@/lib/errors';

import { sha256OfBuffer } from './hash';
import type { StorageObject, UploadInput } from './types';

const UNSAFE_FILENAME_CHARS = /[^A-Za-z0-9._-]/g;
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}T/;

function sanitizeFileName(name: string): string {
  return name.replace(UNSAFE_FILENAME_CHARS, '_');
}

function datePrefix(iso: string): string | undefined {
  if (!ISO_DATE_RE.test(iso)) return undefined;
  return iso.slice(0, 10);
}

/**
 * Write a source document to the local filesystem archive.
 *
 * Idempotent: if the file already exists with the same hash, returns the
 * existing object. Conflicts on same key but different content.
 *
 * Input validation is assumed to have been done by the caller
 * (`uploadSourceDocument` in upload.ts).
 */
export async function uploadSourceDocumentLocally(
  input: UploadInput,
  archiveDir: string,
): Promise<Result<StorageObject>> {
  const yyyymmdd = datePrefix(input.downloadedAtIso);
  if (!yyyymmdd) {
    return err({
      kind: 'Validation',
      field: 'downloadedAtIso',
      reason: 'must be ISO 8601 (yyyy-mm-ddT...)',
    });
  }

  const cleanName = sanitizeFileName(input.fileName);
  const storageKey = `${input.sourceId}/${yyyymmdd}/${cleanName}`;
  const destDir = nodePath.join(archiveDir, input.sourceId, yyyymmdd);
  const destPath = nodePath.join(archiveDir, storageKey);
  const newHash = sha256OfBuffer(input.body);
  const newBytes = input.body.byteLength;

  // ─── Idempotency probe ──────────────────────────────────────────
  try {
    const existing = await fs.readFile(destPath);
    const existingHash = sha256OfBuffer(existing);
    if (existingHash === newHash) {
      return ok({
        storageKey,
        fileHashSha256: existingHash,
        fileSizeBytes: existing.byteLength,
        contentType: input.contentType,
        storageProvider: 'local',
      });
    }
    return err({
      kind: 'Conflict',
      reason: `storage key collision with different content at ${storageKey}`,
    });
  } catch (e) {
    const code = (e as NodeJS.ErrnoException).code;
    if (code !== 'ENOENT') {
      return err({
        kind: 'External',
        service: 'local-fs',
        cause: `probe failed: ${String(e)}`,
      });
    }
  }

  // ─── Write ──────────────────────────────────────────────────────
  try {
    await fs.mkdir(destDir, { recursive: true });
    await fs.writeFile(destPath, input.body);
  } catch (e) {
    return err({
      kind: 'External',
      service: 'local-fs',
      cause: `write failed: ${String(e)}`,
    });
  }

  return ok({
    storageKey,
    fileHashSha256: newHash,
    fileSizeBytes: newBytes,
    contentType: input.contentType,
    storageProvider: 'local',
  });
}
