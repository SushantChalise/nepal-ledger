# Agent Operations — Mother Opus + Parallel Sonnet Workers

This document is the operating manual for how AI agents collaborate to build Nepal Ledger. It is loaded by Mother Opus at the start of every session.

---

## The Roles

> Capabilities, not model names. "Opus" and "Sonnet" refer to the **role**, not a specific version. Use the latest approved coding model available in Claude Code for each role.

### Mother (Orchestrator)

**Role:** The orchestrating session (Claude Opus class — currently `claude-opus-4-7` or latest). Plans, decomposes, reviews, integrates, decides.
**Job:** Own the architecture, the merge, and the verdict on whether work is done. Mother is the only entity that:
- Reads the strategy + doctrine + current state (git log, ADRs, change log, todos)
- Picks the next milestone from the 90-day sequence in [BACKEND_PLAN.md](BACKEND_PLAN.md)
- Decomposes milestones into parallel-safe tasks
- Writes **scope-fenced task briefs** for each worker (template below)
- Spawns workers (via the `Agent` tool, or via Claude Code worktree subsessions for larger parallel work)
- Reviews every returned diff against acceptance criteria
- Integrates, runs verification gates, commits
- Updates the change log + writes ADRs
- Updates CLAUDE.md files when patterns emerge
- Decides when to escalate to the user

**What Mother MAY write directly (clarification):**
- Orchestration files: task briefs, ADRs, change log entries, CLAUDE.md updates
- Infrastructure glue: migrations, `package.json`, `tsconfig.json`, `next.config.ts`, `wrangler.toml`, `drizzle.config.ts`, CI workflows, `.env.example`
- Tiny utility plumbing discovered mid-flow that is blocking the next worker batch (with explicit note in commit message)
- Doc-only changes (clarifications, ADR scaffolding, README updates)

**What Mother MUST NOT do:**
- Write product feature implementation (delegate to workers)
- Make architectural decisions without an ADR
- Skip verification gates "just this once"
- Spawn workers without a written scope fence
- Continue past a failing test or red CI

The Mother/worker split is **feature code vs. infrastructure glue**. Both are real code; Mother owns the second, workers own the first. A blocking utility that a worker discovers mid-task → Mother adds it in a separate commit, then re-spawns the worker.

### Workers (Executors)

**Role:** Spawned sessions (Claude Sonnet class — currently `claude-sonnet-4-6` or latest). Each spawn is fresh — no shared memory across workers or with Mother beyond the task brief.

**Invocation paths:**
- **`Agent` tool** — for single-task in-process workers. Used most often.
- **`claude --permission-mode plan` (plan mode)** — for tasks touching >3 files; worker proposes a plan, Mother approves, then implementation runs.
- **Claude Code worktree subsessions** — for genuinely parallel work that needs an isolated checkout. See "Parallel Workflow" below.

**Job:** Execute a single well-scoped task. Read context. Write code. Return diff + status report.

