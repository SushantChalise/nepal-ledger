# Nepal Ledger — Data Build-out Dispatch Plan

**Date:** 2026-06-07
**Status:** Execution-ready dispatch plan synthesized from 35 per-item build specs.
**Owner:** Mother (orchestrator). Workers execute scope-fenced briefs from this doc.

> Mission anchor: *track whether Nepal's money becomes wealth.* Every item below is graded on whether it feeds a Pillar (Money In / Out / Captured / Wasted / Becomes Wealth) or a Lens.

---

## 1. Situation Summary

Live in Supabase today: **approved_indicator_values** (492 series rows: CMEFs 7 + NCPI 78 + tourist 407), **dne_facts** (38,490 Foreign-Trade-by-commodity dimensional rows), **local_government_fiscal_transfers** (6,008), **banking_sector_facts** (2,088; C5 balance-sheet only, 58 months), **census_facts** (531,618; 753 palikas, 11 NPHC-2021 tables), **entities** (753 local-level), **source_registry** (68 rows, many `status=paused`). Two pages are live: `/pulse` and `/money-map`. The ingestion machinery is mature: indicator-series sources flow staging→validation→approved via `ingestSource()`; typed fact tables (dne_facts, banking, fiscal-transfers, census) use dedicated `scripts/ingest-*.ts` + `bulkInsert*` repos. Python parsers are deterministic (ADR-0003). The dominant un-shipped value is (a) the rest of the **NRB DNE** sectors (fiscal, financial, real, monetary), (b) **MoF/FCGO/PDMO** fiscal-actuals PDFs, and (c) render lenses over data **already in the DB but unrendered** (tourism arrivals, district MRI, census choropleths, fact-ledger provenance).

---

## 2. Ranked Work Items

Sorted by **value desc, then effort asc**. `PS` = parallelSafe. "Shared files" = the cross-cutting files that force serialization (see §3).

