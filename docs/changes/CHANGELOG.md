# Project Change Log

Append-only, reverse-chronological. Each entry captures where reality diverged from the canonical strategy plan and why.

Strategy plan: [`docs/STRATEGY.md`](../STRATEGY.md) (in-repo, canonical).

Format and rules: [CHANGE_CONTROL.md](../CHANGE_CONTROL.md).

---

## 2026-06-11 — Migration Atlas Phase 2/3: origin→destination Sankey + DoFE permit fact domain

**What changed:** Two parallel-built features (one Mother-built, one delegated to a scope-fenced worker — disjoint file scopes). **(1)** A live **origin-province → destination-region Sankey** (the Atlas's Figure 6) on `/migration`. **(2)** The **`migration_permit_facts`** fact-domain foundation (ADR-0026) for the DoFE labour-permit corpus. All gates green: typecheck · lint · **219 tests** · `next build` · `drizzle-kit check` · `check:source-registry`.

### View C — the flow Sankey (Atlas Fig 6)

- `MigrationFlowSankey` (client) renders absent population from origin **province** → destination **region**, reusing the existing `d3-sankey` adapter (ADR-0012) and mirroring `money-flow`'s Sankey field-for-field (mobile stacked-bar fallback + sr-only table). Unit is **people**.
- The roll-up is a pure, unit-tested module: `flow-graph.ts` (`buildMigrationFlowGraph`) — palika-grain census → province×region, consolidating the 13 census buckets to the 6 the Atlas uses. Kept OUT of the `server-only` query file so it's testable (mirrors `choropleth-scale.ts`).
- Province resolution uses `district-province.ts` — an **authoritative** `DISTRICT_TO_PROVINCE` (77→7) generated from the source geometry's province field (not guessed); tested against the constitutional split (14/8/13/11/12/10/9).
- `getMigrationFlowSankey()` (SQL + DB boundary) groups the same non-double-counting census slice by `entities.metadata->>'district_en'` × region. Typed fallback; never throws.

### DoFE migration permit fact domain (ADR-0026)

- **[ADR-0026](../decisions/0026-migration-permit-fact-domain.md)** — `migration_permit_facts`, a dimensional fact table (period × destination × origin × skill × category × sex), NULL = marginal, one **`UNIQUE NULLS NOT DISTINCT`** natural key (the `audit_facts` pattern — no coalesce-sentinel needed). **Foundation only — no data, no parser; source `dofe-labour-migration` stays paused.**
- New: `schema/migration-permit-facts.ts`, 4 enums (`migration_skill_class` / `_permit_category` / `_destination_region` / `_sex`), repository + Zod parser-output contract (`src/lib/ingestion/migration-permit-types.ts`), migration `0007_0008_migration_permit_facts` (`UNIQUE NULLS NOT DISTINCT` generated, not hand-written). +21 tests.

**Next:** the deterministic DoFE parser (flips the source to active + populates the table) + the remittance-BoP backfill.

---

## 2026-06-11 — Migration Atlas Phase 2 (partial): intensity map + pipeline registrations

**What changed:** Upgraded the palika choropleth from absolute count to **migration intensity — share of each local level's population living abroad** (absent ÷ total population), matching the NDRI Atlas's *headline* map ("% of absentee population by municipality"). Registered the next two acquisition-pipeline sources. All gates green (typecheck / lint / 188 tests / build / source-registry).

### Intensity layer (the % map)

- `getAbsenteeShareByPalika()` LEFT JOINs the Hhld19 absent slice to the total-population denominator `Indv01_PopulationBySex` (`total` column → slug `indv01-populationbysex-total`, **verified against the cbs_nphc parser test**, not guessed). Returns `byCode: Record<federal_code, { people, population, pct }>` + national aggregates. A palika with absentees but no population row gets `pct = null` → renders "no data", never a fabricated share (Data Continuity Protocol).
- `PalikaChoropleth` now fills by `pct` (6-class quantile), legend shows % bands + the national share, and the native `<title>` tooltip shows both the **% and the headcount**. Still people-underneath, never rupees.

### Pipeline registrations (Migration Atlas plan §4, minus KNOMAD)

- `fewims-migrant-deaths` (FEWIMS / Foreign Employment Board, Tier 3, paused) — migrant-worker deaths by cause (Atlas Fig 17). Counts only, no PII.
- `idmc-displacement` (IDMC GIDD, Tier 4, paused) — disaster-induced displacement, district-level (Atlas Maps 24–25). Pairs with `ndrrma-damage-tally`.
- Both registered `paused` per ADR-0009 ("register before scraping"); seed rows + `docs/sources/*.md` stub profiles; index regenerated (**73 rows**), `check:source-registry` green.
- **KNOMAD bilateral remittance matrix dropped** from the plan (source dysfunctional as of 2026-06) — recorded in the IDMC notes + plan.

### Independent review pass

Three independent reviewer agents (correctness / geo-pipeline / cleanup) audited the diff. Fixes applied: (1) **degenerate-subpath bug** — the geometry build's `<3 points` guard ran on float points before integer rounding, emitting one zero-area subpath (Lo-Ghekar Damodarkunda's hole); now rounds + dedups before the guard, and a regression test asserts ≥3 distinct points per subpath; (2) the build now asserts **emitted == 753** (not just matched), so geometry loss is fatal; (3) div-by-zero guard on degenerate projected extent; (4) SVG `aria-label` now reports the rendered 753 local levels (+ data coverage); (5) empty/zero-width legend bands (colliding quantile breaks) are dropped. No severe logic bugs were found; the LEFT-JOIN denominator, falsy-zero handling, and Zod boundary were verified correct.

