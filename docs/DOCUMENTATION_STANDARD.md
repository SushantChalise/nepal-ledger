# Documentation Standard

**The contract for keeping Nepal Ledger's documentation consistent with reality.**

This doc answers one question for every kind of change: *what must I write down, where, and when?* It exists because across multi-agent bursts, code ships faster than docs, and undocumented decisions become tomorrow's "huh, why is it like this?". If a change matches a row in the table below and the artifact is missing, the change is **not done**.

Read alongside [CHANGE_CONTROL.md](CHANGE_CONTROL.md) (ADR + CHANGELOG protocol) and [CONTEXT_RULES.md](CONTEXT_RULES.md) (the Six Rules). This doc does not replace them; it enumerates the full surface and adds the feature-CLAUDE.md convention.

---

## The Documentation Surface

| Artifact | Lives at | Required when | Owner |
|----------|----------|---------------|-------|
| **Feature CLAUDE.md** | `src/features/<feature>/CLAUDE.md` | A new `src/features/<feature>/` folder is created | Author of the feature |
| **ADR** | `docs/decisions/NNNN-<title>.md` | A structural choice / pattern / trade-off is made (see CHANGE_CONTROL "What gets an ADR") | Mother |
| **CHANGELOG entry** | `docs/changes/CHANGELOG.md` | Project scope/state shifts vs. the plan, or a session lands substantial work | Mother |
| **Source profile** | `docs/sources/<source-id>.md` | A source is added to `seed-source-registry.ts` (stub OK at registration; rich profile lands with the parser) | Author of the source/parser |
| **Scraper README** | `scrapers/<source-id>/README.md` | A new scraper package is created | Author of the scraper |
| **Ingest CLI doc** | docstring at top of `scripts/ingest-*.ts` + a row in [INGEST_RUNBOOK.md](INGEST_RUNBOOK.md) | A new `ingest:*` / `seed:*` CLI is added | Author of the CLI |
| **Pipeline doc** | [DATA_PIPELINE.md](DATA_PIPELINE.md) | The staging→validation→approved flow or a fact-table path changes | Mother |
| **Handoff** | `docs/HANDOFF_<YYYY-MM-DD>.md` | End of a substantial autonomous session | Mother |
| **Memory (private)** | `~/.claude/.../memory/*.md` | Operational facts an agent needs next session that aren't in the repo | Any agent |

**Rule:** in-repo docs are the shared source of truth. Anything a *teammate* (or future agent) needs goes in the repo; private agent memory is only for machine-/account-specific operational state (paths, credentials location) — and even that should point at the in-repo runbook.

---

## Feature CLAUDE.md — the convention

Per [BACKEND_PLAN.md](BACKEND_PLAN.md) §"Software Design Doctrine" rule 5, every vertical slice under `src/features/<feature>/` owns a local `CLAUDE.md`. It is the first thing an agent reads before touching that feature. Keep it under ~80 lines; it is a map, not a manual.

### Template

```markdown
# <Feature> — feature context

**One-sentence purpose.** What user-facing thing this feature is.

Lens / pillar: <which of the 7 Lenses or 5 Pillars this serves, per STRATEGY.md>
Route(s): <e.g. /pulse>
Status: <stub | live | deprecated> · <data source(s)>

## Data in
- <table(s) read>, via <repository or query module> (`path`)
- Reads production only (`approved_*`); never staging. (or note the exception)

## Files
- `server/queries.ts` — <what it returns>
- `components/<X>.tsx` — <server or 'use client'; what it renders>
- `page` at `src/app/<route>/page.tsx` — <server component entry>

## Invariants (don't break these)
- <e.g. amounts are NPR crore; format via format.ts>
- <e.g. Server Component only — no 'use client' unless interactivity demands>
- <e.g. typed empty/error states; never throw>

## Gotchas
- <non-obvious things that bit us — link the ADR/commit if relevant>

## Related
- ADRs: <NNNN>
- Docs: <DATA_PIPELINE / UI_ACCEPTANCE / etc.>
```

Keep it honest: if the feature has a known gap or a cast that needs revisiting, say so under Gotchas. A feature CLAUDE.md that hides debt is worse than none.

---

## The Documentation Gate (per change)

Before a change is "done", walk this checklist. It is the same spirit as the CI verification gates, applied to docs:

1. **New feature folder?** → feature `CLAUDE.md` exists.
2. **New `src/features` or `src/lib` subsystem with non-obvious design?** → either a feature CLAUDE.md or a short header doc-comment explaining the design.
3. **Structural decision / new pattern / surprising trade-off?** → ADR added (CHANGE_CONTROL "What gets an ADR"). Casts, unit choices, invocation conventions all qualify.
4. **New data source?** → registered in `seed-source-registry.ts` **and** a `docs/sources/<id>.md` profile exists. (Registering without a profile, or shipping a parser whose `SOURCE_ID` isn't in the seed, is a defect — both bit us in the 2026-06-07 session.)
5. **New scraper package?** → `scrapers/<id>/README.md`.
6. **New ingest/seed CLI?** → top-of-file docstring + a row in INGEST_RUNBOOK.md.
7. **Pipeline / fact-table behavior changed?** → DATA_PIPELINE.md updated.
8. **Substantial session?** → CHANGELOG entry + (if autonomous) a HANDOFF doc.
9. **Data unit / semantics established or corrected?** → ADR + the affected feature CLAUDE.md "Invariants" updated. (Units are a top source of silent wrongness — e.g. fiscal transfers were briefly mislabeled NPR_thousand when they are NPR crore.)

Mother enforces this gate at integration time, the same way she enforces typecheck/lint/test.

---

## Anti-drift rules

- **Document the decision, not just the code.** The code shows *what*; the ADR/CLAUDE.md shows *why* and *what not to do*.
- **Date everything.** ADRs and CHANGELOG entries carry dates; "recently" rots.
- **Generated docs are not hand-edited.** `docs/sources/_index.md` is generated by `pnpm gen:source-index`; edit the seed, regenerate.
- **No silent caps.** If a parser/feature covers a subset (e.g. census supports some tables, not all), the doc says exactly which and why the rest are deferred.
- **Link, don't duplicate.** Cross-reference the canonical doc rather than restating it; restated facts drift out of sync.

---

## Cross-reference

- [CHANGE_CONTROL.md](CHANGE_CONTROL.md) — ADR template + CHANGELOG format (this doc defers to it).
- [CONTEXT_RULES.md](CONTEXT_RULES.md) — the Six Rules + sanctioned cast locations.
- [INGEST_RUNBOOK.md](INGEST_RUNBOOK.md) — how to run the pipeline against live Supabase.
- [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) + [ADR-0009](decisions/0009-source-registry-single-source-of-truth.md) — source registration workflow.
