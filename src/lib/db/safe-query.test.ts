import { DrizzleError } from 'drizzle-orm';
import { describe, expect, it } from 'vitest';

import { safeQuery, safeQueryWithRetry } from './safe-query';

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

  it('unwraps a non-Drizzle wrapper Error.cause (the live ECONNRESET case)', async () => {
    // The real failure observed against Supabase's pooler: postgres-js/drizzle
    // throw a wrapper whose message is "Failed query: …" that is NOT a
    // DrizzleError instance, with the socket error (ECONNRESET) on `.cause`.
    // The generic-Error branch must inspect `.cause`, else this misclassifies
    // as QueryFailed and the ingest's transient-retry loop never engages.
    const wrapped = Object.assign(new Error('Failed query: select id from indicators'), {
      cause: Object.assign(new Error('read ECONNRESET'), { code: 'ECONNRESET' }),
    });
    const result = await safeQuery(() => Promise.reject(wrapped));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe('DatabaseUnavailable');
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

describe('safeQueryWithRetry', () => {
  it('retries a transient DatabaseUnavailable op until it succeeds', async () => {
    let calls = 0;
    const op = (): Promise<string> => {
      calls += 1;
      if (calls < 3) {
        return Promise.reject(Object.assign(new Error('read ECONNRESET'), { code: 'ECONNRESET' }));
      }
      return Promise.resolve('ok');
    };
    const result = await safeQueryWithRetry(op, 5, 1); // 1ms backoff in test
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value).toBe('ok');
    expect(calls).toBe(3); // failed twice (transient), succeeded on the third
  });

  it('does NOT retry a non-transient QueryFailed', async () => {
    let calls = 0;
    const op = (): Promise<string> => {
      calls += 1;
      return Promise.reject(new Error('syntax error at or near')); // → QueryFailed
    };
    const result = await safeQueryWithRetry(op, 5, 1);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe('QueryFailed');
    expect(calls).toBe(1); // tried once, never retried
  });
});
