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

  it('unwraps DrizzleError.cause so the underlying error classifies correctly', async () => {
    // postgres-js attaches the connection error as DrizzleError.cause. Without
    // the cause-recursion in toAppError(), this would mask EAI_AGAIN inside a
    // generic "Failed query: …" string and lose the DatabaseUnavailable signal.
    const wrapped = new DrizzleError({ message: 'Failed query: select 1' });
    (wrapped as DrizzleError & { cause?: unknown }).cause = Object.assign(
      new Error('getaddrinfo EAI_AGAIN db.x.supabase.co'),
      { code: 'EAI_AGAIN' },
    );
    const result = await safeQuery(() => Promise.reject(wrapped));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.kind).toBe('DatabaseUnavailable');
    }
  });

  it('classifies bare connection-failure error codes as DatabaseUnavailable', async () => {
    const e = Object.assign(new Error('connect ECONNREFUSED'), { code: 'ECONNREFUSED' });
    const result = await safeQuery(() => Promise.reject(e));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe('DatabaseUnavailable');
  });

  it('does not throw — failure is reified as a Result', async () => {
    await expect(
      safeQuery(() => {
        throw new Error('sync throw inside async');
      }),
    ).resolves.toMatchObject({ ok: false });
  });
});