**Next:** DoFE granular permits (`migration_permit_facts`, needs its own enum ADR) + the live Sankey; backfill remittance BoP.

---

## 2026-06-11 — Migration Atlas Phase 1: palika choropleth engine + base geometry (ADR-0025)

**What changed:** Shipped the **choropleth unlock** — the single missing primitive that blocked reproducing the NDRI Migration Atlas (and the census/land-use/District-MRI maps). Added Nepal's 753-local-level base geometry as a committed asset and rendered the first live choropleth: **absent population by origin palika** (View B at `/migration`), from `census_facts`, Grade A. All verification gates green.

### Base geometry (the reusable primitive)

- **Asset:** `src/lib/viz/geo/palikas-753.geo.json` — 753 palikas, each keyed by its MoFAGA 8-digit `federal_code`, as Mercator-projected, RDP-simplified, viewBox-normalised SVG paths (~384 KB raw / **~99 KB gzipped**). Render-verified as Nepal with spatially-coherent districts.
- **Pipeline:** `scripts/geo/` (pure-Python, no geo/npm deps) — `extract_crosswalk.py` (canonical 753 codes↔names from the MoF workbook) + `build_palika_geo.py`. The crux — joining the source geometry's own codes to `federal_code` — is a **deterministic 4-phase match (exact → confidence-fuzzy → pigeonhole → 3 web-verified renames) reaching 753/753**; the build refuses to write a partial asset.
- **Source registered:** `nepal-admin-boundaries` (Grade A, reference, tier null) + `docs/sources/nepal-admin-boundaries.md` profile + `scripts/geo/README.md`. Index regenerated (71 rows); `check:source-registry` green.

### Runtime (zero client JS)

- `PalikaChoropleth` is a **Server Component** rendering SSR'd `<path>` elements with a 6-class **quantile** fill, native `<title>` tooltips, legend, and a visually-hidden top-30 table — no client geo library, no hydration cost. Pure scale helpers (`choropleth-scale.ts`) + the geometry loader (`src/lib/viz/geo/palikas.ts`, Zod-validated) are unit-tested (15 new tests: classification + asset invariants 753/77/6-11-276-460).
- Wired into `/migration` as View B with its own typed fallback. Unit is **people (count)**, never rupees — the page invariant holds; the remittance placeholder stays disabled (no fabricated money). Absentee-**%** (needs a population denominator) is a tracked follow-up.

### Doctrine

- **[ADR-0025](../decisions/0025-choropleth-geo-adapter.md)** moved Accepted → **implemented**, with an Implementation Note: built as **precomputed SVG paths (Mercator)**, not the originally-specified runtime TopoJSON + `d3-geo` adapter — lighter mobile payload and no cross-worktree dependency install. The load-bearing decisions held (static registered asset, federal_code crosswalk baked at build, `src/lib/viz/geo/`). TopoJSON + `d3-geo` remain the documented upgrade path for future interactive reprojection/zoom.
- `MIGRATION_ATLAS_PLAN.md` §8 Phases 0–1 marked done; `migration-source/CLAUDE.md` updated (View B documented; the old "View B deferred — no GeoJSON" note retired).

### Verification

- `tsc --noEmit` ✓ · `eslint` ✓ (0 errors) · `vitest run` ✓ (**188 tests**, +15) · `next build` ✓ (`/migration` prerenders) · `check:source-registry` ✓.
- Geometry render-verified (colored-by-district + a full synthetic-data choropleth preview). Live per-palika **values** depend on a reachable `census_facts` DB (unavailable in this worktree, as the existing View A already is); the component degrades to typed "no data" without it.

**Next:** Phase 2 — DoFE granular permits (district-of-origin) + register KNOMAD/FEWIMS/IDMC; and the absentee-% layer (join a per-palika population table).

---

## 2026-06-11 — Migration pillar plan + choropleth geometry ADR (plan-only)

**What changed:** Studied the **Migration Atlas of Nepal** (NDRI + AWO International, Nov 2025) to scope a migration data-acquisition pipeline and a *better-than-print* product. **Plan artifacts only — no code, no seed rows, no parsers, no schema.** Two docs added behind a review gate.

### Findings

- **Most of the Atlas's data spine is already in our DB.** Its ~18 census-derived maps draw on NPHC-2021 microdata we already hold in `census_facts` (531,618 rows, 753 palikas); migrant-by-country is live in `dne_facts` (×234 countries ×51 months); `/migration` View A is already shipped. The **single blocker** to reproducing the atlas is the missing geometry primitive (no GeoJSON/`d3-geo` in repo), already flagged as `DATA_BUILDOUT_PLAN.md` #28/#29 and in `migration-source/CLAUDE.md`.
- **We catch a 10× error in the source.** The Atlas states remittance was "NPR 144 billion in 2023/24" (twice), while its own chart shows ~1,500 NPR billion at >25% of GDP; actual ≈ **NPR 1,445 billion** — a dropped digit. This is exactly the failure our cross-source reconciliation gate (ADR-0021) + data-unit identity discipline (ADR-0011) exist to catch; candidate launch story.
- **Decisions taken:** plan-docs-only this round; **palika (753) granularity first** for the choropleths.

