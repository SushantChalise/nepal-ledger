/**
 * Vitest suite for the migration-permit-facts repository.
 *
 * Mirrors banking-sector-facts.test.ts. The load-bearing case is
 * `bulkInsertMigrationPermitFacts`: it MUST call `onConflictDoNothing()` with
 * NO arguments. The table has a single unique constraint
 * (`migration_permit_facts_unique`, declared NULLS NOT DISTINCT), so the bare
 * form skips on exactly the natural key — making re-ingest of marginal
 * (NULL-dimension) rows idempotent. A `target` column list is unnecessary and
 * the bare form is the established pattern for these fact tables.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type {
  MigrationPermitFactRow,
  NewMigrationPermitFactRow,
} from '@/lib/db/schema/migration-permit-facts';

import {
  bulkInsertMigrationPermitFacts,
  findMigrationPermitFacts,
  insertMigrationPermitFact,
} from './migration-permit-facts';

// A fully-marginal aggregate row — every nullable dimension is NULL, the case
// the NULLS NOT DISTINCT constraint exists to dedup. `sex` is the explicit
// 'total' aggregate (NOT NULL).
const sampleRow: MigrationPermitFactRow = {
  id: '44444444-4444-4444-4444-444444444444',
  fiscalYearBs: '2080/81',
  monthNum: null,
  destinationCountry: null,
  destinationRegion: null,
  originEntityId: null,
  skillClass: null,
  permitCategory: null,
  sex: 'total',
  permits: '771327',
  unit: 'permits',
  sourceDocumentId: '55555555-5555-5555-5555-555555555555',
  confidenceGrade: 'A',
  promotedAt: new Date('2025-08-02T00:00:00.000Z'),
  promotedBy: 'ingest-dofe',
};

const sampleInput: NewMigrationPermitFactRow = {
  fiscalYearBs: '2080/81',
  monthNum: null,
  destinationCountry: null,
  destinationRegion: null,
  originEntityId: null,
  skillClass: null,
  permitCategory: null,
  sex: 'total',
  permits: '771327',
  sourceDocumentId: '55555555-5555-5555-5555-555555555555',
  promotedBy: 'ingest-dofe',
};

beforeEach(() => {
  dbMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('insertMigrationPermitFact', () => {
  it('happy path: returns the inserted row', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const values = vi.fn(() => ({ returning }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await insertMigrationPermitFact(sampleInput);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.id).toBe(sampleRow.id);
    expect(values).toHaveBeenCalledWith(sampleInput);
  });

  it('returns QueryFailed when insert...returning produces no row', async () => {
    const returning = vi.fn(() => Promise.resolve([]));
    const values = vi.fn(() => ({ returning }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await insertMigrationPermitFact(sampleInput);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          returning: () => Promise.reject(new Error('unique violation simulated')),
        }),
      }),
    });
    const result = await insertMigrationPermitFact(sampleInput);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('bulkInsertMigrationPermitFacts', () => {
  it('short-circuits on empty input without touching the db', async () => {
    const result = await bulkInsertMigrationPermitFacts([]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual([]);
    expect(dbMock).not.toHaveBeenCalled();
  });

  it('calls onConflictDoNothing with NO target (bare form hits the NULLS NOT DISTINCT key)', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const onConflictDoNothing = vi.fn(() => ({ returning }));
    const values = vi.fn(() => ({ onConflictDoNothing }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await bulkInsertMigrationPermitFacts([sampleInput]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);

    // The contract: bare onConflictDoNothing(), no { target } argument — the
    // table's single unique constraint IS the natural key.
    expect(onConflictDoNothing).toHaveBeenCalledTimes(1);
    expect(onConflictDoNothing).toHaveBeenCalledWith();
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          onConflictDoNothing: () => ({
            returning: () => Promise.reject(new Error('db down')),
          }),
        }),
      }),
    });
    const result = await bulkInsertMigrationPermitFacts([sampleInput]);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('findMigrationPermitFacts', () => {
  it('matches a marginal dimension with isNull when passed null', async () => {
    const findMany = vi.fn(() => Promise.resolve([sampleRow]));
    dbMock.mockReturnValue({ query: { migrationPermitFacts: { findMany } } });

    const result = await findMigrationPermitFacts({
      fiscalYearBs: '2080/81',
      originEntityId: null,
      sex: 'total',
    });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);
    expect(findMany).toHaveBeenCalledTimes(1);
  });

  it('returns ok([]) for the empty-match case', async () => {
    const findMany = vi.fn(() => Promise.resolve([]));
    dbMock.mockReturnValue({ query: { migrationPermitFacts: { findMany } } });

    const result = await findMigrationPermitFacts({ fiscalYearBs: '2079/80' });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual([]);
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      query: {
        migrationPermitFacts: {
          findMany: () => Promise.reject(new Error('db down')),
        },
      },
    });
    const result = await findMigrationPermitFacts({ fiscalYearBs: '2080/81' });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});
