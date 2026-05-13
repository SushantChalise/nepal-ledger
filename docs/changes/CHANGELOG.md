# Project Change Log

Append-only, reverse-chronological. Each entry captures where reality diverged from the canonical strategy plan and why.

Strategy plan: [`docs/STRATEGY.md`](../STRATEGY.md) (in-repo, canonical).

Format and rules: [CHANGE_CONTROL.md](../CHANGE_CONTROL.md).

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
