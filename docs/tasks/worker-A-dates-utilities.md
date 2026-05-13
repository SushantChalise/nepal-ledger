# Worker A — Date / Period Utilities (BS ↔ AD, fiscal year, period math)

**Spawn type:** `general-purpose`
**Plan mode:** required (touches >3 files)
**Worktree:** not needed; scope fence is isolated
**Diff cap:** 300 lines

---

## Goal

Build the `src/lib/dates/` module that every later feature relies on for Nepali calendar handling. Per `docs/CALENDAR_AND_PERIODS.md` this is the **only** place BS↔AD conversion is allowed; inlining the formula elsewhere is rejected at review.

Done = `pnpm typecheck`, `pnpm lint`, `pnpm test --run` all green; the wrapper provides `bsToAd`, `adToBs`, fiscal-year helpers, period helpers (incl. `nine_months_cumulative`), and a `format` namespace; tests cover FY boundary, leap-year, and the existing CMEFs 2082/83 nine-month case.

## Why

Day 4–6 milestone tail. Schema is in (PR #3). The parser, repositories, Pulse, Money Map, and Fact Ledger all need this module before they can compute or display a period. Without it every consumer would reinvent BS arithmetic and the Fact Ledger would silently mix conventions.

## Scope Fence (files this worker MAY touch)

Create:
- `src/lib/dates/index.ts` — public surface: `bsToAd`, `adToBs`, `currentFiscalYear`, `fiscalYearForAdDate`, `periodAdRange`, `parseReportingPeriod`
- `src/lib/dates/bs-ad.ts` — wrapper around `nepali-date-converter` (install via Mother, see below)
- `src/lib/dates/fiscal-year.ts` — FY arithmetic (Shrawan 1 → Ashadh 31)
- `src/lib/dates/period.ts` — period-type math: given (year_bs, period_type) → AD start/end
- `src/lib/dates/format.ts` — display helpers (English/Nepali, table/chart/Fact Ledger formats)
- `src/lib/dates/nepali-months.ts` — canonical month vocab (Shrawan…Ashadh) + transliteration aliases
- `src/lib/dates/types.ts` — `BsDate`, `AdDate`, `FiscalYear`, `Period`, `PeriodType` types
- `src/lib/dates/index.test.ts` — Vitest suite covering everything in this brief

Edit:
- None outside `src/lib/dates/`

**Out of scope (must NOT touch):**
- `package.json` / `pnpm-lock.yaml` — Mother adds `nepali-date-converter` for you before you start
- Any other `src/lib/*` paths
- Schemas (already locked in PR #3)
- `tsconfig.json`, `next.config.ts`, CI workflows

## Context to Read First (in order)

1. `docs/CALENDAR_AND_PERIODS.md` — the canonical spec. Every requirement in this brief traces back to it.
2. `docs/CONVENTIONS.md` §"TypeScript" + §"Testing" — no `any`, no unsanctioned `as`, named exports, Vitest shape.
3. `docs/CONTEXT_RULES.md` — Six Rules; especially Type-Driven (Zod-derived types where applicable) and No Silent Failure.
4. `src/lib/errors.ts` — use `Result<T>` for any function that can fail to parse (e.g. unrecognized month name).
5. `src/lib/db/schema/enums.ts` — your `PeriodType` must match the `reportingPeriodTypeEnum` literal union exactly.

## API Contract (target shape)

```typescript
// src/lib/dates/types.ts
export type BsDate = { year: number; month: number; day: number }; // month 1..12 (Shrawan=1...Ashadh=12)
export type FiscalYear = { startYearBs: number; endYearBs: number }; // FY 2082/83 = { startYearBs: 2082, endYearBs: 2083 }
export type PeriodType =
  | 'monthly' | 'quarterly' | 'annual'
  | 'nine_months_cumulative' | 'year_to_date'
  | 'daily' | 'seasonal';
export type Period = {
  type: PeriodType;
  fiscalYear: FiscalYear;
  bsLabel: string;          // e.g. "Chait 2082" or "FY 2082/83 9M"
  adStart: Date;
  adEnd: Date;              // inclusive of last day
};

// src/lib/dates/index.ts
export function bsToAd(bs: BsDate): Date;
export function adToBs(ad: Date): BsDate;

export function fiscalYearForAdDate(ad: Date): FiscalYear;
export function fiscalYearForBsDate(bs: BsDate): FiscalYear;
export function formatFiscalYearBs(fy: FiscalYear): string;     // "2082/83"
export function formatFiscalYearAdLabel(fy: FiscalYear): string; // "2025/26"

export function periodAdRange(args: { fiscalYear: FiscalYear; type: PeriodType; ordinal?: number; }): Result<{ adStart: Date; adEnd: Date; bsLabel: string }>;
// For monthly: ordinal=1..12 maps to Shrawan..Ashadh
// For quarterly: ordinal=1..4
// For nine_months_cumulative: ordinal ignored; spans Shrawan..Chait
// For annual: ordinal ignored; spans full FY
// For year_to_date: ordinal=1..12, span Shrawan..ordinal-month

export function parseReportingPeriod(label: string): Result<Period>;
// Accepts the strings the NRB documents use:
//   "Nine-Months 2082/83"
//   "FY 2082/83"
//   "Chait 2082"
//   "Mid-Chait 2082"
//   "Q3 FY 2082/83"
//   "2082/83"
// Tolerant to whitespace and case; returns ParseFailed on unrecognized.

// src/lib/dates/format.ts
export const format = {
  bsLabelEn: (period: Period) => string,
  bsLabelNe: (period: Period) => string,
  chartAxis: (period: Period) => string,
  tableHeaderEn: (period: Period) => string,
  factLedger: (period: Period) => string,
};
```

## Required Test Cases (`index.test.ts`)

Use the explicit-`now` injection pattern — never `new Date()` without a fixture.

- `bsToAd / adToBs` round-trip for at least 6 BS dates across different years
- BS leap-year edge: a year where Ashadh has 32 days
- Fiscal-year boundary: Ashadh 31, 2083 BS → mid-July 2026 (within FY 2082/83), and Shrawan 1, 2083 BS → next day → FY 2083/84
- Nine-months cumulative for FY 2082/83: spans Shrawan 1, 2082 BS → Chait 31, 2082 BS (≈ mid-July 2025 → mid-April 2026 AD)
- Quarterly Q1/Q2/Q3/Q4 boundaries for FY 2082/83 match Shrawan–Ashwin / Kartik–Poush / Magh–Chait / Baisakh–Ashadh
- `parseReportingPeriod` happy-path for each NRB label form
- `parseReportingPeriod` returns `Result.err({ kind: 'ParseFailed', ... })` on garbage input
- `format.factLedger` matches the example in CALENDAR_AND_PERIODS.md exactly: `"Published: Baisakh 25, 2083 BS (May 8, 2026 AD). Period: FY 2082/83 9M (Shrawan–Chait)."`

## Acceptance Criteria

- [ ] Files in scope only (`git diff --name-only main`)
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` — all new tests pass; existing 20 still pass
- [ ] No new dependencies
- [ ] No `as` casts outside `src/lib/external/*` (and we have none here — your one library wrap is `nepali-date-converter`, which is fine)
- [ ] No `any`, no `@ts-ignore`
- [ ] Diff under 300 lines total
- [ ] No comments restating code
- [ ] `parseReportingPeriod` covers every label form the existing NRB CSV/PDF use (read `NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv` first — its header rows tell you the label conventions)

## What to Return

1. Summary of changes (≤10 bullets)
2. Acceptance-criteria checklist with checkmarks
3. `git diff --stat main` output proving the scope fence
4. Any deviations from this brief and why
5. Open questions for Mother
6. Suggested commit message in conventional format
