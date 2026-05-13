# Source Registry — Coverage Audit & Expansion Proposal

**Status:** Draft for user review. Not yet codified into `SOURCE_REGISTRY.md`. Once user accepts (with edits), this is folded back into the canonical registry doc and the v1 ADR.

**Why now:** The current `SOURCE_REGISTRY.md` has 12 sources across 4 tiers, drafted in Day 0. With the foundation, parser tooling, and validation job in place, the limiting reagent for the next 90 days is *which sources actually feed which verticals*. This document audits the 17 verticals + 5 pillars + 3 utilities + District MRI + 9 lenses against the registry and proposes what's missing.

---

## Method

For each vertical / pillar / utility, I list what `STRATEGY.md` says it needs (Pulse tiles + Knowledge Base + first story), then map each requirement to a data feed. A feed is **Covered** if it's in the current registry, **New** if it needs adding, or **Reference** if it's a knowledge-base input rather than a time-series feed.

Two structural changes proposed:

1. **Split the registry into two artifacts.** Time-series feeds with parsers vs. reference assets (Economic Survey, NPC plans, sector white papers) that we cite but don't parse into `approved_indicator_values`. Reference assets get a lighter shape (no parser, no Drizzle row).
2. **Re-tier from "0–4" to "0, 1, 2, 3, Phase-2"** with cleaner thematic groupings.

---

## Mapping — by Public Pillar

### Pillar 1 — Money In

| Need | Source | Status |
|---|---|---|
| Macro inflows (remittances, exports, FDI aggregates) | NRB CMEFs (monthly) | **Covered — `nrb-cmefs-monthly`** |
| NCPI inflation context | NRB NCPI Table 2(B) | **Covered — `nrb-ncpi-table`** |
| FDI granular (by country/sector) | NRB *Status of FDI in Nepal* (annual bulletin) | **New — `nrb-fdi-bulletin`** |
| Foreign reserves (daily) | NRB daily reserve disclosure (NRB website) | **New — `nrb-reserves-daily`** |
| Remittance corridor detail | NRB *Nepal Remittance Survey* (every 4–5 years) + NRB monthly remittance series | **New (reference + light feed) — `nrb-remittance-survey`** |
| Foreign aid disbursement | MoF AMP / DFIMIS (Aid Management Platform) | **Already listed — `mof-dfimis` (Tier-4 in current registry)** |
| Tourism arrivals + receipts | NTB monthly + DoT statistics | **Covered — `ntb-tourism-monthly`** |
| Power export revenue (to India) | NEA Annual Report; sometimes monthly bulletins | **New — `nea-power-export`** |
| IT services export estimate | NTA + NCC + NRB BoP "computer & info services" | **New (derived) — `it-services-export-derived`** |
| Diaspora / NRN investment | NRN-MoF reports + IBN disclosures | **New — `nrn-investment-tracker`** |

### Pillar 2 — Money Out

| Need | Source | Status |
|---|---|---|
| Trade (imports) | Department of Customs monthly stats | **Already listed — `customs-monthly-trade` (Tier-2)** |
| Petroleum imports + fuel pricing | Nepal Oil Corporation (NOC) monthly bulletin + price-revision notices | **New — `noc-petroleum-monthly`** |
| Labour migration outflow | DoFE monthly labour permits + airport-records | **Already listed — `dofe-labour-migration` (Tier-4)** |
| Student outflow / education FX | Ministry of Education *No Objection Letter* (NOC) data + NRB BoP education line | **New — `moe-noc-student-outflow`** |
| Medical / travel FX outflow | NRB BoP categories (derived from CMEFs) | **Covered (derived from `nrb-cmefs-monthly`)** |
| Debt service outflow | PDMO debt bulletin (quarterly) | **Already listed — `pdmo-debt-bulletin` (Tier-2)** |

### Pillar 3 — Money Captured

