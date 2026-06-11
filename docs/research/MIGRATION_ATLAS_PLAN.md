# Nepal Ledger — Migration Pillar & Atlas Build-out Plan

**Date:** 2026-06-11
**Status:** Plan-only. No code, no seed rows, no parsers this round — review gate before implementation.
**Owner:** Mother (orchestrator). Workers will execute scope-fenced briefs derived from §8.
**Trigger:** Study of the **Migration Atlas of Nepal** (NDRI + AWO International, Nov 2025, 70pp, ISBN 9789937-1-9285-9) to plan a migration data-acquisition pipeline and a *better-than-print* product.

> Mission anchor: *track whether Nepal's money becomes wealth.* Migration is the single largest channel of "Money In" (remittance > 25% of GDP) and a major "Money Out" of human capital. This plan feeds Pillar 1 (Money In), Pillar 2 (Money Out — people + education outflow + migration-cost loans), and the STRATEGY "Migration Industry" vertical + "Diaspora Capital Desk" lens.

---

## 1. Situation Summary

The NDRI Atlas is the **first spatial atlas of Nepali migration** — a static, print-grade InDesign PDF where *the map is the argument*. It stands on only ~6 triangulated sources, presents 28 GIS choropleths + 17 figures + 6 tables, and is frozen at the 2021 census + permit aggregates. It is closed ("data available upon request"), ungraded (silently mixes Grade-A census with Grade-C single-study anecdotes), and contains at least one **10× factual error repeated twice** (see §3).

**The asymmetric opportunity:** most of the Atlas's data spine is *already in our database.*

- `/migration` page is **live** (absent-population-by-destination, Grade A, reconciled to the published 2,190,592 total).
- `census_facts` — **531,618 rows, 753 palikas, 11 NPHC-2021 tables** — is the *same NPHC-2021 backbone* the Atlas uses for ~18 of its 28 maps (absentee %, internal migration, literacy, wealth, education, female share).
- `dne_facts` — migrant workers ×234 destination countries ×51 months (**live, to Shrawan 2082**) + remittance NPR (short, 3 FY).
- `administrative_units` — full 7→77→753→ward hierarchy with MoFAGA federal codes (the join key for every choropleth).
- Registered-but-paused stubs ready to activate: `dofe-labour-migration`, `moe-noc-student-outflow`, `fepb-manpower-companies`, `nrn-investment-tracker`, `ndrrma-damage-tally`.

