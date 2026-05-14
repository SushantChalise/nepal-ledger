/**
 * Integration tests for the validation driver. Repositories are mocked
 * (no real DB hit) and the driver's per-row decisions, transaction
 * boundary, and Result wiring are asserted against the canonical
 * staging→approved fixture shape.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const mocks = vi.hoisted(() => ({
  listStagingRowsForParserRun: vi.fn(),
  findSourceDocumentById: vi.fn(),
  findIndicatorBySlug: vi.fn(),
  listApprovedTrailingForIndicator: vi.fn(),
  findLatestApprovedByPeriod: vi.fn(),
  insertDataQualityFlag: vi.fn(),
  promoteStagingRow: vi.fn(),
}));

vi.mock('@/lib/db/repositories/staging-indicator-values', () => ({
  listStagingRowsForParserRun: mocks.listStagingRowsForParserRun,
}));
vi.mock('@/lib/db/repositories/source-documents', () => ({
  findSourceDocumentById: mocks.findSourceDocumentById,
}));
vi.mock('@/lib/db/repositories/indicators', () => ({
  findIndicatorBySlug: mocks.findIndicatorBySlug,
}));
vi.mock('@/lib/db/repositories/approved-indicator-values', () => ({
  listApprovedTrailingForIndicator: mocks.listApprovedTrailingForIndicator,
  findLatestApprovedByPeriod: mocks.findLatestApprovedByPeriod,
}));
vi.mock('@/lib/db/repositories/data-quality-flags', () => ({
  insertDataQualityFlag: mocks.insertDataQualityFlag,
}));
vi.mock('./promote', () => ({
  promoteStagingRow: mocks.promoteStagingRow,
}));

const {
  listStagingRowsForParserRun,
  findSourceDocumentById,
  findIndicatorBySlug,
  listApprovedTrailingForIndicator,
  findLatestApprovedByPeriod,
  insertDataQualityFlag,
  promoteStagingRow: promoteStagingRowImpl,
} = mocks;

import type {
  ApprovedIndicatorValueRow,
  StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';
import { ok, err } from '@/lib/errors';

import { validateParserRun } from './index';

const indicator: IndicatorRow = {
  id: '00000000-0000-0000-0000-000000000030',
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

const document: SourceDocumentRow = {
  id: '00000000-0000-0000-0000-000000000020',
  sourceId: 'nrb-cmefs',
  originalUrl: 'https://example.com/file.pdf',
  storageProvider: 'supabase',
  storageKey: 'nrb-cmefs/2026-04-30/file.pdf',
  fileHashSha256: 'a'.repeat(64),
  fileSizeBytes: 1024,
  contentType: 'application/pdf',
  downloadedAt: new Date('2026-04-30T00:00:00.000Z'),
  reportingPeriodLabel: 'Mid-Chaitra 2082',
  notes: null,
};

function stagingFixture(
  overrides: Partial<StagingIndicatorValueRow> = {},
): StagingIndicatorValueRow {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    parserRunId: '00000000-0000-0000-0000-000000000010',
    sourceDocumentId: document.id,
    indicatorId: indicator.id,
    indicatorSlugRaw: indicator.slug,
    value: '5.25',
    unit: 'percent',
    reportingPeriodType: 'monthly',
    reportingPeriodBs: 'Mid-Chaitra 2082',
    reportingPeriodAdStart: new Date('2026-03-14T00:00:00.000Z'),
    reportingPeriodAdEnd: new Date('2026-04-13T00:00:00.000Z'),
    publicationDateAd: new Date('2026-04-30T00:00:00.000Z'),
    publicationDateBs: '2083-01-17',
    fiscalYearBs: '2082/83',
    fiscalYearAdLabel: '2025/26',
    confidenceGradeProposed: 'A',
    parserNotes: null,
    insertedAt: new Date('2026-05-01T00:00:00.000Z'),
    ...overrides,
  };
}

const promotedRow: ApprovedIndicatorValueRow = {
  id: '00000000-0000-0000-0000-000000000200',
  sourceDocumentId: document.id,
  indicatorId: indicator.id,
  value: '5.25',
  unit: 'percent',
  reportingPeriodType: 'monthly',
  reportingPeriodBs: 'Mid-Chaitra 2082',
  reportingPeriodAdStart: new Date('2026-03-14T00:00:00.000Z'),
  reportingPeriodAdEnd: new Date('2026-04-13T00:00:00.000Z'),
  publicationDateAd: new Date('2026-04-30T00:00:00.000Z'),
  publicationDateBs: '2083-01-17',
  fiscalYearBs: '2082/83',
  fiscalYearAdLabel: '2025/26',
  confidenceGrade: 'A',
  revisionNumber: 0,
  promotedAt: new Date('2026-05-01T00:00:00.000Z'),
  promotedBy: 'validation-job/v1',
  notes: null,
};

function setHappyDefaults(): void {
  findSourceDocumentById.mockResolvedValue(ok(document));
  findIndicatorBySlug.mockResolvedValue(ok(indicator));
  listApprovedTrailingForIndicator.mockResolvedValue(ok([]));
  findLatestApprovedByPeriod.mockResolvedValue(ok(null));
  insertDataQualityFlag.mockResolvedValue(
    ok({
      id: 'flag-id',
      stagingRowId: 'row',
      flagType: 'PeriodAmbiguous',
      severity: 'warning',
      detail: 'x',
      createdAt: new Date(),
      resolvedAt: null,
      resolutionNote: null,
    }),
  );
  promoteStagingRowImpl.mockResolvedValue(ok(promotedRow));
}

beforeEach(() => {
  listStagingRowsForParserRun.mockReset();
  findSourceDocumentById.mockReset();
  findIndicatorBySlug.mockReset();
  listApprovedTrailingForIndicator.mockReset();
  findLatestApprovedByPeriod.mockReset();
  insertDataQualityFlag.mockReset();
  promoteStagingRowImpl.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('validateParserRun', () => {
  it('empty parser run returns zeros', async () => {
    listStagingRowsForParserRun.mockResolvedValue(ok([]));
    const result = await validateParserRun('run-id');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({
      parserRunId: 'run-id',
      totalStagingRows: 0,
      promoted: 0,
      promotedWithWarnings: 0,
      blocked: 0,
      blockingFlags: [],
    });
  });

  it('happy path: 3 rows → 3 promoted, no flags written', async () => {
    setHappyDefaults();
    listStagingRowsForParserRun.mockResolvedValue(
      ok([
        stagingFixture({ id: 'r1' }),
        stagingFixture({ id: 'r2' }),
        stagingFixture({ id: 'r3' }),
      ]),
    );
    const result = await validateParserRun('run-id');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.promoted).toBe(3);
    expect(result.value.promotedWithWarnings).toBe(0);
    expect(result.value.blocked).toBe(0);
    expect(result.value.blockingFlags).toHaveLength(0);
    expect(insertDataQualityFlag).not.toHaveBeenCalled();
    expect(promoteStagingRowImpl).toHaveBeenCalledTimes(3);
  });

  it('mixed: 1 promoted, 1 promoted-with-warning, 1 blocked', async () => {
    setHappyDefaults();
    listStagingRowsForParserRun.mockResolvedValue(
      ok([
        // Clean promote.
        stagingFixture({ id: 'r1' }),
        // Promote with PeriodAmbiguous warning (AD range mismatch).
        stagingFixture({
          id: 'r2',
          reportingPeriodAdStart: new Date('2025-01-01T00:00:00.000Z'),
          reportingPeriodAdEnd: new Date('2025-01-31T00:00:00.000Z'),
        }),
        // Block — unknown unit.
        stagingFixture({ id: 'r3', unit: 'parsecs' }),
      ]),
    );

    const result = await validateParserRun('run-id');
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.promoted).toBe(1);
    expect(result.value.promotedWithWarnings).toBe(1);
    expect(result.value.blocked).toBe(1);
    expect(result.value.blockingFlags).toHaveLength(1);
    expect(result.value.blockingFlags[0]?.flagType).toBe('UnitUnrecognized');
    // r2 produced 1 warning, r3 produced 1 block flag → 2 flag inserts.
    expect(insertDataQualityFlag).toHaveBeenCalledTimes(2);
    // r1 and r2 promoted, r3 did not.
    expect(promoteStagingRowImpl).toHaveBeenCalledTimes(2);
  });

  it('DB error during promote propagates as the Result error (no partial summary)', async () => {
    setHappyDefaults();
    promoteStagingRowImpl.mockResolvedValue(
      err({ kind: 'QueryFailed', detail: 'simulated tx failure' }),
    );
    listStagingRowsForParserRun.mockResolvedValue(ok([stagingFixture({ id: 'r1' })]));
    const result = await validateParserRun('run-id');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });

  it('returns the staging-rows DB error verbatim when the initial list fails', async () => {
    listStagingRowsForParserRun.mockResolvedValue(
      err({ kind: 'DatabaseUnavailable', detail: 'pool down' }),
    );
    const result = await validateParserRun('run-id');
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('DatabaseUnavailable');
  });
});
