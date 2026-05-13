/**
 * Vitest suite for the source-registry repository.
 *
 * `db()` is mocked via `vi.mock('@/lib/db/client', ...)`. Each test rebuilds
 * the mock with the structural Drizzle-like surface the function under test
 * actually invokes (e.g. `.query.sourceRegistry.findFirst`, `.insert().values
 * ().onConflictDoUpdate().returning()`). No real Postgres, no env required.
 *
 * Pattern mirrors `src/lib/storage/index.test.ts`'s hand-rolled `makeClient`
 * stub — narrow structural types, no `any`, no casts.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type { NewSourceRegistryRow, SourceRegistryRow } from '@/lib/db/schema/source-registry';

import { findSourceById, listActiveSources, markVerified, upsertSource } from './source-registry';

const sampleRow: SourceRegistryRow = {
  sourceId: 'nrb-cmefs',
  agency: 'Nepal Rastra Bank',
  agencyShort: 'NRB',
  datasetName: 'CMEFs',
  sourceUrl: 'https://example.com',
  publicationFrequency: 'monthly',
  expectedReleaseWindow: null,
  reportingPeriodType: 'monthly',
  fileFormat: 'pdf',
  requiresTableExtraction: false,
  historicalCoverage: null,
  licenseStatus: 'gov_open',
  parserOwner: null,
  parserVersion: null,
  revisionPolicy: null,
  knownBreakageModes: [],
  confidenceDefault: 'A',
  status: 'active',
  notes: null,
  registeredAt: new Date('2026-01-01T00:00:00.000Z'),
  lastVerifiedAt: null,
};

beforeEach(() => {
  dbMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('findSourceById', () => {
  it('happy path: returns ok(row) when found', async () => {
    dbMock.mockReturnValue({
      query: { sourceRegistry: { findFirst: () => Promise.resolve(sampleRow) } },
    });
    const result = await findSourceById('nrb-cmefs');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.sourceId).toBe('nrb-cmefs');
  });

  it('returns NotFound when no row matches', async () => {
    dbMock.mockReturnValue({
      query: { sourceRegistry: { findFirst: () => Promise.resolve(undefined) } },
    });
    const result = await findSourceById('missing');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('NotFound');
    if (result.error.kind === 'NotFound') {
      expect(result.error.resource).toBe('source_registry');
      expect(result.error.id).toBe('missing');
    }
  });

  it('translates DB throw to QueryFailed via safeQuery', async () => {
    dbMock.mockReturnValue({
      query: {
        sourceRegistry: { findFirst: () => Promise.reject(new Error('connection refused')) },
      },
    });
    const result = await findSourceById('nrb-cmefs');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('listActiveSources', () => {
  it('returns ok([rows]) from findMany', async () => {
    dbMock.mockReturnValue({
      query: { sourceRegistry: { findMany: () => Promise.resolve([sampleRow]) } },
    });
    const result = await listActiveSources();
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);
  });
});

describe('upsertSource', () => {
  it('happy path: returns the row produced by insert...onConflictDoUpdate...returning', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    let capturedConflictArg: { target: unknown; set: Record<string, unknown> } | undefined;
    const onConflictDoUpdate = vi.fn((arg: { target: unknown; set: Record<string, unknown> }) => {
      capturedConflictArg = arg;
      return { returning };
    });
    const values = vi.fn(() => ({ onConflictDoUpdate }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const input: NewSourceRegistryRow = {
      sourceId: 'nrb-cmefs',
      agency: 'Nepal Rastra Bank',
      agencyShort: 'NRB',
      datasetName: 'CMEFs',
      sourceUrl: 'https://example.com',
      publicationFrequency: 'monthly',
      reportingPeriodType: 'monthly',
      fileFormat: 'pdf',
    };
    const result = await upsertSource(input);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.sourceId).toBe('nrb-cmefs');
    expect(insert).toHaveBeenCalledTimes(1);
    expect(values).toHaveBeenCalledWith(input);
    // The set payload must not include the primary key or registeredAt.
    expect(capturedConflictArg).toBeDefined();
    expect(capturedConflictArg?.set).not.toHaveProperty('sourceId');
    expect(capturedConflictArg?.set).not.toHaveProperty('registeredAt');
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          onConflictDoUpdate: () => ({
            returning: () => Promise.reject(new Error('boom')),
          }),
        }),
      }),
    });
    const result = await upsertSource({
      sourceId: 'x',
      agency: 'A',
      agencyShort: 'A',
      datasetName: 'd',
      sourceUrl: 'u',
      publicationFrequency: 'monthly',
      reportingPeriodType: 'monthly',
      fileFormat: 'pdf',
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('markVerified', () => {
  it('returns NotFound when update affects no rows', async () => {
    dbMock.mockReturnValue({
      update: () => ({
        set: () => ({
          where: () => ({
            returning: () => Promise.resolve([]),
          }),
        }),
      }),
    });
    const result = await markVerified('missing', '2026-05-13T00:00:00.000Z');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('NotFound');
    if (result.error.kind === 'NotFound') {
      expect(result.error.id).toBe('missing');
    }
  });

  it('returns ok(row) when update returns the row', async () => {
    const updated: SourceRegistryRow = {
      ...sampleRow,
      lastVerifiedAt: new Date('2026-05-13T00:00:00.000Z'),
    };
    dbMock.mockReturnValue({
      update: () => ({
        set: () => ({
          where: () => ({
            returning: () => Promise.resolve([updated]),
          }),
        }),
      }),
    });
    const result = await markVerified('nrb-cmefs', '2026-05-13T00:00:00.000Z');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.lastVerifiedAt).toEqual(new Date('2026-05-13T00:00:00.000Z'));
  });
});
