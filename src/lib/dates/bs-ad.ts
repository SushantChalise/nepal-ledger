/**
 * Single sanctioned BS↔AD wrapper around `nepali-date-converter`.
 *
 * Anywhere else in the codebase that needs a conversion imports from
 * here; per docs/CALENDAR_AND_PERIODS.md inlining the formula is rejected
 * at review. BsDate uses fiscal-year month order (Shrawan=1); the library
 * uses calendar order (Baisakh=0). Translation lives in `nepali-months.ts`.
 */

import NepaliDate from 'nepali-date-converter';

import type { BsDate } from './types';
import { fyMonthFromLibraryMonth, libraryMonthFromFyMonth } from './nepali-months';

export function bsToAd(bs: BsDate): Date {
  const libMonth = libraryMonthFromFyMonth(bs.month);
  const nd = new NepaliDate(bs.year, libMonth, bs.day);
  const ad = nd.getAD();
  return new Date(Date.UTC(ad.year, ad.month, ad.date));
}

export function adToBs(ad: Date): BsDate {
  const utc = new Date(Date.UTC(ad.getUTCFullYear(), ad.getUTCMonth(), ad.getUTCDate()));
  const nd = new NepaliDate(utc);
  const bs = nd.getBS();
  return {
    year: bs.year,
    month: fyMonthFromLibraryMonth(bs.month),
    day: bs.date,
  };
}
