/**
 * Validated environment variables.
 *
 * Per CONVENTIONS.md, env vars are an external boundary — they pass through
 * a Zod schema before any code reads them. Loading this module at startup
 * crashes fast if a required var is missing, which is the right failure mode
 * for a configuration error.
 *
 * Server-only vars are NEVER imported by client components. Client-safe vars
 * use the `NEXT_PUBLIC_` prefix and are exposed separately.
 */

import { z } from 'zod';

const ServerEnvSchema = z.object({
  // ─── Supabase (database + storage) ────────────────────────────
  SUPABASE_URL: z.string().url(),
  SUPABASE_ANON_KEY: z.string().min(1),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
  DATABASE_URL: z.string().url(),
  // Direct connection bypasses the pooler — used by drizzle-kit migrations.
  DIRECT_URL: z.string().url().optional(),
  SUPABASE_STORAGE_BUCKET: z.string().default('source-archive'),

  // ─── Sentry (server) ──────────────────────────────────────────
  SENTRY_DSN: z.string().url().optional(),
  SENTRY_AUTH_TOKEN: z.string().optional(),
  SENTRY_ORG: z.string().optional(),
  SENTRY_PROJECT: z.string().optional(),

  // ─── Runtime ──────────────────────────────────────────────────
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
});

const ClientEnvSchema = z.object({
  NEXT_PUBLIC_SITE_URL: z.string().url().default('http://localhost:3000'),
  NEXT_PUBLIC_SENTRY_DSN: z.string().url().optional(),
  NEXT_PUBLIC_CF_ANALYTICS_TOKEN: z.string().optional(),
});

export type ServerEnv = z.infer<typeof ServerEnvSchema>;
export type ClientEnv = z.infer<typeof ClientEnvSchema>;

let cachedServerEnv: ServerEnv | undefined;
let cachedClientEnv: ClientEnv | undefined;

/**
 * Get the validated server env. Throws on first call if validation fails;
 * subsequent calls return the cached value. NEVER call from a Client Component.
 */
export function serverEnv(): ServerEnv {
  if (cachedServerEnv) return cachedServerEnv;
  const parsed = ServerEnvSchema.safeParse(process.env);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const path = issue?.path.join('.') ?? '<unknown>';
    const message = issue?.message ?? 'invalid';
    throw new Error(`Invalid server environment: ${path} — ${message}`);
  }
  cachedServerEnv = parsed.data;
  return cachedServerEnv;
}

/**
 * Get the validated client env. Safe to call from both Server and Client
 * Components. Reads only NEXT_PUBLIC_* values (inlined at build time).
 */
export function clientEnv(): ClientEnv {
  if (cachedClientEnv) return cachedClientEnv;
  const parsed = ClientEnvSchema.safeParse({
    NEXT_PUBLIC_SITE_URL: process.env['NEXT_PUBLIC_SITE_URL'],
    NEXT_PUBLIC_SENTRY_DSN: process.env['NEXT_PUBLIC_SENTRY_DSN'],
    NEXT_PUBLIC_CF_ANALYTICS_TOKEN: process.env['NEXT_PUBLIC_CF_ANALYTICS_TOKEN'],
  });
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const path = issue?.path.join('.') ?? '<unknown>';
    const message = issue?.message ?? 'invalid';
    throw new Error(`Invalid client environment: ${path} — ${message}`);
  }
  cachedClientEnv = parsed.data;
  return cachedClientEnv;
}