| # | id | kind | value | effort | PS | depends-on / shared-file chokepoint |
|--|----|------|:----:|:----:|:--:|----|
| 1 | nrb-concessional-loan | scraper | 5 | 3 | ✅ | own folder; only `seed-source-registry.ts` status-flip |
| 2 | fcgo-consolidated-financial-statements | scraper | 5 | 3 | ✅ | own folder; `seed-indicators.ts` (+8 slugs, integration) |
| 3 | pdmo-monthly-debt-statistics | scraper | 5 | 3 | ⚠️ | `seed-indicators.ts` (+4 slugs) + `package.json` |
| 4 | dne-fiscal-sector-download-parse | scraper | 5 | 3 | ❌ | **`nrb_dne/parser.py`** + `seed-indicators.ts` |
| 5 | nrb-db-fiscal-sector | scraper | 5 | 3 | ❌ | **`nrb_dne/parser.py`** + `seed-indicators.ts` + `seed-source-registry.ts` (≈ dup of #4 — see note) |
| 6 | dne-monetary-sector-download-parse | scraper | 5 | 3 | ✅ | own files unless novel layout → `nrb_dne/parser.py` |
| 7 | customs-monthly-trade | scraper | 5 | 4 | ✅ | own folder; `seed-source-registry.ts` status-flip + `package.json` |
| 8 | mof-economic-survey-parser | pdf-parser | 5 | 4 | ✅ | own folder; `seed-indicators.ts` + `seed-source-registry.ts`; **new ADR-0016** |
| 9 | nrb-db-real-sector | scraper | 5 | 4 | ❌ | **`nrb_dne/parser.py`** (quarterly layout) + `seed-indicators.ts` |
| 10 | dne-real-sector-download-parse | scraper | 5 | 4 | ❌ | **`nrb_dne/parser.py`** (quarterly) + `seed-indicators.ts` (≈ dup of #9 — see note) |
| 11 | mof-redbook-budget-parser | pdf-parser | 5 | 5 | ❌ | new schema+migration + `schema/index.ts` + `enums.ts` + **new ADR**; code-dictionary |
| 12 | mof-whitebook-foreign-aid-parser | pdf-parser | 5 | 4 | ✅ | own folder + new `foreign_aid_facts` table; `schema/index.ts` + migration + **new ADR** |
| 13 | nrb-financial-stability-report | scraper | 4 | 3 | ❌ | `seed-indicators.ts` + `seed-source-registry.ts` + `pyproject.toml` + `package.json` |
| 14 | nrb-economic-bulletin | scraper | 4 | 3 | ✅ | own folder; `seed-source-registry.ts` (edit row) + `seed-indicators.ts` + `package.json` |
| 15 | nrb-central-bank-balance-sheet-daily | scraper | 4 | 3 | ✅ | own folder; `seed-indicators.ts` (+5 slugs) + `package.json` |
| 16 | promote-fx-bop-single-series-approved | data-quality | 4 | 2 | ✅ | `seed-indicators.ts` only (curated allowlist) — NO parser edit |
| 17 | kalimati-daily-prices | scraper | 4 | 3 | ✅ | own folder; `seed-source-registry.ts` flip + `package.json` |
| 18 | ft-sitc-groupwise-dimensional | dne-dimensional | 4 | 2 | ❌ | **`nrb_dne/parser.py`** |
| 19 | ft-direction-of-trade-partner-dimensional | dne-dimensional | 4 | 3 | ❌ | **`nrb_dne/parser.py`** |
| 20 | nrb-annual-report | scraper | 4 | 4 | ✅ | own folder; `seed-indicators.ts` + `pyproject.toml` + `package.json` |
| 21 | mof-budget-speech | scraper | 4 | 4 | ✅ | **BLOCKED** (no PDF on disk); own folder; `seed-indicators.ts` + `package.json` |
| 22 | dne-financial-sector-download-parse | scraper | 4 | 4 | ❌ | **`nrb_dne/parser.py`** (2 new dimensions) + `seed-indicators.ts`; ADR-0015 amend |
| 23 | nrb-db-financial-sector | scraper | 4 | 4 | ❌ | **`nrb_dne/parser.py`** + reconciliation; **new ADR-0016** (≈ overlaps #22) |
| 24 | mof-yellowbook-soe-parser | pdf-parser | 4 | 4 | ✅ | own folder; `pyproject.toml` + `package.json`; **new ADR** (dne_facts reuse) |
| 25 | moald-agriculture-statistics-parser | pdf-parser | 4 | 4 | ❌ | new `agriculture_facts` table + `schema/index.ts` + migration + **new ADR** + district crosswalk |
| 26 | district-mri-dashboard | render | 4 | 3 | ✅ | own feature/route; `CHANGELOG.md` only |
| 27 | tourism-rupee-arrivals-series | render | 4 | 3 | ✅ | own feature/route + new `viz/adapters/d3-shape.ts` |
| 28 | migration-remittance-source-map | render | 4 | 3 | ✅ | View A own folder; View B needs GeoJSON + `seed-source-registry.ts` (defer) |
| 29 | census-asset-entrepreneurship-choropleth | render | 4 | 4 | ✅ | own feature + new `viz/adapters/d3-geo.ts`; `seed-source-registry.ts` (+1 row) + `package.json` deps |
| 30 | fact-ledger-index | render | 4 | 3 | ✅ | own feature/route; `repositories/index.ts` barrel (+1 line) |
| 31 | nrb-db-external-sector | scraper | 3 | 3 | ❌ | **`nrb_dne/parser.py`** (migrant bug-fix + Direction/SITC sheets) |
| 32 | remittance-by-source-country-dimensional | dne-dimensional | 3 | 4 | ❌ | **`nrb_dne/parser.py`**; ADR-0015 correction |
| 33 | remittance-datetime-period-sheet | pdf-parser | 3 | 2 | ⚠️ | **`nrb_dne/parser.py`** only (no other shared file) |
| 34 | remittance-by-recipient-district-dimensional | dne-dimensional | 2 | 2 | ❌ | **`nrb_dne/parser.py`**; mislabeled (see §6) |
| 35 | banking-sector-timeseries | render | 3 | 5 | ❌ | **BLOCKED** on C7 parser in `nrb_bfi/parser.py` + repo reader (see §6) |

### Critical de-duplication note
Several specs are **near-duplicate pairs** describing the same underlying work from two framings — dispatch ONE of each, not both:
- **#4 `dne-fiscal-sector-download-parse` ≈ #5 `nrb-db-fiscal-sector`** — both: download 3 fiscal XLSX, seed slugs, ingest. Prefer #4's framing (uses `--source-id nrb-dne-xlsx` umbrella, simpler FK). Fold #5's source-profile status-flip into it.
- **#9 `nrb-db-real-sector` ≈ #10 `dne-real-sector-download-parse`** — both: download real-sector XLSX + add quarterly-GDP layout to parser.py. Dispatch as ONE brief.
- **#22 `dne-financial-sector-download-parse` ≈ #23 `nrb-db-financial-sector`** — both: financial-sector XLSX, sector-loans dimensional, reconcile vs banking C7. Dispatch as ONE brief; the reconciliation ADR is shared.

Treat each pair as a single task. This collapses 35 specs to ~32 real tasks.

---

## 3. Shared-File Conflict Map (the serialization constraint)

A wave may run ≤8 workers **only if no two touch the same file**. The chokepoints:

| Shared file | Items that edit it | Rule |
|---|---|---|
| **`scrapers/nrb_dne/parser.py`** | #4/5, #9/10, #18, #19, #22/23, #31, #32, #33, #34 (10 tasks) | **STRICT SERIAL.** Max ONE per wave. This is the single biggest constraint. |
| `scripts/seed-indicators.ts` | #2, #3, #4/5, #8, #9/10, #13, #15, #16, #20, #21, #22/23 | Additive blocks. Safe if ≤1 per wave **or** Mother lands the seed edits at integration (preferred — hand workers the slug list). |
| `scripts/seed-source-registry.ts` | #1, #7, #13, #14, #17, #29 (+status flips) | Mostly 1-line status flips. Safe if ≤1 per wave or Mother batches. |
| `src/lib/db/schema/index.ts` + new migration | #11, #12, #25 | **SERIAL** — Mother owns migrations (root CLAUDE.md). Max ONE new-fact-table per wave. |
| `package.json` (script line) | nearly every scraper/render | 1-line appends; trivially rebased. Not a true blocker but order them. |
| `scrapers/pyproject.toml` | #13, #20, #24 | Additive `packages.find`/`testpaths`. Low collision. |
| `src/lib/viz/adapters/` (new files) | #27 (`d3-shape.ts`), #29 (`d3-geo.ts`) | Different files → safe together. |

**Operating rule for `nrb_dne/parser.py`:** serialize all 10 DNE-parser tasks through a single branch, sequenced by value: #4/5 → #9/10 → #18 → #19 → #22/23 → #31 → #32 → #33 → #34. They never share a wave.

---

## 4. Phased Execution Plan (parallel waves, ≤8 workers, conflict-free)

Each wave is a parallel batch. Within a wave, **no two items touch the same file**. The single `nrb_dne/parser.py` slot per wave is the gating resource; everything else is genuinely independent.

### Wave 1 — Highest value, zero/low shared-file contention (8 workers)
The "ship now" batch. All either own brand-new folders or touch only disjoint files. One DNE-parser slot (#4/5).

| Worker | Item | Why conflict-free |
|--|--|--|
| W1 | **#1 nrb-concessional-loan** (v5,e3) | own `scrapers/nrb_concessional_loan/` + new ingest CLI; only shared touch = seed-registry status flip |
| W2 | **#2 fcgo-consolidated-financial-statements** (v5,e3) | own `scrapers/fcgo_consolidated/`; seed-indicators edit deferred to Mother |
| W3 | **#6 dne-monetary-sector-download-parse** (v5,e3) | download + run existing parser; touches NO shared file unless novel layout (escalate if so) |
| W4 | **#16 promote-fx-bop-single-series** (v4,e2) | edits only `seed-indicators.ts` allowlist + docs; no parser, no registry |
| W5 | **#26 district-mri-dashboard** (v4,e3) | render; own `src/features/district-mri/` + `/districts` route; data already live |
| W6 | **#27 tourism-rupee-arrivals-series** (v4,e3) | render; own feature + new `d3-shape.ts`; data already live |
| W7 | **#30 fact-ledger-index** (v4,e3) | render; own `src/features/fact-ledger/`; only `repositories/index.ts` +1 line |
| W8 | **#4/5 dne-fiscal-sector** (v5,e3) | **the DNE-parser slot.** download + seed + ingest fiscal XLSX |

Conflict check: W4, W8 both can touch `seed-indicators.ts` → **Mother lands seed-indicators edits at integration** (hand W4/W8 their slug lists; they return the list, Mother merges). W1/W8 both touch `seed-source-registry.ts` → W1 is a status flip, W8 may flip the fiscal row; sequence W1's commit first or Mother merges. With seed edits centralized, the wave is clean.

### Wave 2 — Second value tier; next DNE-parser slot + new-fact-table slot (8 workers)

| Worker | Item | Why conflict-free |
|--|--|--|
| W1 | **#7 customs-monthly-trade** (v5,e4) | own `scrapers/customs_trade/`; reuses dne_facts (no migration) |
| W2 | **#8 mof-economic-survey-parser** (v5,e4) | own `scrapers/mof_economic_survey/`; **claims ADR-0016** (see §3 ADR note) |
| W3 | **#12 mof-whitebook-foreign-aid** (v5,e4) | **new-fact-table slot** (`foreign_aid_facts`); own folder + migration |
| W4 | **#15 nrb-central-bank-balance-sheet-daily** (v4,e3) | own folder; seed +5 slugs (hand to Mother) |
| W5 | **#17 kalimati-daily-prices** (v4,e3) | own `scrapers/kalimati/`; registry flip + package.json |
| W6 | **#28 migration-remittance-source-map (View A only)** (v4,e3) | render; own feature; View B deferred (no GeoJSON dep) |
| W7 | **#29 census-asset-entrepreneurship-choropleth** (v4,e4) | render; own feature + new `d3-geo.ts`; GATE-0 GeoJSON join-test first |
| W8 | **#9/10 nrb-db-real-sector** (v5,e4) | **the DNE-parser slot.** quarterly-GDP layout + real-sector XLSX |

Conflict check: W3 and W8... W3 adds a migration + `schema/index.ts`; W8 edits `nrb_dne/parser.py` + `seed-indicators.ts` — disjoint. W7 + W5 both touch `seed-source-registry.ts` (W7 +1 row, W5 status flip) and `package.json` — Mother sequences these two appends. W2/W8 both touch `seed-indicators.ts` → centralize at Mother. Clean.

### Wave 3 — Third tier; DNE-dimensional follow-ons + remaining PDFs (8 workers)

| Worker | Item | Why conflict-free |
|--|--|--|
| W1 | **#3 pdmo-monthly-debt-statistics** (v5,e3) | own `scrapers/pdmo_monthly_debt/`; seed +4 slugs |
| W2 | **#11 mof-redbook-budget-parser** (v5,e5) | **new-fact-table slot** (`redbook_facts`) + code-dictionary; **ADR** |
| W3 | **#24 mof-yellowbook-soe-parser** (v4,e4) | own `scrapers/mof_yellowbook/`; reuses dne_facts; **ADR** |
| W4 | **#13 nrb-financial-stability-report** (v4,e3) | own `scrapers/nrb_fsr/`; seed + registry + pyproject |
| W5 | **#14 nrb-economic-bulletin** (v4,e3) | own `scrapers/nrb_economic_bulletin/`; XLSX (not PDF — see spec) |
| W6 | **#20 nrb-annual-report** (v4,e4) | own `scrapers/nrb_annual_report/`; seed + pyproject |
| W7 | **#18 ft-sitc-groupwise-dimensional** (v4,e2) | **the DNE-parser slot.** SITC sheet → dne_facts |
| W8 | *(reserve / View B of #28 if GeoJSON sourced)* | — |

Conflict check: W2 (redbook) is the migration slot — W3 (yellowbook) reuses dne_facts (no migration) so they don't collide on `schema/index.ts`. W4 edits `seed-source-registry.ts` + `pyproject.toml`; W6 also edits `pyproject.toml` → sequence those two appends. W1/W4/W6 all touch `seed-indicators.ts` → **centralize at Mother**. W7 is the lone parser slot. Clean.

### Wave 4 — Remaining DNE-parser-serial tail (mostly serial — small batch)
These almost all touch `nrb_dne/parser.py`, so they run largely one-at-a-time. Pair each parser task with one independent render/data task to keep throughput up.

| Sequence | Item | Note |
|--|--|--|
| 4a | **#19 ft-direction-of-trade-partner** (v4,e3) | DNE-parser slot |
| 4b | **#22/23 dne-financial-sector** (v4,e4) | DNE-parser slot + reconciliation ADR (after #18 SITC lands) |
| 4c | **#31 nrb-db-external-sector** (v3,e3) | DNE-parser slot; **fixes the migrant-worker mis-parse bug** |
| 4d | **#32 remittance-by-source-country** (v3,e4) | DNE-parser slot; ADR-0015 correction (migrant headcounts, not NPR) |
| 4e | **#33 remittance-datetime-period-sheet** (v3,e2) | DNE-parser slot |
| 4f | **#34 remittance-by-recipient-district** (v2,e2) | DNE-parser slot; **rename before build** (see §6) |
| ‖ | **#25 moald-agriculture** (v4,e4) | runs PARALLEL to the DNE serial chain — own folder + own `agriculture_facts` migration slot |

`#25` and `#33`/`#19` etc. are conflict-free (agriculture touches its own table + parser folder, not `nrb_dne/parser.py`), so run #25 alongside whichever DNE-parser task is active. Note #31/#32/#33/#34 all operate on the **same** `Migrant-Workers-Remittance.xlsx` — coordinate so the migrant-bug-fix (#31) lands first, then the dimensional country/district/datetime sheets build on the corrected routing.

---

## 5. Top-8 Dispatch-Ready Briefs (concrete steps + files)

For the highest-value items, the next round can dispatch workers directly from these.

### #1 — nrb-concessional-loan (v5, e3, PS) — Wave 1
**Goal:** Scrape NRB Interest-Subsidized Loan monthly XLSX (~75 months) → `dne_facts` (program/sector dimension). Reuses ADR-0015 (no migration). URL live (HTTP 200, 393KB, Last-Modified 2026-05-14).
**Steps:** (1) DOWNLOAD one real XLSX (`.../2026/05/Interest-subsidized-loan-Chaitra-2082-Publish.xlsx`) → `Financial Data/nrb_concessional_loan/`; openpyxl-dump the geometry (parser cannot be written blind — BFI/DNE layouts don't transfer). (2) Scaffold `scrapers/nrb_concessional_loan/` as a sibling package; lift BFI period machinery (`_MONTH_ALIAS_TO_CANONICAL`, `_FILENAME_RE`) from `scrapers/nrb_bfi/parser.py`. (3) Emit `DneFactRow`-shaped dimensional dicts: `base_indicator_slug='concessional-loan-outstanding'`/`-borrower-count`, `dimension_kind='program'`, kebab dimension_value, confidence A. (4) Thin `scripts/ingest-concessional-loan.ts` modeled on `ingest-dne-dimensional.ts` (it hardcodes the DNE source-id, so copy not reuse); `bulkInsertDneFacts` from `@/lib/db/repositories/dne-facts`. (5) pytest with synthetic fixture (no 393KB binary). (6) Dry-run. (7) Doc gate: flip `docs/sources/nrb-concessional-loan.md` + `seed-source-registry.ts:1158-1167` paused→active.
**Files:** `scrapers/nrb_concessional_loan/{__init__,parser,README}.py/md` + `tests/`, `scripts/ingest-concessional-loan.ts`, `package.json`, `docs/sources/nrb-concessional-loan.md`.
**ADRs:** 0003, 0015, 0010, 0013.

### #2 — fcgo-consolidated-financial-statements (v5, e3, PS) — Wave 1
**Goal:** Parse FCGO Consolidated Financial Statements (audited all-of-gov outturn, English FY2018/19+). 6 headline aggregates. PDFs verified on disk, clean Latin text layer (no OCR).
**Steps:** (1) Create `scrapers/fcgo_consolidated/` (**underscore** dir, not the hyphenated profile path — Python-importable). (2) pdfplumber text-extract skeleton from `nrb_cmefs/parser.py`, but **scan all pages** for the Executive Summary (page drifts across editions). (3) Encode 6-8 indicators as **alternation** regexes (phrasing drifts: `is|amounts to|stands at`, `total revenue collection|total Receipt`). Capture NPR with commas. unit=npr_million, annual, confidence A; typed `PageLayoutChanged` on miss. (4) AD-FY→BS via +57 (ADR-0013), local `annual_span_ad()` helper (do NOT edit `_common/periods.py`). (5) CLI `scripts/ingest-fcgo-cfs.ts` (clone `ingest-cmefs.ts`). (6) pytest with synthesized text-layer PDFs covering both phrasings. (7) Dry-run.
**Mother at integration:** add ~8 FCGO slugs to `seed-indicators.ts` (else 0 promoted), 1-line `package.json`.
**Files:** `scrapers/fcgo_consolidated/*`, `scripts/ingest-fcgo-cfs.ts`, `package.json`, `seed-indicators.ts`, `docs/sources/fcgo-consolidated-financial-statements.md`.
**ADRs:** 0003, 0013, 0009/0010.

### #4/5 — dne-fiscal-sector (v5, e3, ❌ DNE-parser slot) — Wave 1
**Goal:** Download + ingest 3 fiscal XLSX (Govt budgetary operation, revenue, outstanding debt) → `approved_indicator_values` (single-series). Defer the DAILY Govt-Revenue-and-Expenditure file (parser has no daily layout).
**Steps:** (1) DOWNLOAD from sector page (URLs embed `/2025/07/` dates — re-resolve, don't hardcode; expect TLS sandbox block → out-of-sandbox fetch). (2) DRY-RUN each: `pnpm ingest:dne --dry-run --input <file>` — parser v0.5.0 already handles standard-wide BS+AD annual + monthly. (3) IF 0 rows / PeriodUnparseable → minimal parser branch + version bump + regression test (<300 line diff). (4) **SEED (the real blocker):** collect emitted `dne-*` slugs, add to `DNE_INDICATORS` in `seed-indicators.ts` (only `dne-tourist-arrival` exists today; unseeded slugs BLOCK at promotion — `promote.ts:26`). (5) LIVE: `pnpm ingest:dne --input <file> --source-id nrb-dne-xlsx`. (6) Doc: README matrix + source profile status.
**Files:** 3 XLSX downloads, `seed-indicators.ts`, `nrb_dne/parser.py` (only if layout fix), `nrb_dne/README.md`, `docs/sources/nrb-dne-xlsx.md`.
**ADRs:** 0013, 0014, 0010, 0003. **Fold in** #5's `nrb-db-fiscal-sector` profile flip.

### #6 — dne-monetary-sector-download-parse (v5, e3, PS) — Wave 1
**Goal:** Download + ingest Monetary Survey XLSX (M1/M2/broad money/reserve money/NFA/domestic credit) → `approved_indicator_values`. Parser ALREADY exists (v0.5.0 covers all 5 sectors); this is download + parser-fit-verify + ingest, NOT new parser work.
**Steps:** (1) DOWNLOAD from financial-sector page (URL embeds upload date — resolve live; Monetary Survey lives under Financial Sector taxonomy). (2) `pnpm ingest:dne --dry-run --input "Financial Data/nrb_dne/Monetary-Survey.xlsx"` — expect standard wide single-series, NO code change. (3) IF novel multi-block balance-sheet layout → **escalate** (becomes non-PS, needs parser branch — coordinate with DNE-parser slot holder). (4) Add fixture+test. (5) LIVE `--source-id nrb-dne-xlsx`; seed any `dne-*` slugs if 0 promoted. (6) README matrix + INGEST_RUNBOOK row.
**Files:** `Monetary-Survey.xlsx`, `nrb_dne/tests/`, `nrb_dne/README.md`, `INGEST_RUNBOOK.md` (parser.py ONLY if novel layout).
**ADRs:** 0003, 0009/0010, 0013, 0015 (N/A — single-series).

### #8 — mof-economic-survey-parser (v5, e4, PS) — Wave 2
**Goal:** Parse MoF Economic Survey statistical-annex tables → `approved_indicator_values` (5-10 flagship indicators, English 2023-24 edition only). PDF on disk.
**Hard truth (verified):** front-matter is CID-broken (subsetted fonts, no ToUnicode; pdfplumber→`(cid:N)`, poppler→Caesar-shifted with dropped digits — **NOT parseable**). Only the BACK statistical annex extracts real digits, but **word-reversed and line-scrambled** (bidi artifact). Scope = annex tables ONLY via line-reversal + coordinate column reconstruction. **No OCR** (ADR-0003).
**Steps:** (1) Write **ADR-0016** recording annex-only scope + CID-broken front-matter. (2) Parser: pdfplumber per-page, locate annex pages by matching **reversed** title tokens (`line[::-1]`), reconstruct rows by sorting `.chars`/words by `(top, x0)` then reversing token order; parse numeric cells. Emit `StagingRowDraft` annual, confidence A (B on P/R markers), typed errors on miss. (3) Tests on extracted annex-page text fixtures (not the 5MB PDF). (4) Seed ES slugs + source-map; flip `mof-economic-survey-annual` ingestionMode `reference_only`→`manual_upload`. (5) CLI clone of `ingest-cmefs.ts`. (6) Dry-run → live.
**Files:** `scrapers/mof_economic_survey/*`, `scripts/ingest-economic-survey.ts`, `seed-indicators.ts`, `seed-source-registry.ts`, `docs/decisions/0016-economic-survey-annex-only-parsing.md`.
**ADRs:** 0003, 0009/0010, 0011, **new 0016**.

### #9/10 — nrb-db-real-sector (v5, e4, ❌ DNE-parser slot) — Wave 2
**Goal:** Download + ingest National Accounts, CPI, Agriculture, Energy, **Quarterly-GDP (Old+New base)** → mostly `approved_indicator_values`. GDP/CPI are the per-capita denominator for the mission.
**Steps:** (1) DOWNLOAD 5-6 XLSX (audit lines 254-276; TLS bypass per round-5 workaround). (2) DRY-RUN each — National-Accounts/CPI/Agri/Energy parse on existing v0.5.0 annual/monthly. (3) **ADD QUARTERLY (the hard part):** `_detect_header` emits only annual/monthly; add `_parse_quarter_fy` + `quarterly` branch (enum already supports it) for `2081/82Q2` headers; bump PARSER_VERSION. (4) **Old-vs-New base-year:** qualify slugs per series (`-old`/`-new` or base-year suffix) — identical row labels collide on `(indicator, period)` in approved; never merge (Data Continuity Protocol). (5) Decide dimensional-vs-single-series routing per file (National-Accounts/Agri may be matrices → dne_facts). (6) SEED curated single-series slugs in `seed-indicators.ts`; live ingest. (7) Quarterly fixture + tests.
**Fallback:** if quarterly proves heavy, ship National-Accounts + Provincial-GDP (annual) first, defer Quarterly-GDP.
**Files:** 5-6 XLSX, `nrb_dne/parser.py` (quarterly), `nrb_dne/tests/{conftest,test_parser}.py`, `seed-indicators.ts`, `nrb_dne/README.md`, `docs/sources/nrb-db-real-sector.md`.
**ADRs:** 0013, 0014, 0015, 0003, 0011.

### #26 — district-mri-dashboard (v4, e3, PS render) — Wave 1
**Goal:** Per-district dashboard for 5 launch districts (Kathmandu, Chitwan, Kaski, Jhapa, Morang) over **live** census_facts + fiscal_transfers. No scraper/migration — pure render.
**LOAD-BEARING CORRECTION:** roll-up palika→district is via `entities.metadata->>'district_en'` (a NAME string), **NOT** `federal_code` (the 8-digit code does NOT encode district — confirmed in `generate_crosswalk.py`). There are **no** `kind='district'` entities. A worker following "federal_code" verbatim builds a broken join.
**Steps:** (1) Read `money-map/server/queries.ts` (safeQuery + Zod-at-boundary), `pulse/page.tsx` (typed states). (2) `launch-districts.ts` registry: 5 `{slug, districtEn, nameEn, province}`; `districtEn` must equal `metadata->>'district_en'` exactly. (3) `getDistrictMriData(districtEn)`: two `safeQuery` aggregations joining on `e.metadata->>'district_en'=$1` (fiscal grants-by-type; census via explicit slug **allowlist** — do NOT LIKE-match). (4) Derive % from each table's own `rowtotal` denominator (multi-row tables → filter sexname='Total'). (5) `MissingDataPanel` for un-ingested Pillar fields (remittance NPR, capex rate, crops, disaster) — never fabricate/zero-fill. (6) `format.ts` plain (NOT 'use client' — money-map gotcha). (7) `/districts/[district]/page.tsx` + `generateStaticParams`. (8) `CLAUDE.md` (Doc Gate).
**Files:** `src/features/district-mri/*`, `src/app/districts/{page,[district]/page}.tsx`, `CHANGELOG.md`.
**ADRs:** 0011, 0012 (likely no D3 needed). Gates: typecheck/lint/build + UI_ACCEPTANCE + Doc Gate.

### #27 — tourism-rupee-arrivals-series (v4, e3, PS render) — Wave 1
**Goal:** 34-year monthly tourist-arrivals line chart (`dne-tourist-arrival`, 407 rows live, 1992–2025). Pure render.
**GOTCHA (verified):** plot on `reporting_period_ad_end` (real Gregorian month-end), **NOT** `reporting_period_bs` — BS labels skew near COVID (parser transposed layout-4 mid-month approximation). Latest = Mangsir 2082 = 116,553; COVID trough Apr 2020 = 14 arrivals (annotation anchor). Source label = "Nepal Rastra Bank — Database on Nepalese Economy", Grade B (NOT the paused `ntb-tourism-monthly` stub).
**Steps:** (1) `getTouristArrivalsSeries()`: query approved JOIN indicators WHERE slug=`dne-tourist-arrival` ORDER BY ad_end; Zod boundary; return points + latest + yoyPct. (2) New `src/lib/viz/adapters/d3-shape.ts` (sanctioned cast location, ADR-0012; wraps `line()`/`scaleTime`/`scaleLinear`; verify/add `d3-scale`). (3) `ArrivalsLineChart.tsx` ('use client', ResizeObserver like SankeyDiagram, COVID reference marker, sr-only `<table>`, prefers-reduced-motion). (4) `format.ts` plain (`formatCount` compact). (5) `page.tsx` reuse Pulse `KpiCard`; "what this shows" + source/confidence/unit footer; "Corridor leakage — coming soon" disabled placeholder (do NOT fabricate). (6) `CLAUDE.md`.
**Files:** `src/app/tourism-rupee/page.tsx`, `src/features/tourism-rupee/*`, `src/lib/viz/adapters/d3-shape.ts`.
**ADRs:** 0012, 0003, 0011. Gates: typecheck/lint/build + drizzle-kit check (no schema change).

---

## 6. Known Infeasible / Blocked / Mislabeled

- **#35 banking-sector-timeseries (v3,e5) — INFEASIBLE as a pure render today.** The slugs it needs (`sector-credit-*`, `npl-by-sector-*`) **do not exist** — `nrb_bfi/parser.py` parses ONLY sheet C5 (balance-sheet); sector lending/NPL live on sheet **C7**, which no parser extracts. The named slugs appear only in a schema doc-comment. **Prerequisite data-pipeline task:** extend `nrb_bfi/parser.py` to parse C7 + re-ingest the 50/58-file corpus, AND add a time-series reader to `repositories/banking-sector-facts.ts` (currently write-only). Until then, the only honest render is a C5 balance-sheet series (different, lower-value page). Unit is `npr_million` not `npr_crore`.
- **#21 mof-budget-speech (v4,e4) — ACQUISITION-BLOCKED.** No Budget Speech PDF anywhere on disk (0 of 64 PDFs); `mof.gov.np` SSL chain is incomplete and blocks sandbox fetches; Wayback blocked. The CDN holds the file but its token URL is only discoverable via the SSL-blocked listing page. **Do NOT dispatch as a Wave worker** until a human/Mother drops the EN PDF into `Financial Data/mof_documents/budget_speech/` or fixes the MoF CA trust store out-of-sandbox. Code itself is CMEFs-easy (~250 lines).
- **#34 remittance-by-recipient-district (v2) — MISLABELED, rename before build.** The `district` sheet is titled "Migrant Workers by District" = **person-counts of departing workers by district of ORIGIN**, NOT remittance NPR by recipient district. No remittance-NPR-by-district sheet exists in the NRB DNE catalog. Powers a "where labor departs" (Money-OUT) view, not "where money lands." Worker MUST escalate the rename + base-measure naming (`dne-migrant-workers-*`, unit=count) to Mother before coding (ADR-0011 data-unit verification).
- **#32 remittance-by-source-country (v3) — semantic correction.** Same file: values are migrant-worker HEADCOUNTS (Male/Female/Total), NOT remittance rupees. base_indicator_slug=`dne-migrant-workers`, unit=`count`. ADR-0015 lines 24/53 wrongly imply `dne-remittance-inflow` for this file — correct the ADR. Lower value (3) because the labeled deliverable (remittance-by-country money) is unavailable.
- **#28 migration-remittance-source-map View B (district choropleth) — DEFER.** No Nepal district GeoJSON in repo, no `d3-geo`/`topojson` deps, and district identity is NOT derivable from federal-code substring. Needs a new GeoJSON source registration (ADR-0009) + a new `(prov,dist)→district-name/P-code` crosswalk + ADR-0012 amendment. Ship **View A** (country-ranking bar chart, fully live data) now; spin View B as a separate gated task.
- **#29 census choropleth — GATE-0 risk (not blocked, but may escalate).** Data is live and verified, but **no 753-palika GeoJSON keyed to the 8-digit federal code exists in repo**. STEP 0 must download an open-licensed boundary file (Open Knowledge Nepal CC-BY-4.0 / OCHA HDX), rekey every feature to the federal code via `palika_code_crosswalk.csv`, and **hard-assert 753/753 join**. If the join falls short, STOP and escalate — do not ship a partial-coverage map (never fabricate). Page MUST label metrics "female house/land ownership", "household entrepreneurship", "internet access" — there is NO census bank-account/loan table; do NOT say "financial inclusion".

**ADR-0016 number contention (resolve at Mother):** specs #8, #11, #12, #23, #24, #25 each propose "ADR-0016". Next free number is genuinely 0016. Assign sequentially at integration (e.g. 0016 economic-survey-annex, 0017 redbook-numeric-code, 0018 foreign-aid-fact-model, 0019 financial-sector-dimensions, 0020 yellowbook-soe, 0021 agriculture-facts) — do NOT let two workers both write `0016-*.md`.

---

## Render Track (parallelizes independently of the data track)

The 5 render items (#26, #27, #28-ViewA, #29, #30) and #35 (blocked) are **fully independent of every scraper/DNE-parser task** — they touch only `src/features/<name>/`, `src/app/<route>/`, and at most one new `src/lib/viz/adapters/*` file each (#27 d3-shape, #29 d3-geo — different files). They read data already live in the DB; no ingest, no migration. **They can saturate spare worker slots in any wave** without contending on `nrb_dne/parser.py`, `seed-indicators.ts`, or `seed-source-registry.ts`. Recommended placement: #26/#27/#30 in Wave 1, #28-ViewA/#29 in Wave 2. Shared invariants across all: copy `money-map` Result<T>+safeQuery+Zod-at-boundary, keep `format.ts` a plain (non-'use client') module, typed empty/error states (never throw), sr-only accessible `<table>` + <640px fallback (UI_ACCEPTANCE), new feature folder ⇒ `CLAUDE.md` (Doc Gate). Only cross-touch: #30 adds 1 line to `repositories/index.ts`; #29 adds 1 source row + deps. Everything else is greenfield.
