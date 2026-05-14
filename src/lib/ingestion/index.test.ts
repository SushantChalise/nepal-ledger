/**
 * Ingestion orchestrator integration tests.
 *
 * Mocks the storage wrapper, the validation job, the DB repositories, and the
 * subprocess `spawn` seam. No real DB, no real network, no real subprocess.
 */

import { EventEmitter } from 'node:events';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const mocks = vi.hoisted(() => ({
  uploadSourceDocument: vi.fn(),
  insertSourceDocument: vi.fn(),
  insertParserRun: vi.fn(),
  bulkInsertStagingRows: vi.fn(),
  bulkInsertParserErrors: vi.fn(),
  validateParserRun: vi.fn(),
  readFile: vi.fn(),
}));

vi.mock('node:fs/promises', () => ({
  readFile: mocks.readFile,
}));

vi.mock('@/lib/storage', async () => {
  const actual = await vi.importActual<typeof import('@/lib/storage')>('@/lib/storage');
  return {
    ...actual,
    uploadSourceDocument: mocks.uploadSourceDocument,
  };
});
vi.mock('@/lib/db/repositories/source-documents', () => ({
  insertSourceDocument: mocks.insertSourceDocument,
}));
vi.mock('@/lib/db/repositories/parser-runs', () => ({
  insertParserRun: mocks.insertParserRun,
  bulkInsertParserErrors: mocks.bulkInsertParserErrors,
  findParserRunById: vi.fn(),
}));
vi.mock('@/lib/db/repositories/staging-indicator-values', () => ({
  bulkInsertStagingRows: mocks.bulkInsertStagingRows,
}));
vi.mock('@/lib/validation', () => ({
  validateParserRun: mocks.validateParserRun,
}));

import { err, ok } from '@/lib/errors';

import { ingestSource } from './index';
import type { ParserOutput } from './types';
import type { SpawnLike } from './run-parser';

const SOURCE_DOC_ID = '00000000-0000-0000-0000-000000000020';
const PARSER_RUN_ID = '00000000-0000-0000-0000-000000000040';

const STAGING_ROW = {
  indicator_slug_raw: 'ncpi-overall-index-overall-yoy',
  value: 5.25,
  unit: 'percent_yoy',
  reporting_period_type: 'nine_months_cumulative' as const,
  reporting_period_bs: 'FY 2082/83 9M',
  reporting_period_ad_start: '2025-07-17T00:00:00.000Z',
  reporting_period_ad_end: '2026-04-13T00:00:00.000Z',
  publication_date_ad: '2026-05-08T00:00:00.000Z',
  publication_date_bs: '2083 Baisakh 25',
  fiscal_year_bs: '2082/83',
  fiscal_year_ad_label: '2025/26',
  confidence_grade_proposed: 'A' as const,
  parser_notes: null,
};

const HAPPY_PARSER_OUTPUT: ParserOutput = {
  status: 'success',
  parser_version: '0.1.0',
  // Zod's z.coerce.date() converts ISO strings to Date — ParserOutput type
  // post-validation has Date fields. We construct via the schema to mirror.
  staging_rows: [
    {
      ...STAGING_ROW,
      reporting_period_ad_start: new Date(STAGING_ROW.reporting_period_ad_start),
      reporting_period_ad_end: new Date(STAGING_ROW.reporting_period_ad_end),
      publication_date_ad: new Date(STAGING_ROW.publication_date_ad),
    },
  ],
  errors: [],
};

function makeSpawnReturning(opts: {
  stdout: string;
  stderr?: string;
  exitCode: number;
}): SpawnLike {
  return () => {
    const stdout = new EventEmitter();
    const stderr = new EventEmitter();
    const base = new EventEmitter();
    const child = Object.assign(base, {
      stdout,
      stderr,
      kill: (): void => undefined,
    });
    queueMicrotask(() => {
      stdout.emit('data', Buffer.from(opts.stdout, 'utf8'));
      if (opts.stderr) stderr.emit('data', Buffer.from(opts.stderr, 'utf8'));
      child.emit('close', opts.exitCode);
    });
    return child;
  };
}

