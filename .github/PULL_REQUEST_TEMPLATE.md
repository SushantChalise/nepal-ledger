<!--
  PR Template — Nepal Ledger
  Every section below is required. Delete sections only if explicitly N/A.
  Doctrine reference: docs/GITHUB_PRACTICES.md
-->

## What
<!-- One paragraph: what changed, user-visible -->

## Why
<!-- One paragraph: which plan section this implements (link to docs/STRATEGY.md §...);
     which ADR it follows or proposes (link to docs/decisions/NNNN-*.md if any) -->

## How
<!-- Bullets: the approach; any non-obvious decisions -->

## Testing
<!-- What was tested, what new tests were added.
     Repository or pure-logic changes: Vitest cases.
     Critical user flows: Playwright spec name + run output. -->

## Screenshots / Demo
<!-- For UI changes:
     - Mobile (390×844) attached
     - Desktop (1440×900) attached
     - Loading / Empty / Error / Populated states for data components
     - Lighthouse mobile score (or N/A) -->

## Checklist

### Engineering gates
- [ ] Scope fence respected (files changed match the task brief)
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test` passing
- [ ] `pnpm build` succeeds
- [ ] Tests added for new behavior (where applicable)
- [ ] No new dependencies added (or explicitly approved in task brief / ADR)
- [ ] No `any`, `@ts-ignore`, `as unknown as`, or unsanctioned casts (see docs/CONVENTIONS.md)
- [ ] No silent failure patterns (typed errors only — see docs/CONVENTIONS.md §Error Handling)
- [ ] No secrets committed (`gitleaks detect --staged` clean)

### Doctrine gates
- [ ] ADR added if architectural decision was made
- [ ] Change log entry added (`docs/changes/CHANGELOG.md`) if scope shifted vs. strategy plan
- [ ] CLAUDE.md updated if a new pattern was established
- [ ] Diff stayed under 300 lines (or split into smaller PRs)

### UI gates (delete if non-UI PR)
- [ ] Mobile screenshot (390×844) attached
- [ ] Desktop screenshot (1440×900) attached
- [ ] All states screenshotted (Loading / Empty / Error / Populated) for data-driven components
- [ ] Source citation + confidence badge visible on every data element
- [ ] Plain-language interpretation included for every chart
- [ ] Accessibility audit passed; alt text on charts/images
- [ ] No information conveyed by color alone
- [ ] Bilingual: applicable EN/NE versions present, or follow-up issue filed

### Data gates (delete if non-data PR)
- [ ] Source registered in `source_registry` (see docs/SOURCE_REGISTRY.md)
- [ ] Source document archived to R2 with hash + timestamp
- [ ] Parser writes only to `staging_indicator_values` (see docs/DATA_PIPELINE.md)
- [ ] Validation rules cover schema / period / units / plausibility / duplicate / revision / source-integrity
- [ ] Calendar/period fields populated correctly (see docs/CALENDAR_AND_PERIODS.md)
- [ ] Confidence grade assigned (A/B/C)
