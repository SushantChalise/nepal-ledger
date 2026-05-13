/**
 * Supabase Storage client singleton (server-only).
 *
 * Reads URL + service-role key from validated env. The exported factory
 * accepts an injected client so tests can pass a vi-mocked instance without
 * touching real credentials. Per ADR-0004 we use Supabase Storage in Year 1;
 * the migration to Cloudflare R2 swaps this module's `createClient` call for
 * an S3-compatible equivalent — feature code does not change.
 */

import 'server-only';

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

import { serverEnv } from '@/lib/env';

let cached: SupabaseClient | undefined;

/**
 * Get (or lazily build) the server-side Supabase client. Uses the
 * service-role key — never expose this client to a browser bundle.
 */
export function getSupabaseClient(): SupabaseClient {
  if (cached) return cached;
  const env = serverEnv();
  cached = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return cached;
}

/** For tests: reset the cached singleton between cases. */
export function __resetSupabaseClientForTests(): void {
  cached = undefined;
}

/** For tests: inject a mock client; subsequent calls return it. */
export function __setSupabaseClientForTests(client: SupabaseClient): void {
  cached = client;
}
