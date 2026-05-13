/**
 * Vitest suite for the source-documents repository.
 *
 * `findSourceDocumentByHash` is the load-bearing case: it must return
 * `ok(null)` on no-match (content-addressed dedup), NOT `NotFound`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type { NewSourceDocumentRow, SourceDocumentRow } from '@/lib/db/schema/source-documents';

import {
  findSourceDocumentByHash,
  findSourceDocumentById,
  insertSourceDocument,
  listSourceDocumentsForSource,
} from './source-documents';

const sampleRow: SourceDocumentRow = {
  id: '11111111-1111-1111-1111-111111111111',
  sourceId: 'nrb-cmefs',
  originalUrl: 'https://example.com/file.pdf',
  storageProvider: 'supabase',
  storageKey: 'nrb-cmefs/2026-05-13/file.pdf',
  fileHashSha256: 'abc123',
  fileSizeBytes: 1024,
  contentType: 'application/pdf',
  downloadedAt: new Date('2026-05-13T00:00:00.000Z'),
  reportingPeriodLabel: null,
  notes: null,
};

beforeEach(() => {
  dbMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('insertSourceDocument', () => {
  it('happy path: returns the inserted row', async () => {
    const returning = vi.fn(() => Promise.resolve([sampleRow]));
    const values = vi.fn(() => ({ returning }));
    const insert = vi.fn(() => ({ values }));
    dbMock.mockReturnValue({ insert });

    const input: NewSourceDocumentRow = {
      sourceId: 'nrb-cmefs',
      originalUrl: 'https://example.com/file.pdf',
      storageKey: 'nrb-cmefs/2026-05-13/file.pdf',
      fileHashSha256: 'abc123',
      fileSizeBytes: 1024,
      contentType: 'application/pdf',
    };
    const result = await insertSourceDocument(input);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.id).toBe('11111111-1111-1111-1111-111111111111');
    expect(values).toHaveBeenCalledWith(input);
  });

  it('translates DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          returning: () => Promise.reject(new Error('unique violation simulated')),
        }),
      }),
    });
    const result = await insertSourceDocument({
      sourceId: 'nrb-cmefs',
      originalUrl: 'u',
      storageKey: 'k',
      fileHashSha256: 'h',
      fileSizeBytes: 1,
      contentType: 'application/pdf',
    });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('findSourceDocumentById', () => {
  it('happy path: returns the row', async () => {
    dbMock.mockReturnValue({
      query: { sourceDocuments: { findFirst: () => Promise.resolve(sampleRow) } },
    });
    const result = await findSourceDocumentById(sampleRow.id);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.storageKey).toBe('nrb-cmefs/2026-05-13/file.pdf');
  });

  it('returns NotFound when missing', async () => {
    dbMock.mockReturnValue({
      query: { sourceDocuments: { findFirst: () => Promise.resolve(undefined) } },
    });
    const result = await findSourceDocumentById('missing-id');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('NotFound');
    if (result.error.kind === 'NotFound') {
      expect(result.error.resource).toBe('source_documents');
      expect(result.error.id).toBe('missing-id');
    }
  });
});

describe('findSourceDocumentByHash', () => {
  it('returns ok(null) — not NotFound — when no row matches', async () => {
    dbMock.mockReturnValue({
      query: { sourceDocuments: { findFirst: () => Promise.resolve(undefined) } },
    });
    const result = await findSourceDocumentByHash('hash-with-no-row');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toBeNull();
  });

  it('returns ok(row) when a match exists', async () => {
    dbMock.mockReturnValue({
      query: { sourceDocuments: { findFirst: () => Promise.resolve(sampleRow) } },
    });
    const result = await findSourceDocumentByHash('abc123');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).not.toBeNull();
    expect(result.value?.fileHashSha256).toBe('abc123');
  });

  it('translates DB throw to QueryFailed (does NOT swallow as ok(null))', async () => {
    dbMock.mockReturnValue({
      query: {
        sourceDocuments: { findFirst: () => Promise.reject(new Error('db down')) },
      },
    });
    const result = await findSourceDocumentByHash('anything');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('listSourceDocumentsForSource', () => {
  it('returns rows from findMany', async () => {
    dbMock.mockReturnValue({
      query: { sourceDocuments: { findMany: () => Promise.resolve([sampleRow]) } },
    });
    const result = await listSourceDocumentsForSource('nrb-cmefs', 10);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toHaveLength(1);
  });
});
