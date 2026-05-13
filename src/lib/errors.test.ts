import { describe, expect, it } from 'vitest';

import { err, formatAppError, ok, type AppError, type Result } from './errors';

describe('Result<T> constructors', () => {
  it('ok wraps a value with ok: true', () => {
    const r: Result<number> = ok(42);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBe(42);
  });

  it('err wraps an AppError with ok: false', () => {
    const r = err({ kind: 'NotFound', resource: 'indicator', id: 'ncpi-yoy' });
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.error.kind).toBe('NotFound');
      if (r.error.kind === 'NotFound') {
        expect(r.error.resource).toBe('indicator');
      }
    }
  });
});

describe('formatAppError', () => {
  it.each<[AppError, string]>([
    [{ kind: 'NotFound', resource: 'indicator', id: 'x' }, 'NotFound: indicator (x)'],
    [{ kind: 'Validation', field: 'email', reason: 'invalid' }, 'Validation: email — invalid'],
    [{ kind: 'External', service: 'NRB', cause: '500' }, 'External(NRB): 500'],
    [{ kind: 'Conflict', reason: 'duplicate' }, 'Conflict: duplicate'],
    [
      { kind: 'DatabaseUnavailable', detail: 'connection refused' },
      'DatabaseUnavailable: connection refused',
    ],
    [
      { kind: 'ConstraintViolation', constraint: 'unique', detail: 'slug already exists' },
      'ConstraintViolation(unique): slug already exists',
    ],
    [{ kind: 'QueryFailed', detail: 'timeout' }, 'QueryFailed: timeout'],
    [{ kind: 'MigrationMismatch', detail: 'drift' }, 'MigrationMismatch: drift'],
    [
      { kind: 'ParseFailed', field: 'period', reason: 'unknown month' },
      'ParseFailed: period — unknown month',
    ],
  ])('formats %j → %s', (error, expected) => {
    expect(formatAppError(error)).toBe(expected);
  });
});