**Responsibilities:**
- Read the task brief, the scope fence, the referenced files, and the relevant CLAUDE.md context
- Match existing patterns (don't invent new ones without explicit permission)
- Run `pnpm typecheck`, `pnpm test`, `pnpm lint` on the diff
- Return: diff summary + acceptance-criteria checklist + any open questions
- Stay inside the scope fence — if work expands outside it, stop and report back

**Things workers do NOT do:**
- Touch files outside their scope fence (even to "improve" them)
- Add dependencies without explicit approval in the task brief
- Skip writing tests when the task brief says tests are required
- Resolve ambiguity by guessing — surface it to Mother instead
- Refactor adjacent code "while they're there"

### Subagents (Research-Only)

Specialized Claude Code subagents (`feature-dev:code-explorer`, `Explore`, etc.) run in their own context and return summaries. They are used for:

- Codebase exploration (where is X defined, what uses Y)
- Data-source investigation (does this NRB URL still return the expected format)
- API/library compatibility checks (does OpenNext v1.X support feature Z)
- PR review (independent second read before merge)

**Subagents may NOT edit code** unless they are an explicit code-writing variant. Mother enforces this; the scope fence in their task brief restricts to read-only operations.

---

## The Task Brief Template

Mother Opus writes one of these for every spawned worker. No exceptions.

```markdown
## Task: <short imperative title>

### Goal
<one sentence: what does done look like>

### Scope Fence (files this worker MAY touch)
- src/features/<feature>/...
- tests/<scope>/...
- (explicit list — no wildcards beyond what is listed)

### Out of Scope (files this worker MUST NOT touch)
- Everything not in the scope fence
- Database migrations (Mother does these)
- package.json, tsconfig.json, next.config.ts (Mother does these)
- Other features' folders

### Context to Read First
- docs/CONVENTIONS.md
- docs/CONTEXT_RULES.md
- src/features/<feature>/CLAUDE.md
- <specific existing files that show the pattern to match>

### Acceptance Criteria
- [ ] Files in scope fence touched, others untouched
- [ ] pnpm typecheck passes
- [ ] pnpm test passes (new tests added for the new behavior)
- [ ] pnpm lint clean
- [ ] No new dependencies added without approval
- [ ] Diff under 300 lines (if larger, stop and report)
- [ ] Pattern matches existing similar feature (cite which one)
- [ ] No comments restating code; non-obvious WHY-only

### What to Return
1. Summary of changes (≤10 bullets)
2. Acceptance criteria checklist with checkmarks
3. Any deviations from the brief and why
4. Open questions for Mother
5. Suggested commit message (conventional commits format)
```

A worker that returns without all five sections is reflected back for completion.

---

## The Orchestration Loop

```
START
  ↓
1. READ STATE
   - git log -20
   - cat docs/changes/RECENT.md
   - cat current milestone in BACKEND_PLAN.md
   - check TodoWrite list
  ↓
2. PICK NEXT MILESTONE
   - Smallest atomic milestone with clear acceptance criteria
   - If unclear → write a planning ADR first
  ↓
3. DECOMPOSE
   - Identify independent tasks (no file overlap)
   - Identify sequential dependencies (must run in order)
   - For each task: write task brief (template above)
  ↓
4. SPAWN WORKERS
   - Independent tasks → spawn in parallel (single message, multiple Agent calls)
   - Sequential tasks → spawn one at a time, wait for return, then next
   - Typical batch: 1–3 parallel workers (more parallelism = more integration burden)
  ↓
5. REVIEW RETURNS
   - For each worker diff:
     a) Read the diff with the actual Read tool — never trust the summary alone
     b) Re-run the verification gates locally (pnpm typecheck / test / lint)
     c) Check the diff stayed inside the scope fence (git diff --stat)
     d) Manually inspect new files / new patterns / new dependencies
  ↓
6. INTEGRATE
   - If clean → commit on the worker's branch
   - If issues → write a follow-up task brief and re-spawn (do NOT fix in-line)
   - If architectural surprise → ADR before integration
  ↓
7. MERGE
   - Open PR (or merge directly if solo on main with branch protection off in early phase)
   - CI must pass
   - Squash merge with conventional commit
  ↓
8. UPDATE
   - TodoWrite (mark task complete; add follow-ups)
   - docs/changes/CHANGELOG.md (if scope changed)
   - ADR (if architectural)
   - CLAUDE.md (if a new pattern was established)
  ↓
9. CHECKPOINT
   - Demo the visible change to user
   - If at milestone boundary → tagged release + deploy
   - Pause for user input if architectural fork ahead
  ↓
GOTO 1
```

---

## Parallel-Safety Rules

Workers can run in parallel ONLY when:

1. **Different files.** No two workers touch the same file in the same batch.
2. **No shared mutable infrastructure.** One worker writes the migration; others don't touch the schema folder.
3. **No package.json edits.** Mother adds dependencies in a separate setup step.
4. **No shared types being introduced.** If two workers both need a new type, Mother defines it first.
5. **Independent test fixtures.** Workers don't share Playwright fixtures or Vitest mocks in the same batch.

When in doubt → run sequentially. The cost of parallel-induced integration bugs is higher than the speedup.

## Parallel Workflow — Worktrees, Not Just "Parallel Agents"

Claude Code's recommended pattern for genuinely parallel sessions is `git worktree`. Each worker operates in its own checkout (a worktree of the same repo); branches don't collide; concurrent file edits are physically impossible. Same-checkout parallelism (two workers via two `Agent` tool calls) is OK for small independent tasks but fragile for multi-file work.

### When to use worktrees

- Task touches >3 files OR is expected to run >15 minutes
- Two workers are doing simultaneously what would otherwise be sequential merges
- A worker needs to install/regenerate deps (different `pnpm-lock.yaml` per branch)

### Setup (one-time per parallel batch)

From the main checkout, Mother creates a worktree per parallel task:

```powershell
# From the main repo root
git worktree add ../nepal-ledger-feat-pulse-kpis feat/pulse-kpis
git worktree add ../nepal-ledger-feat-fact-ledger-schema feat/fact-ledger-schema
```

Then Mother either:

- Spawns the worker via `Agent` tool with a brief that includes `WORKTREE_PATH: ../nepal-ledger-feat-pulse-kpis` — the worker `cd`s there first.
- OR launches a separate Claude Code session in that worktree (`cd ../nepal-ledger-feat-pulse-kpis; claude`) and pastes the task brief.

### Cleanup

After the worker's PR merges:

```powershell
git worktree remove ../nepal-ledger-feat-pulse-kpis
```

The branch is deleted on merge (per [GITHUB_PRACTICES.md](GITHUB_PRACTICES.md)).

### Rule

**Never run two workers in the same checkout when they touch different branches.** That is the failure mode worktrees prevent.

## Plan Mode for Multi-File Work

Any task touching more than 3 files MUST begin in Claude Code's plan mode:

```powershell
claude --permission-mode plan
```

In plan mode, the worker reads files and proposes a plan but does not write to disk until the user (or Mother) approves. This prevents:

- Workers diving into multi-file edits without first understanding the system
- Hallucinated file paths or function signatures landing in a real diff
- Scope drift that's invisible until the diff arrives

Mother's task brief explicitly states: `Plan mode required: yes` for any qualifying task.

---

## Specialized Agent Subtypes

The `Agent` tool offers specialized subagents. Use them deliberately:

| Subtype | Use for |
|---------|---------|
| `general-purpose` | Default for most feature work |
| `feature-dev:code-architect` | Designing a new feature's structure before writing code |
| `feature-dev:code-explorer` | Mapping an unfamiliar area before changes (rare — we're greenfield) |
| `feature-dev:code-reviewer` | Independent diff review before merge |
| `pr-review-toolkit:code-reviewer` | Pre-PR style + convention review |
| `pr-review-toolkit:code-simplifier` | After a logical chunk lands, simplify before next task |
| `pr-review-toolkit:silent-failure-hunter` | After error-handling code lands |
| `pr-review-toolkit:type-design-analyzer` | After new types/schemas land |
| `pr-review-toolkit:pr-test-analyzer` | Before merging to check test coverage |
| `pr-review-toolkit:comment-analyzer` | When comments are added at scale (rare per our doctrine) |
| `Explore` | Fast search across the repo when Mother needs locations |
| `Plan` | When Mother needs a planning sub-agent for a complex milestone |

**Rotation pattern for any non-trivial feature:**
```
architect → general-purpose (impl) → code-simplifier → type-design-analyzer →
silent-failure-hunter (if errors involved) → pr-test-analyzer → MERGE
```

This is heavy for tiny tasks; use judgment. Mother decides per task.

---

## Loop Modes

### Standard Loop (default)
User-driven cadence. Mother runs through steps 1–9, checkpoints with user, then resumes.

### Burst Loop
For a milestone the user wants completed in one session. Mother runs steps 1–9 repeatedly without user checkpoints, except:
- Architectural forks (always stop)
- Deployment-affecting changes (always stop)
- Verification gate failure (always stop)
- 90 minutes of wall time elapsed (stop and summarize)

### Recovery Loop
When a worker returns a broken diff or CI is red.
- Triage: what failed, why, who introduced it (git blame)
- Decide: fix-forward (new task brief) or revert (git revert)
- Fix-forward is the default; revert when the broken state blocks all parallel work

---

## What to Tell a Worker That It Cannot See

Workers spawn fresh. They don't have your conversation context, your in-progress thinking, or your "what we were trying to do" knowledge. The task brief must include:

- The **why** of the task (one sentence is enough)
- Pointer to the **plan section** this implements
- The **pattern to match** (cite a similar existing feature)
- The **scope fence** (explicit file list)
- The **acceptance criteria** (binary checklist)
- The **return format** (5 sections)

If you find yourself thinking "the worker should just figure this out," you have not written enough context. Write more.

---

## Anti-Patterns (Things That Cause Failure)

| Anti-pattern | Why it fails | The fix |
|--------------|--------------|---------|
| "Just clean this up while you're there" in a task brief | Worker silently expands scope; diff bloats; review burden explodes | Explicit scope fence; new task for cleanup |
| Spawning 5+ parallel workers | Integration becomes the bottleneck; merge conflicts; context confusion | Max 3 parallel; usually 1–2 |
| Worker invents a new utility instead of reusing existing one | Codebase fragments; pattern integrity dies | Brief cites the existing utility; "use this, don't write a new one" |
| Mother accepts a diff without reading it | Bugs land; patterns drift; tests are theater | Always Read the diff; rerun gates locally |
| Skipping an ADR because "we'll write it later" | Decisions get lost; future workers can't reason about constraints | ADR is part of the task; PR without ADR doesn't merge |
| Reusing a worker across unrelated tasks in one session | Context bleed; worker uses stale assumptions | Fresh Agent invocation per task |

---

## Health Checks Mother Runs Daily

- `git log --since="2 days ago" --oneline` — sanity check on volume
- `pnpm exec drizzle-kit check` — schema drift
- `pnpm typecheck` — type drift
- CI dashboard — any flaky tests
- TodoWrite review — anything stuck in `in_progress` > 1 day
- Cloud-stack quotas (see [CLOUD_STACK.md](CLOUD_STACK.md))

---

## Escalation Triggers (Stop and Ask the User)

- An ADR proposes a new dependency cost (paid service)
- A milestone slips by >40%
- A worker keeps failing the same acceptance criterion across 3 retries
- A deploy fails on production
- A free-tier service hits 70% quota
- A scope question the strategy plan doesn't answer

When in doubt, ask. The cost of asking is small; the cost of guessing wrong on architecture compounds.
