import { DrizzleError } from 'drizzle-orm';
import { describe, expect, it } from 'vitest';

import { safeQuery } from './safe-query';

// We exercise the error-translation paths without booting Postgres.
// PostgresError instances are constructed via the postgres-js module — but
// since we can't easily instantiate the real class here, we lean on the
// fact that toAppError() falls through to the Error branch for generic
// Errors. That covers the most common path; the SQLSTATE-specific branches
// are exercised via integration tests when the DB is reachable (next
// milestone).

describe('safeQuery', () => {
  it('returns ok(value) on success', async () => {
    const result = await safeQuery(() => Promise.resolve(42));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value).toBe(42);
  });

  it('translates a generic Error to QueryFailed', async () => {
    const result = await safeQuery(() => Promise.reject(new Error('boom')));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.kind).toBe('QueryFailed');
      if (result.error.kind === 'QueryFailed') {
        expect(result.error.detail).toBe('boom');
      }
    }
  });

  it('translates a DrizzleError to QueryFailed', async () => {
    const result = await safeQuery(() =>
      Promise.reject(new DrizzleError({ message: 'invalid query' })),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.kind).toBe('QueryFailed');
      if (result.error.kind === 'QueryFailed') {
        expect(result.error.detail).toBe('invalid query');
      }
    }
  });

  it('translates a non-Error reject value to QueryFailed', async () => {
    const result = await safeQuery(() => Promise.reject('string error'));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.kind).toBe('QueryFailed');
      if (result.error.kind === 'QueryFailed') {
        expect(result.error.detail).toBe('string error');
      }
    }
  });

  it('does not throw — failure is reified as a Result', async () => {
    await expect(
      safeQuery(() => {
        throw new Error('sync throw inside async');
      }),
    ).resolves.toMatchObject({ ok: false });
  });
});
