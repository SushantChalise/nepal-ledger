# Worker G — Validation Job (staging → approved promoter)

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** soft 300 / hard 500 non-test source lines (per ADR-0007)

---

## Goal

Implement the validation job per `docs/DATA_PIPELINE.md` §"The Validation Job". Given a `parser_run_id`, walk its staging rows, apply the 8 ordered checks, and either:
- Promote the row to `approved_indicator_values` (delete the staging row)
- Write a `data_quality_flag` with `severity = blocking` (keep staging row for human review)
- Promote AND write a warning-severity flag

Done = `pnpm typecheck`, `pnpm lint`, `pnpm test --run` green; the module exposes `validateParserRun(parserRunId)` returning a typed result; 12+ Vitest cases cover the per-check decision matrix.

## Why

Schema + parser + repositories all exist. Without this job, staging rows pile up forever and nothing reaches `approved_indicator_values`. This is the last piece before the first live end-to-end ingestion.

## Scope Fence (files this worker MAY touch)

Create:
- `src/lib/validation/index.ts` — public surface: `validateParserRun(parserRunId): Promise<Result<ValidationSummary>>`, `ValidationSummary` type
- `src/lib/validation/checks.ts` — pure functions, one per check (schemaCheck, indicatorResolutionCheck, periodParseCheck, unitRecognitionCheck, plausibilityCheck, duplicateCheck, revisionFlowCheck, sourceIntegrityCheck)
- `src/lib/validation/promote.ts` — promote a staging row to `approved_indicator_values` (delete staging in same transaction)
- `src/lib/validation/flag.ts` — write a `data_quality_flag` row
- `src/lib/validation/types.ts` — `ValidationSummary`, `CheckOutcome`, `CheckContext`
- `src/lib/validation/checks.test.ts` — pure-function unit tests (no DB)
- `src/lib/validation/index.test.ts` — integration tests mocking `db()` and repositories
- `src/lib/db/repositories/staging-indicator-values.ts` — typed repository for staging rows: `listForParserRun`, `deleteById`, `findById`. Extends the pattern Worker D established.
- `src/lib/db/repositories/approved-indicator-values.ts` — typed repository: `insertApproved`, `findLatestByIndicator`. Same pattern.
- `src/lib/db/repositories/data-quality-flags.ts` — typed repository: `insertFlag`.

Edit:
- `src/lib/db/repositories/index.ts` — barrel re-exports for the three new repository modules.

