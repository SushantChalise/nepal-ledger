/**
 * Vitest suite for the DoFE migration-permit parser-output contract
 * (migration-permit-types.ts).
 *
 * Pure schema tests — no DB, no env. Pins the dimensional + count invariants:
 * marginal dimensions are `null` (not omitted), `sex` is required, `permits`
 * is a whole non-negative integer string, and the enum/identity shape.
 */

import { describe, expect, it } from 'vitest';

import { MigrationPermitFactInputSchema } from './migration-permit-types';

const DOC = '11111111-1111-4111-8111-111111111111';
const ENTITY = '22222222-2222-4222-8222-222222222222';

/** Fully-specified cell: one district, one country, one skill/category, male. */
const validFullCell = {
  fiscal_year_bs: '2080/81',
  month_num: 4,
  destination_country: 'Qatar',
  destination_region: 'middle_east',
  origin_entity_id: ENTITY,
  skill_class: 'semi_skilled',
  permit_category: 'new_individual',
  sex: 'male',
  permits: '1234',
  source_document_id: DOC,
  promoted_by: 'test',
};

/** All-Nepal annual total over every dimension — every nullable is null. */
const validMarginalRow = {
  fiscal_year_bs: '2080/81',
  month_num: null,
  destination_country: null,
  destination_region: null,
  origin_entity_id: null,
  skill_class: null,
  permit_category: null,
  sex: 'total',
  permits: '771327',
  source_document_id: DOC,
  promoted_by: 'test',
};

describe('MigrationPermitFactInputSchema', () => {
  it('accepts a fully-specified cell', () => {
    expect(MigrationPermitFactInputSchema.safeParse(validFullCell).success).toBe(true);
  });

  it('accepts a fully-marginal aggregate row (all nullable dims null, sex total)', () => {
    expect(MigrationPermitFactInputSchema.safeParse(validMarginalRow).success).toBe(true);
  });

  it('defaults unit to permits and confidence_grade to A', () => {
    const r = MigrationPermitFactInputSchema.safeParse(validFullCell);
    expect(r.success).toBe(true);
    if (!r.success) return;
    expect(r.data.unit).toBe('permits');
    expect(r.data.confidence_grade).toBe('A');
  });

  it('rejects a missing sex (no implicit aggregate)', () => {
    const noSex = {
      fiscal_year_bs: '2080/81',
      month_num: 4,
      destination_country: 'Qatar',
      destination_region: 'middle_east',
      origin_entity_id: ENTITY,
      skill_class: 'semi_skilled',
      permit_category: 'new_individual',
      permits: '1234',
      source_document_id: DOC,
      promoted_by: 'test',
    };
    expect(MigrationPermitFactInputSchema.safeParse(noSex).success).toBe(false);
  });

  it('rejects an unknown sex', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, sex: 'unknown' }).success,
    ).toBe(false);
  });

  it('rejects an unknown destination_region', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({
        ...validFullCell,
        destination_region: 'antarctica',
      }).success,
    ).toBe(false);
  });

  it('rejects an unknown skill_class', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, skill_class: 'wizard' }).success,
    ).toBe(false);
  });

  it('rejects an unknown permit_category', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, permit_category: 'lottery' })
        .success,
    ).toBe(false);
  });

  it('rejects a fractional / non-integer permits value', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, permits: '12.5' }).success,
    ).toBe(false);
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, permits: '-3' }).success,
    ).toBe(false);
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, permits: 1234 }).success,
    ).toBe(false);
  });

  it('rejects a month_num outside 1–12', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, month_num: 0 }).success,
    ).toBe(false);
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, month_num: 13 }).success,
    ).toBe(false);
  });

  it('rejects a non-uuid origin_entity_id', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, origin_entity_id: 'D-12' })
        .success,
    ).toBe(false);
  });

  it('rejects an empty fiscal_year_bs', () => {
    expect(
      MigrationPermitFactInputSchema.safeParse({ ...validFullCell, fiscal_year_bs: '' }).success,
    ).toBe(false);
  });
});