### Doctrine

- **[ADR-0025](../decisions/0025-choropleth-geo-adapter.md)** (Proposed) — choropleth geometry layer: static versioned **TopoJSON** (not PostGIS, not raw GeoJSON), boundaries as a registered source (`nepal-admin-boundaries`) with recorded license, MoFAGA `federal_code` crosswalk baked in at build time, type-bridges in a new `src/lib/viz/adapters/d3-geo.ts` (extends ADR-0012), `geoConicConformal` projection, and a mobile strategy (district-77 default render, palika detail on zoom, ≤~250 KB gzipped target). Unblocks ~11 atlas maps + census choropleth (#29) + Land Use Atlas + District MRI locators with one primitive.
- **[`docs/research/MIGRATION_ATLAS_PLAN.md`](../research/MIGRATION_ATLAS_PLAN.md)** — master plan: report decode, differentiators, the source-acquisition table (M1–M10) with fully-specified proposed registry rows (KNOMAD bilateral remittance, IDMC displacement, FEWIMS deaths, MoLESS BLAs) + stub activations, the atlas-map→our-data crosswalk, the 4-phase dispatch sequence, and open escalations (DoFE `migration_permit_facts` enums ADR; boundary provider/license; historical 2001/2011 census totals).

### Gates

- Plan-only: no schema/migration/seed/parser changes. Documentation Gate satisfied (structural decision → ADR; new sources → registry-row specs staged for the implementation PR). No CI-affecting edits.

**Next:** review gate → Phase 1 vertical slice (ADR-0025 deps + palika TopoJSON asset + `d3-geo.ts` adapter + one flagship *absentee % by palika* choropleth from `census_facts`).

---

## 2026-06-11 — Government audit fact domain (ADR-0024): OAG beruju + findings model

**What changed:** Added a dedicated, entity-keyed fact domain for Nepal's government audit reports (Office of the Auditor General — federal/provincial/local/corporations) instead of forcing audit data into the time-series `indicator_values` pipeline. Implements the Money Wasted pillar + Budget Watch / Local Ledger data need ([STRATEGY.md](../STRATEGY.md) Pillar 4, Vertical #10). **Foundation only — no corpus parsed, no data ingested.** (Renumbered from ADR-0010 / migration idx 0003 after the loving-wing build-out claimed those numbers in parallel.)

### Doctrine

- **ADR-0024** — government audit reports are a distinct fact domain (*beruju* irregularities + structured narrative findings), populated direct-to-fact-table like `local_government_fiscal_transfers`. Locks 5 enums (`audit_subject_class` / `beruju_category` / `audit_amount_basis` / `extraction_method` / `review_status`), 3 tables, raw+normalized amount provenance, OCR-locator provenance, NULL-entity tier aggregates (`UNIQUE NULLS NOT DISTINCT`), source-precedence-guarded upserts, and a reconciliation-gate (ADR-0021) ship requirement.

### Schema + scaffolding (across PRs #42–47)

- `src/lib/db/schema/audit-facts.ts` — `audit_entity_summaries`, `audit_beruju_lines`, `audit_findings`. Migration `0006_0007_audit_facts.sql` (generated; `drizzle-kit check` clean).
- Plus: the repository (`audit-facts.ts`) + Zod parser-output contract; a 7-province + entities-repo seed; the OAG acquisition scraper (`scrapers/oag_audit_reports/`); and two pre-ingest recon docs.

### Verification

- `pnpm typecheck` / `lint` / `test` / `drizzle-kit check` / `check:source-registry` — green.

---

## 2026-06-10 (round 17) — Overnight AI-pass build step 1: Master Recovery Ledger over the whole OCR corpus

**What changed:** Built the methodical backbone for the overnight AI-pass (plan: [`docs/OVERNIGHT_AI_PASS_PLAN.md`](../OVERNIGHT_AI_PASS_PLAN.md)): a deterministic, re-runnable **table-locator scan** over the entire Surya-OCR corpus that emits the **Master Recovery Ledger** — every `(document → table-region)`, value-ordered, deduped against the documented truth layer, with the OCR-in-progress state recorded. **Recover + stage only**; the human promotes in the morning (no unattended DB writes). Build step 1 of 5.

- **Scope.** 50 OCR'd documents, **11,061 / 13,297 pages present** (Surya OCR still running — 3 redbooks + 1 P5 not yet started, 1 redbook partial). The locator reads the *current* OCR state and is idempotent + resumable: ids are stable (`doc + first page`), and a re-run **preserves** any loop/human-set status (`--no-merge` forces a clean rebuild).
- **Output.** **1,339 table candidates** (1,337 pending) → `RECOVERY_LEDGER.json` (the nightly loop's source of truth) + generated `RECOVERY_LEDGER.md` (morning dashboard). Detection = numeric-density + annex/title grep (`अनुसूची`/`तालिका`/section numbers / English `Table`/`Statement`/`Details of`) + printed-unit header (`रु. लाखमा`, `Rs. in '00000'`). Section splitting is **category-aware**: annex/section docs (economic survey, yellowbook, intergovernmental) split per section; a redbook is one dataset (budget-head × {total,recurrent,capital}) so only explicit title words split it (this dropped the oldest redbook from 410 spurious "tables" to 7).
- **Dedup model.** Baseline = [`docs/DATA_AUDIT.md`](../DATA_AUDIT.md) + recovered `_ai_pass` artifacts. (A *live* DB query is unreliable from this worktree — `.env.local` still points at the retired online Supabase and the local-Postgres migration (ADR-0006) is on a later branch; the nightly loop / morning promotion re-checks live via `pnpm audit:data`.) Classes: `partly-in-db` 817, `new` 491, `owned-deterministic` 22 (whitebooks → `mof_whitebook` owns foreign aid; OCR = cross-check only), `unknown` 6, `needs-decision` 3. The 2 already-recovered tables (GVA annex 13.1 promoted; SOE p79 P&L staged) are detected, deduped, and excluded from the worklist.
- **Render-verified.** The #1 value-ranked target — intergovernmental **FY2077/78** (P0, 4,941 numeric lines) — was render-verified against the source page: the local-level fiscal-transfer table with **4 aggregate grant columns** (समानीकरण / सशर्त / विशेष / समपूरक + जम्मा), 9-digit codes, province subtotals — confirming the `needs-decision` 4-aggregate-grant schema block (DATA_AUDIT §6). Flagged for escalation, **not** auto-decided.
- **Gates:** read-only scan — **no DB writes, no schema changes, nothing promoted**. `py_compile` clean on both scripts.

**Related:** `docs/OVERNIGHT_AI_PASS_PLAN.md`; ADR-0003 (AI = QA, not the source of digits); ADR-0021/0022 (OCR tiers + reconciliation gate). Artifacts: `scrapers/surya_ocr/_ai_pass/{locate_tables.py, render_ledger.py, RECOVERY_LEDGER.json, RECOVERY_LEDGER.md, README.md}`. **Next:** build step 2 — extend `ocr-table-recovery` for nested-subtotal + multi-page tables and validate the cross-column repair phase live.

---

## 2026-06-10 (round 16) — Economic Survey macro annex: GVA-by-sector recovered (Tier-2 OCR, FY2081/82)

**What changed:** First recovery from the previously-deferred Economic Survey **macro annex** (ADR-0016 deferred it as RTL-mirrored / CID-broken; ADR-0021 designated OCR-of-the-rendered-page as the route, and the overnight Surya run OCR'd both Nepali editions). Recovered **annex 13.1 — प्रदेशगत कुल मूल्य अभिवृद्धि (provincial GVA by industrial classification)** for **FY2081/82**: national 18 industries + 7 provinces × 18 = **144 facts** → `dne_facts` (`economic-survey-gva-current`) — the GVA-by-sector gap (DATA_AUDIT §6).

- **Method (Tier-2 OCR + AI-QA).** Pure OCR of the dense 16-col × 21-row landscape table had ~27% province-cell damage. Resolved by Mother **render-verification**: each column rendered as a `Matrix(8)` strip and read off the printed page; OCR errors corrected (e.g. आवास `93244`→13255, स्वास्थ्य `90788`→10264 — spurious leading `9`). No digit invented; nothing computed-and-left-unread.
- **Dual reconciliation gate (over-determined).** Σ(18 sectors)=printed GVA per province (residual 0…+3 crore); GVA+tax=GDP (±1); Σ(7 provinces)=national per sector (−1…+2); **national GDP 610,722 crore = `dne-gdp-nominal` to the rupee.** Worst residual 3 crore (rounding). New **G5** check in `data-audit.ts` makes it a permanent regression.
- **Model (ADR-0023, no migration).** One measure `economic-survey-gva-current`, two dimension kinds: `industry` (national, 18) + `province-industry` (composite `<prov>__<sector>`, 126; ADR-0018). `npr_crore`, `extraction_method=surya-ocr`, confidence B. New `source_documents` row for the Nepali ES 2081-82 PDF under `mof-economic-survey-annual`.
- **Excluded, honestly.** FY2080/81 carries a **+799 printed-source Σ-vs-total defect** (every cell render-verified correct-as-printed) → not promoted, documented (never force-reconciled). Constant-price tables, fiscal annex, other editions deferred.
- **Orchestration learning.** A delegated worker thrashed on open-ended *visual* verification while Mother idled — `docs/AGENT_OPS.md` gains a "Stuck / Hung / Thrashing Worker Recovery" protocol (detect from output-dir artifacts, `TaskStop`, take over inline; never delegate open-ended visual QA; never block idly on a worker).
- **Gates:** `pnpm audit:data` re-run — G1–G4 still pass, **new G5 within rounding (worst 2 crore), no new mismatch**.

**Live DB:** dne_facts **271,745** (+144) · `economic-survey-gva-current` 144 (18 `industry` + 126 `province-industry`, FY2081/82). Accuracy flags open: **0**.

**Related:** ADR-0023; ADR-0016 (the deferral this revisits), ADR-0021/0022 (OCR tier + verification gate), ADR-0018 (composite dimension); DATA_AUDIT §2/§5/§6; `scripts/ingest-economic-survey-gva.ts`; artifacts `scrapers/surya_ocr/_ai_pass/es2081_annex13_1/`.

---

## 2026-06-08 (round 15) — Intergovernmental fiscal transfers: 5 FYs (deterministic multi-edition recovery)

**What changed:** Asked to "tackle the 6 scanned FYs" via OCR, the investigation overturned the premise — **most weren't scanned**. Re-inspecting the bytes (the do-not-assume rule), of the 6 deferred FYs only **FY2077/78 is genuinely image-only**; the rest have exact text layers the template parser simply couldn't read. So they were recovered **deterministically** (text-layer, exact, reconciled) — strictly better than OCR (no digit-error risk).

- **+2 FYs ingested: FY2080/81 + FY2081/82** → `local_government_fiscal_transfers` (18,056 → **30,104 rows; 5 FYs**, 2078/79–2082/83). Each: 753/753 rows reconcile AND the 753 grand totals sum to the printed `स्थानीय तह` document total to the rupee (NPR 295.0bn, 312.4bn); 0 unresolved. (FY2082/83 was already present via the XLSX feed; its PDF is redundant, not re-ingested.)
- **Edition-aware parser** (minimal): these editions print the bare **8-digit** federal code; FY2078/79+2079/80 print a 9-digit code (federal + trailing '3'). `_crosswalk_code` is now length-aware; the 14-column model + x-anchors fit all four exactly. Honest three-way FY classification: `RECONCILABLE_FYS` (2078/79–2082/83), `DEFERRED_LAYOUT_FYS` (2074/75, 2075/76, 2076/77 — text layer, non-template layout; parse() refuses rather than mis-map), `SCANNED_FYS` (2077/78 only).
- **3 FYs precisely characterized + deferred (honest blockers, documented in DATA_AUDIT §6):**
  - **FY2074/75 + FY2075/76 — schema-granularity blocker.** Visually verified: the early books carry 4 **aggregate** grant columns (equalization / conditional / complementary / special + total), NOT the schema's 8 *atomic* sub-types; unit is thousands (not lakh); 7-digit codes need an old→federal crosswalk. Recovering them honestly needs a schema extension (aggregate grant types) + an ADR — never fabricate the atomic split.
  - **FY2076/77 — complex layout** (landscape, glyphs overprinted 4×, transposed matrix) — deterministic but needs geometry reverse-engineering.
  - **FY2077/78 — genuinely scanned** → Surya OCR (harness validated; reconciliation of OCR digits is the open risk).
- **Gates:** 63 surya_ocr pytest, ruff + mypy clean; `pnpm audit:data` F3 = 5 FYs, all reconciliation checks (G1–G4) still pass.

**Live DB:** approved 877 · dne_facts 271,601 · foreign_aid_facts 1,024 · **`local_government_fiscal_transfers` 30,104 (5 FYs)** · census 531,618. Accuracy flags open: **0**.

**Related:** commit `5075478`; DATA_AUDIT §1/§2/§6; ADR-0021/0022. Next decision: schema extension for early aggregate grant years (2074/75–2075/76).

---

## 2026-06-08 (round 14) — Stream 2 integrated: Tier-2 Surya OCR harness + intergovernmental fiscal-transfer history

**What changed:** Completed the 3rd recovery stream. The reusable Tier-2 Surya OCR harness (`scrapers/surya_ocr/`) is banked, and the **intergovernmental fiscal-transfer history** is extended from 1 FY to 3 — the federal→local money flow (753 local levels × 8 grant types), per ADR-0022's dual-channel design.

- **ADR-0022 — Surya OCR pipeline + dual-channel design.** Reusable harness: render (`fitz.Matrix(3,3)`) → OpenCV preprocess → tile → Surya recognition → stitch (IoU de-dup of tile-seam overlaps) → `ocr_tracking` trio → reconstruct. The dual-channel principle: for books with a clean numeric **text layer**, take the VALUES from the text layer (deterministic, exact, self-reconciling) and use Surya as an **independent cross-check + Devanagari-label recovery + provenance** channel — maximizing completeness (no rows lost to OCR digit error) AND accuracy (reconciliation). Surya is the SOLE route only for genuinely scanned pages.
- **Data — 2 FYs ingested (text-layer).** `scrapers/surya_ocr/parsers/intergovernmental.py` + `scripts/ingest-intergovernmental.ts` → **FY2078/79 + FY2079/80** into `local_government_fiscal_transfers` (6,008 → **18,056** rows, 3 FYs). Both reconcile to the rupee: each book's 753 local-level grand totals sum to the printed `स्थानीय तह` document total (FY2078/79 NPR 283.0bn, FY2079/80 NPR 300.4bn). 9→8-digit code crosswalk verified 753/753, 0 unresolved. `npr_crore`, confidence B. New `mof-intergovernmental` source (registry 69→70, active); CLI enforces the ADR-0021 reconciliation gate (exit 1 on any non-reconciling/scanned FY).
- **Provenance-honesty fix.** The parser hardcoded `extraction_method=surya-ocr+textlayer-xcheck` on every row even when Surya never ran. Made it honest + conditional: `textlayer` by default, the xcheck label only when `--surya` actually runs (`parse(..., surya_xcheck=run_surya)`). The 2 ingested FYs carry `extraction_method=textlayer` — true, since values are text-layer-derived. +1 test. (Mission guardrail: never claim a cross-check that didn't happen.)
- **Deferred, documented honestly:** (a) the **6 scanned transfer FYs** (no text layer) await the Surya-OCR-only path — harness ready, ship per-FY only when OCR reconciles; (b) the **Surya GPU `ocr_tracking` cross-check pass** for the 2 ingested FYs needs a small CLI fix first — the parser is invoked as a bare script, under which its lazy `from ..` relative import doesn't resolve (needs absolute import + `sys.path` bootstrap), then a ~5–15 min/FY GPU run. The DATA does not depend on it (text-layer values already reconcile + shipped). Both tracked in DATA_AUDIT §6 + RECOVERY_PROGRAM follow-ups.
- **Gates:** `typecheck` 0 · `eslint` 0 errors · `vitest` 148 · `ruff` clean · `mypy` 17 files clean (new `fitz`/`cv2`/`surya`/`PIL`/`numpy` overrides) · **`pytest` 604 passed** · `pnpm audit:data` re-run — F3 shows 3 FYs, every reconciliation check (G1–G4) still passes, **no new mismatch**.

**Live DB:** approved 877 · dne_facts 271,601 · foreign_aid_facts 1,024 · **`local_government_fiscal_transfers` 18,056 (3 FYs)** · census 531,618 · banking 2,088 · source_registry 70 (17 active). Accuracy flags open: **0**.

**Related:** ADR-0022, ADR-0021 (gate), ADR-0003 (Surya = recognition, not generative extraction); DATA_AUDIT.md §1/§2/§4/§5/§6/§8; RECOVERY_PROGRAM.md; `docs/sources/mof-intergovernmental.md`.

---

## 2026-06-08 (round 13) — Data audit + 3-stream recovery (accuracy fix, customs depth, resilience)

**What changed:** Built the accuracy/completeness backbone (`pnpm audit:data` + `DATA_AUDIT.md`), then ran a tracked 3-stream parallel recovery program (`docs/research/RECOVERY_PROGRAM.md`) — closing the one accuracy flag the audit found, deepening customs history, and hardening ingest resilience. Mission emphasis: this DB's value IS completeness + accuracy, so the audit is the regression gate for everything.

- **Data audit** (`scripts/data-audit.ts`): exhaustive live-DB inventory — per-series temporal coverage, source-registry gaps, provenance, and machine-checked reconciliation. Wired into CLAUDE.md as the mandatory anti-hallucination reference; re-run after every ingest.
- **Stream 1 — accuracy fix (`8d482c7`):** the audit caught foreign-aid FY2070/71 donor≠sector (~15% gap). Root cause: 2 ministry rows whose names wrap to a 2nd line were dropped from the sector table (pdfplumber merge artifact) — their totals = exactly the gap. Fixed by deterministic wrapped-name recovery (mof_whitebook v0.2.1, no AI/OCR), re-ingested 154→158; **all 7 aid FYs now reconcile donor==sector exactly**. No value fabricated.
- **Stream 3 — customs depth + resilience (`74c08ee`):** customs trade **1 → 7 periods** (5 annual FYs 2076/77–2081/82 + monthly + cumulative; **+164,612 dne_facts**). Two fixes: (a) blank-description fallback (older editions have HS-coded rows with empty description → label falls back to the HS code, v0.3.0); (b) **`safeQueryWithRetry`** — bounded retry on transient ECONNRESET, adopted by `bulkInsertDneFacts` (a 42k-row ingest had failed mid-stream on the pooler; now resilient). This hardens ALL large dimensional ingests.
- **Stream 3 findings (parser-blocked, documented):** CMEFs monthly history is fully acquirable but the parser hardcodes the period (needs a period-aware fix); remittance-NPR history exists in BPM5 but needs a new route + a labelled methodology discontinuity vs BPM6. Both recorded in DATA_AUDIT §8.
- **Stream 2 — Tier-2 Surya OCR** (intergovernmental fiscal-transfer history) building on the GPU (in progress).

**Live DB:** approved 877 · **dne_facts 271,601** · **foreign_aid_facts 1,024** (all reconciled) · census 531,618 · banking 2,088. Accuracy flags open: **0**.

**Related:** DATA_AUDIT.md, RECOVERY_PROGRAM.md; mof_whitebook v0.2.1; customs_trade v0.3.0; ADR-0011/0021.

---

## 2026-06-08 (round 12) — PDF recovery Tier-1: deferred data was recoverable

**What changed:** A robust PDF-recovery program replaced the policy of deferring "hard" PDFs. The user challenged the over-deferral; the diagnosis confirmed it: workers had collapsed three distinct techniques under "ADR-0003 = no AI" and refused all three, when only generative-LLM-extraction is actually banned.

- **ADR-0021 — PDF recovery tiers + verification gate** (clarifies ADR-0003): Tier 1 deterministic (1a font transliteration, 1b geometry un-mirror — both ADR-0003-clean), Tier 2 Surya tile-OCR, AI permitted only as dev/QA assistant. Trust boundary: reconcile to printed totals + sample-verify against the rendered PDF page + `extraction_method` provenance + method-based confidence. No unreconciled data ships.
- **Tier-1a Preeti → 2008–2011 foreign-aid history.** The pre-2012 White Books are Preeti legacy-font (Latin bytes → Devanagari), NOT CID-broken — a fixed byte-map recovers them, zero OCR/AI. New `scrapers/_common/preeti.py` (deterministic converter, 38 tests; `j}b]lzs`→वैदेशिक verified live), wired into the whitebook parser. Recovered **FY2065/66 (144) + 2066/67 (142) + 2067/68 (128) = 414 `foreign_aid_facts`**. Verified per ADR-0021: reconciliation tests pass, values are exact ASCII digits (not OCR), and the rendered FY2065/66 page was read + confirmed as the ministrywise aid summary. `foreign_aid_facts` 606 → **1,020**.
- **Red Book federal budget (FY2074/75) → 171 `dne_facts`** (57 budget-heads × total/recurrent/capital, npr_thousand). Σ total = **NPR 1,195.4 billion** (correct budget magnitude); per-head recurrent+capital = total. **Parser perf fix** (v0.2.0): was scanning all ~650 pages (>5min, timed out) — capped to the front-matter appropriation summary (80 pages) → 1m34s.
- **Tier-1b Economic Survey un-mirror → routed to Tier-2 Surya** (not shipped): the deterministic un-mirror failed reconciliation twice (fragile wrapped-label/column-reversal geometry); the headline GDP/CPI is already live from the DNE ingest; and since the mirror is a text-layer-only artifact (visual page correct), OCR-reading the rendered page is the right tool. Deferred honestly, not faked.
- **Operational note:** long-running background agents did not survive idle/suspend gaps (several killed mid-flight); their code was recovered + finished/verified by Mother directly. Future heavy work favors direct execution + immediately-integrated small steps.

**Live DB:** approved 877 · **dne_facts 106,989** · **foreign_aid_facts 1,020** (now spanning AD 2008–2024) · census 531,618 · sources 69. Data now reaches **2005 → 2025**.

**Next — Tier-2 Surya:** install the OCR stack (surya-ocr v0.17.1 pinned, `--detect_boxes`, OpenCV preprocess; pymupdf already installed); recover intergovernmental fiscal-transfer history (8 FYs), full Yellow Book SOE financials (revenue/profit/capital), the Preeti/CID redbook + whitebook editions, and the Economic Survey macro annex via OCR-of-visual-page — all through the ADR-0021 verification gate + the live `ocr_tracking` schema.

**Related:** ADR-0021; ADR-0003 (clarified); ADR-0011 (reconcile); FINANCIAL_DATA_STRATEGY §Phase B; surya-ocr-findings.md.

---

## 2026-06-07 (round 11) — Wave 6: /trade + /foreign-aid pages + edition backfill

**What changed:** Rendered the two Wave-5 data sources into pages (the customs and foreign-aid facts had no UI), backfilled the remaining clean editions, and wired both into the nav — **10 live pages** now.

- **`/trade` render page** (Worker K): Nepal's customs merchandise trade + structural deficit from `dne_facts`. Imports **NPR 1.80tn** vs exports **NPR 277bn** → **deficit NPR 1.53tn, coverage 15.4%, imports 6.5×** exports; top imports diesel/soya-oil/petrol/LPG; partners India 59.4% + China 18.9%. Top-N honesty enforced ("top 15 of 5,264 — X% of total; remainder not shown"). The worker caught + root-caused **two real SQL bugs** via live DB verification (a `SELECT DISTINCT`+`ORDER BY CASE` rejection, and an alias-shadowing bug sorting by the text slug instead of the amount) — fixed, not papered over.
- **`/foreign-aid` render page** (Worker J): aid by donor + sector (grant vs loan) from `foreign_aid_facts`. **Unit-aware conversion** is the crux — the two editions use different units (npr_lakh FY2020/21 ÷10,000, npr_thousand FY2015/16 ÷1,000,000 → NPR bn), applied per-row before any sum; verified 360.0bn (loan-heavy COVID surge) / 205.9bn (grant-heavy), donor-total == sector-total.
- **Edition backfill** (Mother ingests, no new code): customs **cumulative (6,809) + monthly (4,706)** editions → `dne_facts` (now 3 periods); White Book **FY2013/14 (154) + FY2014/15 (174)** → `foreign_aid_facts` (now 4 fiscal years 2070/71→2077/78).
- **Nav:** `/trade` + `/foreign-aid` added to `SiteNav` (11 routes). Both render workers correctly left the nav edit to Mother (no SiteNav contention).

**Live DB:** approved_indicator_values 877 · **dne_facts 67,934** (+11,515 customs editions) · **foreign_aid_facts 606** (+328, 4 FYs) · fiscal 6,008 · banking 2,088 · census 531,618 · sources 69. **10 live pages, all navigable.**

**Next (Wave 7):** customs commodity×partner cross-tab (needs a 2-dimension ADR); remittance-by-country NPR (no source yet); redbook/budget-execution; a money-flow synthesis (Sankey enrichment from the new trade + aid facts).

**Related:** ADR-0017 (foreign_aid_facts); ADR-0015 (dne_facts dimensional); ADR-0011 (units); HANDOFF_2026-06-07.

---

## 2026-06-07 (round 10) — Wave 5: site nav, remittance NPR, customs trade, foreign aid

**What changed:** A 4-worker batch closed the biggest remaining "Money In/Out" gaps and finally made the site navigable. Notably, three of the four involved a data-honesty or infrastructure judgment, not just extraction.

- **Shared site nav** (Worker F): a single `<SiteNav/>` in the root layout gives all **8 pages** a primary nav (they were islands). `'use client'` only for `usePathname`→`aria-current`; build-confirmed all routes still prerender static. Skip-link + landmark + 360px disclosure (WCAG AA).
- **Real remittance inflow (NPR)** (parser nrb_dne v0.8.0, Worker G): the "Money In" cornerstone — Nepal's largest forex source — from BoP BPM6 "Personal transfers" Credit. **FY2079/80 NPR 1.24tn · 2080/81 1.45tn · 2081/82 1.73tn** (`dne-remittance-inflow`, npr_million → `approved`). The Wave-4 migrant-workers file was *headcounts*; this is the actual money. Caught + fixed a detector bug that was reading the August-cumulative column as the annual total (~13× low) and dumping ~100 BoP lines as catalogue pollution → added a `_BOP_FILE_STEMS` allowlist route.
- **Customs trade detail** (`scrapers/customs_trade`, Worker I → `dne_facts`): **downloaded** the Dept. of Customs FTS XLSX (cleanest source in the repo) via sandbox bypass. Annual FY2081/82 → **6,886 facts**: imports/exports × {HS-commodity, country, customs_office}, npr_thousand, confidence A (imports NPR 1.80tn / exports NPR 277bn — the structural deficit).
- **White Book foreign aid** (`scrapers/mof_whitebook`, Worker H, **new `foreign_aid_facts` table**, [ADR-0017](../decisions/0017-foreign-aid-fact-model.md)): aid by donor + sector. **FY2020/21 134 facts (NPR 360bn COVID surge, npr_lakh) + FY2015/16 144 facts (NPR 205.9bn, npr_thousand)**, donor sums reconcile to published totals. Preeti editions + a mislabelled CID intergovernmental file deferred (ADR-0003); FY2013/14+2014/15 (Devanagari-named) a follow-up. Migration `0005_0006` generated + applied live (Mother); barrel wired; `drizzle-kit check` clean.
- **Process notes:** two workers (E earlier, G) hit transient API socket errors mid-run and recovered cleanly on re-dispatch. The whitebook repo file (referencing the un-barrelled table) made the project typecheck fail mid-batch — reaffirmed that render/data commits must wait until Mother wires the schema barrel + applies the migration; commits were held and sequenced accordingly.

**Live DB:** approved_indicator_values **877** · **dne_facts 56,419** (+6,886 customs) · **foreign_aid_facts 278 (new table)** · fiscal 6,008 · banking 2,088 · census 531,618 · source_registry **69**. **8 live pages, now navigable.** pytest grows by +58 (customs 27 + whitebook 31).

**Next (Wave 6):** whitebook FY2013/14+2014/15 editions; customs monthly/cumulative editions + the commodity×partner cross-tab (2-dimension model); remittance-by-country NPR if a source surfaces; a `/foreign-aid` or `/trade` render page on the new facts.

**Related:** ADR-0017 (foreign_aid_facts); ADR-0015 (dimensional precedent); ADR-0011 (units); ADR-0003 (no OCR); DATA_BUILDOUT_PLAN.md; HANDOFF_2026-06-07.

---

## 2026-06-07 (round 9) — Wave 4: /growth macro page + migrant-workers by destination

**What changed:** Rendered the headline macro series (first consumer of Wave 3's GDP/CPI data) and ingested migrant-worker departures by country — again catching a remittance-vs-headcount mislabel before it could lie.

- **`/growth` render page** (Worker E, the **8th live page**): the first page to surface the Wave-3 macro series — KPI strip (nominal GDP, real growth, per-capita USD, inflation), a nominal-vs-real GDP trajectory chart (d3-shape adapter, ADR-0012), and an inflation table, ~50 fiscal years deep. One JOIN loads all six slugs; each series renders independently (a missing one never blanks the page); unit honesty enforced (npr_billion→NPR trillion, per-capita always USD, CPI labelled an index). Latest: **GDP NPR 6.1 tn, per-capita USD 1,496, inflation 5.44%**. (Worker E's first run died on a transient API socket error before writing anything; re-dispatched clean.)
- **DNE migrant-workers by destination country** (parser nrb_dne v0.7.0, Worker D): `Migrant-Workers-Remittance.xlsx` is **headcounts, not remittance NPR** — verified before coding (sheet titles "Migrant workers by Country", Male/Female/Total triples, FY2021/22 = 630,686 workers / Qatar 185,023; no Rs/NPR). Emitted the honest `dne-migrant-workers` / `count`, NOT the `dne-remittance-inflow`/npr_million ADR-0015 tentatively named — the same mislabel trap caught on `/migration`. **10,910 `dne_facts`, 234 countries** (top corridors UAE 775K / Qatar 628K / Saudi 625K / Malaysia 468K / Kuwait 191K — correct), monthly, BS 2078/79–2082/83. District + sex-split + the single-series outflow sheet deferred (documented). Real remittance NPR is now flagged as an unfulfilled target in `docs/sources/nrb-db-external-sector.md` (it lives in a different DNE/BoP file). Tests 102→**117**.
- **Latent env bug surfaced (not fixed here):** the *parent* checkout's `scrapers/_common/types.py` lacks `ParserError.to_json_dict()` (this branch's has it) — only bites a parser that emits errors when `PYTHONPATH` isn't pinned to the worktree. All ingest commands pin it; the real fix lands when this branch merges to main.

**Live DB:** approved_indicator_values 874 · **dne_facts 49,533** (was 38,623; +10,910 migrant-workers) · fiscal 6,008 · banking 2,088 · census 531,618 · sources 68. **8 live pages.**

**Next (Wave 5):** real remittance-NPR (correct DNE/BoP file), DNE migrant-workers district + sex dimensions, customs-monthly-trade (#7, download-gated), whitebook foreign-aid (#12, new fact table + migration), and a **shared site nav** (8 pages cross-link inline only).

**Related:** ADR-0015 (dimensional model), ADR-0012 (viz adapter), ADR-0011 (units), DATA_BUILDOUT_PLAN.md §6 (the mislabel catch); HANDOFF_2026-06-07.

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
