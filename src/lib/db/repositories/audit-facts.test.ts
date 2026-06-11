/**
 * Vitest suite for the audit fact-domain repository.
 *
 * `db()` is mocked with a structural Drizzle-like stub (same approach as
 * source-registry.test.ts) — no real Postgres. These tests pin the UPSERT
 * CONTRACT: the conflict target columns, the precedence `setWhere` guard on
 * summaries/lines, the document-scoped DO NOTHING on findings, empty-input
 * short-circuit, the attempted/upserted/skipped math, and error translation.
 *
 * The actual NULLS-NOT-DISTINCT and precedence-WHERE semantics are guaranteed
 * by the migration SQL (verified) + `drizzle-kit check`, not by this layer.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

const dbMock = vi.fn();
vi.mock('@/lib/db/client', () => ({
  db: () => dbMock(),
}));

import type {
  NewAuditBerujuLineRow,
  NewAuditEntitySummaryRow,
  NewAuditFinancialStockRow,
  NewAuditFindingRow,
  NewAuditParagraphMetricRow,
} from '@/lib/db/schema/audit-facts';

import {
  bulkInsertAuditFindings,
  bulkUpsertBerujuLines,
  bulkUpsertAuditSummaries,
  bulkUpsertFinancialStocks,
  bulkUpsertParagraphMetrics,
} from './audit-facts';

type ConflictArg = {
  target: { name: string }[];
  set: Record<string, unknown>;
  setWhere?: unknown;
};

const summaryRow: NewAuditEntitySummaryRow = {
  auditSubjectClass: 'federal_government',
  auditedEntityId: null,
  aggregateScope: 'all_federal_offices',
  fiscalYearBs: '2079/80',
  berujuRaisedNpr: '236000000000.00',
  berujuRaisedRaw: '२३६ अर्ब',
  sourceDocumentId: '00000000-0000-0000-0000-000000000001',
  sourcePrecedence: 1,
  extractionMethod: 'text_layer',
  confidenceGrade: 'A',
  promotedBy: 'test',
};

const lineRow: NewAuditBerujuLineRow = {
  auditSubjectClass: 'local_government',
  auditedEntityId: null,
  aggregateScope: 'all_local_levels',
  fiscalYearBs: '2079/80',
  amountBasis: 'current_year_raised',
  berujuCategory: 'recoverable',
  sourceTableCode: 'ch2_irregularity_classification',
  amountNpr: '193000000000.00',
  amountRaw: '१९३ अर्ब',
  sourceDocumentId: '00000000-0000-0000-0000-000000000001',
  sourcePrecedence: 1,
  extractionMethod: 'text_layer',
  confidenceGrade: 'A',
  promotedBy: 'test',
};

const stockRow: NewAuditFinancialStockRow = {
  auditSubjectClass: 'federal_government',
  auditedEntityId: null,
  aggregateScope: 'all_federal_offices',
  fiscalYearBs: '2079/80',
  stockType: 'revenue_arrears',
  closingNpr: '215568700000.00',
  closingRaw: '215,568.7',
  sourceTableCode: 'ch_outstanding_stock',
  sourceDocumentId: '00000000-0000-0000-0000-000000000001',
  sourcePrecedence: 1,
  extractionMethod: 'text_layer',
  confidenceGrade: 'A',
  promotedBy: 'test',
};

const metricRow: NewAuditParagraphMetricRow = {
  auditSubjectClass: 'federal_government',
  auditedEntityId: null,
  aggregateScope: 'all_federal_offices',
  fiscalYearBs: '2079/80',
  paragraphStatus: 'issued',
  paragraphCount: 8149,
  sourceTableCode: 'ch4_section38',
  sourceDocumentId: '00000000-0000-0000-0000-000000000001',
  sourcePrecedence: 1,
  extractionMethod: 'text_layer',
  confidenceGrade: 'A',
  promotedBy: 'test',
};

const findingRow: NewAuditFindingRow = {
  auditSubjectClass: 'local_government',
  auditedEntityId: '00000000-0000-0000-0000-0000000000aa',
  fiscalYearBs: '2079/80',
  findingOrdinal: 1,
  sourceLocatorHash: 'abc123',
  sourceDocumentId: '00000000-0000-0000-0000-000000000001',
  sourcePrecedence: 2,
  extractionMethod: 'surya_ocr',
  confidenceGrade: 'B',
  promotedBy: 'test',
};

beforeEach(() => dbMock.mockReset());
afterEach(() => vi.restoreAllMocks());

/** Build a db() stub for an insert().values().onConflictDoUpdate().returning() chain. */
function mockUpdateChain(returningRows: { id: string }[]) {
  let captured: ConflictArg | undefined;
  const returning = vi.fn(() => Promise.resolve(returningRows));
  const onConflictDoUpdate = vi.fn((arg: ConflictArg) => {
    captured = arg;
    return { returning };
  });
  const values = vi.fn(() => ({ onConflictDoUpdate }));
  const insert = vi.fn(() => ({ values }));
  dbMock.mockReturnValue({ insert });
  return {
    insert,
    values,
    get captured() {
      return captured;
    },
  };
}

