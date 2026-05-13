# Nepal Ledger — Backend Engineering Plan

**Master engineering doctrine.** This is the umbrella document. It links to the specialist docs.

---

## Mission

Build the Nepal Ledger platform (canonical spec: [docs/STRATEGY.md](STRATEGY.md)) on a free-tier cloud stack, executed by a Mother Opus orchestrator running parallel Sonnet worker agents in a disciplined loop, with anti-hallucination + anti-scope-drift rules enforced via context engineering and verification gates.

## The Operating Model (One Sentence)

> Mother Opus reads the plan → decomposes into scope-fenced tasks → spawns parallel Sonnet workers → reviews diffs → integrates → verifies → commits → updates the change log → loops.

## The Layers of This Doctrine

| Doc | What it locks down |
|-----|--------------------|
| [AGENT_OPS.md](AGENT_OPS.md) | Mother Opus + Sonnet workers orchestration loop; task decomposition; review/integration; parallel-safety rules |
| [CONTEXT_RULES.md](CONTEXT_RULES.md) | Anti-hallucination + anti-scope-drift rules; CLAUDE.md hierarchy; read-before-write; pattern matching |
| [CLOUD_STACK.md](CLOUD_STACK.md) | Free-tier cloud services (Cloudflare + Supabase + Resend + GitHub Actions); when to use what; secrets management |
| [GITHUB_PRACTICES.md](GITHUB_PRACTICES.md) | Branching, conventional commits, PR templates, CI/CD, Actions, code review gates |
| [CHANGE_CONTROL.md](CHANGE_CONTROL.md) | ADRs (Architecture Decision Records), scope-change log, deprecation protocol |
| [decisions/](decisions/) | ADRs themselves — one per architectural decision |

## Software Design Doctrine

Read [CONVENTIONS.md](CONVENTIONS.md) for the full version. The top-level rules:

1. **TypeScript strict mode.** No `any`. No `@ts-ignore`. No `as` casts unless typed at a boundary.
2. **Server-first.** Next.js Server Components by default. `'use client'` only when interactivity demands it.
3. **Validate at boundaries.** Zod schemas for every external input (user input, API responses, parsed PDFs, scraped data). Internal code trusts validated types.
4. **Drizzle is the only ORM.** Never raw SQL except in migrations. Repository pattern in `src/lib/db/repositories/`.
5. **Feature-domain folders.** `src/features/{verdict, pulse, fact-ledger, money-map, ...}` — vertical slices, not horizontal layers. Each feature owns its UI + server logic + types + tests + local CLAUDE.md.
6. **Server Actions for mutations.** Typed end-to-end. Never expose unwrapped DB calls to client.
7. **No shared mutable state.** Pure functions + immutable data + explicit state owners.
8. **Errors are typed.** Use `neverthrow` or tagged error unions. Never throw strings. Never swallow errors silently.
9. **Tests are gates, not theater.** Vitest for pure logic + repositories. Playwright for the 3–5 critical user flows. Skip the rest.
10. **Comments only for non-obvious WHY.** Identifiers do the WHAT. No comments restating code. No "added for issue X" comments.

