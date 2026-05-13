/**
 * Period-type math: (fiscalYear, periodType, ordinal) → inclusive AD range + BS label.
 * Semantics per docs/CALENDAR_AND_PERIODS.md "Period Type Definitions".
 */

import { err, ok, type Result } from '@/lib/errors';

import type { FiscalYear, PeriodType } from './types';
import { bsToAd } from './bs-ad';
import { FY_MONTHS_EN } from './nepali-months';
import { formatFiscalYearBs } from './fiscal-year';

const MS_PER_DAY = 86_400_000;

// Shrawan..Chait (FY months 1..9) live in the start BS year; Baisakh..Ashadh (10..12) in the end.
const bsYearForFyMonth = (fy: FiscalYear, m: number): number =>
  m <= 9 ? fy.startYearBs : fy.endYearBs;

const monthStartAd = (fy: FiscalYear, m: number): Date =>
  bsToAd({ year: bsYearForFyMonth(fy, m), month: m, day: 1 });

function monthEndAd(fy: FiscalYear, m: number): Date {
  const nextM = m === 12 ? 1 : m + 1;
  const nextFy: FiscalYear =
    m === 12 ? { startYearBs: fy.endYearBs, endYearBs: fy.endYearBs + 1 } : fy;
  return new Date(monthStartAd(nextFy, nextM).getTime() - MS_PER_DAY);
}

type PeriodRange = { adStart: Date; adEnd: Date; bsLabel: string };

const validation = (field: string, reason: string): Result<PeriodRange> =>
  err({ kind: 'Validation', field, reason });

export function periodAdRange(args: {
  fiscalYear: FiscalYear;
  type: PeriodType;
  ordinal?: number;
}): Result<PeriodRange> {
  const { fiscalYear: fy, type, ordinal } = args;
  const fyLabel = formatFiscalYearBs(fy);

  switch (type) {
    case 'monthly': {
      if (ordinal === undefined || ordinal < 1 || ordinal > 12)
        return validation('ordinal', `monthly requires ordinal 1..12; got ${ordinal}`);
      const monthName = FY_MONTHS_EN[ordinal - 1];
      return ok({
        adStart: monthStartAd(fy, ordinal),
        adEnd: monthEndAd(fy, ordinal),
        bsLabel: `${monthName} ${bsYearForFyMonth(fy, ordinal)}`,
      });
    }
    case 'quarterly': {
      if (ordinal === undefined || ordinal < 1 || ordinal > 4)
        return validation('ordinal', `quarterly requires ordinal 1..4; got ${ordinal}`);
      const first = (ordinal - 1) * 3 + 1;
      return ok({
        adStart: monthStartAd(fy, first),
        adEnd: monthEndAd(fy, first + 2),
        bsLabel: `Q${ordinal} FY ${fyLabel}`,
      });
    }
    case 'annual':
      return ok({
        adStart: monthStartAd(fy, 1),
        adEnd: monthEndAd(fy, 12),
        bsLabel: `FY ${fyLabel}`,
      });
    case 'nine_months_cumulative':
      return ok({
        adStart: monthStartAd(fy, 1),
        adEnd: monthEndAd(fy, 9),
        bsLabel: `FY ${fyLabel} 9M`,
      });
    case 'year_to_date': {
      if (ordinal === undefined || ordinal < 1 || ordinal > 12)
        return validation('ordinal', `year_to_date requires ordinal 1..12; got ${ordinal}`);
      return ok({
        adStart: monthStartAd(fy, 1),
        adEnd: monthEndAd(fy, ordinal),
        bsLabel: `FY ${fyLabel} YTD ${FY_MONTHS_EN[ordinal - 1]}`,
      });
    }
    case 'daily':
    case 'seasonal':
      return validation('type', `${type} not produced by periodAdRange; use specialized helper`);
  }
}
