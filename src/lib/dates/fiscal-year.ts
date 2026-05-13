/**
 * Fiscal-year arithmetic. FY runs Shrawan 1 → Ashadh 31 (mid-July to mid-July AD).
 * Labels per docs/CALENDAR_AND_PERIODS.md: BS "2082/83", AD context "2025/26".
 */

import type { BsDate, FiscalYear } from './types';
import { adToBs } from './bs-ad';

export function fiscalYearForBsDate(bs: BsDate): FiscalYear {
  // FY months 1..9 (Shrawan..Chait) live in the start BS year;
  // 10..12 (Baisakh..Ashadh) in the end BS year of the same FY.
  const startYearBs = bs.month <= 9 ? bs.year : bs.year - 1;
  return { startYearBs, endYearBs: startYearBs + 1 };
}

export const fiscalYearForAdDate = (ad: Date): FiscalYear => fiscalYearForBsDate(adToBs(ad));

export const formatFiscalYearBs = (fy: FiscalYear): string =>
  `${fy.startYearBs}/${String(fy.endYearBs).slice(-2)}`;

export function formatFiscalYearAdLabel(fy: FiscalYear): string {
  const adStart = fy.startYearBs - 57;
  return `${adStart}/${String((adStart + 1) % 100).padStart(2, '0')}`;
}
