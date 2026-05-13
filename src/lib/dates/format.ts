/**
 * Display helpers per docs/CALENDAR_AND_PERIODS.md §"Display Rules".
 * Every user-facing date string in the codebase routes through here.
 */

import type { Period } from './types';
import { adToBs } from './bs-ad';
import { FY_MONTHS_EN, FY_MONTHS_NE } from './nepali-months';
import { formatFiscalYearBs } from './fiscal-year';

const AD_SHORT = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

const adShort = (d: Date): string =>
  `${AD_SHORT[d.getUTCMonth()] ?? ''} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;

const nineMonthLabel = (p: Period, lang: 'en' | 'ne'): string =>
  lang === 'ne'
    ? `आ.व. ${formatFiscalYearBs(p.fiscalYear)} ९M (साउन–चैत)`
    : `FY ${formatFiscalYearBs(p.fiscalYear)} 9M (Shrawan–Chait)`;

export const format = {
  bsLabelEn: (p: Period): string =>
    p.type === 'nine_months_cumulative' ? nineMonthLabel(p, 'en') : p.bsLabel,
  bsLabelNe(p: Period): string {
    const fy = formatFiscalYearBs(p.fiscalYear);
    if (p.type === 'nine_months_cumulative') return nineMonthLabel(p, 'ne');
    if (p.type === 'monthly') {
      const bs = adToBs(p.adStart);
      return `${FY_MONTHS_NE[bs.month - 1] ?? ''} ${bs.year}`;
    }
    return `आ.व. ${fy}`;
  },
  chartAxis(p: Period): string {
    if (p.type !== 'monthly') return `FY ${formatFiscalYearBs(p.fiscalYear)}`;
    const bs = adToBs(p.adStart);
    return `${FY_MONTHS_EN[bs.month - 1] ?? ''} '${String(bs.year).slice(-2)}`;
  },
  tableHeaderEn(p: Period): string {
    const fy = formatFiscalYearBs(p.fiscalYear);
    if (p.type !== 'monthly') return `FY ${fy}`;
    const bs = adToBs(p.adStart);
    return `FY ${fy} ${FY_MONTHS_EN[bs.month - 1] ?? ''}`;
  },
  factLedger: (p: Period): string => `Period: ${format.bsLabelEn(p)}.`,
};

// Matches docs/CALENDAR_AND_PERIODS.md exact example:
// "Published: Baisakh 25, 2083 BS (May 8, 2026 AD). Period: FY 2082/83 9M (Shrawan–Chait)."
export function formatFactLedgerEntry(args: { publishedAd: Date; period: Period }): string {
  const bs = adToBs(args.publishedAd);
  const name = FY_MONTHS_EN[bs.month - 1] ?? '';
  return `Published: ${name} ${bs.day}, ${bs.year} BS (${adShort(args.publishedAd)} AD). ${format.factLedger(args.period)}`;
}