## The Tech Stack (Decided)

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | **Next.js 15** App Router + TypeScript strict | Server Components + ISR + ecosystem |
| Package manager | **pnpm** | Fast, strict, monorepo-ready |
| UI | **Tailwind CSS v4** + shadcn/ui primitives | Speed + escape hatches |
| Charts | **Recharts** (custom) + **Tremor** (KPI cards) | Custom data viz where it matters; quick where it doesn't |
| Diagrams | **D3.js** | Money Map, Money Funnel, Land Use Atlas |
| Database | **Supabase Postgres** + **Drizzle ORM** | Free tier 500MB; great DX; typed queries |
| ORM migrations | **Drizzle Kit** | Schema-first; SQL diffs in git |
| File storage | **Supabase Storage** (Year 1; see [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md)) → Cloudflare R2 (Phase 2) | No card required Year 1; S3-compatible API for clean R2 migration later |
| Hosting | **Cloudflare Workers via `@opennextjs/cloudflare`** (see [ADR-0002](decisions/0002-cloudflare-workers-opennext.md)) / Vercel (emergency fallback) | Unlimited bandwidth; App Router + RSC + Server Actions + ISR + Middleware all supported |
| Email | **Resend** | 3K emails/month free; great DX |
| Analytics | **Cloudflare Web Analytics** | Free; privacy-first; no cookie banner |
| Search | **Pagefind** | Static, free, builds at build time |
| Errors | **Sentry** free tier | 5K events/month |
| Scrapers | **Python 3.12** + pdfplumber + httpx | Existing data is PDF; pdfplumber handles tables |
| CI/CD | **GitHub Actions** | 2K minutes/month private; free public |
| Scheduled jobs | **GitHub Actions cron** | Simpler than Workers cron in Year 1 |
| Domain | **Cloudflare Registrar** | Wholesale pricing |
| Secrets | GitHub Actions Secrets + Cloudflare/Supabase native | Never `.env` in repo |

Full justification per choice: see [decisions/](decisions/) ADRs.

## Repository Structure (Locked)

```
Economy/                              (git repo root → nepal-ledger)
├── .github/
│   ├── workflows/                    (CI, scrapers, deploys)
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
├── docs/
│   ├── BACKEND_PLAN.md               (this file)
│   ├── AGENT_OPS.md
│   ├── CONTEXT_RULES.md
│   ├── CLOUD_STACK.md
│   ├── GITHUB_PRACTICES.md
│   ├── CHANGE_CONTROL.md
│   ├── CONVENTIONS.md
│   ├── DATA_MODEL.md                 (Drizzle schema doc, auto-generated)
│   ├── decisions/                    (ADRs)
│   ├── changes/                      (scope-change log)
│   └── research/                     (Gemini/ChatGPT critique docs)
├── scripts/
│   ├── bootstrap.ps1                 (install missing CLIs)
│   ├── new-adr.ps1                   (scaffold an ADR)
│   └── new-feature.ps1               (scaffold a feature folder)
├── scrapers/                         (Python data ingestion)
│   ├── pyproject.toml
│   ├── parse_ncpi.py
│   ├── parse_cmefs.py
│   └── ...
├── source-data/                      (GITIGNORED — large PDFs, raw downloads; archived to Supabase Storage Year 1, R2 Phase 2)
│   ├── nrb/
│   ├── customs/
│   └── stats/
├── src/
│   ├── app/                          (Next.js App Router pages)
│   │   ├── [locale]/
│   │   ├── api/
│   │   └── ...
│   ├── features/                     (vertical slices)
│   │   ├── verdict/
│   │   │   ├── CLAUDE.md             (feature-local agent context)
│   │   │   ├── components/
│   │   │   ├── server/
│   │   │   ├── types.ts
│   │   │   └── tests/
│   │   ├── pulse/
│   │   ├── fact-ledger/
│   │   ├── money-map/
│   │   ├── encyclopedia/
│   │   └── ...
│   ├── lib/
│   │   ├── db/
│   │   │   ├── schema/               (Drizzle schemas)
│   │   │   ├── repositories/         (typed data access)
│   │   │   └── client.ts
│   │   ├── storage/                  (Supabase Storage client Year 1; R2 client Phase 2)
│   │   ├── resend/                   (email client)
│   │   └── utils.ts
│   └── styles/
├── tests/
│   ├── e2e/                          (Playwright)
│   └── fixtures/
├── CLAUDE.md                         (root agent doctrine — auto-loaded)
├── README.md
├── package.json
├── pnpm-lock.yaml
├── drizzle.config.ts
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── playwright.config.ts
├── vitest.config.ts
├── .gitignore
├── .env.example                      (committed — template, no secrets)
└── .nvmrc / .node-version            (pin Node version)
```