| Need | Source | Status |
|---|---|---|
| Banking concentration | NRB *Banking and Financial Statistics* (quarterly) | **Already listed — `nrb-banking-stats` (Tier-2)** |
| NEPSE market structure | NEPSE EOD + market-cap by stock | **Already listed — `nepse-eod` (Tier-3)** |
| Cooperative regulatory status | Department of Cooperatives portal + Sahakari Bibhag | **New — `coops-regulatory-status`** |
| Cross-ownership / business groups | Office of Company Registrar (OCR) + Beed Management cross-references | **New (HARD — mostly PDF, no structured API) — `ocr-company-register`** |
| Large taxpayer concentration | IRD *Top Taxpayers* annual disclosure + LTO data | **New — `ird-top-taxpayers`** |
| Real estate developer concentration | Department of Land Management + Survey transaction data | **New (HARD — Land Survey is Phase-2) — defer** |

### Pillar 4 — Money Wasted

| Need | Source | Status |
|---|---|---|
| Federal fiscal preliminary (daily) | FCGO daily revenue + expenditure | **Already listed — `fcgo-daily` (Tier-2)** |
| Public debt + service | PDMO bulletin | **Already listed — `pdmo-debt-bulletin` (Tier-2)** |
| Audit observations | OAG audit reports | **Already listed — `oag-audit-reports` (Tier-4)** |
| Annual budget + reconciliation | MoF *Budget Red Book* + Mid-Term Review + Economic Survey | **New (reference + light feed) — `mof-budget-redbook`** |
| Public enterprise losses | DPM Office *Annual Performance Report* of public enterprises | **New — `dpm-public-enterprises-annual`** |
| Capital expenditure execution | LMBIS (Line Ministry Budget Information System) + SuTRA (Sub-national Treasury Regulatory Application) | **New — `mof-lmbis` + `mof-sutra`** |
| Local government audits | OAG-LBL (Local Body audit reports) — published per FY | **New — `oag-lbl-local-audits`** |
| Project execution tracker | NPC Project Bank + line-ministry monitoring | **New — `npc-project-bank`** |

### Pillar 5 — Where Money Becomes Wealth

| Need | Source | Status |
|---|---|---|
| GDP quarterly | NSO quarterly GDP | **Already listed — `nso-gdp` (Tier-3)** |
| Agricultural production | MoALD seasonal crop production + agriculture census | **Already listed — `moald-crop-production` (Tier-3)** |
| Hydropower generation | NEA Annual Report; periodic generation snapshots | **New — `nea-generation-monthly`** |
| Hydropower project pipeline | DoED (Department of Electricity Development) licence + project registry | **New — `doed-project-pipeline`** |
| Tourism receipts (per-tourist spend, leakage) | NTB + NRB BoP services + survey data | **Already listed (`ntb-tourism-monthly`); leakage derived** |
| Health system outcomes | DoHS HMIS (Health Management Information System) | **New — `dohs-hmis`** |
| Education outcomes | CEHRD / DoEd EMIS (Education Management Info System) | **New — `dohs-emis`** |
| Forest cover change | Hansen Global Forest Change (annual, satellite) | **Already listed — `hansen-gfc` (Tier-4)** |
| Land use classification | ESA WorldCover (decadal) | **Already listed — `esa-worldcover` (Tier-4)** |
| Manufacturing index | Department of Industry — Industrial Production Index (thin) | **New (data quality C-tier) — `doi-industrial-production`** |

---

## Mapping — by Vertical (where it diverges from Pillar mapping)

Most verticals are covered by the pillar mapping above; the ones below need additional or sub-national sources:

### Vertical 5 — Sahakari Tracker
Already partially covered by `coops-regulatory-status` (Pillar 3). Also needs:
- Nepal Sahakari Sangh (apex body) cooperative directory — `nesss-coop-directory` **New**
- Sahakari Recovery Committee status updates — manual / press releases; not a structured feed

### Vertical 7 — Price Chain Nepal + Border Economy
- Kalimati Fruits & Vegetables Market daily wholesale — `kalimati-daily-prices` **New (DAILY — critical for one of the flagship stories)**
- Pokhara / Birgunj / Itahari wholesale markets — `regional-wholesale-prices` **New (partial coverage; each market publishes differently)**
- Cross-border price comparison (NP vs IN) — manual + NRB peg context

