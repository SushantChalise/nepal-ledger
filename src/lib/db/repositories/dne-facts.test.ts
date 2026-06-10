/**
 * Vitest suite for the dne-facts repository.
 *
 * The load-bearing cases:
 *   - `bulkInsertDneFacts` MUST call `onConflictDoNothing({ target: [...] })`
 *     naming the six plain columns of `dne_facts_unique_idx`. Unlike the
 *     banking table (COALESCE expression index → bare form), this index is a
 *     plain NOT NULL composite, so the explicit target is correct.
 *   - It MUST chunk at CHUNK_ROWS (2000) so a >2000-row matrix emits multiple
 *     INSERT statements, each ON CONFLICT DO NOTHING.
 *   - Empty input is a no-op that never touches the db.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type { DneFactRow, NewDneFactRow } from '@/lib/db/schema/dne-facts';

import { bulkInsertDneFacts, insertDneFact } from './dne-facts';

const sampleRow: DneFactRow = {
  id: '44444444-4444-4444-4444-444444444444',
  sourceDocumentId: '55555555-5555-5555-5555-555555555555',
  baseIndicatorSlug: 'dne-merchandise-exports',
  baseIndicatorName: 'Merchandise Exports',
  dimensionKind: 'commodity',
  dimensionValue: 'agarbatti',
  dimensionLabel: 'Agarbatti / अगरबत्ती',
  value: '1234.5600',
  unit: 'npr_million',
  reportingPeriodType: 'annual',
  reportingPeriodBs: '2081-82',
  reportingPeriodAdStart: new Date('2024-07-16T00:00:00.000Z'),
  reportingPeriodAdEnd: new Date('2025-07-15T00:00:00.000Z'),
  fiscalYearBs: '2081-82',
  fiscalYearAdLabel: '2024/25',
  confidenceGrade: 'A',
  createdAt: new Date('2026-06-07T00:00:00.000Z'),
};

const sampleInput: NewDneFactRow = {
  sourceDocumentId: '55555555-5555-5555-5555-555555555555',
  baseIndicatorSlug: 'dne-merchandise-exports',
  baseIndicatorName: 'Merchandise Exports',
  dimensionKind: 'commodity',
  dimensionValue: 'agarbatti',
  dimensionLabel: 'Agarbatti / अगरबत्ती',
  value: '1234.5600',
  unit: 'npr_million',
  reportingPeriodType: 'annual',
  reportingPeriodBs: '2081-82',
  reportingPeriodAdStart: new Date('2024-07-16T00:00:00.000Z'),
  reportingPeriodAdEnd: new Date('2025-07-15T00:00:00.000Z'),
  fiscalYearBs: '2081-82',
  fiscalYearAdLabel: '2024/25',
};

beforeEach(() => {
  dbMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('insertDneFact', () => {
  it('happy path: returns the inserted row', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const values = vi.fn(() => ({ returning }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await insertDneFact(sampleInput);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.id).toBe(sampleRow.id);
    expect(values).toHaveBeenCalledWith(sampleInput);
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          returning: () => Promise.reject(new Error('db down')),
        }),
      }),
    });
    const result = await insertDneFact(sampleInput);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('bulkInsertDneFacts', () => {
  it('short-circuits on empty input without touching the db', async () => {
    const result = await bulkInsertDneFacts([]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual([]);
    expect(dbMock).not.toHaveBeenCalled();
  });

  it('calls onConflictDoNothing with the six-column unique-index target', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const onConflictDoNothing = vi.fn((_target?: unknown) => ({ returning }));
    const values = vi.fn(() => ({ onConflictDoNothing }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const result = await bulkInsertDneFacts([sampleInput]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);

    expect(onConflictDoNothing).toHaveBeenCalledTimes(1);
    const arg = onConflictDoNothing.mock.calls[0]?.[0] as { target?: unknown[] } | undefined;
    // The plain composite index has exactly six columns — distinct from the
    // banking table's bare (no-target) COALESCE form.
    expect(arg?.target).toHaveLength(6);
  });

  it('chunks at 2000 rows: 2001 inputs emit two INSERT statements', async () => {
    const onConflictDoNothing = vi.fn(() => ({
      returning: () => Promise.resolve([sampleRow]),
    }));
    const values = vi.fn((_rows: readonly unknown[]) => ({ onConflictDoNothing }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const inputs = Array.from({ length: 2001 }, () => sampleInput);
    const result = await bulkInsertDneFacts(inputs);
    expect(result.ok).toBe(true);
    // Two chunks: 2000 + 1.
    expect(insert).toHaveBeenCalledTimes(2);
    expect(values.mock.calls[0]?.[0]).toHaveLength(2000);
    expect(values.mock.calls[1]?.[0]).toHaveLength(1);
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
    const result = await bulkInsertDneFacts([sampleInput]);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});