## The 90-Day Bootstrap Sequence (Tightened)

Aligned with the strategy plan's 90-day roadmap. Tightened during Day-0 hardening: data provenance (Source Registry + Fact Ledger + first pipeline) lands BEFORE the visible Pulse, with one small public artifact at Day 7–10 to maintain momentum. Each milestone produces an ADR (if architectural) + a change-log entry + a verifiable demo.

| Days | Milestone | Verifiable output |
|------|-----------|------------------|
| **1–3** | **Bootstrap** — repo init with branch protection, CI (typecheck/lint/test/build/gitleaks), Cloudflare Workers + OpenNext scaffold, Supabase project provisioned, drizzle config, .env.example, pre-commit hooks | `pnpm dev` renders empty page; `pnpm preview` runs OpenNext locally (in WSL2); CI green; first preview deploy URL live |
| **4–6** | **Schema foundation** — Drizzle schemas: `source_registry`, `source_documents`, `parser_runs`, `parser_errors`, `staging_indicator_values`, `approved_indicator_values`, `data_quality_flags`, `indicators`, `fact_ledger_claims` with FULL [calendar/period fields](CALENDAR_AND_PERIODS.md); first migration; `safeQuery` wrapper; date utility wrapper with BS↔AD tests | Migration applied to Supabase; date utility passes leap-year + FY-boundary + nine-month tests; first `findIndicatorBySlug` repository function returns typed `Result<Indicator>` |
| **7–10** | **"Hello, Nepal" static landing page** — single page declaring the mission, listing the 5 pillars, capturing email signups (writes to Supabase), linking the 90-day roadmap; deployed to Workers + R2 source archive bucket created; gitleaks runs on every commit | Public URL live; signup form works; first deploy verified on real domain or Workers subdomain; momentum win |
| **11–28** | **First ingestion pipeline + Fact Ledger** — register `nrb-cmefs-monthly` + `nrb-ncpi-table` in source registry; archive existing CSV + PDF to R2 with hash; write first parser (NCPI CSV → staging); validation job promotes to approved; Fact Ledger schema + clickable claim component (MDX `<Claim>`); first ADR per source | Existing NCPI data ingested with full provenance; 23 NCPI subcategories × 3 geographies × 3 periods in `approved_indicator_values`; one Fact Ledger claim renders with source PDF + confidence badge + last-verified |
| **29–45** | **Pulse + Monthly Verdict v1** — 5 KPI cards on homepage; Pulse page with all NCPI subcategories; Monthly Verdict MDX template with 5-pillar prose synthesis; bilingual scaffold (`/en/` + `/ne/`) wired with next-intl | Homepage shows 5 real Chait 2082 numbers, each with source + confidence; first Monthly Verdict article publishable; Nepali toggle works on Pulse |
| **46–60** | **Money Map v0** — D3 Sankey component with `src/lib/viz/adapters/`; sourced FY 2081/82 flows (entering/circulating/leaking/destroyed); each flow links to its Knowledge Base node page; mobile fallback (stacked-bar simplification) | Money Map renders at `/lenses/money-map`; every flow has source citation + confidence; mobile screenshot passes UI acceptance |
| **61–75** | **First flagship story + first entity profile** — Kalimati price-chain investigation OR foundational "How Nepal's Economy Actually Works"; Kalimati Market entity profile; second source ingestion (Customs trade monthly) | Flagship story published with article + chart + Fact Ledger claims + Nepali version 1 week later; entity profile live; 2 sources ingested |
| **76–90** | **Public beta + one signature utility** — Household Ledger Calculator (bilingual not required) OR Loan→Project→Asset Tracker v0 (one project); launch package (ten short clips, newsletter v1, LinkedIn post, r/Nepal post); public beta announcement | Calculator/Tracker works on mobile; launch artifacts shipped; v0.9 tag on `main` |

