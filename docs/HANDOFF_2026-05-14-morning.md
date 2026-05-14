# Morning Handoff — 2026-05-14 (Surya + Financial Data session)

> Mother Opus operated autonomously per your "continue till I say stop" + "don't ask me anything as I am going to sleep" instruction. This is the morning brief.

---

## TL;DR (one-paragraph)

You added the pre-staged `Financial Data/` corpus (50 NRB BFI XLSX + 64 MoF PDFs + Cleaned/FY 2082/83 + 89 CSV + 8 Excel Census 2021 + 10,263-row admin-hierarchy + voter DB SQL dump). Overnight, Mother absorbed the new architecture (Surya OCR + tile pipeline + entities dimension), shipped 8 new tables in migration 0002, dispatched 5 Sonnet + 1 Opus workers to extract data and run the OCR evaluation, and wrote the doctrine + ADRs + source profiles + ingest scripts that turn the corpus into queryable Nepal Ledger data. Nothing was applied to live Supabase per system permission rules; everything is staged to `staging-data/` (gitignored) and the apply-all wrapper lets you go live with one command.

---

## What landed in PRs

| PR | Title | Status |
|----|-------|--------|
| #15 | docs(research): comprehensive Surya OCR findings | **merged** |
| #17 | feat(db): migration 0002 — entities + 5 fact tables + OCR tracking | **merged** |
| #18 | docs: SOURCE_REGISTRY audit + Financial Data strategy + Worker H brief | **auto-merging** |
| #19 | docs+scripts: ADR-0008/0009 + SOURCE_REGISTRY rewrite + overnight ingest pipeline | **open for review** |
| #20 | feat(scrapers): port Devanagari normalization + municipality resolver (Worker ε) | **open for review** |
| [Worker δ output] | docs(research): OCR evaluation across 5 Devanagari-complex pages | **pending review on commit** |
| [Worker ζ output] | feat(scrapers): NRB BFI XLSX parser v0.1.0 | **pending review on commit** |

---

## What's IN `main`

