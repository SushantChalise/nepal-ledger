# Project Change Log

Append-only, reverse-chronological. Each entry captures where reality diverged from the canonical strategy plan and why.

Strategy plan: [`docs/STRATEGY.md`](../STRATEGY.md) (in-repo, canonical).

Format and rules: [CHANGE_CONTROL.md](../CHANGE_CONTROL.md).

---

## 2026-05-14 (sixth pass) — Surya OCR doctrine + Financial Data corpus integration

**What changed:** A second overnight session expanded scope substantially. The user provided a pre-staged `Financial Data/` corpus (50 NRB BFI monthly XLSX, 64 MoF PDFs across Red/White/Yellow/Agreement/Intergovernmental, plus the FY 2082/83 pre-cleaned fiscal transfer XLSX, plus 17.8M voter records aggregated into a 10,263-row administrative hierarchy CSV, plus the CBS NPHC 2021 census with 89 CSV + 8 Excel files, plus constituency mapping and a voter DB backup). Two architectural decisions absorbed:

### New ADRs

- **ADR-0008** — Surya OCR routing + tile-based pipeline. Pinned to v0.17.1. Default invocation: 384 DPI 2×2 tiled with 80px overlap, layout-aware tile boundaries (never cut through detected cells), pre-Surya OpenCV deskew + denoise + binarize for Devanagari pages, `TABLE_REC_MAX_BOXES=500`, mandatory `--detect_boxes` (the prior chat's #1 failure mode per the findings doc). PaddleOCR fallback gated on confidence + seam-disagreement thresholds set by Worker δ's empirical evaluation. 12 tile/stitch failure modes catalogued with concrete mitigations. Devanagari numerals preserved losslessly in both representations.
- **ADR-0009** — Entities dimension + per-domain fact tables. Replaces string-prefix slug overloading with a proper `entities` polymorphic dimension covering 13 entity kinds (bank, public_enterprise, local_level, district, province, cooperative, business_group, ministry, department, donor, constituency, ward, polling_station). 1:1 `administrative_units` specialization for the federal politico-geographic data. Per-domain fact tables for fiscal transfers, census, banking sector facts. Future migrations add Yellow Book PE financials, foreign-aid projects, loan agreements.

### Schema

- **Migration 0002** (PR #17, merged): 8 new tables — `entities`, `administrative_units`, `local_government_fiscal_transfers`, `census_facts`, `banking_sector_facts`, `ocr_tile_manifests`, `ocr_cell_extractions`, `ocr_stitch_disagreements`. 7 new enums (`ingestion_mode`, `entity_kind`, `grant_type`, `local_level_type`, `bank_class`, `census_indicator_family`, `stitch_resolution`). Added `ingestion_mode` column to `source_registry`. Tests 96/96 still pass.

### Doctrine

- **`docs/SOURCE_REGISTRY.md` rewritten** — from 12 entries across 4 tiers to ~40 entries across Tier 0 + Tier 1–4 + Phase-2 paused + reference-only assets. New `ingestion_mode` enum distinguishes `automated_cron` / `manual_upload` / `reference_only`. Captures the Financial Data corpus + every missing source the audit identified.
- **`docs/FINANCIAL_DATA_STRATEGY.md`** — inventory of the pre-staged corpus, three-phase extraction plan, intelligence map per Nepal Ledger vertical, schema impact analysis.
- **`docs/SOURCE_REGISTRY_AUDIT_PROPOSAL.md`** — the audit that drove the registry rewrite (all 13 questions answered yes-as-proposed).
- **`docs/research/surya-ocr-findings.md`** — 690-line comprehensive read of 100% of Surya OCR documentation (per user mandate). Critical findings: `--detect_boxes` is mandatory; `TABLE_REC_MAX_BOXES` default is 150 (truncating); DPI hard-cap at 192 with segfaults above; Devanagari regression open at v0.17.1.
- **`docs/research/ocr-eval/EVALUATION_REPORT.md`** (Worker δ output, pending) — empirical evaluation across 5 Devanagari-complex pages × 4 pipelines (Surya flat / Surya 2×2 tiled / Surya 3×3 tiled / PaddleOCR), with Opus-as-judge.

### Pipeline scripts (no live DB writes; staged-output pattern)

- `scripts/apply-migrations.ts` — applies migrations 0001 + 0002 to live Supabase via `.env.local`
- `scripts/ingest-fiscal-transfer-canonical.ts` — parses Cleaned/FY 2082/83 XLSX → 753 local levels + 77 districts + 7 provinces + ~6,000 fiscal-transfer rows. `--dry-run` writes staging JSON.
- `scripts/ingest-admin-hierarchy.ts` — parses administrative_hierarchy_FINAL.csv → 6,285 ward rollups + 10,263 polling stations + 17.8M voters aggregated. Writes staging JSON.
- `scripts/apply-all.ts` — single-command wrapper sequencing migration apply + all ingests in order, with idempotent re-runs and `--from`/`--only` flags.

### Worker ports

- **Worker ε** (`feat/scrapers-common-utils`): `scrapers/_common/devanagari_normalization.py` (31-entry OCR substitution dict ported byte-for-byte from `manual_match_reasoning.py`) + `scrapers/_common/municipality_resolver.py` (rapidfuzz-based 753-row canonical resolver). 79 pytest cases (12 existing + 67 new) green.

### Active workers (overnight, not yet returned at time of this CHANGELOG entry)

- **Worker δ** (Opus model) — OCR eval harness + Opus judging across 5 test pages × 4 pipelines. Writes `docs/research/ocr-eval/` + `EVALUATION_REPORT.md`.
- **Worker ζ** — NRB BFI XLSX parser v0.1.0 covering C4 / C5 / C6 / C7 sheets across 50 monthly files. Writes `scrapers/nrb_bfi/` + `staging-data/nrb-bfi/`.
- **Worker η** (queued — pending ζ completion): Census 2021 parser for 89 CSVs + 8 Excel.
- **Worker θ** (queued — pending ζ completion): constituency table + admin-hierarchy constituency fix.

### gitignore + safety

- `/Financial Data/` added to .gitignore (raw corpus contains a 546MB voter DB SQL dump with PII + a .env with credentials; never committed).
- `/staging-data/` added (parse outputs re-generatable from Financial Data/; not in git).

**Why this pass:** The user provided the pre-staged Financial Data corpus mid-session and mandated (a) reading 100% of Surya OCR docs before integration, (b) a tile/stitch architecture with programmatic tracking and 12-item proactive failure-mode foresight, (c) live ingestion of XLSX data into DB for Claude analytical work to derive trends/anomalies. The schema + doctrine + parser infrastructure to support those mandates landed in this pass; the live DB application + parser worker outputs land overnight as the workers complete.

**Plan section affected:** No strategy scope changes. Day 4–6 milestone complete since prior pass. Day 11–28 milestone (data provenance core) substantially in flight with this pass.

**Related:** ADR-0008 (added), ADR-0009 (added). Migration 0002 (PR #17). Doctrine docs SOURCE_REGISTRY / FINANCIAL_DATA_STRATEGY / surya-ocr-findings shipped. Worker ε output on `feat/scrapers-common-utils`. Workers δ, ζ, η, θ tracked separately.

**Backward compatibility:** Schema additions in 0002 are purely additive (new tables, new enums, optional column on `source_registry`). Migration 0001 unchanged.

---

## 2026-05-14 (fifth pass) — Overnight backend burst: schema foundation + Day 11–28 staging

**What changed:** Mother Opus operated autonomously through the night per a user-issued rescope ("complete the backend; wireframes for the front end come in the morning"). 10 squash-merged PRs landed via branch protection, advancing two milestones from `BACKEND_PLAN.md` substantially in one session.

### Milestones advanced

- **Day 4–6 — Schema foundation. Complete.**
  - `src/lib/errors.ts` (AppError union + `Result<T>`), `src/lib/env.ts` (Zod-validated server + client env), `src/lib/db/safe-query.ts` (SQLSTATE → typed AppError), `src/lib/db/client.ts` (server-only Drizzle + postgres-js singleton), `drizzle.config.ts`.
  - 13 Drizzle tables under `src/lib/db/schema/`: source_registry, source_documents, parser_runs, parser_errors, indicators, indicator_source_map, indicator_units, staging_indicator_values, approved_indicator_values, data_quality_flags, fact_ledger_claims, fact_ledger_challenges, leads.
  - First migration generated at `src/lib/db/migrations/0000_0001_initial_schema.sql` — **NOT applied** to the live Supabase (deferred to the user per the no-shared-infra-mutation autonomy rule).
  - 20 Vitest cases on errors, env, safeQuery.

- **Day 11–28 — Data provenance core. Staged.**
  - `src/lib/dates/` (Worker A) — BS↔AD wrapper, fiscal-year + period math, `parseReportingPeriod` covering every NRB CMEFs label form, `formatFactLedgerEntry` exact-match for the CALENDAR_AND_PERIODS.md canonical example. 31 tests.
  - `src/lib/storage/` (Worker B) — content-addressed Supabase Storage wrapper with R2 migration seam. Idempotent on (key, same-hash); Conflict on different-hash. Structural `StorageClientLike` for mocking without `as` casts. 16 tests.
  - `scrapers/` (Worker C) — Python 3.12 toolchain (uv-compatible), `_common/` shared types/hashing/periods/parser-contract, `nrb_ncpi/parser.py` v0.1.0 emitting 78 rows (26 indicators × 3 geographies) of YoY % change from the existing CMEFs CSV. ruff + mypy --strict clean. 12 pytest cases.
  - `src/lib/db/repositories/` (Worker D) — typed accessors for source_registry, source_documents, indicators. Every call composes `safeQuery`; every return is `Result<T>`. 23 tests with mocked `db()`.
  - `src/lib/fact-ledger/` (Worker E) — Zod `ClaimDraftSchema`, derived `ClaimDraft` type, pure `buildClaimDraftFromIndicatorValue` builder. Deterministic; same inputs yield the same citation prose. Provisional-suffix rule per agency string. 6 tests.
  - `scripts/seed-source-registry.ts` + `docs/sources/*.md` (Worker F) — Tier-1 starter sources (`nrb-cmefs-monthly`, `nrb-ncpi-table`) seed script with `--dry-run` (no DATABASE_URL needed) + full Markdown profiles per SOURCE_REGISTRY.md template.

### Doctrine

- **ADR-0006** — Next.js 16, not 15. Reconciles doctrine with scaffold reality (create-next-app delivered Next 16.2.6; Next 16 supports every feature ADR-0002 enumerates; downgrade would be churn).
- **ADR-0007** — Diff-cap rule applies to non-test source lines. Codifies the interpretation Workers A/B/C all triggered: 300 lines is a soft target on non-test source; tests, header doc-comments, structural-type interfaces, and Prettier reformatting don't count. Hard ceiling at 500 non-test source lines.

### Verification

- 96 Vitest cases across 9 TS test files, 12 pytest cases on the Python side. CI green on `main` after every merge.
- `pnpm typecheck` / `lint` / `test --run` / `build` / `drizzle-kit check` / gitleaks — all clean.

### What deliberately did NOT happen

- No migration applied to Supabase.
- No data loaded into Supabase Storage.
- No Cloudflare Workers deploy attempted (deploy workflow blocked on user-set secrets — unchanged from Day 1).
- No Sentry wizard run (interactive; user-only).
- No frontend code (wireframes pending).

**Why this pass:** The user gave Mother an overnight window with explicit autonomy authorization ("Recscope if needed"). The scope-fence + Result<T> + safeQuery + branch-protection-and-PR-loop discipline from Day 0 held under autonomous execution. The repo is in a state where the next session can spawn the first live ingestion worker the moment the user applies the migration and seeds.

**Plan section affected:** No strategy scope changes. Day 4–6 milestone marked complete. Day 11–28 milestone substantially staged (validation job + first live ingestion are the next concrete deliverables).

**Related:** ADR-0006 (added), ADR-0007 (added). Workers A–F outputs reviewed and merged via PRs #5, #7, #9, #10, #11, #12.

**Backward compatibility:** N/A — every change is additive on a Day-1 project.

---

## 2026-05-13 (fourth pass) — Pre-bootstrap doctrine reconciliation

**What changed:** Mother Opus's pre-scaffold read of the doctrine surfaced stale references that contradicted the constraint-driven decisions from the third pass. Fixed in a single non-feature commit BEFORE the scaffold lands so the historical record is clean from the first commit forward.

- `docs/BACKEND_PLAN.md`: mission paragraph now points to in-repo `docs/STRATEGY.md` (was the external `.claude/plans/...` path); tech-stack table rows for hosting and file storage updated to match [ADR-0002](../decisions/0002-cloudflare-workers-opennext.md) (Workers + OpenNext) and [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md) (Supabase Storage Year 1); repo-structure block `src/lib/r2/` → `src/lib/storage/`; `source-data/` archive target updated; First Actions section rewritten to reflect temp-scaffold-and-merge flow and Sentry Step A as pre-bootstrap.
- `docs/decisions/0001-tech-stack.md`: references section now points at in-repo `docs/STRATEGY.md`.
- `docs/CLOUD_STACK.md`: Supabase egress in the at-a-glance table corrected from 2GB to 5GB (the third pass corrected this in the Quota Tracking section but missed the headline table).
- `docs/decisions/0005-sentry-setup.md`: Sentry project name corrected from `nepal-ledger` to `javascript-nextjs` (Sentry's platform-default name; not renamed because the wizard expects the platform-default identifier). Step B wizard invocation now passes `--saas --org nepal-ledger --project javascript-nextjs` so the wizard runs non-interactively where possible. Verification block updated.
- `.env.example`: header references Cloudflare Workers (not Pages); `SENTRY_ORG` defaulted to `nepal-ledger`; `SENTRY_PROJECT` defaulted to `javascript-nextjs`.
- `docs/GITHUB_PRACTICES.md`: repository visibility flipped from "Private until Day 90" to "Public from Day 1". Aligns with the open-source-from-Day-1 license intent in CLAUDE.md and unlocks unlimited free GitHub Actions minutes from the start.
- `.github/workflows/ci.yml`: Drizzle schema-check step gated on `hashFiles('drizzle.config.ts', ...)` so CI doesn't fail before Day 4–6 lands the schema foundation. `pnpm test --run` augmented with `--passWithNoTests` so the first push doesn't fail on an empty test suite.

**Why:** The third pass changed the storage and parsing layers but the umbrella plan + a couple of tables continued to reference the old choices. Without this pass, the first commit would have embedded contradictions between BACKEND_PLAN.md and the ADRs it cites — the doctrine would have shipped already drifting from itself.

**Plan section affected:** No strategy scope changes. Doctrine-document hygiene only.

**Related:** ADR-0001, ADR-0002, ADR-0004, ADR-0005 (text changes; no status changes).

**Backward compatibility:** N/A — Day 0, still pre-scaffold.

---

## 2026-05-13 (third pass) — Constraint-driven stack refinement

**What changed:** Two hard constraints surfaced; doctrine adjusted; three factual corrections + two new alternatives documented.

### Hard constraints absorbed

1. **No Anthropic API key.** Claude CLI / Sonnet 4.6 (via the user's Claude.ai subscription) is used as a local development assistant; production parsers stay deterministic Python. Codified in [ADR-0003](../decisions/0003-ai-assisted-parsing-policy.md) and [PARSING_WORKFLOW.md](../PARSING_WORKFLOW.md). [CLOUD_STACK.md](../CLOUD_STACK.md) §"AI-Assisted Parsing Policy" lists gating requirements if API parsing is ever added later.

2. **No Cloudflare R2.** R2 requires a credit card on file even for the free tier. Replaced with **Supabase Storage** for Year 1 — same Supabase project as the database; no separate credentials; 1GB free; 5GB egress shared with DB; S3-compatible API for clean migration to R2 in Phase 2 when a payment method is on file. Codified in [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md). All references across SOURCE_REGISTRY.md, DATA_PIPELINE.md, CLOUD_STACK.md, CLAUDE.md, .env.example, and bootstrap.ps1 updated.

### Factual corrections

3. **Supabase egress is 5GB/mo, not 2GB.** Quota alert thresholds in [CLOUD_STACK.md §"Quota Tracking"](../CLOUD_STACK.md) corrected to 3.5GB / 4.5GB.

### Alternatives documented (not switched to)

4. **Neon Postgres** documented as a strong alternative to Supabase. Decision rule added: prefer Supabase if Auth/RLS/Realtime might matter in 30 days; prefer Neon if first 30 days are mostly public data + Drizzle + preview branches. Year 1 stays on Supabase.

5. **Cloudflare Hyperdrive** documented as the future DB-acceleration path. Not enabled Day 1.

### Resilience addition

6. **48-Hour OpenNext escape hatch** added to [CLOUD_STACK.md](../CLOUD_STACK.md). If Workers + OpenNext causes friction in the first 48 hours of bootstrap, swap hosting to Vercel; keep Supabase / Storage / Resend / Sentry / scrapers unchanged; ADR-0005 documents which gate failed. `vercel.json` committed at bootstrap so the swap is a 1-hour mechanical task.

### Updated bootstrap

- Bootstrap script's user-action checklist updated: no R2 step; explicit Supabase Storage bucket creation step; 48-hour escape hatch reminder.
- `.env.example` updated: R2 variables commented out (Phase 2); `SUPABASE_STORAGE_BUCKET=source-archive` added.

**Why:** The previous CLOUD_STACK.md had a 2GB Supabase egress typo and assumed R2 + API parsing were feasible Day 1. Both assumptions broke against real constraints. Better to absorb now than discover at Day 1 of bootstrap.

**Plan section affected:** No strategy scope changes. Implementation layer only — storage provider, AI-parsing approach, and a documented Vercel fallback.

**Related:** ADR-0003 (added), ADR-0004 (added), ADR-0001 (cross-refs updated), ADR-0002 (still load-bearing).

**Backward compatibility:** N/A — Day 0, still pre-scaffold.

---

## 2026-05-13 (later that day) — Day-0 doctrine hardening pass

**What changed:** Major hardening of the doctrine before any feature code, in response to an external review that flagged execution-failure risks:

- Strategy plan copied in-repo as `docs/STRATEGY.md` (1595 lines). All doctrine docs now reference the in-repo path; the external `.claude/plans/*` path is demoted to working draft.
- `docs/CONTENT_FORMATS.md` extracted from STRATEGY (the 17 editorial templates) for standalone reference.
- `docs/SOURCE_REGISTRY.md` added — every external data feed must be registered before any scraper is written.
- `docs/CALENDAR_AND_PERIODS.md` added — BS/AD + fiscal year + nine-month-cumulative period handling locked at schema level.
- `docs/DATA_PIPELINE.md` added — staging → validation → approved quarantine workflow; parser contract; revision flow.
- `docs/UI_ACCEPTANCE.md` added — viewport / state / accessibility / performance gates replacing vague "manual eyeball."
- `docs/WINDOWS_DEV.md` added — PowerShell-for-dev / WSL2-for-OpenNext-preview split.
- `docs/CLOUD_STACK.md` updated: **primary host changed from Cloudflare Pages to Cloudflare Workers + `@opennextjs/cloudflare`**. Pages is now static-only fallback; Vercel emergency fallback.
- `docs/decisions/0002-cloudflare-workers-opennext.md` ADR added for the hosting change. ADR-0001 cross-references it.
- `docs/CONVENTIONS.md` updated: `safeQuery` DB boundary wrapper added (typed DB error variants); sanctioned `as` cast escape hatches defined (post-Zod, DOM, `src/lib/viz/adapters/*`, `src/lib/external/*`).
- `docs/CONTEXT_RULES.md` updated: Rule 6 supplemented with the four sanctioned cast locations.
- `docs/AGENT_OPS.md` updated: roles described by capability not specific model version; clarified that Mother MAY write infra/config/migrations/CI but NOT product feature code; `git worktree` workflow documented; plan mode required for >3-file tasks; subagents are research-only by default.
- `docs/GITHUB_PRACTICES.md` updated: branch protection on `main` enabled from Day 1 (after first green CI), not Day 90.
- `docs/BACKEND_PLAN.md` 90-day sequence tightened: data provenance (Source Registry + Fact Ledger + first ingestion) now lands BEFORE the visible Pulse. New "Hello, Nepal" static landing page at Day 7–10 for momentum.
- `scripts/bootstrap.ps1` updated for OpenNext scaffold + simple-git-hooks + lint-staged + gitleaks pre-commit.
- `.github/workflows/ci.yml` added (typecheck + lint + test + build + opennext build + drizzle check + gitleaks).
- `.github/workflows/deploy-production.yml` added for Workers deploys via Wrangler.
- `.github/PULL_REQUEST_TEMPLATE.md` added with engineering/doctrine/UI/data gate checklists.
- Root `CLAUDE.md` updated: in-repo strategy path; `/memory` first-action verification; full doctrine doc index.

**Why:** The original doctrine was directionally strong but under-mechanized — too many rules depended on Mother "remembering." External review correctly diagnosed that without scripts, hooks, CI checks, templates, and verifiable Day-0 gates, the multi-agent build would silently drift. This pass converts policy into mechanics.

**Plan section affected:** No strategy scope changes. Hosting layer changed from Pages to Workers+OpenNext (ADR-0002). 90-day milestone sequence within Phase 1 reordered to put provenance before visible product, but Phase 1 end-state is unchanged.

**Related:** ADR-0001 (cross-referenced), ADR-0002 (added), plus 8 new doctrine docs.

**Backward compatibility:** N/A — Day 0, still pre-scaffold.

---

## 2026-05-13 — Engineering doctrine established (Day 0)

**What changed:** First write of the engineering doctrine (`docs/BACKEND_PLAN.md`, `AGENT_OPS.md`, `CONTEXT_RULES.md`, `CONVENTIONS.md`, `CLOUD_STACK.md`, `GITHUB_PRACTICES.md`, `CHANGE_CONTROL.md`) plus root `CLAUDE.md` and ADR-0001.

**Why:** Before any code is written, the operating model (Mother + workers), the anti-hallucination rules, the free-tier stack, the GitHub practices, and the change-control protocol need to exist and be checked in. Without this layer, the multi-agent build will drift.

**Plan section affected:** Strategy plan §"Tech Stack" formalized into ADR-0001. No scope changes.

**Related:** ADR-0001.

**Backward compatibility:** N/A — Day 0.
