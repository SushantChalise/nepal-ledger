import { afterEach, beforeEach, describe, expect, it } from 'vitest';

/**
 * env.ts caches its parsed result in module-scope variables. To test
 * different configurations we re-import the module via vi.resetModules.
 * Each test sets up its own process.env subset and re-imports.
 */

const ORIGINAL_ENV = { ...process.env };

async function freshEnvModule() {
  // Drop the cache so the first call re-validates.
  const mod = await import('./env');
  // Force a re-parse by clearing the module's cached results via re-import.
  return mod;
}

describe('serverEnv', () => {
  beforeEach(async () => {
    process.env = { ...ORIGINAL_ENV };
    // Strip any DB / Supabase env we don't want to leak into tests.
    delete process.env['SUPABASE_URL'];
    delete process.env['SUPABASE_ANON_KEY'];
    delete process.env['SUPABASE_SERVICE_ROLE_KEY'];
    delete process.env['DATABASE_URL'];
    const { vi } = await import('vitest');
    vi.resetModules();
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
  });

  it('throws when required vars are missing', async () => {
    const { serverEnv } = await freshEnvModule();
    expect(() => serverEnv()).toThrow(/Invalid server environment/);
  });

  it('parses successfully when all required vars are set', async () => {
    process.env['SUPABASE_URL'] = 'https://example.supabase.co';
    process.env['SUPABASE_ANON_KEY'] = 'anon-key';
    process.env['SUPABASE_SERVICE_ROLE_KEY'] = 'service-role-key';
    process.env['DATABASE_URL'] = 'postgresql://user:pw@host:5432/db';
    const { serverEnv } = await freshEnvModule();
    const env = serverEnv();
    expect(env.SUPABASE_URL).toBe('https://example.supabase.co');
    expect(env.SUPABASE_STORAGE_BUCKET).toBe('source-archive');
  });

  it('rejects an invalid URL', async () => {
    process.env['SUPABASE_URL'] = 'not-a-url';
    process.env['SUPABASE_ANON_KEY'] = 'anon-key';
    process.env['SUPABASE_SERVICE_ROLE_KEY'] = 'service-role-key';
    process.env['DATABASE_URL'] = 'postgresql://user:pw@host:5432/db';
    const { serverEnv } = await freshEnvModule();
    expect(() => serverEnv()).toThrow(/Invalid server environment/);
  });
});

describe('clientEnv', () => {
  beforeEach(async () => {
    process.env = { ...ORIGINAL_ENV };
    delete process.env['NEXT_PUBLIC_SITE_URL'];
    delete process.env['NEXT_PUBLIC_SENTRY_DSN'];
    delete process.env['NEXT_PUBLIC_CF_ANALYTICS_TOKEN'];
    const { vi } = await import('vitest');
    vi.resetModules();
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
  });

  it('falls back to the default site URL when unset', async () => {
    const { clientEnv } = await freshEnvModule();
    const env = clientEnv();
    expect(env.NEXT_PUBLIC_SITE_URL).toBe('http://localhost:3000');
  });
});
