/**
 * Vitest suite for the indicators repository.
 *
 * `linkIndicatorToSource` is the load-bearing case: an existing
 * (indicator_id, source_id) pair must short-circuit to the existing row,
 * not throw or insert a duplicate.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type { IndicatorRow, IndicatorSourceMapRow } from '@/lib/db/schema/indicators';

import { findIndicatorBySlug, linkIndicatorToSource, listIndicatorsByCategory } from './indicators';

const sampleIndicator: IndicatorRow = {
  id: '22222222-2222-2222-2222-222222222222',
  slug: 'inflation-yoy',
  nameEn: 'Inflation (YoY)',
  nameNe: null,
  category: 'price',
  unit: 'percent',
  nativeFrequency: 'monthly',
  sourceAgency: 'NRB',
  parentIndicatorId: null,
  descriptionEn: null,
  descriptionNe: null,
  createdAt: new Date('2026-01-01T00:00:00.000Z'),
  updatedAt: new Date('2026-01-01T00:00:00.000Z'),
};

const sampleMapRow: IndicatorSourceMapRow = {
  id: '33333333-3333-3333-3333-333333333333',
  indicatorId: sampleIndicator.id,
  sourceId: 'nrb-cmefs',
  notes: null,
  createdAt: new Date('2026-01-01T00:00:00.000Z'),
};

beforeEach(() => {
  dbMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('findIndicatorBySlug', () => {
  it('happy path: returns ok(row)', async () => {
    dbMock.mockReturnValue({
      query: { indicators: { findFirst: () => Promise.resolve(sampleIndicator) } },
    });
    const result = await findIndicatorBySlug('inflation-yoy');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.slug).toBe('inflation-yoy');
  });

  it('returns NotFound when no row matches', async () => {
    dbMock.mockReturnValue({
      query: { indicators: { findFirst: () => Promise.resolve(undefined) } },
    });
    const result = await findIndicatorBySlug('nope');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('NotFound');
    if (result.error.kind === 'NotFound') {
      expect(result.error.resource).toBe('indicators');
      expect(result.error.id).toBe('nope');
    }
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      query: { indicators: { findFirst: () => Promise.reject(new Error('boom')) } },
    });
    const result = await findIndicatorBySlug('anything');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('listIndicatorsByCategory', () => {
  it('returns rows from findMany', async () => {
    dbMock.mockReturnValue({
      query: { indicators: { findMany: () => Promise.resolve([sampleIndicator]) } },
    });
    const result = await listIndicatorsByCategory('price');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);
  });
});

describe('linkIndicatorToSource', () => {
  it('returns existing row when the pair already exists (idempotent)', async () => {
    const insert = vi.fn();
    dbMock.mockReturnValue({
      query: {
        indicatorSourceMap: { findFirst: () => Promise.resolve(sampleMapRow) },
      },
      insert,
    });
    const result = await linkIndicatorToSource(sampleIndicator.id, 'nrb-cmefs');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.id).toBe(sampleMapRow.id);
    expect(insert).not.toHaveBeenCalled();
  });

  it('inserts and returns the new row when no pair exists', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleMapRow]));
    const values = vi.fn(() => ({ returning }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({
      query: {
        indicatorSourceMap: { findFirst: () => Promise.resolve(undefined) },
      },
      insert,
    });
    const result = await linkIndicatorToSource(sampleIndicator.id, 'nrb-cmefs', 'primary source');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.id).toBe(sampleMapRow.id);
    expect(values).toHaveBeenCalledWith({
      indicatorId: sampleIndicator.id,
      sourceId: 'nrb-cmefs',
      notes: 'primary source',
    });
  });

  it('translates DB throw on the existence check to QueryFailed', async () => {
    dbMock.mockReturnValue({
      query: {
        indicatorSourceMap: { findFirst: () => Promise.reject(new Error('db down')) },
      },
    });
    const result = await linkIndicatorToSource(sampleIndicator.id, 'nrb-cmefs');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});
