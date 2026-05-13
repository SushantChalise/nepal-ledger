/**
 * `downloadSourceDocument` — read bytes back out of Supabase Storage.
 *
 * Returns the raw body + size + content type. The Fact Ledger uses this to
 * verify hash equality at read time, which is the integrity check that
 * lets us prove a citation hasn't been tampered with since archival.
 */

import { err, ok, type Result } from '@/lib/errors';
import { serverEnv } from '@/lib/env';

import { getSupabaseClient } from './supabase-client';
import type { DownloadResult, StorageClientLike } from './types';

export async function downloadSourceDocument(
  storageKey: string,
  clientOverride?: StorageClientLike,
): Promise<Result<DownloadResult>> {
  if (!storageKey || storageKey.length === 0) {
    return err({ kind: 'Validation', field: 'storageKey', reason: 'empty' });
  }
  const client = clientOverride ?? getSupabaseClient();
  const bucket = serverEnv().SUPABASE_STORAGE_BUCKET;
  const resp = await client.storage.from(bucket).download(storageKey);
  if (resp.data === null) {
    if (resp.error.status === 404) {
      return err({ kind: 'NotFound', resource: 'source_document', id: storageKey });
    }
    return err({
      kind: 'External',
      service: 'supabase-storage',
      cause: resp.error.message,
    });
  }
  const body = Buffer.from(await resp.data.arrayBuffer());
  return ok({
    body,
    contentType: resp.data.type || 'application/octet-stream',
    sizeBytes: body.byteLength,
  });
}
