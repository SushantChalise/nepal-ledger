# Context Rules — Anti-Hallucination + Anti-Scope-Drift

This document is loaded by every Sonnet worker via its scope brief and by Mother Opus at session start. **Violating these rules is the #1 cause of vibecoding failure.** Read carefully.

---

## The Three Failure Modes We Are Preventing

| Failure | What it looks like | Cost |
|---------|--------------------|------|
| **Hallucination** | Worker invents a file path, function signature, library API, type, or behavior that does not exist | Bugs, mysterious errors, integration breakage |
| **Scope drift** | Worker "improves" code outside the task; refactors adjacent; adds features not requested | Diff bloat; review burden; merge conflicts; pattern fragmentation |
| **Pattern fragmentation** | Worker invents a new way to do something the codebase already has a way for | Codebase becomes inconsistent; future workers don't know which pattern to follow |

The rules below prevent all three.

---

## The Seven Rules (Every Worker Reads These)

### Rule 1: Read Before Write

Before writing a single line of code, the worker MUST:

1. Read every file in the scope fence
2. Read at least one similar existing feature (cited in the task brief)
3. Read the local `CLAUDE.md` (if the scope is inside a feature folder)
4. Read the relevant Drizzle schema (if database is involved)
5. Use the Grep tool to confirm any function/utility name actually exists before calling it

If the worker cannot find what it needs, it stops and asks Mother. It does not invent.

### Rule 2: Pattern Match First

If the codebase has a way to do X, do X that way. Workers MAY NOT introduce a new pattern without:

1. Explicit permission in the task brief, OR
2. An ADR proposing the new pattern

When in doubt, the worker reads three existing features and matches the dominant pattern.

### Rule 3: Type-Driven Development

For any feature involving data:

1. Define the Zod schema first (validates at boundary)
2. Derive the TypeScript type from the schema (`z.infer<typeof Schema>`)
3. Implement against the type
4. Tests check the schema

This makes hallucination structurally impossible — if the type doesn't compile, the code doesn't ship.

### Rule 4: Scope Fence Is Absolute

The task brief lists files the worker MAY touch. The worker:

- Touches only those files
- If a fix requires touching a file outside the fence → stops and reports
- Does NOT "drive-by" fix typos in adjacent files
- Does NOT reformat or restructure files in the fence beyond what the task requires
- Does NOT add dependencies (Mother does this in a separate step)

If a worker returns a diff that violates the scope fence, the diff is rejected entirely. Not partially accepted. Rejected.

### Rule 5: Diff Size Cap

Workers cannot ship a diff larger than 300 lines (additions + deletions). If a task brief implies more:

- Worker stops and reports
- Mother decomposes further
- New task briefs are written

This protects review quality. A 300-line diff a human can review carefully. A 1000-line diff a human skims and bugs slip through.

### Rule 6: No Silent Failure Patterns

Workers MUST NOT:

- Wrap calls in `try/catch` and swallow the error
- Return `null` or `undefined` on failure without typed error handling
- Add fallback values that mask broken behavior
- Use `any` or `as unknown as` to bypass type checks
- Use `// eslint-disable-next-line` without an accompanying comment explaining the WHY (and Mother sign-off in the brief)

See [docs/CONVENTIONS.md](CONVENTIONS.md) §"Error Handling" for the full doctrine.

### Rule 7: Pre-Ingest Data Audit (added 2026-05-14)

Before writing a parser, ingest script, or staging row for any external dataset, the dataset folder MUST be audited per [PRE_INGEST_AUDIT.md](PRE_INGEST_AUDIT.md). The audit:

- Inventories ALL files in the source folder (not just the obviously-canonical one)
- Diffs variants (e.g. `X.csv` vs `X_COMPLETE.csv` vs `X_FINAL.csv`)
- Identifies which file is authoritative for each downstream-needed field
- Lands as `docs/research/<dataset-id>-audit.md` BEFORE the ingest brief is written
- Requires user sign-off on the "discarded files" verdict

Adding because the admin-hierarchy folder shipped 3 variants (953 / 10,263 / 10,263 rows) where the largest variant had **broken municipality_type and only 10% constituency coverage**, and the actual canonical source was in a different folder entirely. Ingest wrote against the wrong file. One full ingest cycle wasted.

A worker that spawns a parser without first writing or citing an audit is reflected back. Same severity as scope-fence violation.

### Cast Escape Hatches (Sanctioned Only)

Workers may use `as` casts ONLY in these four locations (see [CONVENTIONS.md](CONVENTIONS.md) §"Sanctioned `as` Cast Escape Hatches"):

1. Same function as a Zod `.parse()` call — bridging unknown to validated type
2. DOM event-target narrowing — local, brief, no `unknown` chain
3. Files under `src/lib/viz/adapters/*` — D3/Recharts type bridges, with a co-located test asserting the contract
4. Files under `src/lib/external/*` — third-party SDK response adapters, with a co-located test