**The single blocker** (stated verbatim in `src/features/migration-source/CLAUDE.md` and anticipated as items #28/#29 in `DATA_BUILDOUT_PLAN.md`): there is **no Nepal boundary geometry (GeoJSON/TopoJSON) and no `d3-geo` adapter in the repo**. The data largely exists; the **map engine does not.** That one unlock converts our existing census facts into the entire Atlas — but interactive, live, and provenanced. It is formalized in **[ADR-0025](../decisions/0025-choropleth-geo-adapter.md)**.

---

## 2. The Report, Decoded

### 2.1 Data spine (only ~6 sources, triangulated)
| Atlas source | What it powers |
|---|---|
| **NPHC 2021 census** (NSO microdata) | Every "absentee %" map, internal-migration flows, wealth/literacy/education overlays, decadal population change, female-absentee share — the analytical backbone |
| **DoFE labour permits** (MoLESS) | Permit trends by region/category/gender/skill; destination-country maps; district-of-origin map; BLAs |
| **NRB** (BoP + FOREX dept.) | Remittance trend + % GDP; remittance-by-channel (banks vs remittance companies) |
| **NLSS** 2010/11 & 2022/23 | Use-of-remittance (consumption/education/loan-repayment); source/destination split |
| **KNOMAD / World Bank** bilateral remittance matrix 2021 | Per-country remittance + migrant stock + per-migrant average (Table 6) |
| **IDMC / NDRRMA / BIPAD** | Climate-displacement maps + event table (2012–2024) |
| **FEWIMS / Foreign Employment Board** | Women migrant-worker deaths by cause; family-disruption stats |

### 2.2 Visual grammar (what we must reproduce, then surpass)
- **Choropleths (28):** sequential ramps at **753-palika** and **77-district** grain; several with per-destination-country **pie overlays** (Maps 9, 12); one bivariate-ish food-security provincial map.
- **Figures (17):** two **population pyramids** (2011 vs 2021; plus an absentee-only pyramid), a **Sankey** origin-province→destination-region flow (Fig 6), **stacked-area** permit trend by region (Fig 7), **grouped gender bars** by category/skill (Figs 8, 11), **dual-axis** remittance line+%GDP (Fig 13), small-multiple **single-country permit lines** (Cyprus/Croatia/Mauritius), **pie/donut** remittance-channel and source/destination splits.
- **Tables (6):** top destinations (women), reasons-for-absence, top district-to-district corridors, top-10 remittance-sending countries.

### 2.3 Narrative arc (the editorial template to beat)
Overview → demographic transition (fertility 1.9, working-age 62%) → migration "at a glance" → **where from** (internal: 8.24M recent internal migrants, 19.2% for work; international: Eastern Terai dominant) → **where to** (Gulf core → Europe emerging 15× since 2021 → India invisible/open-border) → gender (18% of absentees, 10% of permits, rising) → migrant profile (poorest quintile, unskilled, undereducated) → **why** (push: jobs/food-insecurity/climate; pull: wages/networks/12 BLAs) → remittance → consequences (Dutch disease, fallow land, GBV, 258 women dead 2008–2022, return/reintegration) → recommendations.

---

## 3. What We Beat (the differentiators)

1. **Live, not frozen.** Our `dne-migrant-workers` runs monthly to Shrawan 2082; their permit charts stop at FY2023/24. A migration lens that updates with each NRB/DoFE release vs. a one-time print.
2. **Provenance + confidence on every claim.** Inline A/B/C grade + source + "as of" on hover, clickable into the Fact Ledger. The Atlas mixes Grade-A census with Grade-C "one study reported NPR 20,000–50,000" with no signal.
3. **We catch their error.** Page 49/57 states remittance was **"NPR 144 billion in 2023/24"** and repeats it ("43.2% of the NPR 144 billion came through BFIs"). The chart on the *same page* tops near **1,500 NPR billion** at >25% of GDP. Actual FY2023/24 worker remittance ≈ **NPR 1,445 billion** — a dropped digit, twice. **This is exactly what our cross-source reconciliation gate (ADR-0021) exists to catch.** Candidate launch story: *"We rebuilt Nepal's migration atlas — and found the number that was off by 10×."*
4. **Honest about India.** The Atlas leaves the open-border flow as a near-blank. We model it with explicit confidence bands (census absentee-in-India share by palika is Grade A; the *volume/earnings* is Grade C) rather than implying precision we don't have. Never zero-fill (Data Continuity Protocol).
5. **Open + queryable.** Every figure backed by a fact row, not a PDF "available upon request."

---

## 4. Data-Acquisition Pipeline

Each Atlas layer mapped to a concrete registry action, in doctrine order (register → `docs/sources/` profile → deterministic Python parser → staging → reconcile → approve). **Proposed seed rows are fully specified in §4.2 so the implementation PR is copy-paste ready;** no seed edits happen this round.

### 4.1 Source action table
| # | Atlas layer | Source | Our status | Action | Tier |
|--|---|---|---|---|--|
| M1 | Absentee %, internal flows, wealth/literacy/education maps | NPHC 2021 | ✅ `census_facts` | **Surface only** (needs ADR-0025 geometry) | 4 |
| M2 | Migrant workers by country, monthly | DoFE→NRB DNE | ✅ live (B) | Promote into migration model + fix DNE migrant sheet | 1 |
| M3 | Permits by **district-of-origin**, skill, category, gender | **DoFE direct** | stub `dofe-labour-migration` (paused) | **Activate** — richest new feed; new typed fact table | 2 |
| M4 | Remittance NPR long series + % GDP | NRB BoP `Trade-and-Balance-of-Payments.xlsx` | ⚠️ 3 FY in `dne_facts` | Backfill historical `BOP 2000-` sheet | 1 |
| M5 | ~~Per-country remittance + migrant stock~~ | ~~KNOMAD bilateral matrix~~ | **DROPPED** | Source dysfunctional as of 2026-06 — removed from plan | — |
| M6 | Climate displacement (palika events + district persons) | IDMC + NDRRMA/BIPAD | stub `ndrrma-damage-tally` (paused) | Activate NDRRMA; **register IDMC** | 4 |
| M7 | Bilateral Labour Agreements (12 countries) | MoLESS | ❌ | Register as reference + entity-keyed facts | 3 |
| M8 | Women migrant-worker deaths by cause | FEWIMS / FEB | ❌ | **Register new** (annual) | 3 |
| M9 | Use-of-remittance + channel split (BFI vs remit-co) | NLSS + NRB FOREX dept. | NLSS=reference; channel=❌ | Activate channel split (annual) | 3 |
| M10 | Student outflow (NOC) | MoE | stub `moe-noc-student-outflow` (paused) | Activate (complements permits in Fig 3) | 4 |

### 4.2 Proposed new source-registry rows (spec — NOT seeded yet)
> When implemented, each lands as a `seed-source-registry.ts` row **and** a `docs/sources/<id>.md` profile (Documentation Gate). Fields below are the registration contract.

- ~~**`knomad-bilateral-remittance`**~~ — **DROPPED 2026-06-11** (source dysfunctional). Per-country remittance economics will need an alternative source (NRB FOREX-dept corridor data, or World Bank WDI aggregate) — TBD.
- **`idmc-displacement`** — Agency: IDMC (Internal Displacement Monitoring Centre) · Dataset: GIDD disaster-displacement (Nepal, by year/event) · Frequency: annual · Format: xlsx/api-export · Mode: manual_upload · Tier 4 · Confidence: **B** · License: CC-BY-NC.
- **`fewims-migrant-deaths`** — Agency: Foreign Employment Welfare Information Management System / Foreign Employment Board · Dataset: migrant-worker deaths by cause/sex/destination/FY · Frequency: annual · Format: pdf/manual · Mode: manual_upload · Tier 3 · Confidence: **B** · License: gov_open. *Sensitivity: report counts only; never name individuals.*
- **`moless-bla`** — Agency: MoLESS · Dataset: Bilateral Labour Agreements + G2G arrangements (signatory, date, scope) · Frequency: ad_hoc · Format: pdf/manual · Mode: manual_upload · Tier 3 · Confidence: **A** (legal instruments) · License: gov_open. *Modeled as entity facts (one entity per agreement), not a time series.*

### 4.3 Activations (existing stubs → active; status-flip + rich profile only)
`dofe-labour-migration` (Tier 2), `moe-noc-student-outflow` (Tier 4), `ndrrma-damage-tally` (Tier 4), `fepb-manpower-companies` (Tier 4, for the "Cost of Leaving" calculator's recruitment-cost ceilings), `nrn-investment-tracker` (Tier 4, Diaspora Capital Desk).

### 4.4 The DoFE granular fact model (M3 — biggest new build)
DoFE permits carry dimensions the census cannot: **origin district**, **destination country**, **skill class** (unskilled/semi/skilled/high-skilled/professional), **permit category** (new individual / re-entry / recruitment-agency / G2G), **sex**, **FY/month**. This is a new typed fact table (`migration_permit_facts`, dimensional like `dne_facts`) — needs its own ADR at implementation time (enums for skill/category), referenced here but **not** designed in this plan-only round. ADR-0003 holds: production parser is deterministic Python; Claude CLI is QA only.

---

## 5. Atlas-Map → Our-Data Crosswalk

How completely we can reproduce each Atlas artifact *today* vs. what acquisition unblocks it. (G = geometry/ADR-0025 only; D = needs new data.)

| Atlas artifact | Our data status | Unblocks with |
|---|---|---|
| Maps 3, 4, 5, 13, 14, 15, 16, 19, 20, 21, 26 (census choropleths) | ✅ `census_facts` (palika) | **G** (ADR-0025) |
| Maps 7, 8 (decadal population change) | ⚠️ need 2001/2011 census totals joined to 2021 | G + D (historical census totals) |
| Map 6, 9–12, 17, 18 (DoFE permit maps, by district/country) | ⚠️ country×month live; district-of-origin & per-country aggregates needed | G + D (M3 DoFE) |
| Fig 1, 2, 4 (population pyramids) | ✅ census age×sex | none (chart only) |
| Fig 3 (labour + education migration trend) | ⚠️ permits ✅; NOC student outflow ❌ | D (M10) |
| Fig 5, 6 (origin→destination Sankey) | ✅ census + ✅ `d3-sankey` adapter already in repo | none |
| Fig 7, 8, 11 (permit by region/category/skill) | ⚠️ region/category/skill | D (M3) |
| Fig 13 (remittance trend + %GDP) | ⚠️ 3 FY only | D (M4 backfill) |
| Fig 14, 15, 16 (remittance use/channel) | ❌ | D (M9) |
| Fig 17 (women migrant deaths) | ❌ | D (M8) |
| Table 6 (per-country remittance) | ❌ | D (M5 KNOMAD) |
| Maps 24, 25 + Table 4 (climate displacement) | ⚠️ stub | D (M6) |
| Map 27 (BLAs) | ❌ | D (M7) |

**Takeaway:** ~11 of 28 maps + 3 figures + the Sankey are reproducible with **geometry only** (no new data) — that is the entire Phase-1 visible win, drawn from data already reconciled in our DB.

---

## 6. Geometry Decision (the unlock)

**Granularity: palika (753) first** (user decision, 2026-06-11). Rationale: it is our `census_facts` native grain and matches the Atlas's most detailed maps; districts (77) and provinces (7) are dissolved-up aggregations of the same geometry, so palika-first gives all three levels for free. Cost: heavier geometry + mobile-performance care — addressed in **[ADR-0025](../decisions/0025-choropleth-geo-adapter.md)** (TopoJSON + simplification + quantization; viewport/zoom-gated palika detail). Join key = MoFAGA `federal_code` on `administrative_units` (8-digit for local levels). The Atlas itself notes "district identity is not derivable from the federal code" — ADR-0025 specifies the crosswalk that fixes this.

---

## 7. Product — the Migration Lens (better than print)

Extends the live `/migration` page into a three-mode lens (mobile-first, per UI_ACCEPTANCE.md):

- **The Map** — interactive palika→district→province choropleth with a **layer switcher** (absentee %, female %, by-destination-region, internal out/in-migration, wealth quintile, literacy, climate displacement). Hover/tap = the value + **source + A/B/C grade + as-of date**. This collapses the Atlas's 28 maps into one live surface.
- **The Flow** — live D3 Sankey (origin province → destination region/country) rebuilt each release from census + DoFE; the Atlas's static Fig 6, animated through time.
- **The Ledger** — remittance trend + per-country economics (KNOMAD), the reconciliation note that surfaces the 10× error, channel split, and the **"Cost of Leaving Nepal" calculator** hook (STRATEGY Signature Utility 3, fed by `fepb-manpower-companies` recruitment ceilings).

Every figure is a clickable Fact Ledger claim; absent India volume shown as a labelled confidence band, never fabricated.

---

## 8. Phased Dispatch Sequence

- **Phase 0 — ✅ done (2026-06-11):** this doc + ADR-0025 + CHANGELOG.
- **Phase 1 — ✅ done (2026-06-11) — vertical slice (the unlock):** the `nepal-admin-boundaries` geometry asset (`src/lib/viz/geo/palikas-753.geo.json`, 753 palikas, federal-code-joined 753/753, render-verified) + the build pipeline (`scripts/geo/`) + the **absent-population-by-origin palika choropleth** (`PalikaChoropleth`, View B at `/migration`), end-to-end from `census_facts`. **Implemented as precomputed SVG paths (zero runtime geo deps), not TopoJSON+d3-geo** — see ADR-0025 Implementation Note. Note: ships as absent-population **count** (Grade A, single census table); the absentee-**%** layer (needs a per-palika population denominator) is a Phase-3 follow-up. All gates green (typecheck/lint/test/build/source-registry). Pairs with `DATA_BUILDOUT_PLAN.md` #29 (the census choropleth now has its base geometry).
- **Phase 2 — data acquisition (✅ 2026-06-11, ingest-deferred):** registered `fewims-migrant-deaths` (M8) + `idmc-displacement` (M6); **KNOMAD (M5) dropped — dysfunctional.** The **absentee-% intensity layer** shipped early. The **`migration_permit_facts` fact-domain foundation** (M3) built ([ADR-0026](../decisions/0026-migration-permit-fact-domain.md)). **Two deterministic parsers built + verified against real files** (ADR-0003): `nrb_remittance_history` (the BPM5 long remittance series, M4 backfill, FY2000/01–2020/21, reproduces Atlas Fig 13) and `dofe_migrant_workers` (44,891 permit-count rows for `migration_permit_facts`, reconciliation-gated). **The only remaining step is ingestion** (operator runbook, needs a populated DB) + flipping `dofe-labour-migration` active.
- **Phase 3 — lens build-out:** ~~absentee-% intensity~~ (✅), ~~live origin→destination Sankey~~ (✅ 2026-06-11, View C — the Atlas's Fig 6), layer switcher across the other census layers, remittance ledger + error-catch story, "Cost of Leaving" calculator.
- **Phase 4 — editorial:** first flagship migration story (uses CONTENT_FORMATS templates) + Fact Ledger cross-links + District-MRI migration row wiring.

---

## 9. Open Decisions / Escalations

1. **`migration_permit_facts` schema + enums** — needs its own ADR (skill-class + permit-category enums) at Phase-2 start. Escalate before coding (Rule 2: new pattern → ADR).
2. **Boundary geometry provenance + license** — survey-dept official vs. OCHA/HDX COD-AB vs. community (e.g. mesaugat/nepal-geojson). Must be a registered source with license recorded. Decided in ADR-0025; flagged here for the registry.
3. **Historical census totals (2001/2011)** for decadal-change maps (Maps 7/8) — is district/palika historical population already on disk, or a new acquisition? Verify against `docs/DATA_AUDIT.md` before promising those two maps.
4. **FEWIMS sensitivity** — death data is counts-only, no PII; confirm the published source granularity before registering.

---

## 10. References

- Source PDF: NDRI & AWO International (2025), *Migration Atlas of Nepal*, ISBN 9789937-1-9285-9, www.ndri.org.np.
- [ADR-0025](../decisions/0025-choropleth-geo-adapter.md) — choropleth geometry adapter (the unlock).
- [ADR-0003](../decisions/0003-ai-assisted-parsing-policy.md) — deterministic parsers only.
- [ADR-0009](../decisions/0009-source-registry-single-source-of-truth.md) — registry is the single source of truth.
- [ADR-0011](../decisions/0011-fiscal-data-units-and-identity.md) — data-unit identity (the "144 vs 1,445" discipline).
- [ADR-0021](../decisions/0021-pdf-recovery-tiers-and-verification-gate.md) — reconciliation gate (catches the 10× error).
- `src/features/migration-source/CLAUDE.md` — live View A; the GeoJSON deferral this plan resolves.
- `docs/research/DATA_BUILDOUT_PLAN.md` #28 (migration source map) + #29 (census choropleth / d3-geo).
- `docs/DATA_AUDIT.md` §migrant-workers + §remittance — the live truth layer for grades/coverage.
- `docs/STRATEGY.md` — Migration Industry vertical, Diaspora Capital Desk, Signature Utility 3 ("Cost of Leaving Nepal").
