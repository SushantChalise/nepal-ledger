/**
 * Supabase Storage wrapper — the typed boundary the scraper pipeline uses to
 * archive source documents (NRB CMEFs PDFs, customs Excel, OAG reports).
 *
 * Per ADR-0004, this is Supabase Storage for Year 1; the migration to
 * Cloudflare R2 only swaps `supabase-client.ts` — the surface here is stable.
 */

export { sha256OfBuffer } from './hash';
export { uploadSourceDocument } from './upload';
export { downloadSourceDocument } from './download';
export { getPublicUrl, getSignedUrl } from './url';
export type { StorageObject, UploadInput, DownloadResult } from './types';
