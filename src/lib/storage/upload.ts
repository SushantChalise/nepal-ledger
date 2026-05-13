/**
 * `uploadSourceDocument` — content-addressed upload to Supabase Storage.
 *
 * Flow:
 *   1. Validate the input (sourceId regex, non-empty body, ISO date).
 *   2. Sanitize the filename and compose the deterministic storage key
 *      `<source-id>/<yyyy-mm-dd>/<filename>`.
 *   3. Hash the new body up front so we can detect both idempotent re-uploads
 *      and Conflict-on-different-content collisions before touching the
 *      network with a write.
 *   4. Read any existing object at the key. We compare hashes by downloading
 *      the existing bytes — Supabase's stored ETag is not SHA-256, so a head
 *      check would not let us prove equivalence. Bytes are cheap for the
 *      sub-30 MB PDFs we archive (see ADR-0004 sizing).
 *   5. If equal, return the existing object. If different, return Conflict.
 *      Otherwise upload and return the freshly-stored object.
 */

import { err, ok, type Result } from '@/lib/errors';

import { sha256OfBuffer } from './hash';
import { getSupabaseClient } from './supabase-client';
import {
  SupabaseUploadOkSchema,
  type StorageClientLike,
  type StorageObject,
  type UploadInput,
} from './types';

import { serverEnv } from '@/lib/env';

const SOURCE_ID_RE = /^[a-z0-9][a-z0-9-]{2,}$/;
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}T/;
const UNSAFE_FILENAME_CHARS = /[^A-Za-z0-9._-]/g;

/**
 * Sanitize a filename per the brief: anything outside `[A-Za-z0-9._-]`
 * collapses to `_`. Leading dots are preserved (some archives ship
 * `.gitattributes`-style names); empty result is rejected upstream.
 */
export function sanitizeFileName(name: string): string {
  return name.replace(UNSAFE_FILENAME_CHARS, '_');
}

/** Extract the yyyy-mm-dd prefix from an ISO 8601 timestamp. */
function datePrefix(iso: string): string | undefined {
  if (!ISO_DATE_RE.test(iso)) return undefined;
  return iso.slice(0, 10);
}

/**
 * Upload a source document. Idempotent on (key, hash); Conflict on (key, ≠hash).
 *
 * Pass `clientOverride` from tests; production code uses the cached singleton.
 */
export async function uploadSourceDocument(
  input: UploadInput,
  clientOverride?: StorageClientLike,
): Promise<Result<StorageObject>> {
  // ─── Validate ───────────────────────────────────────────────────
  if (!SOURCE_ID_RE.test(input.sourceId)) {
    return err({
      kind: 'Validation',
      field: 'sourceId',
      reason: `must match ${SOURCE_ID_RE.source}`,
    });
  }
  if (!input.fileName || input.fileName.length === 0) {
    return err({ kind: 'Validation', field: 'fileName', reason: 'empty' });
  }
  if (input.body.byteLength === 0) {
    return err({ kind: 'Validation', field: 'body', reason: 'empty' });
  }
  if (!input.contentType || input.contentType.length === 0) {
    return err({ kind: 'Validation', field: 'contentType', reason: 'empty' });
  }
  const yyyymmdd = datePrefix(input.downloadedAtIso);
  if (!yyyymmdd) {
    return err({
      kind: 'Validation',
      field: 'downloadedAtIso',
      reason: 'must be ISO 8601 (yyyy-mm-ddT...)',
    });
  }

  const cleanName = sanitizeFileName(input.fileName);
  if (cleanName.length === 0 || cleanName === '_'.repeat(cleanName.length)) {
    return err({ kind: 'Validation', field: 'fileName', reason: 'sanitizes to empty' });
  }

  const storageKey = `${input.sourceId}/${yyyymmdd}/${cleanName}`;
  const newHash = sha256OfBuffer(input.body);
  const newBytes = input.body.byteLength;

  const client = clientOverride ?? getSupabaseClient();
  const bucket = serverEnv().SUPABASE_STORAGE_BUCKET;
  const fileApi = client.storage.from(bucket);

  // ─── Idempotency probe ──────────────────────────────────────────
  const existing = await fileApi.download(storageKey);
  if (existing.data !== null) {
    const existingBuf = Buffer.from(await existing.data.arrayBuffer());
    const existingHash = sha256OfBuffer(existingBuf);
    if (existingHash === newHash) {
      return ok({
        storageKey,
        fileHashSha256: existingHash,
        fileSizeBytes: existingBuf.byteLength,
        contentType: existing.data.type || input.contentType,
        storageProvider: 'supabase',
      });
    }
    return err({
      kind: 'Conflict',
      reason: `storage key collision with different content at ${storageKey}`,
    });
  } else if (existing.error.status !== undefined && existing.error.status !== 404) {
    // Anything other than not-found is a real upstream failure.
    return err({
      kind: 'External',
      service: 'supabase-storage',
      cause: `probe failed (${existing.error.status}): ${existing.error.message}`,
    });
  }

  // ─── Upload ────────────────────────────────────────────────────
  const uploadResp = await fileApi.upload(storageKey, input.body, {
    contentType: input.contentType,
    upsert: false,
  });
  if (uploadResp.error !== null) {
    return err({
      kind: 'External',
      service: 'supabase-storage',
      cause: uploadResp.error.message,
    });
  }
  const parsed = SupabaseUploadOkSchema.safeParse(uploadResp.data);
  if (!parsed.success) {
    return err({
      kind: 'External',
      service: 'supabase-storage',
      cause: `unexpected upload response shape: ${parsed.error.message}`,
    });
  }

  return ok({
    storageKey,
    fileHashSha256: newHash,
    fileSizeBytes: newBytes,
    contentType: input.contentType,
    storageProvider: 'supabase',
  });
}