- **8 new schema tables** (migration 0002, PR #17):
  - `entities` (polymorphic, 13 entity kinds)
  - `administrative_units` (1:1 specialization for politicogeo)
  - `local_government_fiscal_transfers`
  - `census_facts`
  - `banking_sector_facts`
  - `ocr_tile_manifests` + `ocr_cell_extractions` + `ocr_stitch_disagreements`
- **6 new enums** + `ingestion_mode` column on `source_registry`
- **Doctrine docs**: ADR-0008 (Surya routing — pending PR #19 merge), ADR-0009 (entities/domain tables — pending PR #19 merge), revised SOURCE_REGISTRY with ~40 entries across new tiers
- 96/96 Vitest tests still pass; CI green

## What's STAGED on disk (in `staging-data/`, gitignored)

| Path | Content | Row count |
|------|---------|----------:|
| `staging-data/fiscal-transfer-canonical/fy-2082-83.json` | FY 2082/83 fiscal transfers (Cleaned/ XLSX) | 753 local levels × ~8 grant types ≈ 6,000 transfer rows + 77 districts + 7 provinces |
| `staging-data/admin-hierarchy/wards-and-polling-stations.json` | Admin hierarchy (voter-DB-derived CSV) | 6,285 wards + 10,203 polling stations + 17.8M voters aggregated |
| `staging-data/nrb-bfi/*.json` (50 files) | NRB BFI 49-month monthly statistics | **TBD — see Worker ζ output below** |
| `staging-data/census-2021/*.json` | NPHC 2021 by-municipality facts | **Worker η pending spawn** |
| `staging-data/constituency-mapping/*.json` | Constituency → local-level mapping | **Worker θ pending spawn** |

## What's NOT in Supabase yet

> **Mother could not apply migrations or run live ingests** — the system permission rule guards "modifying shared Supabase production database" against the agent's own doctrine. Your "continue till stop" instruction was general; not specific enough to override. **The system was right to refuse.** You apply with one command:

```powershell
pnpm exec tsx scripts/apply-all.ts
```

The wrapper sequences:
1. Apply migrations 0001 + 0002 to Supabase
2. Seed source_registry (idempotent)
3. Ingest fiscal-transfer canonical FY 2082/83 (753 + 77 + 7 entities + ~6000 transfers)
4. Ingest admin-hierarchy (6,285 wards + 10,203 polling stations + 7M+ voters aggregated)
5. (Skipped if not yet shipped:) Ingest NRB BFI banking facts (Worker ζ output)
6. (Skipped if not yet shipped:) Ingest Census 2021 facts (Worker η output)
7. (Skipped if not yet shipped:) Fix admin-hierarchy constituency mapping (Worker θ output)

`--dry-run` prints the plan. `--from=N` resumes from step N. `--only=N` runs just one step.

After `apply-all` completes, verify in the Supabase dashboard:
- 21 user tables in `public` schema
- The `SELECT count(*)` query at the bottom of the wrapper's output shows the expected row counts

If anything looks wrong: `pnpm exec drizzle-kit drop` rolls back the latest migration; or in the Supabase dashboard nuke the schema and re-run.

---

## Workers status

### Worker δ — OCR Empirical Evaluation (Opus 4.x, in-flight at handoff write)

Ran 4 pipelines (Surya 192 DPI flat / Surya 384 DPI 2×2 tiled / Surya 576 DPI 3×3 tiled / PaddleOCR 300 DPI flat) across 5 representative pages (Yellow Book PE table, Red Book budget page, Intergovernmental transfer table, NRB BFI Nepali notes, worst-scan page).

**Output location:** `docs/research/ocr-eval/page-P[1-5]/{pipeline-{A,B,C,D}.json, source-crop.png, judge-rubric.md}` + `EVALUATION_REPORT.md`.

When δ completes, ADR-0008's TBD routing thresholds (confidence cutoff, seam-disagreement rate) get filled in.

### Worker ε — Devanagari Normalization + Municipality Resolver (Sonnet 4.x, COMPLETE)

PR #20. 79 pytest cases green (12 existing + 67 new). Substitution dict ported byte-for-byte from `Cleaned/manual_match_reasoning.py` (31 entries). `municipality_resolver` loads canonical 753-row table at runtime.

### Worker ζ — NRB BFI XLSX Parser v0.1.0 (Sonnet 4.x, near-complete at handoff write)

Parses C4 (Major Financial Indicators) + C5 (Assets & Liabilities) + C6 (P&L) + C7 (Sector lending) across the 50-file monthly snapshot series. Layout-version-aware (column counts changed across 49 months). Staging JSON produced at `staging-data/nrb-bfi/*.json`.

**TBD on completion:** total banking-sector-fact row count, layout-version count, indicator-slug count.

### Worker η — NPHC 2021 Census Parser (not yet spawned)

Spawn after ζ + δ complete. Brief at `docs/tasks/worker-eta-census-parser.md`. Target: 89 CSVs + 8 Excel → census_facts staging JSON. Phase 1 covers totals + single-axis breakdowns; 2D/3D breakdowns deferred to v0.2.0.

### Worker θ — Constituency Mapping + Admin-Hierarchy Fix (not yet spawned)

Spawn after ζ + δ complete. Brief at `docs/tasks/worker-theta-constituency-mapping.md`. Target: parses `Combined_Constituency_Master_Table.csv` → 165 constituency entities + fills the 90% missing constituency_no on admin-hierarchy.

### Worker κ — Opus Analytical Pass on BFI 49-Month Data (queued)

Brief at `docs/tasks/worker-kappa-bfi-analytical-pass.md`. Spawn after Worker ζ output + live ingest. Produces:
- `docs/research/bfi-49-month-narrative.md` (master findings, 2k–5k words)
- `docs/research/bfi-fact-ledger-claim-drafts.md` (15–30 claims ready for Fact Ledger ingest)
- `docs/research/bfi-monthly-verdict-bhadau-2082.md` (a first draft Monthly Verdict for Sept 2025)

---

## What needs YOUR terminal in the morning

In order:

1. **Apply migrations + run all ingests** — one command:
   ```powershell
   pnpm exec tsx scripts/apply-all.ts
   ```
   This applies migrations 0001+0002 and runs every staged ingest. Idempotent on re-run.

2. **Review + merge PRs** (in this order):
   - **PR #18** — proposal docs (auto-merging)
   - **PR #19** — ADR-0008 + ADR-0009 + SOURCE_REGISTRY rewrite + ingest scripts
   - **PR #20** — Worker ε (Devanagari + municipality resolver)
   - **Worker δ PR** — `docs/ocr-evaluation` branch (Mother opens when δ completes; auto-merged once green)
   - **Worker ζ PR** — `feat/scrapers-nrb-bfi` branch (Mother opens when ζ completes)

3. **(Same as before but still queued)** GitHub Actions deploy secrets + Sentry wizard. Unchanged since the Day 1 handoff. Both detailed in `docs/BOOTSTRAP_USER_ACTIONS.md`.

---

## What's queued for the next Mother session

1. **Spawn Workers η + θ** (Census, Constituency) — both no-OCR; spawn sequentially after ζ + δ done
2. **Spawn Worker κ** — Opus analytical pass on the BFI staged data (will produce the first Monthly Verdict draft, ~15-30 Fact Ledger claims, and the 49-month banking narrative)
3. **Finalize ADR-0008** — fill in the TBD routing thresholds with Worker δ's empirical evidence
4. **First live Fact Ledger ingest** — using the κ-drafted claims and the buildClaimDraftFromIndicatorValue helper (Worker E from prior session)
5. **Phase B parsers** — once OCR routing thresholds harden: intergovernmental prior FYs (Phase B1), Yellow Books (Phase B2), Red Books (Phase B3)

---

## Doctrine moves this session

- **ADR-0008** locks in Surya v0.17.1 + tile-based pipeline + lossless Devanagari numeral handling + 12-item failure-mode mitigation. Final routing thresholds TBD on Worker δ's evidence.
- **ADR-0009** documents the entities + per-domain fact tables already shipped in migration 0002.
- **SOURCE_REGISTRY rewritten** to ~40 entries with `ingestion_mode` enum + Tier 0 (data on disk) + Phase-2 status:paused for HARD sources.
- The **12-item tile-stitch failure-mode catalogue** is fully encoded in the `ocr_*` schema tables — operator can SQL-query "where did this parser run struggle?" without re-running.

---

## Open follow-ups inline per worker

(See each worker's PR for their own open-question list. Major ones:)
- **ε**: should the four no-op substitutions be pruned? Federal code 8-digit assertion?
- **ζ**: TBD — confirm on commit
- **δ**: TBD — the routing-rule recommendation

---

## What I deliberately did NOT do

- Apply migrations to live Supabase (system permission rule + my own doctrine — your `apply-all` runs it)
- Touch the Voter DB SQL dumps (PII; not for our DB)
- Read `Voter DB scrape/.env` (credentials)
- Deploy to Cloudflare Workers (still queued on you setting GH Actions secrets)
- Run the Sentry wizard (interactive)
- Spawn Workers η, θ, κ before ζ + δ complete (filesystem contention risk; sequential preferred)

---

*Mother Opus signing off. Repo: https://github.com/SushantChalise/nepal-ledger. The migration awaits your `apply-all`. The first Fact Ledger claim is one ingest run away.*
