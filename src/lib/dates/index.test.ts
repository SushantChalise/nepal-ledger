import { describe, expect, it } from 'vitest';

import {
  adToBs,
  bsToAd,
  currentFiscalYear,
  fiscalYearForAdDate,
  fiscalYearForBsDate,
  format,
  formatFactLedgerEntry,
  formatFiscalYearAdLabel,
  formatFiscalYearBs,
  parseReportingPeriod,
  periodAdRange,
  type Period,
} from './index';

const FY_2082 = { startYearBs: 2082, endYearBs: 2083 };
const MS_PER_DAY = 86_400_000;

describe('bs ↔ ad round-trip', () => {
  it.each([
    { year: 2082, month: 1, day: 1 },
    { year: 2082, month: 9, day: 15 },
    { year: 2083, month: 12, day: 30 },
    { year: 2080, month: 6, day: 10 },
    { year: 2079, month: 4, day: 28 },
    { year: 2078, month: 11, day: 5 },
  ])('round-trips %j', (bs) => {
    expect(adToBs(bsToAd(bs))).toEqual(bs);
  });

  it('accepts BS leap-year Ashadh 32 (BS 2079 Asar has 32 days)', () => {
    const bs = { year: 2079, month: 12, day: 32 };
    expect(adToBs(bsToAd(bs))).toEqual(bs);
  });
});

describe('fiscal-year', () => {
  it('Ashadh 31, 2083 BS lives in FY 2082/83', () => {
    expect(fiscalYearForBsDate({ year: 2083, month: 12, day: 31 })).toEqual(FY_2082);
  });
  it('Shrawan 1, 2083 BS starts FY 2083/84', () => {
    expect(fiscalYearForBsDate({ year: 2083, month: 1, day: 1 })).toEqual({
      startYearBs: 2083,
      endYearBs: 2084,
    });
  });
  it('mid-July 2026 AD falls in FY 2082/83 via AD path', () => {
    expect(fiscalYearForAdDate(new Date(Date.UTC(2026, 6, 10)))).toEqual(FY_2082);
  });
  it('currentFiscalYear honours injected now', () => {
    expect(currentFiscalYear(new Date(Date.UTC(2025, 9, 1)))).toEqual(FY_2082);
  });
  it('formats BS label as "2082/83"', () => {
    expect(formatFiscalYearBs(FY_2082)).toBe('2082/83');
  });
  it('formats AD context label as "2025/26"', () => {
    expect(formatFiscalYearAdLabel(FY_2082)).toBe('2025/26');
  });
});

describe('periodAdRange', () => {
  it('nine_months_cumulative covers Shrawan 2082 → Chait 2082', () => {
    const r = periodAdRange({ fiscalYear: FY_2082, type: 'nine_months_cumulative' });
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.adStart).toEqual(bsToAd({ year: 2082, month: 1, day: 1 }));
    expect(r.value.adEnd).toEqual(
      new Date(bsToAd({ year: 2083, month: 10, day: 1 }).getTime() - MS_PER_DAY),
    );
    expect(r.value.bsLabel).toBe('FY 2082/83 9M');
    expect(r.value.adStart.getUTCFullYear()).toBe(2025);
    expect(r.value.adEnd.getUTCFullYear()).toBe(2026);
  });

  it('annual spans Shrawan 2082 → Ashadh 2083', () => {
    const r = periodAdRange({ fiscalYear: FY_2082, type: 'annual' });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.bsLabel).toBe('FY 2082/83');
  });

  it.each([
    [1, 1],
    [2, 4],
    [3, 7],
    [4, 10],
  ])('quarter Q%i starts at FY month %i', (q, first) => {
    const r = periodAdRange({ fiscalYear: FY_2082, type: 'quarterly', ordinal: q });
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(adToBs(r.value.adStart).month).toBe(first);
    expect(r.value.bsLabel).toBe(`Q${q} FY 2082/83`);
  });

  it('monthly Chait yields "Chait 2082"', () => {
    const r = periodAdRange({ fiscalYear: FY_2082, type: 'monthly', ordinal: 9 });
    expect(r.ok && r.value.bsLabel).toBe('Chait 2082');
  });

  it('rejects monthly with missing ordinal', () => {
    expect(periodAdRange({ fiscalYear: FY_2082, type: 'monthly' }).ok).toBe(false);
  });
});

describe('parseReportingPeriod', () => {
  it.each([
    ['Nine-Months 2082/83', 'nine_months_cumulative', 'FY 2082/83 9M'],
    ['FY 2082/83', 'annual', 'FY 2082/83'],
    ['2082/83', 'annual', 'FY 2082/83'],
    ['Chait 2082', 'monthly', 'Chait 2082'],
    ['Mid-Chait 2082', 'monthly', 'Chait 2082'],
    ['Q3 FY 2082/83', 'quarterly', 'Q3 FY 2082/83'],
  ])('parses %s → %s', (label, type, bsLabel) => {
    const r = parseReportingPeriod(label);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.type).toBe(type);
    expect(r.value.bsLabel).toBe(bsLabel);
  });

  it('rejects garbage input as ParseFailed', () => {
    const r = parseReportingPeriod('not a date at all');
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.kind).toBe('ParseFailed');
  });
  it('rejects empty input', () => {
    expect(parseReportingPeriod('   ').ok).toBe(false);
  });
});

describe('format', () => {
  it('formatFactLedgerEntry matches the canonical example exactly', () => {
    const period: Period = {
      type: 'nine_months_cumulative',
      fiscalYear: FY_2082,
      bsLabel: 'FY 2082/83 9M',
      adStart: bsToAd({ year: 2082, month: 1, day: 1 }),
      adEnd: new Date(bsToAd({ year: 2083, month: 10, day: 1 }).getTime() - MS_PER_DAY),
    };
    const publishedAd = bsToAd({ year: 2083, month: 10, day: 25 });
    expect(formatFactLedgerEntry({ publishedAd, period })).toBe(
      'Published: Baisakh 25, 2083 BS (May 8, 2026 AD). Period: FY 2082/83 9M (Shrawan–Chait).',
    );
  });

  it('bsLabelEn substitutes long form for nine-month', () => {
    const r = parseReportingPeriod('Nine-Months 2082/83');
    expect(r.ok).toBe(true);
    if (r.ok) expect(format.bsLabelEn(r.value)).toBe('FY 2082/83 9M (Shrawan–Chait)');
  });
});
