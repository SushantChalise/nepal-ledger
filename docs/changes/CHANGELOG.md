# Project Change Log

Append-only, reverse-chronological. Each entry captures where reality diverged from the canonical strategy plan and why.

Strategy plan: [`docs/STRATEGY.md`](../STRATEGY.md) (in-repo, canonical).

Format and rules: [CHANGE_CONTROL.md](../CHANGE_CONTROL.md).

---

## 2026-06-07 (round 8) — Wave 3: GDP/CPI real-sector, labour annex, SOE page + ingest resilience

**What changed:** Ran Wave 3 as a 3-worker parallel batch (one DNE-parser slot + one new PDF parser + one render page), then root-caused and fixed a connection-resilience bug that was silently aborting chatty ingests. The mission's per-capita denominators (GDP, CPI) are now live.

- **DNE real-sector → GDP + CPI live** (parser v0.6.0, Worker A): National-Accounts + CPI + Provincial-GDP. Headline series in `approved_indicator_values` (50yr GDP, 52yr CPI): **nominal GDP FY2081/82 = NPR 6,107 bn (~6.1 trillion)**, real GDP 2,798 bn, per-capita **USD 1,496**, real growth 4.61%, CPI 166.2, inflation 5.44%. Unit is `npr_billion` (sheet header "Rs. in billion"; ADR-0011 — a 10³ trap avoided). **Provincial-GDP → 49 `dne_facts`** (7 provinces, `dimension_kind='province'`; Bagamati NPR 2.23 tn). Province sum ≈ 88% of national (taxes-less-subsidies + statistical discrepancy) ✓. Deferred (documented): GVA-by-industry, Quarterly-GDP (base-year discontinuity), Energy/Agriculture (unit reconciliation).
- **MoF Economic Survey annex parser** (`scrapers/mof_economic_survey/`, Worker B, [ADR-0016](../decisions/0016-economic-survey-annex-only-parsing.md)): the EN edition's headline macro annex is **RTL-mirrored** (char/column/row-reversed) and the Nepali editions' annex is **CID-broken** — both deferred (ADR-0003 forbids the fragile un-mirroring), documented with typed `PageLayoutChanged`/`EncodingError` diagnostics. Extracted the one clean table: **Annex 6.1 foreign-employment permits → 24 rows** (8 FY × total/female/male, `labour`, `count`). FY2079/80 total 494,224 (female 53,500 + male 440,724 ✓). A decoded mirrored GDP cell read NPR 5,704.8 bn — **independently matching NRB's National-Accounts** figure.
- **`/state-enterprises` render page** (Worker C): the 7th live page — Public Enterprise X-Ray ranking SOEs by government equity vs loan exposure from the Yellow Book `dne_facts` (NEA NPR 181.33 bn), npr_thousand→NPR bn, accessible table + decorative composition bar.
- **Ingest resilience fix** ([safe-query](../../src/lib/db/safe-query.ts) + [validation](../../src/lib/validation/index.ts)): the National-Accounts ingest aborted twice at different queries. A 400-pair probe pinned it to **`ECONNRESET` ~0.1%/query** on Supabase's pooler — over the validation loop's ~1,000 round-trips that's a ~70% chance of one reset (census survived because it bulk-inserts). Two fixes: (1) `safeQuery` now inspects `Error.cause` for connection codes (a latent bug — resets were mis-typed `QueryFailed` instead of `DatabaseUnavailable`, since the wrapper isn't a `DrizzleError` instance); (2) the validation driver retries `DatabaseUnavailable` per-row with exponential backoff (reads idempotent; promote is transactional; the `DuplicateOfApproved` check absorbs any post-commit-reset re-run). + regression test.
- **CI completeness:** `mof_economic_survey` added to `pyproject.toml` include + testpaths; full suite **319 → 378** (+25 nrb_dne real-sector, +34 economic-survey).

**Live DB:** approved_indicator_values **874** (was 498; +GDP/CPI/labour) · **dne_facts 38,623** (was 38,574; +49 provincial) · fiscal 6,008 · banking 2,088 · census 531,618 · source_registry 68.