Casts anywhere else in the diff = the diff is rejected. If a worker thinks they need one outside these four cases, they stop and surface to Mother.

---

## The CLAUDE.md Hierarchy

Context is layered so workers receive only what they need.

```
/CLAUDE.md                          (root — auto-loaded; project doctrine, top-level rules)
/docs/CONTEXT_RULES.md              (this file — cited in every task brief)
/src/features/<feature>/CLAUDE.md   (feature-local — patterns specific to this slice)
```

**Rules for CLAUDE.md files:**
- Root CLAUDE.md is short (under 150 lines). It points to specialist docs.
- Feature CLAUDE.md is shorter (under 50 lines). It captures the WHY of decisions specific to that feature.
- CLAUDE.md never restates code. It captures things code cannot express.
- CLAUDE.md is updated when patterns emerge — by Mother, not workers.

---

## What Workers See, What They Don't

**Workers DO see:**
- The task brief (their entire reality)
- The scope-fence files
- The CLAUDE.md hierarchy referenced in the brief
- The Conventions doc
- This Context Rules doc

**Workers DO NOT see:**
- The conversation history with the user
- Mother's planning rationale (only the task brief)
- Other workers' tasks in the same batch
- The strategy plan in full (only the section cited in the brief)
- ADRs not directly relevant to the task

This is by design. A worker with too much context becomes a confused worker. The task brief is the worker's entire universe.

---

## Anti-Hallucination Checks Mother Runs on Every Diff

Before integration:

1. **Files exist:** Read every file path mentioned in the diff. If a path is new, was it justified in the brief?
2. **Functions exist:** Grep every imported function. Imports that resolve to nothing = hallucination.
3. **Types exist:** `pnpm typecheck`. Type errors = stop.
4. **APIs exist:** If the diff uses a third-party API call, verify it against the library docs (WebFetch the docs page).
5. **Test what changed:** Run the new tests. Do they actually test what they claim? Read the assertions.
6. **Diff stayed in scope:** `git diff --stat` shows only files in the fence.

A diff that fails any of these checks is rejected — not patched in-line. New task brief, new worker.

---

## Pattern Citations (Required in Task Briefs)

When Mother writes a task brief, she cites the existing pattern to match.

Bad task brief snippet:
> "Build the entity profile page for NEA."

Good task brief snippet:
> "Build `/encyclopedia/entities/nea` following the pattern of `/encyclopedia/entities/noc` (already in repo). Use the same `EntityProfile` component, the same 13-section template from `docs/CONTENT_FORMATS.md` §"Entity Page", and the same Drizzle entity_financials query in `src/lib/db/repositories/entities.ts:getEntityFinancials`. Differences: NEA data sources are listed in `scrapers/nea/README.md`."

The good brief gives the worker:
- A code template to mimic
- A document template to follow
- A function to use (with exact path + name)
- A scoped delta (only the differences are new work)

This is how to make Sonnet workers produce consistent, integrate-able code.

---

## When a Worker Should Stop and Ask

Workers stop and report (do not invent answers) when:

1. The scope fence is unclear or appears wrong
2. A required file or function cited in the brief doesn't exist
3. A new dependency seems necessary
4. A pattern in the brief contradicts a pattern they found in the code
5. An acceptance criterion is impossible to meet given the constraints
6. The diff is approaching 300 lines and the task isn't done
7. A test failure has an ambiguous cause

When a worker stops and asks → Mother either resolves and re-spawns, or escalates to user.

---

## The "Three Reads" Rule

For any new feature touching unfamiliar code, the worker reads three things before writing:

1. The closest existing similar feature (full read)
2. The repository pattern (full read of `src/lib/db/repositories/<related>.ts`)
3. The component pattern (full read of one similar UI component)

Then writes. No exceptions.

---

## Anti-Scope-Drift Spot Checks

Mother runs these on every PR:

| Check | Command | What good looks like |
|-------|---------|---------------------|
| Files touched | `git diff --name-only main` | Subset of the scope fence |
| Files NOT touched | (manual check) | No edits to package.json, tsconfig, migrations, other features |
| New dependencies | `git diff main package.json` | No diff (or explicitly approved) |
| New patterns | (Grep for new utility names, new component types) | Cited in brief or rejected |
| Comments added | `git diff main \| grep '^+.*//'` | Only WHY comments, no code-restating |

If any check fails → diff is rejected → new task brief.

---

## TL;DR for Workers

> Read first. Match the pattern. Stay in the fence. Type-drive everything. Cap your diff. Surface uncertainty. **Audit before ingesting external data.** Don't invent. Don't drift. Don't fragment.

Stick to this and your work merges. Don't, and it bounces.