### Vertical 10 — Budget Watch + Local Ledger (753)
The "Local Ledger" piece is the heaviest single requirement we don't have:
- LMBIS — federal line-ministry budget execution — `mof-lmbis` **New**
- SuTRA — sub-national fiscal — `mof-sutra` **New**
- NNRFC — fiscal transfer allocations (Nepal Natural Resources & Fiscal Commission) — `nnrfc-allocations` **New**
- 753 local governments × budgets × audits — at scale impossible Year 1; sample 50 in Year 1 — `local-govt-budgets-sampled` **New (sampled)**

### Vertical 13 — The Soil Economy
- Department of Forest Research & Survey (DFRS) — National Forest Inventory — `dfrs-forest-inventory` **New (every 5–10 years; semi-static reference)**
- DoLS (Department of Land Survey) cadastral aggregates — `dols-cadastral` **New (Phase-2)**
- ICIMOD geospatial layers — `icimod-geospatial` **New (semi-reference)**
- Agriculture Census (Decennial; last 2011/12, next due) — `agri-census` **Reference**

### Vertical 14 — The Tax State
- IRD revenue dashboard (digital) — `ird-revenue-monthly` **New**
- Customs duty exemption list (sometimes annexed to budget) — `customs-exemptions` **New (annual)**
- VAT refund / pending refund — `ird-vat-refunds` **New (data quality C-tier)**

### Vertical 15 — Migration Industry + FX Corridor
- DoFE monthly labour outflow — already listed (`dofe-labour-migration`)
- Foreign Employment Promotion Board (FEPB) — recruitment-cost ceilings, manpower licenses — `fepb-manpower-companies` **New**
- MTO published exchange rates (IME, Prabhu, Western Union via their websites/disclosures) — `mto-exchange-rates` **New (HARD — fragmented per MTO)**
- NRB inter-bank reference rate — `nrb-interbank-fx` **New** (in CMEFs sub-tables)
- Recruitment-loan stress proxy — derived (cooperative + microfinance arrears)

### Vertical 16 — Collateral State (Credit Allocation)
- NRB *Quarterly Economic Bulletin* (loans & advances by sector) — `nrb-loans-by-sector` **New** (sometimes inside CMEFs; sometimes separate)
- Credit Information Bureau Nepal (CIB) — aggregated sectoral credit — `cib-sectoral-credit` **New** (HARD — partial public release)

### Vertical 17 — Household Ledger
- NCPI ✓ Covered
- NLSS (National Living Standards Survey) — last 2010/11, next pending — `nlss-survey` **Reference (decadal)**
- Census 2078 (NSO; published 2023) — `census-2078` **Reference (decadal)**
- Nepal Demographic & Health Survey (NDHS — quinquennial) — `ndhs-survey` **Reference**

---

## District MRI (Year 1 covers 5 districts: Kathmandu, Chitwan, Kaski, Jhapa, Morang)

District-level data is its own dimension. We need:

- Census 2078 district-level disaggregated data — `census-2078-district` **Reference + light feed (one-time ingest)**
- Sub-national fiscal transfers (NNRFC) — `nnrfc-allocations` covers this
- District-level revenue (DRA — District Revenue Administration) — **HARD**, often paper-based
- District-level migration outflow (DoFE has district breakdown sometimes) — covered by `dofe-labour-migration` if disaggregated
- District-level land transactions (Department of Land Management — *Malpot* statistics) — `dolm-malpot-stats` **New**
- District-level economic surveys (MoF Economic Survey annexes sometimes have provincial; rarely district) — `mof-economic-survey` **Reference**

---

## Crosscutting / Special

### Climate exposure (Vertical 11 — Hydropower + Climate)
- Department of Hydrology & Meteorology (DHM) — flood / discharge / precipitation — `dhm-hydro-met` **New**
- NDRRMA (National Disaster Risk Reduction & Management Authority) — disaster damage tally — `ndrrma-damage-tally` **New**
- ICIMOD glacier inventory — `icimod-glacier-inventory` **New (reference)**

### International benchmarks (Reference)
- World Bank Indicators (WDI) — `wb-wdi` **Reference (continuous)**
- World Bank International Debt Statistics — already listed (Tier-4)
- IMF Article IV reports for Nepal — `imf-article-iv` **Reference**
- ADB Asian Development Outlook (annual Nepal section) — `adb-ado-nepal` **Reference**
- UN Comtrade (trade partner perspective) — `un-comtrade` **Reference + light feed**

