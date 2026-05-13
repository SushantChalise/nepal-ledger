/**
 * Public surface for src/lib/dates. Canonical entry point for every
 * BS-AD conversion, fiscal-year derivation, period range, and
 * reporting-period label parse. See docs/CALENDAR_AND_PERIODS.md.
 */

import { err, ok, type Result } from '@/lib/errors';

import type { FiscalYear, Period, PeriodType } from './types';
import { fiscalYearForAdDate } from './fiscal-year';
import { FY_MONTHS_EN, normalizeMonthName } from './nepali-months';
import { periodAdRange } from './period';

export { bsToAd, adToBs } from './bs-ad';
export {
  fiscalYearForBsDate,
  fiscalYearForAdDate,
  formatFiscalYearBs,
  formatFiscalYearAdLabel,
} from './fiscal-year';
export { periodAdRange } from './period';
export { format, formatFactLedgerEntry } from './format';
export { FY_MONTHS_EN, FY_MONTHS_NE, normalizeMonthName } from './nepali-months';
export type { BsDate, AdDate, FiscalYear, Period, PeriodType } from './types';

export const currentFiscalYear = (now: Date = new Date()): FiscalYear => fiscalYearForAdDate(now);

const FY_RE = /(\d{4})\s*\/\s*(\d{2,4})/;

function parseFyToken(s: string): FiscalYear | null {
  const m = FY_RE.exec(s);
  if (!m) return null;
  const start = Number(m[1]);
  const endRaw = m[2] ?? '';
  if (!Number.isFinite(start) || endRaw.length === 0) return null;
  const end = endRaw.length === 2 ? Math.floor(start / 100) * 100 + Number(endRaw) : Number(endRaw);
  return Number.isFinite(end) && end === start + 1 ? { startYearBs: start, endYearBs: end } : null;
}

function build(type: PeriodType, fy: FiscalYear, ordinal?: number): Result<Period> {
  const r = periodAdRange(
    ordinal === undefined ? { fiscalYear: fy, type } : { fiscalYear: fy, type, ordinal },
  );
  if (!r.ok) return r;
  return ok({ type, fiscalYear: fy, ...r.value });
}

const parseFail = (label: string, reason: string): Result<Period> =>
  err({ kind: 'ParseFailed', field: 'label', reason: `${reason} in "${label}"` });

export function parseReportingPeriod(label: string): Result<Period> {
  const raw = label.trim();
  if (raw.length === 0) return err({ kind: 'ParseFailed', field: 'label', reason: 'empty input' });
  const normalized = raw.replace(/\s+/g, ' ');
  const lower = normalized.toLowerCase();

  if (/^nine[\s-]?months?\b/.test(lower) || /\b9m\b/.test(lower)) {
    const fy = parseFyToken(normalized);
    return fy ? build('nine_months_cumulative', fy) : parseFail(label, 'no FY token');
  }

  const q = /\bq([1-4])\b/i.exec(normalized);
  if (q) {
    const fy = parseFyToken(normalized);
    return fy ? build('quarterly', fy, Number(q[1])) : parseFail(label, 'no FY token');
  }

  const mid = /^mid-([a-z]+)\s+(\d{4})$/i.exec(normalized);
  const month = mid ?? /^([a-zA-Z]+)\s+(\d{4})$/.exec(normalized);
  if (month) {
    const name = normalizeMonthName(month[1] ?? '');
    const year = Number(month[2]);
    if (name && Number.isFinite(year)) {
      const idx = FY_MONTHS_EN.indexOf(name) + 1;
      const startYearBs = idx <= 9 ? year : year - 1;
      return build('monthly', { startYearBs, endYearBs: startYearBs + 1 }, idx);
    }
    if (mid) return parseFail(label, 'unknown month or year');
  }

  if (/^fy\s/i.test(normalized) || FY_RE.test(normalized)) {
    const fy = parseFyToken(normalized);
    if (fy) return build('annual', fy);
  }
  return parseFail(label, 'unrecognized reporting-period label');
}
