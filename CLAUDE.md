# Nepal Ledger — Agent Doctrine

**Auto-loaded at every session.** Entry point for both Mother (orchestrator) and Sonnet workers (executors).

> **First action every session:** run `/memory` and verify that this file plus the current feature's `CLAUDE.md` (if working inside `src/features/<feature>/`) are loaded. If not, stop and fix the memory path before editing.

---

## Read These Before Acting

1. [docs/STRATEGY.md](docs/STRATEGY.md) — canonical product spec (in-repo; do NOT use external `.claude/plans/*` paths)
2. [docs/BACKEND_PLAN.md](docs/BACKEND_PLAN.md) — engineering umbrella + 90-day sequence
3. [docs/AGENT_OPS.md](docs/AGENT_OPS.md) — Mother + worker orchestration; worktrees; plan mode
4. [docs/CONTEXT_RULES.md](docs/CONTEXT_RULES.md) — anti-hallucination + anti-scope-drift (**mandatory**)
5. [docs/CONVENTIONS.md](docs/CONVENTIONS.md) — code conventions; sanctioned cast escape hatches; `safeQuery`
6. [docs/SOURCE_REGISTRY.md](docs/SOURCE_REGISTRY.md) — every external data feed must be registered before scraping
6a. [docs/PRE_INGEST_AUDIT.md](docs/PRE_INGEST_AUDIT.md) — **mandatory**: audit every new dataset folder BEFORE writing a parser. Established 2026-05-14 after the admin-hierarchy folder failure.
7. [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) — staging → validation → approved quarantine
8. [docs/PARSING_WORKFLOW.md](docs/PARSING_WORKFLOW.md) — Claude CLI as dev assistant; production parsers stay deterministic Python
9. [docs/CALENDAR_AND_PERIODS.md](docs/CALENDAR_AND_PERIODS.md) — BS/AD + fiscal year handling at schema level
9. [docs/CONTENT_FORMATS.md](docs/CONTENT_FORMATS.md) — 17 editorial templates
10. [docs/UI_ACCEPTANCE.md](docs/UI_ACCEPTANCE.md) — viewport/state/accessibility/performance gates
11. [docs/CLOUD_STACK.md](docs/CLOUD_STACK.md) — Cloudflare Workers + OpenNext primary; services; quotas
12. [docs/GITHUB_PRACTICES.md](docs/GITHUB_PRACTICES.md) — branching, PR template, CI, branch protection from Day 1
13. [docs/CHANGE_CONTROL.md](docs/CHANGE_CONTROL.md) — ADR + change log protocol
14. [docs/WINDOWS_DEV.md](docs/WINDOWS_DEV.md) — Windows + WSL2 split for OpenNext

ADRs live in [docs/decisions/](docs/decisions/). Current ADRs:
- [ADR-0001](docs/decisions/0001-tech-stack.md) — overall stack
- [ADR-0002](docs/decisions/0002-cloudflare-workers-opennext.md) — Cloudflare Workers + OpenNext (not Pages)
- [ADR-0003](docs/decisions/0003-ai-assisted-parsing-policy.md) — Claude CLI as dev assistant; NO production API parsing
- [ADR-0004](docs/decisions/0004-supabase-storage-instead-of-r2.md) — Supabase Storage Year 1 (R2 deferred until payment method on file)
- [ADR-0005](docs/decisions/0005-sentry-setup.md) — Sentry two-step rollout (account now, wizard post-scaffold)

Read the relevant ADR before touching code in a domain it covers.

---

## Mission (One Sentence)

> Nepal Ledger tracks whether Nepal's money becomes wealth.

If a decision does not serve that mission, push back.

---

## Operating Mode: Mother + Sonnet Workers

- **Mother** (Opus-class orchestrator) plans, decomposes, reviews, integrates. Owns infra/config/migrations/ADRs/CI. Does NOT write product feature code.
- **Workers** (Sonnet-class executors) take scope-fenced task briefs, write code, return diffs.
- **Parallel** when independent (different files). Use `git worktree` for multi-file parallel work — see [AGENT_OPS.md](docs/AGENT_OPS.md) §"Parallel Workflow".
- **Plan mode** required for tasks touching >3 files (`claude --permission-mode plan`).
- **Max 3 parallel workers per batch.**

---

## The Six Rules (Workers Read These First)

From [CONTEXT_RULES.md](docs/CONTEXT_RULES.md):

1. **Read Before Write** — read every file in the scope fence + cited reference patterns before typing
2. **Pattern Match First** — match existing patterns; new patterns need an ADR
3. **Type-Driven** — Zod schema → derived type → implementation → tests
4. **Scope Fence Is Absolute** — touch only listed files; nothing else
5. **Diff Size Cap** — 300 lines max per worker diff
6. **No Silent Failure Patterns** — typed errors; no swallowed try/catch; no `any`; no `as unknown as`

