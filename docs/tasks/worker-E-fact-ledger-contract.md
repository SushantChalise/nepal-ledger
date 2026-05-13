# Worker E — Fact Ledger Typed Contract (no UI)

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** 300 non-test source lines

---

## Goal

Build `src/lib/fact-ledger/` — the typed contract for Fact Ledger claims. Defines Zod schemas, derived types, and a server-side helper that turns an `approved_indicator_value` + `source_document` pair into a claim draft. No UI yet (wireframes pending).

Done = `pnpm typecheck`, `pnpm lint`, `pnpm test --run` green; the module exposes `ClaimDraftSchema`, `validateClaimDraft`, `buildClaimDraftFromIndicatorValue`, and Vitest covers each path.

## Why

Day 11–28 prep. The Fact Ledger is the project's moat (every claim is auditable). When the parser pipeline promotes an indicator value, we want to mint a claim draft from it deterministically — same value, same source document, same confidence → same claim string. Locking the contract here means the (future) UI just renders; it doesn't have to invent claim text on the client.

## Scope Fence (files this worker MAY touch)

Create:
- `src/lib/fact-ledger/schemas.ts` — Zod schemas for `ClaimDraft`, `ClaimSource`, `ConfidenceGrade`
- `src/lib/fact-ledger/types.ts` — derived TypeScript types
- `src/lib/fact-ledger/build-claim.ts` — `buildClaimDraftFromIndicatorValue({ indicator, value, sourceDocument, verifiedBy })` → `Result<ClaimDraft>`
- `src/lib/fact-ledger/build-claim.test.ts`
- `src/lib/fact-ledger/index.ts` — barrel

Edit:
- None outside `src/lib/fact-ledger/`

**Out of scope:**
- `package.json`, schemas, dates module (use it; don't modify), storage module, repositories, anything else

## Context to Read First

1. `docs/STRATEGY.md` §"The Visible Fact Ledger" — the why
2. `docs/CONTENT_FORMATS.md` if present — any claim-format precedents
3. `docs/CALENDAR_AND_PERIODS.md` §"Display Rules" — Fact Ledger format
4. `src/lib/dates/` — use `formatFactLedgerEntry` for the metadata string
5. `src/lib/db/schema/fact-ledger.ts` — the persistence shape
6. `src/lib/db/schema/indicator-values.ts` — the source shape
7. `src/lib/db/schema/source-documents.ts` — the citation target shape
8. `src/lib/errors.ts` — Result + AppError variants

## API Contract

```typescript
// src/lib/fact-ledger/types.ts
export type ConfidenceGrade = 'A' | 'B' | 'C';

export type ClaimDraft = {
  slug: string;             // stable kebab-case; deterministic from input
  textEn: string;           // one sentence
  textNe: string | null;
  indicatorValueId: string;
  indicatorId: string;
  sourceDocumentId: string;
  confidenceGrade: ConfidenceGrade;
  verifiedBy: string;
  // For display + Fact Ledger metadata:
  reportingPeriodLabel: string;     // "FY 2082/83 9M (Shrawan–Chait)"
  publicationDateAd: Date;
  publicationDateBs: string;
};

// src/lib/fact-ledger/schemas.ts
export const ClaimDraftSchema: z.ZodSchema<ClaimDraft>;
export const validateClaimDraft = (input: unknown): Result<ClaimDraft>;

// src/lib/fact-ledger/build-claim.ts
export type BuildInput = {
  indicator: { id: string; slug: string; nameEn: string; nameNe: string | null; unit: string; sourceAgency: string };
  value: {
    id: string;
    value: string;  // numeric stringified, as Drizzle returns
    unit: string;
    reportingPeriodType: ReportingPeriodType;
    reportingPeriodBs: string;
    reportingPeriodAdStart: Date;
    reportingPeriodAdEnd: Date;
    publicationDateAd: Date;
    publicationDateBs: string;
    fiscalYearBs: string;
    confidenceGrade: ConfidenceGrade;
  };
  sourceDocument: { id: string };
  verifiedBy: string;
};

export function buildClaimDraftFromIndicatorValue(input: BuildInput): Result<ClaimDraft>;
```

## Behavior Rules

- `slug` = `${indicator.slug}-${value.fiscalYearBs.replace('/', '-')}-${value.reportingPeriodType}` (kebab; deterministic; collision-resistant within one indicator-year-period)
- `textEn` = a single sentence of the form `"{indicator.nameEn} for {reportingPeriodLabel}: {formattedValue} {unit}."` — keep punctuation exactly as shown
- `textNe` = `null` unless `indicator.nameNe` is set (in which case render the Nepali sentence equivalent)
- `formattedValue` uses `Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })` on the parsed value
- `reportingPeriodLabel` uses `src/lib/dates` to derive the human-readable label (compose from `parseReportingPeriod` or directly from inputs — pick the cleanest path; document the choice)
- Confidence-grade downgrade rule: if `confidenceGrade` is `'C'` AND the source agency string contains `'preliminary'` or `'provisional'` (case-insensitive), append ` (provisional)` to `textEn`
- Validation: any missing input returns `Validation` with the specific field; never throw

## Required Test Cases

- Happy path: NCPI inflation YoY for FY 2082/83 9M → slug, textEn, textNe (null), confidence A all match expected values
- Bilingual: indicator with `nameNe` set → both `textEn` and `textNe` populated
- Provisional FCGO-style row → textEn has the ` (provisional)` suffix
- Validation: empty `verifiedBy` → `Validation` error
- Validation: non-numeric `value.value` → `Validation` error
- `validateClaimDraft` accepts a well-formed object; rejects on shape drift (e.g. missing `slug`)

## Acceptance Criteria

- [ ] Files in scope only
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` — new tests pass, existing 67 still pass
- [ ] No new dependencies (Zod is already on the stack)
- [ ] No `as` casts, no `any`, no `@ts-ignore`
- [ ] `buildClaimDraftFromIndicatorValue` is pure (no DB, no IO) — repositories call it; tests don't need to mock the DB
- [ ] Diff under 300 non-test lines

## What to Return

Standard 6-section report (summary, checklist, diff stat, deviations, open questions, commit message).
