/**
 * Type shapes for the Supabase Storage wrapper.
 *
 * Per docs/CONVENTIONS.md, response shapes from third-party SDKs are
 * validated with Zod at the boundary so the rest of the module works on
 * `z.infer` types — no `as` casts in this folder.
 */

import { z } from 'zod';

import type { StorageProvider } from '@/lib/db/schema/enums';

export type StorageObject = {
  storageKey: string;
  fileHashSha256: string;
  fileSizeBytes: number;
  contentType: string;
  storageProvider: StorageProvider;
};

export type UploadInput = {
  sourceId: string;
  downloadedAtIso: string;
  fileName: string;
  body: Buffer | Uint8Array;
  contentType: string;
};

export type DownloadResult = {
  body: Buffer;
  contentType: string;
  sizeBytes: number;
};

// ─── Zod schemas validating the Supabase JS client response shapes ──────

export const SupabaseUploadOkSchema = z.object({
  id: z.string(),
  path: z.string(),
  fullPath: z.string(),
});

export const SupabaseSignedUrlOkSchema = z.object({
  signedUrl: z.string().url(),
});

export type SupabaseUploadOk = z.infer<typeof SupabaseUploadOkSchema>;
export type SupabaseSignedUrlOk = z.infer<typeof SupabaseSignedUrlOkSchema>;

// ─── Narrowed structural interface for the storage surface we depend on. ──
// Production passes a SupabaseClient (which structurally satisfies this);
// tests pass a hand-rolled stub. This lets us inject without `as` casts.

/**
 * Supabase Storage surfaces "object not found" as HTTP 400 with a
 * body-encoded `statusCode: "404"` (see `@supabase/storage-js` StorageApiError).
 * We model both so the not-found branch can check either signal.
 */
export type StorageErrorLike = {
  message: string;
  status?: number | undefined;
  statusCode?: string | undefined;
};

/**
 * True for any "object does not exist" response from Supabase Storage —
 * whether surfaced as HTTP 404, body-encoded statusCode '404', or only as a
 * "not found" message. Centralized so upload + download stay in sync.
 */
export function isNotFoundStorageError(error: StorageErrorLike): boolean {
  if (error.status === 404) return true;
  if (error.statusCode === '404') return true;
  return /not[_ ]?found/i.test(error.message);
}

export type DownloadResp = { data: Blob; error: null } | { data: null; error: StorageErrorLike };

export type UploadResp =
  | { data: { id: string; path: string; fullPath: string }; error: null }
  | { data: null; error: StorageErrorLike };

export type SignedUrlResp =
  | { data: { signedUrl: string }; error: null }
  | { data: null; error: StorageErrorLike };

export type StorageFileApiLike = {
  download(path: string): Promise<DownloadResp>;
  upload(
    path: string,
    body: Buffer | Uint8Array,
    opts: { contentType: string; upsert: boolean },
  ): Promise<UploadResp>;
  createSignedUrl(path: string, expiresIn: number): Promise<SignedUrlResp>;
};

export type StorageClientLike = {
  storage: { from(bucket: string): StorageFileApiLike };
};