### Election / governance (Phase 2+)
- Election Commission Nepal — results by federal / provincial / local — `ecn-results` **Phase-2**
- Ministry of Industry — company registration trends — `moic-company-registry` **Phase-2**

### Editorial reference assets (NOT time-series feeds; cite-only)
- MoF Economic Survey (annual; the giant macro reference) — `mof-economic-survey-annual` **Reference**
- MoF Budget Speech + Red Book — `mof-budget-redbook-annual` **Reference**
- NPC 16th Five-Year Plan (FY 2081/82–2085/86) — `npc-16th-plan` **Reference**
- Sectoral white papers + master plans — track in `docs/reference-assets/` per ministry
- IBN (Investment Board Nepal) project pipeline — `ibn-project-pipeline` **Reference + light feed**

---

## Proposed re-tiered structure (replaces Tier 1–4 in `SOURCE_REGISTRY.md`)

### Tier 0 — Already ingestable today (existing files in repo)
| ID | Status |
|---|---|
| `nrb-ncpi-table` | Worker C parser ships v0.1.0; registry seeded by Worker F |
| `nrb-cmefs-monthly` | Registry seeded; parser pending (needs Surya for PDF tables) |

### Tier 1 — Days 1–28 (the macro spine + first flagship inputs)
| ID | Need it for | Priority |
|---|---|---|
| `nrb-reserves-daily` | Money In Pulse tile | High |
| `customs-monthly-trade` | Money Out Pulse + flagship #2 | High |
| `noc-petroleum-monthly` | Money Out + flagship #4 (NOC) | High |
| `fcgo-daily` | Money Wasted Pulse + Local Ledger | High |
| `nepse-eod` | Money Captured Pulse + Private Capital | High |
| `kalimati-daily-prices` | Price Chain Pulse + flagship #2 | High |

### Tier 2 — Days 28–60 (quarterly macro + first deep-dives)
| ID | Need it for | Priority |
|---|---|---|
| `pdmo-debt-bulletin` | Borrowed Time vertical | High |
| `nrb-banking-stats` | Money Captured + Collateral State | High |
| `nrb-loans-by-sector` | Collateral State vertical | High |
| `dofe-labour-migration` | Migration Industry | High |
| `nrb-fdi-bulletin` | Money In granular | Medium |
| `nso-gdp` | Where Money Becomes Wealth | Medium |
| `ntb-tourism-monthly` | Tourism Value Chain | Medium |

### Tier 3 — Days 60–120 (verticals + utilities deepen)
| ID | Need it for | Priority |
|---|---|---|
| `coops-regulatory-status` | Sahakari Tracker (signature utility approach) | High |
| `oag-audit-reports` | Money Wasted | High |
| `dpm-public-enterprises-annual` | Public Enterprise X-Ray | High |
| `moald-crop-production` | Soil Economy | Medium |
| `mof-lmbis` | Budget Watch | Medium |
| `mof-sutra` | Local Ledger (sub-national) | Medium |
| `nnrfc-allocations` | Local Ledger (transfers) | Medium |
| `ird-revenue-monthly` | Tax State | Medium |
| `nea-generation-monthly` | Hydropower Monitor | Medium |
| `doed-project-pipeline` | Hydropower Monitor | Medium |
| `npc-project-bank` | Money Wasted (project failure) | Medium |

### Tier 4 — Days 120–365 (the long-tail of Year 1)
| ID | Need it for | Priority |
|---|---|---|
| `census-2078-district` | District MRI (5 districts) | High for District MRI launch |
| `moe-noc-student-outflow` | Money Out + Migration | Medium |
| `ird-top-taxpayers` | Tax concentration | Medium |
| `oag-lbl-local-audits` | Local Ledger audits | Medium |
| `dohs-hmis` | Where Money Becomes Wealth (health) | Medium |
| `dohs-emis` | Where Money Becomes Wealth (education) | Medium |
| `mof-budget-redbook` | Budget Watch + reference | Medium |
| `fepb-manpower-companies` | Migration Industry | Medium |
| `dhm-hydro-met` | Climate Exposure | Medium |
| `ndrrma-damage-tally` | Climate Exposure | Medium |
| `customs-exemptions` | Tax State | Low |
| `dolm-malpot-stats` | Soil Economy (land transactions) | Low |
| `un-comtrade` | Trade Partner perspective (Reference + light feed) | Low |
| `nrn-investment-tracker` | Diaspora Capital | Low |

