/**
 * URL minting for archived source documents.
 *
 * `getPublicUrl` composes the public path synchronously — no network call.
 * `getSignedUrl` mints a time-bounded URL via the Supabase API (for private
 * objects or off-platform sharing).
 */

import { err, ok, type Result } from '@/lib/errors';
import { serverEnv } from '@/lib/env';

import { getSupabaseClient } from './supabase-client';
import { SupabaseSignedUrlOkSchema, type StorageClientLike } from './types';

/**
 * Compose the public URL for an object. Does NOT verify that the bucket is
 * public — the bucket policy is configured once at provisioning time.
 */
export function getPublicUrl(storageKey: string): string {
  const env = serverEnv();
  return `${env.SUPABASE_URL}/storage/v1/object/public/${env.SUPABASE_STORAGE_BUCKET}/${storageKey}`;
}

export async function getSignedUrl(
  storageKey: string,
  expiresSec: number,
  clientOverride?: StorageClientLike,
): Promise<Result<string>> {
  if (!storageKey || storageKey.length === 0) {
    return err({ kind: 'Validation', field: 'storageKey', reason: 'empty' });
  }
  if (!Number.isFinite(expiresSec) || expiresSec <= 0) {
    return err({ kind: 'Validation', field: 'expiresSec', reason: 'must be positive' });
  }
  const client = clientOverride ?? getSupabaseClient();
  const bucket = serverEnv().SUPABASE_STORAGE_BUCKET;
  const resp = await client.storage.from(bucket).createSignedUrl(storageKey, expiresSec);
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
  const parsed = SupabaseSignedUrlOkSchema.safeParse(resp.data);
  if (!parsed.success) {
    return err({
      kind: 'External',
      service: 'supabase-storage',
      cause: `unexpected createSignedUrl response shape: ${parsed.error.message}`,
    });
  }
  return ok(parsed.data.signedUrl);
}