describe('bulkUpsertAuditSummaries', () => {
  it('empty input short-circuits without touching the db', async () => {
    const result = await bulkUpsertAuditSummaries([]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({ attempted: 0, upserted: 0, skipped: 0 });
    expect(dbMock).not.toHaveBeenCalled();
  });

  it('upserts on the 4-column natural key with a precedence guard, excluding key columns from set', async () => {
    const chain = mockUpdateChain([{ id: 'a' }, { id: 'b' }]);
    const result = await bulkUpsertAuditSummaries([summaryRow, summaryRow]);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({ attempted: 2, upserted: 2, skipped: 0 });
    expect(chain.values).toHaveBeenCalledWith([summaryRow, summaryRow]);

    const arg = chain.captured;
    expect(arg).toBeDefined();
    expect(arg?.target.map((c) => c.name)).toEqual([
      'audit_subject_class',
      'audited_entity_id',
      'aggregate_scope',
      'fiscal_year_bs',
    ]);
    // Precedence guard must be present — distinguishes this from a blind upsert.
    expect(arg?.setWhere).toBeDefined();
    // The natural-key columns and the PK are never overwritten from excluded.
    for (const key of [
      'auditSubjectClass',
      'auditedEntityId',
      'aggregateScope',
      'fiscalYearBs',
      'id',
    ]) {
      expect(arg?.set).not.toHaveProperty(key);
    }
    // But the value + provenance columns ARE overwritten.
    expect(arg?.set).toHaveProperty('berujuRaisedNpr');
    expect(arg?.set).toHaveProperty('confidenceGrade');
    expect(arg?.set).toHaveProperty('sourceDocumentId');
  });

  it('reports skipped rows when fewer come back than were attempted', async () => {
    mockUpdateChain([{ id: 'a' }]); // 1 of 2 won the precedence guard
    const result = await bulkUpsertAuditSummaries([summaryRow, summaryRow]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({ attempted: 2, upserted: 1, skipped: 1 });
  });

  it('translates a DB throw to QueryFailed', async () => {
    dbMock.mockReturnValue({
      insert: () => ({
        values: () => ({
          onConflictDoUpdate: () => ({ returning: () => Promise.reject(new Error('boom')) }),
        }),
      }),
    });
    const result = await bulkUpsertAuditSummaries([summaryRow]);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('QueryFailed');
  });
});

describe('bulkUpsertBerujuLines', () => {
  it('upserts on the collision-proof 9-column key (doc + role + source_table) with a precedence guard', async () => {
    const chain = mockUpdateChain([{ id: 'a' }]);
    const result = await bulkUpsertBerujuLines([lineRow]);
    expect(result.ok).toBe(true);
    expect(chain.captured?.target.map((c) => c.name)).toEqual([
      'source_document_id',
      'audit_subject_class',
      'audited_entity_id',
      'aggregate_scope',
      'fiscal_year_bs',
      'amount_basis',
      'beruju_category',
      'aggregation_role',
      'source_table_code',
    ]);
    expect(chain.captured?.setWhere).toBeDefined();
    expect(chain.captured?.set).toHaveProperty('amountNpr');
    expect(chain.captured?.set).toHaveProperty('valueOrigin');
    // Key columns are never overwritten from excluded.
    expect(chain.captured?.set).not.toHaveProperty('berujuCategory');
    expect(chain.captured?.set).not.toHaveProperty('aggregationRole');
    expect(chain.captured?.set).not.toHaveProperty('sourceTableCode');
  });

  it('empty input short-circuits', async () => {
    const result = await bulkUpsertBerujuLines([]);
    expect(result.ok).toBe(true);
    expect(dbMock).not.toHaveBeenCalled();
  });
});

describe('bulkUpsertFinancialStocks', () => {
  it('upserts on the document-scoped stock key with a precedence guard', async () => {
    const chain = mockUpdateChain([{ id: 'a' }]);
    const result = await bulkUpsertFinancialStocks([stockRow]);
    expect(result.ok).toBe(true);
    expect(chain.captured?.target.map((c) => c.name)).toEqual([
      'source_document_id',
      'audit_subject_class',
      'audited_entity_id',
      'aggregate_scope',
      'fiscal_year_bs',
      'stock_type',
    ]);
    expect(chain.captured?.setWhere).toBeDefined();
    expect(chain.captured?.set).toHaveProperty('closingNpr');
    expect(chain.captured?.set).not.toHaveProperty('stockType');
  });

  it('empty input short-circuits', async () => {
    const result = await bulkUpsertFinancialStocks([]);
    expect(result.ok).toBe(true);
    expect(dbMock).not.toHaveBeenCalled();
  });
});

describe('bulkUpsertParagraphMetrics', () => {
  it('upserts on the document-scoped paragraph-status key with a precedence guard', async () => {
    const chain = mockUpdateChain([{ id: 'a' }]);
    const result = await bulkUpsertParagraphMetrics([metricRow]);
    expect(result.ok).toBe(true);
    expect(chain.captured?.target.map((c) => c.name)).toEqual([
      'source_document_id',
      'audit_subject_class',
      'audited_entity_id',
      'aggregate_scope',
      'fiscal_year_bs',
      'paragraph_status',
    ]);
    expect(chain.captured?.setWhere).toBeDefined();
    expect(chain.captured?.set).toHaveProperty('paragraphCount');
    expect(chain.captured?.set).not.toHaveProperty('paragraphStatus');
  });

  it('empty input short-circuits', async () => {
    const result = await bulkUpsertParagraphMetrics([]);
    expect(result.ok).toBe(true);
    expect(dbMock).not.toHaveBeenCalled();
  });
});

describe('bulkInsertAuditFindings', () => {
  it('inserts document-scoped with DO NOTHING on the ordinal key (no precedence guard)', async () => {
    let captured: { target: { name: string }[] } | undefined;
    const returning = vi.fn(() => Promise.resolve([{ id: 'a' }]));
    const onConflictDoNothing = vi.fn((arg: { target: { name: string }[] }) => {
      captured = arg;
      return { returning };
    });
    const values = vi.fn(() => ({ onConflictDoNothing }));
    dbMock.mockReturnValue({ insert: () => ({ values }) });

    const result = await bulkInsertAuditFindings([findingRow]);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({ attempted: 1, upserted: 1, skipped: 0 });
    expect(captured?.target.map((c) => c.name)).toEqual([
      'source_document_id',
      'audited_entity_id',
      'fiscal_year_bs',
      'finding_ordinal',
    ]);
  });

  it('empty input short-circuits', async () => {
    const result = await bulkInsertAuditFindings([]);
    expect(result.ok).toBe(true);
    expect(dbMock).not.toHaveBeenCalled();
  });
});