Notes on this tighter sequence vs. the earlier draft:

- Days 1–3 explicitly include CI + branch protection + gitleaks before any feature code — previously these were soft-enabled.
- Days 7–10 introduces a small static landing page so a public URL exists from week 2 without requiring data pipelines to be done — momentum win.
- Days 11–28 (the longest single milestone) is the data-provenance core. Source Registry + Fact Ledger schema + first end-to-end ingestion all happen before the visible Pulse. This is the critic's "don't build 7 surfaces before provenance is trustworthy" point.
- Pulse + Monthly Verdict v1 (Days 29–45) consumes the data the previous milestone trusted.
- Money Map v0 (Days 46–60) consumes the structured indicator data.
- Days 61–75 produces the first piece of editorial content with full Fact Ledger discipline.
- Days 76–90 ships one (not all) of the signature utilities to test the calculator pattern end-to-end. The remaining utilities + Land Use Atlas slide to Phase 2.

This sequence ships fewer visible surfaces but a trustworthy spine. Phase 2 (Days 91–180) layers on Borrowed Time, Private Capital X-Ray, Land Use Atlas, and the remaining utilities — each on top of solid provenance.

## Verification Gates (Non-Negotiable)

Before any code merges to `main`:

1. `pnpm typecheck` — zero errors
2. `pnpm lint` — zero errors
3. `pnpm test` — all pass
4. `pnpm build` — succeeds
5. Manual eyeball on UI changes (Mother Opus does this — never delegated)
6. ADR written if the change is architectural
7. Change log entry if scope shifted

CI enforces 1–4. Mother Opus enforces 5–7.

## Anti-Failure Modes (How This Project Could Die — and What Prevents It)

| Failure mode | Prevention |
|-------------|-----------|
| Agent hallucination (invented file paths, function signatures, library APIs) | [CONTEXT_RULES.md](CONTEXT_RULES.md) — read-before-write rule; pattern-match-first; type-driven |
| Scope drift (Sonnet worker "fixes" things outside its task) | Scope fence in task brief; diff-size cap; Mother review on every PR |
| Architectural drift (decisions made implicitly via code without ADR) | Every PR template asks "Does this need an ADR?"; Mother enforces |
| Documentation rot (docs say X, code does Y) | Doc tests where possible; quarterly doc audit; CLAUDE.md hierarchy stays close to code |
| Free-tier exhaustion (a service moves to paid before we want) | Budget gates per service; alerts at 70%; documented migration paths in [CLOUD_STACK.md](CLOUD_STACK.md) |
| Secret leakage | Never `.env` in repo; secrets always in GitHub Actions / Cloudflare / Supabase native stores; pre-commit hook scans for known secret patterns |
| Data continuity gaps (NRB/FCGO break) | Continuous archival to R2; revision tracking; visible discontinuity labels — see strategy plan's Data Continuity Protocol |
| Burnout / Year 1 cadence failure | Content Kill Switch (strategy plan); engineering kill switch: if velocity drops 3 weeks in a row, Mother pauses workers and re-plans |

## First Actions

1. Confirm/install missing CLIs (`uv` is the only one missing — optional)
2. Create Cloudflare account + Supabase project + Sentry account (Step A only per [ADR-0005](decisions/0005-sentry-setup.md)) + Resend account (optional Year 1) + GitHub repo
3. Mother Opus runs the temp-scaffold-and-merge flow (see [WINDOWS_DEV.md](WINDOWS_DEV.md)) rather than `scripts/bootstrap.ps1` as-is — the Economy/ folder already contains doctrine and `pnpm create cloudflare` into a non-empty dir is risky.
4. Mother Opus reads this plan + spawns first parallel task batch (Day 1–3 bootstrap completion, then the Day 7–10 landing page worker)
5. First green CI run → enable branch protection → first deploy to Cloudflare Workers → checkpoint

---

*This document is the engineering source of truth. If reality diverges from this doc, fix the doc.*
