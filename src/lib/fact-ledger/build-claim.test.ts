import { describe, expect, it } from 'vitest';

import { bsToAd } from '@/lib/dates';

import { buildClaimDraftFromIndicatorValue, type BuildInput } from './build-claim';
import { validateClaimDraft } from './schemas';

const INDICATOR_ID = '11111111-1111-4111-8111-111111111111';
const VALUE_ID = '22222222-2222-4222-8222-222222222222';
const SOURCE_DOC_ID = '33333333-3333-4333-8333-333333333333';

const baseInput = (): BuildInput => ({
  indicator: {
    id: INDICATOR_ID,
    slug: 'ncpi-overall-yoy',
    nameEn: 'NCPI overall YoY inflation',
    nameNe: null,
    unit: 'percent',
    sourceAgency: 'Nepal Rastra Bank',
  },
  value: {
    id: VALUE_ID,
    value: '3.13',
    unit: 'percent',
    reportingPeriodType: 'nine_months_cumulative',
    reportingPeriodBs: 'FY 2082/83 9M',
    reportingPeriodAdStart: bsToAd({ year: 2082, month: 1, day: 1 }),
    reportingPeriodAdEnd: bsToAd({ year: 2083, month: 9, day: 30 }),
    publicationDateAd: bsToAd({ year: 2083, month: 10, day: 25 }),
    publicationDateBs: 'Baisakh 25, 2083',
    fiscalYearBs: '2082/83',
    confidenceGrade: 'A',
  },
  sourceDocument: { id: SOURCE_DOC_ID },
  verifiedBy: 'sushant@nepal-ledger',
});

describe('buildClaimDraftFromIndicatorValue', () => {
  it('happy path: NCPI 9M FY 2082/83 with confidence A', () => {
    const r = buildClaimDraftFromIndicatorValue(baseInput());
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.slug).toBe('ncpi-overall-yoy-2082-83-nine-months-cumulative');
    expect(r.value.textEn).toBe(
      'NCPI overall YoY inflation for FY 2082/83 9M (Shrawan–Chait): 3.13 percent.',
    );
    expect(r.value.textNe).toBeNull();
    expect(r.value.confidenceGrade).toBe('A');
    expect(r.value.indicatorId).toBe(INDICATOR_ID);
    expect(r.value.indicatorValueId).toBe(VALUE_ID);
    expect(r.value.sourceDocumentId).toBe(SOURCE_DOC_ID);
    expect(r.value.reportingPeriodLabel).toBe('FY 2082/83 9M (Shrawan–Chait)');
  });

  it('bilingual: nameNe set → textNe rendered with Nepali template', () => {
    const input = baseInput();
    input.indicator.nameNe = 'राष्ट्रिय उपभोक्ता मूल्य सूचकाङ्क वार्षिक मुद्रास्फीति';
    const r = buildClaimDraftFromIndicatorValue(input);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.textNe).toBe(
      'राष्ट्रिय उपभोक्ता मूल्य सूचकाङ्क वार्षिक मुद्रास्फीति FY 2082/83 9M (Shrawan–Chait): 3.13 percent।',
    );
    expect(r.value.textEn).toContain('NCPI overall YoY inflation');
  });

  it('provisional: FCGO-style row (grade C + "Preliminary" agency) appends suffix', () => {
    const input = baseInput();
    input.indicator.sourceAgency = 'FCGO (Preliminary)';
    input.value.confidenceGrade = 'C';
    input.value.value = '425000.5';
    const r = buildClaimDraftFromIndicatorValue(input);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.textEn.endsWith(' (provisional)')).toBe(true);
    expect(r.value.textEn).toContain('425,000.5 percent');
  });

  it('validation: empty verifiedBy → Validation error on field "verifiedBy"', () => {
    const input = baseInput();
    input.verifiedBy = '   ';
    const r = buildClaimDraftFromIndicatorValue(input);
    expect(r.ok).toBe(false);
    if (r.ok) return;
    expect(r.error.kind).toBe('Validation');
    if (r.error.kind === 'Validation') expect(r.error.field).toBe('verifiedBy');
  });

  it('validation: non-numeric value.value → Validation error on field "value.value"', () => {
    const input = baseInput();
    input.value.value = 'not-a-number';
    const r = buildClaimDraftFromIndicatorValue(input);
    expect(r.ok).toBe(false);
    if (r.ok) return;
    expect(r.error.kind).toBe('Validation');
    if (r.error.kind === 'Validation') expect(r.error.field).toBe('value.value');
  });

  it('validateClaimDraft accepts a well-formed object and rejects shape drift', () => {
    const r = buildClaimDraftFromIndicatorValue(baseInput());
    expect(r.ok).toBe(true);
    if (!r.ok) return;

    const accepted = validateClaimDraft(r.value);
    expect(accepted.ok).toBe(true);

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { slug: _omit, ...withoutSlug } = r.value;
    const rejected = validateClaimDraft(withoutSlug);
    expect(rejected.ok).toBe(false);
    if (rejected.ok) return;
    expect(rejected.error.kind).toBe('Validation');
    if (rejected.error.kind === 'Validation') expect(rejected.error.field).toBe('slug');
  });
});
