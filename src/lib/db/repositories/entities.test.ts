/**
 * Vitest suite for the entities repository. `db()` is mocked with a structural
 * Drizzle-like stub (same approach as source-registry.test.ts) — no real
 * Postgres. Pins the upsert conflict target/set shape and the resolve helpers.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type { EntityRow, NewEntityRow } from '@/lib/db/schema/entities';

import { bulkUpsertEntities, findEntityByKindAndSlug, findProvinceByNo } from './entities';

const provinceRow: NewEntityRow = {
  kind: 'province',
  slug: '1',
  nameEn: 'Koshi Province',
  nameNe: 'कोशी प्रदेश',
  metadata: { province_no: 1 },
};

const sampleEntity: EntityRow = {
  id: '11111111-1111-4111-8111-111111111111',
  kind: 'province',
  slug: '1',
  nameEn: 'Koshi Province',
  nameNe: 'कोशी प्रदेश',
  parentEntityId: null,
  metadata: { province_no: 1 },
  createdAt: new Date('2026-01-01T00:00:00.000Z'),
  updatedAt: new Date('2026-01-01T00:00:00.000Z'),
};

beforeEach(() => dbMock.mockReset());
afterEach(() => vi.restoreAllMocks());

describe('bulkUpsertEntities', () => {
  it('empty input short-circuits without touching the db', async () => {
    const result = await bulkUpsertEntities([]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({ attempted: 0, upserted: 0 });
    expect(dbMock).not.toHaveBeenCalled();
  });

  it('upserts on the (kind, slug) key and never overwrites id/createdAt', async () => {
    let captured: { target: { name: string }[]; set: Record<string, unknown> } | undefined;
    const returning = vi.fn(() => Promise.resolve([{ id: 'a' }]));
    const onConflictDoUpdate = vi.fn(
      (arg: { target: { name: string }[]; set: Record<string, unknown> }) => {
        captured = arg;
        return { returning };
      },
    );
    dbMock.mockReturnValue({ insert: () => ({ values: () => ({ onConflictDoUpdate }) }) });

    const result = await bulkUpsertEntities([provinceRow]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({ attempted: 1, upserted: 1 });
    expect(captured?.target.map((c) => c.name)).toEqual(['kind', 'slug']);
    expect(captured?.set).toHaveProperty('nameEn');
    expect(captured?.set).toHaveProperty('metadata');
    expect(captured?.set).not.toHaveProperty('id');
    expect(captured?.set).not.toHaveProperty('createdAt');
  });

  it('translates a DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          onConflictDoUpdate: () => ({ returning: () => Promise.reject(new Error('boom')) }),
        }),
      }),
    });
    const result = await bulkUpsertEntities([provinceRow]);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('findEntityByKindAndSlug', () => {
  it('returns ok(row) when found', async () => {
    dbMock.mockReturnValue({
      query: { entities: { findFirst: () => Promise.resolve(sampleEntity) } },
    });
    const result = await findEntityByKindAndSlug('province', '1');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value?.slug).toBe('1');
  });

  it('returns ok(null) — not NotFound — when absent', async () => {
    dbMock.mockReturnValue({
      query: { entities: { findFirst: () => Promise.resolve(undefined) } },
    });
    const result = await findEntityByKindAndSlug('ministry', 'missing');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toBeNull();
  });
});

describe('findProvinceByNo', () => {
  it('resolves province 1 by number (slug = "1")', async () => {
    const findFirst = vi.fn(() => Promise.resolve(sampleEntity));
    dbMock.mockReturnValue({ query: { entities: { findFirst } } });
    const result = await findProvinceByNo(1);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value?.kind).toBe('province');
  });
});
