/**
 * Vitest suite for the banking-sector-facts repository.
 *
 * The load-bearing case is `bulkInsertBankingSectorFacts`: it MUST call
 * `onConflictDoNothing()` with NO arguments. The bare form skips on the
 * table's only unique index, `banking_facts_unique_idx`, which is an
 * EXPRESSION index over `coalesce(bank_entity_id, <sentinel>::uuid)`. Passing
 * an explicit `target` would emit a plain `(col, …)` column list that cannot
 * name that expression — so a `target` would silently fail to dedup the
 * NULL-entity aggregate rows the COALESCE index exists to dedup.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type {
  BankingSectorFactRow,
  NewBankingSectorFactRow,
} from '@/lib/db/schema/banking-sector-facts';

import { bulkInsertBankingSectorFacts, insertBankingSectorFact } from './banking-sector-facts';

const sampleRow: BankingSectorFactRow = {
  id: '44444444-4444-4444-4444-444444444444',
  bankClass: 'commercial',
  // NULL entity — the system-aggregate case the COALESCE index protects.
  bankEntityId: null,
  sourceSheet: 'C5',
  indicatorSlug: 'paid-up-capital',
  value: '1000.000000',
  unit: 'npr_million',
  reportingPeriodType: 'monthly',
  reportingPeriodBs: '2082-03',
  reportingPeriodAdStart: new Date('2025-06-15T00:00:00.000Z'),
  reportingPeriodAdEnd: new Date('2025-07-16T00:00:00.000Z'),
  publicationDateAd: new Date('2025-08-01T00:00:00.000Z'),
  publicationDateBs: '2082-04-16',
  fiscalYearBs: '2081-82',
  sourceDocumentId: '55555555-5555-5555-5555-555555555555',
  confidenceGrade: 'A',
  promotedAt: new Date('2025-08-02T00:00:00.000Z'),
  promotedBy: 'ingest-nrb-bfi',
};

const sampleInput: NewBankingSectorFactRow = {
  bankClass: 'commercial',
  bankEntityId: null,
  sourceSheet: 'C5',
  indicatorSlug: 'paid-up-capital',
  value: '1000.000000',
  unit: 'npr_million',
  reportingPeriodType: 'monthly',
  reportingPeriodBs: '2082-03',
  reportingPeriodAdStart: new Date('2025-06-15T00:00:00.000Z'),
  reportingPeriodAdEnd: new Date('2025-07-16T00:00:00.000Z'),
  publicationDateAd: new Date('2025-08-01T00:00:00.000Z'),
  publicationDateBs: '2082-04-16',
  fiscalYearBs: '2081-82',
  sourceDocumentId: '55555555-5555-5555-5555-555555555555',
  promotedBy: 'ingest-nrb-bfi',
};

beforeEach(() => {
  dbMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('insertBankingSectorFact', () => {
  it('happy path: returns the inserted row', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const values = vi.fn(() => ({ returning }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await insertBankingSectorFact(sampleInput);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.id).toBe(sampleRow.id);
    expect(values).toHaveBeenCalledWith(sampleInput);
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          returning: () => Promise.reject(new Error('unique violation simulated')),
        }),
      }),
    });
    const result = await insertBankingSectorFact(sampleInput);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('bulkInsertBankingSectorFacts', () => {
  it('short-circuits on empty input without touching the db', async () => {
    const result = await bulkInsertBankingSectorFacts([]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual([]);
    expect(dbMock).not.toHaveBeenCalled();
  });

  it('calls onConflictDoNothing with NO target (bare form hits the COALESCE index)', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const onConflictDoNothing = vi.fn(() => ({ returning }));
    const values = vi.fn(() => ({ onConflictDoNothing }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await bulkInsertBankingSectorFacts([sampleInput]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);

    // The fix's contract: bare onConflictDoNothing(), no { target } argument.
    // A target would emit a plain column list and bypass the expression index.
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
    const result = await bulkInsertBankingSectorFacts([sampleInput]);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});