function happyParserStdout(): string {
  return JSON.stringify({
    status: 'success',
    parser_version: '0.1.0',
    staging_rows: [STAGING_ROW],
    errors: [],
  });
}

function setHappyMocks(): void {
  mocks.uploadSourceDocument.mockResolvedValue(
    ok({
      storageKey: 'nrb-ncpi-table/2026-05-14/file.csv',
      fileHashSha256: 'a'.repeat(64),
      fileSizeBytes: 1024,
      contentType: 'text/csv',
      storageProvider: 'supabase',
    }),
  );
  mocks.insertSourceDocument.mockResolvedValue(ok({ id: SOURCE_DOC_ID }));
  mocks.insertParserRun.mockResolvedValue(ok({ id: PARSER_RUN_ID }));
  mocks.bulkInsertStagingRows.mockResolvedValue(ok([]));
  mocks.bulkInsertParserErrors.mockResolvedValue(ok([]));
  mocks.validateParserRun.mockResolvedValue(
    ok({
      parserRunId: PARSER_RUN_ID,
      totalStagingRows: 1,
      promoted: 1,
      promotedWithWarnings: 0,
      blocked: 0,
      blockingFlags: [],
    }),
  );
}

beforeEach(() => {
  for (const m of Object.values(mocks)) m.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ingestSource', () => {
  it('happy path (filePath input): pipes through every stage and returns the summary', async () => {
    setHappyMocks();
    mocks.readFile.mockResolvedValue(Buffer.from('csv,bytes\n'));

    const result = await ingestSource(
      {
        filePath: '/tmp/fake.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'file.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      { spawnImpl: makeSpawnReturning({ stdout: happyParserStdout(), exitCode: 0 }) },
    );

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.sourceDocumentId).toBe(SOURCE_DOC_ID);
    expect(result.value.parserRunId).toBe(PARSER_RUN_ID);
    expect(result.value.parserStatus).toBe('success');
    expect(result.value.stagingRowsWritten).toBe(1);
    expect(result.value.validation.promoted).toBe(1);
    expect(mocks.validateParserRun).toHaveBeenCalledTimes(1);
    expect(mocks.validateParserRun).toHaveBeenCalledWith(PARSER_RUN_ID);
  });

  it('happy path (url input): fetch is called once; body is uploaded', async () => {
    setHappyMocks();
    const fetchSpy = vi.fn(
      async () => new Response(Buffer.from('csv,bytes\n'), { status: 200, statusText: 'OK' }),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const result = await ingestSource(
      {
        url: 'https://example.com/file.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'file.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      { spawnImpl: makeSpawnReturning({ stdout: happyParserStdout(), exitCode: 0 }) },
    );

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.sourceDocumentId).toBe(SOURCE_DOC_ID);
  });

  it('fetch returns non-2xx: returns External(http) without retrying', async () => {
    setHappyMocks();
    const fetchSpy = vi.fn(
      async () => new Response('not found', { status: 404, statusText: 'Not Found' }),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const result = await ingestSource(
      {
        url: 'https://example.com/missing.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'missing.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      { spawnImpl: makeSpawnReturning({ stdout: '{}', exitCode: 0 }) },
    );

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('External');
    if (result.error.kind === 'External') {
      expect(result.error.service).toBe('http');
      expect(result.error.cause).toContain('404');
    }
  });

  it('storage upload Conflict short-circuits the pipeline', async () => {
    setHappyMocks();
    mocks.uploadSourceDocument.mockResolvedValue(err({ kind: 'Conflict', reason: 'collision' }));
    mocks.readFile.mockResolvedValue(Buffer.from('csv,bytes\n'));

    const result = await ingestSource(
      {
        filePath: '/tmp/fake.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'file.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      { spawnImpl: makeSpawnReturning({ stdout: happyParserStdout(), exitCode: 0 }) },
    );

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('Conflict');
    expect(mocks.insertSourceDocument).not.toHaveBeenCalled();
    expect(mocks.validateParserRun).not.toHaveBeenCalled();
  });

  it('parser exit code 2: returns External(python-parser) usage error', async () => {
    setHappyMocks();
    mocks.readFile.mockResolvedValue(Buffer.from('csv,bytes\n'));

    const result = await ingestSource(
      {
        filePath: '/tmp/fake.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'file.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      {
        spawnImpl: makeSpawnReturning({
          stdout: '',
          stderr: 'usage: parser.py <path> <id>\n',
          exitCode: 2,
        }),
      },
    );

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('External');
    if (result.error.kind === 'External') {
      expect(result.error.service).toBe('python-parser');
      expect(result.error.cause).toContain('usage error');
    }
    expect(mocks.insertParserRun).not.toHaveBeenCalled();
    expect(mocks.validateParserRun).not.toHaveBeenCalled();
  });

  it('parser stdout malformed JSON: returns ParseFailed', async () => {
    setHappyMocks();
    mocks.readFile.mockResolvedValue(Buffer.from('csv,bytes\n'));

    const result = await ingestSource(
      {
        filePath: '/tmp/fake.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'file.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      { spawnImpl: makeSpawnReturning({ stdout: 'not-json{', exitCode: 0 }) },
    );

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('ParseFailed');
    if (result.error.kind === 'ParseFailed') {
      expect(result.error.field).toBe('parser stdout');
    }
  });

  it('validation surfaces blocked rows: orchestrator still returns ok with the summary', async () => {
    setHappyMocks();
    mocks.validateParserRun.mockResolvedValue(
      ok({
        parserRunId: PARSER_RUN_ID,
        totalStagingRows: 2,
        promoted: 1,
        promotedWithWarnings: 0,
        blocked: 1,
        blockingFlags: [
          {
            stagingRowId: 'row-1',
            flagType: 'SchemaInvalid',
            detail: 'missing field',
          },
        ],
      }),
    );
    mocks.readFile.mockResolvedValue(Buffer.from('csv,bytes\n'));

    const result = await ingestSource(
      {
        filePath: '/tmp/fake.csv',
        sourceId: 'nrb-ncpi-table',
        fileName: 'file.csv',
        contentType: 'text/csv',
        parserPath: 'scrapers/nrb_ncpi/parser.py',
      },
      { spawnImpl: makeSpawnReturning({ stdout: happyParserStdout(), exitCode: 0 }) },
    );

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.validation.blocked).toBe(1);
    expect(result.value.validation.blockingFlags).toHaveLength(1);
  });

  it('same-document re-run creates a new source_documents row (storage dedups, table does not)', async () => {
    setHappyMocks();
    // Storage returns the same key on idempotent re-upload.
    mocks.uploadSourceDocument.mockResolvedValue(
      ok({
        storageKey: 'nrb-ncpi-table/2026-05-14/file.csv',
        fileHashSha256: 'a'.repeat(64),
        fileSizeBytes: 1024,
        contentType: 'text/csv',
        storageProvider: 'supabase',
      }),
    );
    mocks.insertSourceDocument.mockResolvedValueOnce(ok({ id: 'doc-1' }));
    mocks.insertSourceDocument.mockResolvedValueOnce(ok({ id: 'doc-2' }));
    mocks.readFile.mockResolvedValue(Buffer.from('csv,bytes\n'));

    const input = {
      filePath: '/tmp/fake.csv',
      sourceId: 'nrb-ncpi-table',
      fileName: 'file.csv',
      contentType: 'text/csv',
      parserPath: 'scrapers/nrb_ncpi/parser.py',
    } as const;
    const opts = {
      spawnImpl: makeSpawnReturning({ stdout: happyParserStdout(), exitCode: 0 }),
    };
    const r1 = await ingestSource(input, opts);
    const r2 = await ingestSource(input, opts);

    expect(r1.ok && r2.ok).toBe(true);
    if (!r1.ok || !r2.ok) return;
    expect(r1.value.sourceDocumentId).not.toBe(r2.value.sourceDocumentId);
    expect(mocks.insertSourceDocument).toHaveBeenCalledTimes(2);
  });
});

// Silence unused-import warning when the module is not invoked in a branch.
void HAPPY_PARSER_OUTPUT;