**Next (Wave 3 remaining → Wave 4):** customs-monthly-trade (#7, needs download), whitebook foreign-aid (#12, new fact table + migration), DNE GVA-by-industry + SITC/Direction-of-Trade dimensional sheets, a shared site nav (7 pages, currently inline-cross-linked only).

**Related:** ADR-0016; ADR-0011 (units); ADR-0014/0015 (DNE single-series vs dimensional); DATA_BUILDOUT_PLAN.md §"#9/10"; HANDOFF_2026-06-07.

---

## 2026-06-07 (round 7) — Wave 2: migration map + Yellow Book SOE balance-sheet

**What changed:** Executed Wave 2 of the build-out roadmap — a render page on already-ingested census data, plus a new audited gov-finance source (public enterprises). Both workers held the line on the project's data-honesty rules: one correctly relabelled its own output, the other deliberately narrowed scope rather than ship a fragile parser.

- **`/migration` render page** (Worker #28A): absent-population by destination region from `census_facts` (`getMigrationByCountrySeries`, top 15). **Caught the roadmap's own mislabel** — items #32/#34 are migrant *headcounts*, not remittance NPR — and labelled the page accordingly. Total absent population **2,190,592** (sex=total, all-ages, country≠rowtotal), validated three ways against the published census figure. Top destinations: Middle East 804,614 (36.7%), India 744,855 (34%). Site now has **6 live pages**.
- **Yellow Book SOE parser** (`scrapers/mof_yellowbook/`, Worker #24, [ADR-0020](../decisions/0020-yellowbook-soe-annex1-scope.md)): the Annual Performance Review of Public Enterprises is mixed-encoding Devanagari (CID-broken bodies, Preeti-font annexes, ragged per-sector tables). The worker **scoped to the one deterministically parseable matrix** — Annex-1 (FY 2080/81), Unicode 10-column — and **deferred** the un-parseable per-sector revenue/profit/capital tables (documented, not silently dropped; ADR-0003 forbids OCR/transliteration). Reuses `dne_facts` (`dimension_kind=public_enterprise`).
- **84 `dne_facts` ingested** via new `ingest:dne-yellowbook`: 42 enterprises × {`soe-government-share`, `soe-loan-principal`}, unit `npr_thousand` (header "रु. हजारमा"; ADR-0011 magnitude check: NEA equity = 181,330,245 thousand = NPR 181.33 bn ✓). `dpm-public-enterprises-annual` flipped `paused→active`.
- **CI completeness:** `mof_yellowbook` added to `pyproject.toml` `include` + `testpaths`; full suite **319** (was 297, +22).

**Live DB:** approved_indicator_values 498 · **dne_facts 38,574** (+84) · fiscal 6,008 · banking 2,088 · census 531,618 · source_registry 68.

**Next (Wave 2 remaining → Wave 3):** MoF economic-survey annex parser (#8, CID-broken fonts — hardest item), customs-trade (#7), whitebook foreign-aid (#12), DNE real-sector quarterly-GDP (#9/10, files pre-staged), DNE SITC/Direction-of-Trade/Remittance dimensional sheets.

**Related:** ADR-0020; ADR-0015 (dne_facts reuse); ADR-0011; DATA_BUILDOUT_PLAN.md; HANDOFF_2026-06-07.

---

## 2026-06-07 (round 6) — Build-out workflow + Wave 1 (3 pages, FCGO, roadmap)

**What changed:** Ran a 41-agent build-out workflow, then executed its Wave 1 as a parallel worker batch. Two pages and a new audited source landed; the workflow's conflict-aware roadmap (`docs/research/DATA_BUILDOUT_PLAN.md`) now drives the remaining waves.

- **`data-buildout-plan` workflow** (4 domain-inventory agents → 35 per-item spec agents → synthesis): ranked all 35 remaining work items, mapped the shared-file chokepoints (10 tasks serialize on `nrb_dne/parser.py`; seed files centralize at Mother), clustered into parallel waves of ≤8 conflict-free workers. It also caught real traps pre-emptively (district join is by name not federal_code; tourist plot on ad_end; #32/#34 are migrant headcounts not remittance NPR; budget-speech acquisition-blocked; GeoJSON gates).
- **Wave 1 — 3 render pages (live data):** `/districts` (District MRI, 5 launch districts, palika→district via `metadata->>'district_en'`), `/tourism-rupee` (34-yr arrivals chart, 407 pts), `/fact-ledger` (all 498 approved facts by category + coverage strip). Site now has 5 live pages.
- **Wave 1 — FCGO audited gov-finance:** first worker correctly STOPPED (no PDF — refused to fabricate); Mother acquired the real FY2022/23 CFS via the sandbox bypass + re-dispatched. 6 aggregates now in `approved_indicator_values` (Grade A): revenue 1,506,321.46 / expenditure 1,672,128.84 / recurrent 1,356,150.86 / capital 527,447.04 / provincial 204,678.62 / local-level 453,817.73 npr_million (FY 2079/80). `approved` 492→498.
- **CI hole closed:** `nrb_dne` + `fcgo_consolidated` were missing from `pyproject.toml` testpaths — the full suite silently skipped 98 tests. Added; full suite now 297 (was 199).
- **Deferred (findings):** #16 FX-reserve promotion — the file mixes percent/months/npr_million units the parser flattens; needs per-row unit detection before promotion (would corrupt the truth layer otherwise).

**Live DB:** approved_indicator_values 498 · dne_facts 38,490 · fiscal 6,008 · banking 2,088 · census 531,618.

**Next (Wave 2, from the roadmap):** customs-trade, MoF economic-survey annex parser, whitebook foreign-aid (new fact table), central-bank-daily, kalimati, DNE real-sector (quarterly GDP), census choropleth (GeoJSON-gated), migration-source-map.

**Related:** ADR-0010–0015; DATA_BUILDOUT_PLAN.md; HANDOFF_2026-06-07.

---

## 2026-06-07 (round 5) — DNE dimensional model live (trade by commodity) + MoF downloads

**What changed:** Built the DNE dimensional fact model end-to-end and landed the first dimensional data; downloaded the MoF Economic Surveys (sandbox-TLS blocker removed).

- **`dne_facts` dimensional table** ([ADR-0015](../decisions/0015-dne-dimensional-fact-model.md), Worker T): base measure + `dimension_kind`/`dimension_value` + period, chunked idempotent repo, migration `0004_0005` applied live. The home for breakdowns that don't fit single-indicator `approved_indicator_values`.
- **Trade-by-commodity ingested** (parser v0.5.0 Worker R + `ingest:dne-dimensional` Mother): **38,490 `dne_facts`** — 168 commodities × exports/imports × India/China/Other, monthly 2012→2025. Verified: top export to India FY2024/25 = Soyabean Oil NPR 106.8bn (correct). Base slug is partner-qualified to avoid unique-index collisions. `parse()` short-circuits dimensional files (no silent bogus rows); `parse_dne()` carries both row kinds; `_common/types` unchanged.
- **FX-reserve/BoP slug cleanup** (Worker R): all `-rNN`/enumerator artifacts removed (`dne-gross-foreign-exchange-reserve` etc.) — single series now promotable.
- **MoF Economic Surveys downloaded** (sandbox bypass): 2081/82 + 2080/81 (NP) + 2023/24 (EN). The earlier "MoF TLS" failure was the network sandbox intercepting TLS — `dangerouslyDisableSandbox` + the `mof.gov.np/content/<id>/` → `giwmscdnone.gov.np` CDN pattern works. Files on disk; MoF PDF parsing is future work.

**Live DB:** approved_indicator_values 492 · **dne_facts 38,490 (new)** · local_government_fiscal_transfers 6,008 · banking_sector_facts 2,088 · census_facts 531,618.

**Open follow-ups:** DNE SITC-groupwise + Direction-of-Trade partner sheets + Remittance-by-country/district (same dimensional contract); promote the cleaned FX-reserve/BoP single series; aggregate-row ("MAJOR ITEMS") flagging in trade; MoF Economic Survey PDF parser.

**Related:** ADR-0013, ADR-0014, ADR-0015; HANDOFF_2026-06-07.

---

## 2026-06-07 (round 4) — DNE all-layouts parse, first DNE→approved series, BFI idempotency

**What changed:** Closed the three blockers from round 3 (DNE→approved, DNE complex layouts, BFI NULL-entity index) — two as concrete fixes, one as a deliberate architectural decision that avoided polluting the truth layer.

- **DNE all 6 External Sector layouts now parse** (parser v0.4.0, Worker P): + integer-year+month (FX reserves 6,716), long-panel (exchange rate 2,172), transposed years-as-rows (tourist arrivals 407). AD month→BS via the inverse of `_BS_MONTH_TO_AD_MONTH`; honest `PeriodAmbiguous`/`UnitAmbiguous` flags, never a silent wrong value.
- **First DNE data in `approved_indicator_values`** ([ADR-0014](../decisions/0014-dne-promotion-and-dimensional-model.md)): `dne-tourist-arrival` — 407 monthly points, Ashadh 2048 (1991) → Shrawan 2082 (2025), peak 147,859 in Mangsir 2075 (2018/19, pre-COVID). `approved_indicator_values` 85 → 492.
- **ADR-0014 — DNE promotion policy.** DNE files split into single-dimensional series (promotable) and dimensional matrices (Foreign Trade by commodity ~745, Remittance by country/district ~314). The matrices must NOT be registered as indicators (would dump ~1,000 commodity/country slugs into the catalogue) — they await a future dimensional fact model. Only clean single series promote. FX-reserve components (auto-prefix/`-rNN` slug artifacts) + BoP detail deferred pending slug cleanup.
- **BFI re-ingest now idempotent** (Worker Q, migration `0003_0004_banking_facts_null_dedup`, applied live): unique index over `COALESCE(bank_entity_id, sentinel)` so NULL-entity aggregate rows collide. Verified — double re-ingest inserts 0.

**Open follow-ups:** the DNE dimensional fact model (unlocks trade-by-commodity / remittance-by-country for Money-Map composition) — its own ADR; FX-reserve/BoP slug cleanup for promotion; the one DNE Remittance datetime-period sheet; MoF real-file downloads (TLS).

**Related:** ADR-0013, ADR-0014; HANDOFF_2026-06-07.

---

## 2026-06-07 (round 3) — DNE External Sector parsing, census 753/753, provenance archival

**What changed:** Five parallel workers (J/K/L/M/N) + Mother integration pushed on the deeper data-quality gaps. Two were real parser/data fixes with big payoffs; two are well-characterized blockers now documented for a decision rather than rushed.

### Census: complete, correctly-attributed geography (the headline win)
- Built a deterministic **`(prov,dist,gapa)→federal_code` crosswalk** (`scrapers/cbs_nphc/palika_code_crosswalk.csv`, 753 rows / 753 distinct codes) — census CSVs carry only CBS triples, no federal code, and the 8-digit HLCIT code isn't derivable. Name-matched *within district* (3-rung ladder: exact → fuzzy≥85 → 19-row curated drift map), codes sourced from the same MoF Sheet2 as the entity seed so they join `entities.slug` by construction.
- The parser now resolves **753/753 palikas** (was ~299); `MunicipalityUnresolved` **12,231→0** on Hhld19.
- **Re-ingested all 11 census tables**: `census_facts` **211,094 → 531,618** rows, distinct palikas **299 → 753**, 0 skipped. Every fact now attributes to its local level — unblocks District MRI and per-palika analysis. (Worker K first fixed a parser-level false-collision drop; Worker N built the crosswalk that fixes attribution at the root.)

### DNE External Sector now parses (ADR-0013)
- Downloaded 6 real NRB *Database on Nepalese Economy* External Sector files. They label periods by **AD** fiscal year, not BS. Per [ADR-0013](../decisions/0013-dne-ad-fiscal-year-periods.md) the parser now converts AD→BS (`+57`, deterministic by magnitude) and **fails loud** on genuinely unparseable layouts (it previously mislabeled 2021/22 data as 1964/65). Parser v0.3.0.
- Unlocks ~13K rows at the parser level: Balance of Payments (360), Foreign Trade (11,334), Remittance (1,407 partial). Verified correct: `dne-current-account` = NPR 139,114 million, AD 2022/23 → BS 2079/80.

### Provenance
- The three direct-fact CLIs (BFI, census, fiscal) now **archive source bytes to Supabase Storage** (shared `scripts/_lib/archive-source-document.ts`), closing the ADR-0010 deferral. Verified: real storage key + sha256 + size.

**Open blockers (documented, not silently skipped):**
1. **DNE → approved** needs indicator-registration-at-scale — DNE emits hundreds of `dne-*` slugs; the CMEFs/NCPI hand-seed doesn't scale. Decision needed (register-on-ingest vs curated headline subset) before DNE rows promote past staging.
2. **DNE complex layouts** — forex reserves / exchange rate (integer-year+monthly) and tourist arrivals (transposed) remain `PeriodUnparseable` pending per-layout handling.
3. **BFI NULL-`bank_entity_id` idempotency** — aggregate rows (NULL entity) dodge the unique index, so re-ingesting a BFI file duplicates them (cleaned a 36-row instance this round). A partial/`COALESCE` index is the real fix.

**Related:** ADR-0010, ADR-0011, ADR-0013; HANDOFF_2026-06-07.

---

## 2026-06-07 (continued) — Gap-closing: latest data, remittance geography, two data-integrity fixes

**What changed:** A second Mother + worker round closed the gaps carried in the morning handoff, and caught two more data-integrity bugs in the process.

### Two data-integrity fixes (both made the data materially wrong)
- **BFI reporting period was hardcoded.** `scrapers/nrb_bfi/parser.py` emitted `"Bhadra 2082"` for *every* monthly file — the whole banking series collapsed onto one period (and duplicated, because NULL `bank_entity_id` dodges the unique index). Parser v0.2.0 now derives the BS month+year from the filename. After clear + full re-ingest: **2,088 rows across 58 distinct months, Shrawan 2078 → Ashadh 2082** (4-year series).
- (The fiscal NPR-crore + federal-code fix from the first 2026-06-07 entry was the other.)

### New data ingested
- **Census absent-population (remittance-source geography):** `cbs_nphc` extended for the three multi-row-per-palika tables (dimensions folded into the slug). **Hhld19 = 113,022** facts (palika × sex × age × destination country), Hhld18 = 14,352, Hhld20 = 64,584. `census_facts` now **211,094** rows (191,958 migration). Added chunked `bulkInsert` (Postgres 65k-param cap) to handle the volume.
- **7 latest BFI months downloaded** from NRB (Asoj→Chaitra 2082, mid-Oct 2025 → mid-Apr 2026) and ingested; CMEFs confirmed current (Nine-Months is the latest NRB issue).

### Other
- **`nrb-dne-xlsx` registered** as the umbrella DNE ingest source (ADR-0010 reconciliation) — FK-unblocks live DNE ingest. Registry now 68 sources.
- Worktree data junctions extended to `NRB Current/` + `Stastical Information/` (full scraper suite now green: 194 Python tests).

**Gaps now closed:** latest-data download (NRB), census Hhld18–20, BFI per-file period, DNE source registration, Saun-2082. **Still open:** DNE/MoF *real-file* downloads (NRB SSL OK, MoF SSL was blocked); source-byte archival to Storage; census fuzzy-resolver ~collisions on shared romanized palika names (Hhld19 surfaced 378).

**Related:** ADR-0010, ADR-0011; HANDOFF_2026-06-07.

---

## 2026-06-07 — The data pipeline goes live: ingest, publish, document

**What changed:** Mother + a rolling fleet of Sonnet workers took the dormant pipeline from "plumbing built, pipes dry" to live data ingested, rendered on two public pages, and documented. The Supabase project (paused, DNS dead) was resumed by the user; from an empty DB, migrations were applied and the full chain — storage → `source_documents` → deterministic Python parser → staging → validation → approved — ran for real for the first time.

### Data now live in Supabase
- `approved_indicator_values`: **85** (7 NRB CMEFs macro headline indicators + 78 NCPI inflation categories × overall/rural/urban).
- `local_government_fiscal_transfers`: **6,008** (751 local levels × 8 grant types) — **NPR 321.01 arab** total, FY 2082/83.
- `banking_sector_facts`: **1,836** (50 of 51 NRB BFI monthly XLSX files).
- `census_facts`: **19,136** (8 NPHC 2021 tables incl. financial-inclusion: female asset ownership, small-scale business, absent households).
- `source_registry`: **67** sources (15 newly discovered via NRB/MoF catalog audits + `nrb-bfi-monthly-xlsx` and `cbs-nphc-2021` which had profiles/parsers but were missing from the seed); `entities`: 753 local levels.

### Pages (first public data rendering)
- `/pulse` — Server Component, 85 indicators grouped Prices / Money In / Money Out.
- `/money-map` — D3 Sankey of fiscal transfers (Federal → 8 grant types → 4 local-level tiers), NPR crore/arab formatting.

### New ingest CLIs
`ingest:cmefs`, `ingest:ncpi`, `ingest:fiscal-transfers`, `ingest:bfi-monthly`, `ingest:census-2021` (live); `ingest:dne` (wired, dry-run). New scraper `scrapers/nrb_dne` (28 tests).

### Correctness fixes worth remembering
- **Fiscal unit was wrong** (NPR_thousand → **NPR crore**); a data-unit verification protocol is now doctrine (ADR-0011).
- **Fuzzy name resolution inflated the fiscal total ~65%** (NPR 530 → 321 arab) via duplicate-code collisions; the parser now reads the workbook's federal Code column directly (ADR-0011, parser v0.5.0).
- Infra bugs fixed: Supabase storage probe (body-encoded 404), `PostgresError` import (RSC 500), `server-only` under tsx, N+1 entity lookups, a client-function-called-from-server 500 on /money-map.

### Documentation pass (this session's second half)
- **[DOCUMENTATION_STANDARD.md](../DOCUMENTATION_STANDARD.md)** added — the doc surface + feature-CLAUDE.md template + a per-change **Documentation Gate**, now a CI-style gate in root `CLAUDE.md`.
- **[INGEST_RUNBOOK.md](../INGEST_RUNBOOK.md)** added (operational runbook, previously only in private agent memory).
- First feature-local `CLAUDE.md` files (`src/features/pulse`, `src/features/money-map`).
- ADRs **0010** (ingest CLI conventions), **0011** (fiscal units + identity), **0012** (viz adapter cast location).
- 7 backfilled `docs/sources/` profile stubs; `scrapers/nrb_dne/README.md`; `docs/HANDOFF_2026-06-07.md`.

**Plan section affected:** Advances BACKEND_PLAN Day 11–28 (ingestion pipeline) to live, and lands the first two Lenses (Pulse, Money Map) ahead of the visible-Pulse milestone. No scope change to the strategy.

**Open gaps (carried in [HANDOFF_2026-06-07.md](../HANDOFF_2026-06-07.md)):** latest-data downloads not yet pulled from NRB/MoF; census Hhld18–20 (absent-population-by-country) blocked on a multi-row reader extension; DNE live ingest pending source-id reconciliation; source bytes not yet archived to Storage.

**Related:** ADR-0009 through ADR-0012; DOCUMENTATION_STANDARD; INGEST_RUNBOOK.

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
