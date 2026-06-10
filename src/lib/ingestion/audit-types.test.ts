/**
 * Vitest suite for the OAG audit parser-output contract (audit-types.ts).
 *
 * Pure schema tests — no DB, no env. Pins the two boundary invariants
 * (raw-provenance-when-amount-present, explicit confidence) plus enum/identity
 * shape and the full parser-output + validation-report envelopes.
 */

import { describe, expect, it } from 'vitest';

import {
  AuditBerujuLineDraftSchema,
  AuditFindingDraftSchema,
  AuditParserOutputSchema,
  AuditSummaryDraftSchema,
  AuditValidationReportSchema,
} from './audit-types';

const DOC = '11111111-1111-4111-8111-111111111111';
const ENTITY = '22222222-2222-4222-8222-222222222222';

const baseProvenance = {
  source_document_id: DOC,
  source_precedence: 1,
  extraction_method: 'text_layer',
  confidence_grade: 'A',
  promoted_by: 'test',
} as const;

const validSummary = {
  audited_entity_id: null,
  audit_subject_class: 'federal_government',
  aggregate_scope: 'all_federal_offices',
  fiscal_year_bs: '2079/80',
  beruju_raised_npr: '236000000000.00',
  beruju_raised_raw: '२३६ अर्ब',
  ...baseProvenance,
};

const validLine = {
  audited_entity_id: null,
  audit_subject_class: 'local_government',
  aggregate_scope: 'all_local_levels',
  fiscal_year_bs: '2079/80',
  amount_basis: 'current_year_raised',
  beruju_category: 'recoverable',
  amount_npr: '193000000000.00',
  amount_raw: '१९३ अर्ब',
  ...baseProvenance,
};

const validFinding = {
  audited_entity_id: ENTITY,
  audit_subject_class: 'local_government',
  fiscal_year_bs: '2079/80',
  finding_ordinal: 1,
  source_locator_hash: 'h1',
  ...baseProvenance,
  confidence_grade: 'B',
  extraction_method: 'surya_ocr',
};

describe('AuditSummaryDraftSchema', () => {
  it('accepts a well-formed aggregate summary', () => {
    expect(AuditSummaryDraftSchema.safeParse(validSummary).success).toBe(true);
  });

  it('rejects a normalized amount without its raw expression', () => {
    const noRaw = {
      audited_entity_id: null,
      audit_subject_class: 'federal_government',
      fiscal_year_bs: '2079/80',
      beruju_raised_npr: '236000000000.00', // no beruju_raised_raw
      ...baseProvenance,
    };
    const r = AuditSummaryDraftSchema.safeParse(noRaw);
    expect(r.success).toBe(false);
    if (r.success) return;
    expect(r.error.issues.some((i) => i.path.includes('beruju_raised_raw'))).toBe(true);
  });

  it('rejects a row missing confidence_grade (no silent A)', () => {
    const noConf = {
      audited_entity_id: null,
      audit_subject_class: 'federal_government',
      fiscal_year_bs: '2079/80',
      beruju_raised_npr: '236000000000.00',
      beruju_raised_raw: '२३६ अर्ब',
      source_document_id: DOC,
      source_precedence: 1,
      extraction_method: 'text_layer',
      promoted_by: 'test', // no confidence_grade
    };
    expect(AuditSummaryDraftSchema.safeParse(noConf).success).toBe(false);
  });
});

describe('AuditBerujuLineDraftSchema', () => {
  it('accepts a well-formed line', () => {
    expect(AuditBerujuLineDraftSchema.safeParse(validLine).success).toBe(true);
  });

  it('rejects an unknown amount_basis', () => {
    expect(
      AuditBerujuLineDraftSchema.safeParse({ ...validLine, amount_basis: 'nope' }).success,
    ).toBe(false);
  });

  it('rejects a non-decimal amount_npr', () => {
    expect(
      AuditBerujuLineDraftSchema.safeParse({ ...validLine, amount_npr: 'रु. हजार' }).success,
    ).toBe(false);
  });
});

describe('AuditFindingDraftSchema', () => {
  it('accepts findings with repeated / missing para_ref (identity is ordinal + hash)', () => {
    const a = { ...validFinding, finding_ordinal: 1, source_locator_hash: 'h1', para_ref: '12' };
    const b = { ...validFinding, finding_ordinal: 2, source_locator_hash: 'h2', para_ref: '12' };
    const c = { ...validFinding, finding_ordinal: 3, source_locator_hash: 'h3' }; // no para_ref
    expect(AuditFindingDraftSchema.safeParse(a).success).toBe(true);
    expect(AuditFindingDraftSchema.safeParse(b).success).toBe(true);
    expect(AuditFindingDraftSchema.safeParse(c).success).toBe(true);
  });

  it('rejects a finding amount without its raw expression', () => {
    const r = AuditFindingDraftSchema.safeParse({ ...validFinding, amount_npr: '5000.00' });
    expect(r.success).toBe(false);
  });
});

describe('AuditParserOutputSchema', () => {
  it('parses a full envelope', () => {
    const out = {
      status: 'success',
      parser_version: '0.1.0',
      source_id: 'oag-audit-reports',
      source_document_id: DOC,
      fiscal_year_bs: '2079/80',
      summaries: [validSummary],
      beruju_lines: [validLine],
      findings: [validFinding],
      errors: [],
    };
    expect(AuditParserOutputSchema.safeParse(out).success).toBe(true);
  });
});

describe('AuditValidationReportSchema', () => {
  it('parses a PASS report', () => {
    const report = {
      document_id: DOC,
      source_id: 'oag-audit-reports',
      fiscal_year_bs: '2079/80',
      extraction_method_distribution: { text_layer: 10 },
      confidence_grade_distribution: { A: 10 },
      rows_extracted: { summaries: 5, beruju_lines: 20, findings: 12 },
      unresolved_entity_count: 0,
      parked_entity_count: 0,
      flagged_ocr_disagreement_count: 0,
      category_to_summary: [
        {
          scope: 'beruju by category → summary',
          raw_printed_total: '236000000000.00',
          computed_extracted_total: '236000000000.00',
          variance_npr: '0.00',
          passed: true,
        },
      ],
      entity_to_aggregate: [],
      aggregate_to_grand_total: [],
      decision: 'PASS',
    };
    expect(AuditValidationReportSchema.safeParse(report).success).toBe(true);
  });

  it('rejects an unknown decision', () => {
    const bad = { decision: 'MAYBE' };
    expect(AuditValidationReportSchema.safeParse(bad).success).toBe(false);
  });
});