Sanctioned `as` casts: ONLY in (a) post-Zod boundary, (b) DOM narrowing, (c) `src/lib/viz/adapters/*`, (d) `src/lib/external/*` — see CONTEXT_RULES §"Cast Escape Hatches".

---

## Verification Gates (CI-Enforced)

Every PR must pass:

- `pnpm typecheck` — zero errors
- `pnpm lint` — zero errors
- `pnpm test` — all pass
- `pnpm build` — succeeds
- `pnpm exec drizzle-kit check` — schema diff clean
- `gitleaks detect --staged` — no secrets
- Manual eyeball on UI changes (Mother enforces — see [UI_ACCEPTANCE.md](docs/UI_ACCEPTANCE.md))
- ADR added if architectural; change-log entry if scope shifted

Branch protection on `main` is enabled from Day 1 (after first green CI). All merges via PR with squash.

---

## 90-Day Sequence (Tightened)

Day 1–3: Bootstrap (CI, OpenNext scaffold, branch protection, hooks).
Day 4–6: Schema foundation (Drizzle, calendar/periods, safeQuery, date utilities).
Day 7–10: "Hello, Nepal" static landing page (first public URL, momentum win).
Day 11–28: Source Registry + Fact Ledger + first NCPI ingestion pipeline (provenance core).
Day 29–45: Pulse + Monthly Verdict v1 (consumes trusted indicator data).
Day 46–60: Money Map v0 (D3 Sankey on trusted flows).
Day 61–75: First flagship story + first entity profile.
Day 76–90: Public beta + one signature utility (Household Ledger Calculator OR Loan→Project→Asset Tracker v0).

Full milestone descriptions: [BACKEND_PLAN.md](docs/BACKEND_PLAN.md) §"The 90-Day Bootstrap Sequence (Tightened)".

---

## Escalate to User When

- An ADR proposes paid spending
- A milestone slips >40%
- A worker fails the same acceptance criterion 3 times
- A free-tier service hits 70% quota
- A scope question STRATEGY.md doesn't answer
- A deploy fails on production
- A secret leak is detected

When in doubt, ask. The cost of asking is low; the cost of guessing on architecture compounds.

---

## Day 0 State

- Strategy plan in-repo: [docs/STRATEGY.md](docs/STRATEGY.md) (1595 lines, v6 final + Day-0 hardening)
- Doctrine docs complete (14 files in `docs/`)
- ADRs: 0001 (tech stack) + 0002 (Cloudflare Workers + OpenNext)
- Bootstrap script ready: `scripts/bootstrap.ps1`
- CI workflow scaffold: `.github/workflows/ci.yml`
- PR template: `.github/PULL_REQUEST_TEMPLATE.md`
- Existing data to ingest first:
  - `NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv`
  - `Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf`
  - `Stastical Information/Statistical Information on Nepalese Agriculture 2080_81_a7s8aj4.pdf`

## Day 0 Open Decisions

- **Project name** (Hisaab / Paisa / Rupaiya / Conversion / other) — pending user pick
- **Domain registration** — defer or register; tied to name pick
- **Resend account** — sign up vs. defer email to Day 60
- **License selection** for public-from-Day-1 (MIT/Apache for code + CC BY-NC-SA for content recommended)
- **GitHub repo creation** — pending name pick; then `gh repo create <name> --public --source=. --remote=origin`

---

## Quick Glossary

- **Pulse** — live macro data layer, KPI cards, refreshed monthly
- **Monthly Verdict** — prose synthesis published with NRB CMEFs release; the habit loop
- **Money Map** — D3 Sankey of flows entering/circulating/leaking/destroyed
- **Money Funnel** — concentration visualization (household Rs 100 → group)
- **Fact Ledger** — visible claims database; every claim clickable with source + confidence (A/B/C)
- **Knowledge Base** — encyclopedia: entities, indicators, concepts, money flows
- **Lenses** — 7 mobile-first views (Pulse / Money Map / Money Funnel / Borrowed Time / Land Use Atlas / Tourism Rupee / Latest Stories)
- **5 Public Pillars** — Money In / Money Out / Money Captured / Money Wasted / Where Money Becomes Wealth
- **17 Internal Verticals** — operating editorial machinery (see STRATEGY.md)
- **3 Signature Public Utilities** — Loan→Project→Asset Tracker, Household Ledger Calculator, Cost of Leaving Nepal Calculator
- **District MRI** — per-district economic dashboard (5 districts Year 1)
- **Content Kill Switch** — when capacity is constrained, short-form sheds first; canonical assets are protected
- **Data Continuity Protocol** — archive on download, preserve revisions, label discontinuities, version parsers, never fabricate forward
- **Source Registry** — every external data feed registered with provenance metadata before any parser is written
- **safeQuery** — `src/lib/db/safe-query.ts` boundary that converts DB exceptions to typed `AppError`