**Out of scope:**
- Schemas (locked in PR #3 / #11)
- Drizzle config, package.json
- The Python parser (already done by Worker C)
- The integration orchestrator (Worker H — separate)

## Context to Read First

1. `docs/DATA_PIPELINE.md` §"The Validation Job" + §"Confidence Grade Assignment" — the canonical check order and the outcomes
2. `docs/CALENDAR_AND_PERIODS.md` §"Revisions" — append-only revision flow
3. `docs/decisions/0007-diff-cap-non-test-source-lines.md` — the cap interpretation
4. `src/lib/errors.ts` + `src/lib/db/safe-query.ts`
5. `src/lib/db/schema/indicator-values.ts` (staging + approved + flags) and `src/lib/db/schema/enums.ts` (DataQualityFlagType, FlagSeverity)
6. `src/lib/db/repositories/source-registry.ts`, `source-documents.ts`, `indicators.ts` — the Worker D pattern you're extending
7. `src/lib/dates/index.ts` — `parseReportingPeriod` is useful for PeriodParseCheck

## API Contract

```typescript
// src/lib/validation/types.ts
export type CheckOutcome =
  | { kind: 'pass' }
  | { kind: 'warn'; flagType: DataQualityFlagType; detail: string }
  | { kind: 'block'; flagType: DataQualityFlagType; detail: string };

export type CheckContext = {
  stagingRow: StagingIndicatorValueRow;
  sourceDocument: SourceDocumentRow;
  indicator: IndicatorRow | null;  // null when IndicatorResolutionCheck fails
  // For PlausibilityCheck: 24-month trailing approved values for this indicator (any periodType)
  approvedTrailing24m: ApprovedIndicatorValueRow[];
  // For DuplicateCheck: existing approved row with same (indicatorId, periodType, periodBs) if any
  existingApprovedForPeriod: ApprovedIndicatorValueRow | null;
};

export type ValidationSummary = {
  parserRunId: string;
  totalStagingRows: number;
  promoted: number;
  promotedWithWarnings: number;
  blocked: number;
  blockingFlags: Array<{ stagingRowId: string; flagType: DataQualityFlagType; detail: string }>;
};

// src/lib/validation/index.ts
export async function validateParserRun(parserRunId: string): Promise<Result<ValidationSummary>>;

// src/lib/validation/checks.ts — pure functions (no DB)
export function schemaCheck(row: StagingIndicatorValueRow): CheckOutcome;
export function indicatorResolutionCheck(row: StagingIndicatorValueRow, indicator: IndicatorRow | null): CheckOutcome;
export function periodParseCheck(row: StagingIndicatorValueRow): CheckOutcome;
export function unitRecognitionCheck(row: StagingIndicatorValueRow, knownUnits: ReadonlySet<string>): CheckOutcome;
export function plausibilityCheck(row: StagingIndicatorValueRow, trailing: readonly ApprovedIndicatorValueRow[]): CheckOutcome;
export function duplicateCheck(row: StagingIndicatorValueRow, existing: ApprovedIndicatorValueRow | null): CheckOutcome;
export function revisionFlowCheck(row: StagingIndicatorValueRow, existing: ApprovedIndicatorValueRow | null): CheckOutcome;
export function sourceIntegrityCheck(row: StagingIndicatorValueRow, doc: SourceDocumentRow): CheckOutcome;
```

## Check Semantics (per DATA_PIPELINE.md)

1. **SchemaCheck** — Zod-validate the staging row shape. Real-world drift would have been caught at parse time; this is a belt-and-braces.
2. **IndicatorResolutionCheck** — `indicatorId` must be set OR `indicatorSlugRaw` must match a known indicator (you receive the resolved indicator from the orchestrator). Block if neither.
3. **PeriodParseCheck** — pass `reporting_period_bs` to `parseReportingPeriod` from `src/lib/dates`. If parse fails, block with `PeriodAmbiguous`. If parse succeeds but the parsed AD range doesn't align with the row's `reporting_period_ad_start/end` (±2 days tolerance), warn with `PeriodAmbiguous`.
4. **UnitRecognitionCheck** — `unit` must be in the `knownUnits` set (caller provides it from `indicator_units` table; for v0 you can hard-code a starter set in `index.ts` if the table is empty). Block if not.
5. **PlausibilityCheck** — value within ±5 stdev of trailing-24m mean for this indicator. Skip (pass) if trailing has <3 rows. Warn (not block) on out-of-band — the validator is wide on purpose.
6. **DuplicateCheck** — if an approved row exists for `(indicatorId, periodType, periodBs)` AND `source_document_id` is the SAME, block as `DuplicateOfApproved`. If different `source_document_id`, defer to RevisionFlowCheck.
7. **RevisionFlowCheck** — if an approved row exists with different doc:
   - The new value must differ from the existing (else block as `DuplicateOfApproved`)
   - The new row's `revision_number` must equal `existing.revision_number + 1` (orchestrator computes this before passing to staging — if not set correctly, block as `RevisionMismatch`)
8. **SourceIntegrityCheck** — recompute SHA-256 of the source document via the storage wrapper... actually NO, that's expensive. Cheaper: confirm `sourceDocument.file_hash_sha256` is non-empty and `sourceDocument.id === stagingRow.source_document_id`. Block as `SourceHashCollision` on mismatch.

## Outcomes

- **All checks pass:** promote (insert into approved, delete staging) inside a transaction. Increment `promoted` counter.
- **Any warn but no block:** promote AND write each warn flag. Increment `promotedWithWarnings`.
- **Any block:** do NOT promote; write all blocking flags (and any warnings discovered before the block). Increment `blocked`. Append to `blockingFlags[]`.

Checks should fire in order. After the first block, you may stop checking that row (early exit) OR continue to surface all issues (preferred for ops visibility — fewer back-and-forth cycles with a human reviewer). Pick one approach and document it.

## Transaction discipline

The promote-and-delete operation MUST be atomic. Use Drizzle's `db.transaction(...)` inside `promote.ts`. Wrap the whole thing in `safeQuery`.

## Test Cases (12+)

In `checks.test.ts` (pure):
- SchemaCheck rejects a missing-required-field row
- IndicatorResolutionCheck blocks when indicator is null AND slug doesn't match
- PeriodParseCheck happy + parse-fails + AD-misalignment-warn
- UnitRecognitionCheck blocks on unknown unit
- PlausibilityCheck skips with <3 trailing rows
- PlausibilityCheck warns on >5 stdev outlier
- DuplicateCheck blocks on same-doc same-period
- RevisionFlowCheck blocks on wrong revision number
- SourceIntegrityCheck blocks on doc mismatch

In `index.test.ts` (mocked db + repositories):
- Happy path: 3 staging rows → 3 promoted; staging cleared; flags table untouched
- Mixed: 1 promoted, 1 warned-and-promoted, 1 blocked
- Empty parser run: returns ok({ totalStagingRows: 0, promoted: 0, ... })
- DB error during promote: returns err({ kind: 'QueryFailed', ... }); no partial state

## Acceptance Criteria

- [ ] Files in scope only
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` — new tests pass, existing 96 still pass
- [ ] No new dependencies
- [ ] No `as` casts outside sanctioned locations
- [ ] No `any`, no `@ts-ignore`
- [ ] All DB ops composed via `safeQuery`
- [ ] `validateParserRun` returns `Result<ValidationSummary>` — never throws
- [ ] Diff under 500 non-test source lines (hard ceiling)

## What to Return

Standard 6-section report (summary, checklist, diff stat, deviations, open questions, commit message).
