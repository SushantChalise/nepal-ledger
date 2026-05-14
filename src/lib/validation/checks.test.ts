/**
 * Pure unit tests for the 8 validation checks.
 *
 * No DB mocks needed — every check is a pure function over its inputs.
 * Fixtures live inline so a reviewer can read a single file and see the
 * full per-check decision matrix.
 */

import { describe, expect, it } from 'vitest';

import type {
  ApprovedIndicatorValueRow,
  StagingIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';

import {
  duplicateCheck,
  indicatorResolutionCheck,
  periodParseCheck,
  plausibilityCheck,
  revisionFlowCheck,
  schemaCheck,
  sourceIntegrityCheck,
  unitRecognitionCheck,
} from './checks';

const baseStagingRow: StagingIndicatorValueRow = {
  id: '00000000-0000-0000-0000-000000000001',
  parserRunId: '00000000-0000-0000-0000-000000000010',
  sourceDocumentId: '00000000-0000-0000-0000-000000000020',
  indicatorId: '00000000-0000-0000-0000-000000000030',
  indicatorSlugRaw: 'inflation-yoy',
  value: '5.25',
  unit: 'percent',
  reportingPeriodType: 'monthly',
  // "Mid-Chaitra 2082" → FY 2082/83, Chaitra (month 9), AD range mid-March
  // to mid-April 2026. We pin the AD range to match.
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
};

const baseIndicator: IndicatorRow = {
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

const baseDocument: SourceDocumentRow = {
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

function approvedFixture(
  overrides: Partial<ApprovedIndicatorValueRow> = {},
): ApprovedIndicatorValueRow {
  return {
    id: '00000000-0000-0000-0000-000000000100',
    sourceDocumentId: '00000000-0000-0000-0000-000000000099',
    indicatorId: baseIndicator.id,
    value: '5.10',
    unit: 'percent',
    reportingPeriodType: 'monthly',
    reportingPeriodBs: 'Mid-Chaitra 2082',
    reportingPeriodAdStart: new Date('2026-03-14T00:00:00.000Z'),
    reportingPeriodAdEnd: new Date('2026-04-13T00:00:00.000Z'),
    publicationDateAd: new Date('2026-04-25T00:00:00.000Z'),
    publicationDateBs: '2083-01-12',
    fiscalYearBs: '2082/83',
    fiscalYearAdLabel: '2025/26',
    confidenceGrade: 'A',
    revisionNumber: 0,
    promotedAt: new Date('2026-04-25T00:00:00.000Z'),
    promotedBy: 'validation-job/v1',
    notes: null,
    ...overrides,
  };
}

const KNOWN_UNITS: ReadonlySet<string> = new Set(['percent', 'NPR_billion']);

describe('schemaCheck', () => {
  it('passes a complete row', () => {
    expect(schemaCheck(baseStagingRow).kind).toBe('pass');
  });

  it('blocks a row whose value is not numeric', () => {
    const outcome = schemaCheck({ ...baseStagingRow, value: 'not-a-number' });
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('SchemaInvalid');
  });

  it('blocks a row with an empty indicatorSlugRaw', () => {
    const outcome = schemaCheck({ ...baseStagingRow, indicatorSlugRaw: '' });
    expect(outcome.kind).toBe('block');
  });
});

describe('indicatorResolutionCheck', () => {
  it('passes when indicator is provided', () => {
    expect(indicatorResolutionCheck(baseStagingRow, baseIndicator).kind).toBe('pass');
  });

  it('blocks with IndicatorUnknown when indicator is null and slug does not match', () => {
    const outcome = indicatorResolutionCheck(
      { ...baseStagingRow, indicatorId: null, indicatorSlugRaw: 'no-such-slug' },
      null,
    );
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('IndicatorUnknown');
  });
});

describe('periodParseCheck', () => {
  it('passes when BS label parses and AD range matches within tolerance', () => {
    expect(periodParseCheck(baseStagingRow).kind).toBe('pass');
  });

  it('blocks when BS label is unparseable', () => {
    const outcome = periodParseCheck({ ...baseStagingRow, reportingPeriodBs: 'gibberish' });
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('PeriodAmbiguous');
  });

  it('warns when parsed AD range disagrees with row AD range by more than 2 days', () => {
    const outcome = periodParseCheck({
      ...baseStagingRow,
      reportingPeriodAdStart: new Date('2025-01-01T00:00:00.000Z'),
      reportingPeriodAdEnd: new Date('2025-01-31T00:00:00.000Z'),
    });
    expect(outcome.kind).toBe('warn');
    if (outcome.kind === 'warn') expect(outcome.flagType).toBe('PeriodAmbiguous');
  });
});

describe('unitRecognitionCheck', () => {
  it('passes when unit is in the known set', () => {
    expect(unitRecognitionCheck(baseStagingRow, KNOWN_UNITS).kind).toBe('pass');
  });

  it('blocks on an unknown unit', () => {
    const outcome = unitRecognitionCheck({ ...baseStagingRow, unit: 'parsecs' }, KNOWN_UNITS);
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('UnitUnrecognized');
  });
});

describe('plausibilityCheck', () => {
  it('skips (passes) when fewer than 3 trailing rows', () => {
    const trailing = [approvedFixture({ value: '5.0' }), approvedFixture({ value: '5.1' })];
    expect(plausibilityCheck(baseStagingRow, trailing).kind).toBe('pass');
  });

  it('passes a value within band', () => {
    const trailing = [
      approvedFixture({ value: '5.0' }),
      approvedFixture({ value: '5.2' }),
      approvedFixture({ value: '5.4' }),
      approvedFixture({ value: '5.1' }),
    ];
    expect(plausibilityCheck(baseStagingRow, trailing).kind).toBe('pass');
  });

  it('warns on a >5 stdev outlier', () => {
    const trailing = [
      approvedFixture({ value: '5.00' }),
      approvedFixture({ value: '5.05' }),
      approvedFixture({ value: '5.10' }),
      approvedFixture({ value: '4.95' }),
      approvedFixture({ value: '5.02' }),
    ];
    // Order-of-magnitude error: lakh-vs-crore mistake.
    const outcome = plausibilityCheck({ ...baseStagingRow, value: '500' }, trailing);
    expect(outcome.kind).toBe('warn');
    if (outcome.kind === 'warn') expect(outcome.flagType).toBe('ValueOutOfPlausibleRange');
  });
});

describe('duplicateCheck', () => {
  it('passes when no prior approved row exists', () => {
    expect(duplicateCheck(baseStagingRow, null).kind).toBe('pass');
  });

  it('blocks on same-doc same-period', () => {
    const existing = approvedFixture({ sourceDocumentId: baseStagingRow.sourceDocumentId });
    const outcome = duplicateCheck(baseStagingRow, existing);
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('DuplicateOfApproved');
  });

  it('passes (defers to revisionFlow) on different-doc same-period', () => {
    const existing = approvedFixture({
      sourceDocumentId: '00000000-0000-0000-0000-0000000000aa',
    });
    expect(duplicateCheck(baseStagingRow, existing).kind).toBe('pass');
  });
});

describe('revisionFlowCheck', () => {
  it('passes when no prior row exists', () => {
    expect(revisionFlowCheck(baseStagingRow, null).kind).toBe('pass');
  });

  it('blocks when revision candidate value matches prior (no real change)', () => {
    const existing = approvedFixture({
      sourceDocumentId: '00000000-0000-0000-0000-0000000000aa',
      value: baseStagingRow.value,
    });
    const outcome = revisionFlowCheck(baseStagingRow, existing);
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('DuplicateOfApproved');
  });

  it('blocks when prior row has an invalid revisionNumber', () => {
    const existing = approvedFixture({
      sourceDocumentId: '00000000-0000-0000-0000-0000000000aa',
      revisionNumber: -1,
    });
    const outcome = revisionFlowCheck(baseStagingRow, existing);
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('RevisionMismatch');
  });
});

describe('sourceIntegrityCheck', () => {
  it('passes when doc.id matches row.sourceDocumentId and hash is present', () => {
    expect(sourceIntegrityCheck(baseStagingRow, baseDocument).kind).toBe('pass');
  });

  it('blocks when the doc id does not match', () => {
    const outcome = sourceIntegrityCheck(baseStagingRow, {
      ...baseDocument,
      id: '99999999-9999-9999-9999-999999999999',
    });
    expect(outcome.kind).toBe('block');
    if (outcome.kind === 'block') expect(outcome.flagType).toBe('SourceHashCollision');
  });

  it('blocks when the doc hash is empty', () => {
    const outcome = sourceIntegrityCheck(baseStagingRow, {
      ...baseDocument,
      fileHashSha256: '',
    });
    expect(outcome.kind).toBe('block');
  });
});
