/**
 * Date / period types. BsDate uses fiscal-year month order (Shrawan=1),
 * distinct from the calendar order used by `nepali-date-converter`.
 * Bridge lives in `bs-ad.ts`. See docs/CALENDAR_AND_PERIODS.md.
 */

import type { ReportingPeriodType } from '@/lib/db/schema/enums';

export type BsDate = { year: number; month: number; day: number };
export type AdDate = Date;
export type FiscalYear = { startYearBs: number; endYearBs: number };
export type PeriodType = ReportingPeriodType;
export type Period = {
  type: PeriodType;
  fiscalYear: FiscalYear;
  bsLabel: string;
  adStart: Date;
  adEnd: Date;
};