### Phase 2 (post-Day 365)
| ID | Need it for |
|---|---|
| `ocr-company-register` | Cross-ownership maps (HARD; manual phase) |
| `mto-exchange-rates` | FX Corridor (HARD; per-MTO scraping) |
| `cib-sectoral-credit` | Collateral State (HARD; partial public release) |
| `dols-cadastral` | Soil Economy (Land Survey — Phase 2) |
| `hansen-gfc` | Forest cover change |
| `esa-worldcover` | Land use classification |
| `icimod-glacier-inventory` | Climate Exposure |
| `ecn-results` | Election / governance overlays |
| `mof-dfimis` (aid disbursement) | Aid management |
| `regional-wholesale-prices` | Price Chain breadth |

### Reference-only assets (separate `docs/reference-assets/` track — NOT in `source_registry` table)
| Asset | Use |
|---|---|
| MoF Economic Survey (annual) | Macro narrative reference |
| MoF Budget Speech + Red Book (annual) | Budget Watch reference |
| NPC 16th Plan (5-yr) | Reference + project pipeline |
| NLSS (decadal) | Household Ledger reference |
| NDHS (quinquennial) | Health reference |
| Agriculture Census (decennial) | Soil Economy reference |
| DFRS Forest Inventory | Soil Economy reference |
| IMF Article IV | International benchmark |
| ADB ADO Nepal section | International benchmark |
| World Bank WDI | International benchmark |
| Census 2078 (full survey) | Reference + District MRI source |

---

## Summary of changes vs. current `SOURCE_REGISTRY.md`

- **From 12 entries across 4 tiers** → **proposed ~40 entries across 5 tiers + ~10 reference assets**.
- **Existing 12 entries reorganized:** `customs-monthly-trade` moves Tier-2→Tier-1; `nso-gdp` Tier-3→Tier-2; `oag-audit-reports` Tier-4→Tier-3; etc.
- **New "Reference-only" category** for editorial inputs we cite but don't parse into `approved_indicator_values`.
- **Tier 4 becomes the "long-tail of Year 1"** rather than a Phase-2 marker; new Phase-2 tier handles genuinely deferred work.

---

## Open questions for the user

1. **District MRI Year 1 — confirm the 5 districts.** STRATEGY.md mentions Kathmandu, Chitwan, Kaski, Jhapa, Morang. Accept, or change?
2. **Sahakari Tracker as a signature utility** vs. as a vertical. STRATEGY.md frames it as a vertical with a "Check your cooperative" search. Is that a separate utility (4th utility?) or part of the Sahakari vertical?
3. **`kalimati-daily-prices` priority.** It's listed Tier-1 here because Story #2 ("Why Farmers Get Rs 25") needs it. If Story #2 slips to month 3, this can drop to Tier-2.
4. **"Reference-only" assets**: do we still want them in a registry (lighter shape), or just in `docs/reference-assets/<asset>.md` files cited from `STRATEGY.md` and `KNOWLEDGE_BASE` entries?
5. **HARD sources** (OCR, MTOs, CIB, DoLS): should they get registry entries now as "Status: Paused — known-hard" so the doctrine surface tracks them even though no parser is planned? I lean **yes** — it keeps them visible.
6. **Manual / non-scraped sources** (OAG audits, NRB ad-hoc bulletins, NPC plans): the current registry doesn't distinguish "automated scraper" from "manual upload + parse". Add a `ingestion_mode` enum (`automated_cron` / `manual_upload` / `reference_only`)? Lean **yes**.

---

## Next steps once user accepts (or edits)

1. Land this audit into `SOURCE_REGISTRY.md` (rewriting the Tier-1–4 section).
2. Update `src/lib/db/schema/source-registry.ts` if we add the `ingestion_mode` enum.
3. Extend `scripts/seed-source-registry.ts` to seed the new Tier-1 rows (currently only seeds the original 2).
4. Tier-1 parsers become the next round of worker tasks.
