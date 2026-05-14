# Nepal Ledger — Data Requirements (Year 1)

> Single source of truth for what data flows into the Fact Ledger, in what order, with what acceptance criteria. Consolidates [STRATEGY](STRATEGY.md), [BACKEND_PLAN](BACKEND_PLAN.md), [SOURCE_REGISTRY](SOURCE_REGISTRY.md), [SOURCE_REGISTRY_AUDIT_PROPOSAL](SOURCE_REGISTRY_AUDIT_PROPOSAL.md), [FINANCIAL_DATA_STRATEGY](FINANCIAL_DATA_STRATEGY.md), and the recent CBS and Surya research audits.
>
> **Update protocol:** when a source moves between status columns, when an ADR adds or removes a source, or when a milestone slips — update this file in the same PR and append a row to §7 Changelog. Do not edit upstream docs from here; this file consolidates, it does not amend.

---

## 1. How To Read This Doc

### Status legend (Feed Inventory column)

| Status | Meaning | Concrete evidence today |
|---|---|---|
| `Not started` | No registry row, no parser, no source files in repo | Source named in STRATEGY but absent everywhere else |
| `Registered` | Row in `source_registry` (live DB or `scripts/seed-source-registry.ts`) and a Markdown profile in `docs/sources/<id>.md` | Profile + seed row exists |
| `Parser shell` | `scrapers/<id>/` directory exists with `parser.py` scaffold + tests harness but no end-to-end run | Directory present, fixtures empty or thin |
| `Parser complete` | Parser passes its own fixture tests and writes `staging_indicator_values`; no production rows yet | Tests green; staging populated in dev |
| `Staging only` | Parser run against real downloaded file; `staging_indicator_values` populated; not yet promoted | parser_runs row exists, no `approved_indicator_values` |
| `Approved` | Rows in `approved_indicator_values` (or the matching domain fact table) with provenance + confidence grade | Production-readable via repository functions |

### Confidence grades (reminder, full rules in [DATA_PIPELINE.md](DATA_PIPELINE.md) §"Confidence Grade Assignment")

- **A** — official audited / authoritative AND parser confident (NRB CMEFs published values, PDMO bulletin)
- **B** — official but preliminary OR parser ambiguity (FCGO daily preliminary, P-flagged CMEFs values)
- **C** — single source, extracted from prose, or computed from a proxy (estimated tourism leakage, IT-export proxies)

### Where to look upstream

- **What** to ingest and **why** → [STRATEGY.md](STRATEGY.md) (pillars, verticals, lenses)
- **When** to ingest in the 90-day plan → [BACKEND_PLAN.md](BACKEND_PLAN.md) §"The 90-Day Bootstrap Sequence"
- **How** to register a source → [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) §"Workflow"
- **How** to pipe scraped data to production → [DATA_PIPELINE.md](DATA_PIPELINE.md)
- **Period typing / BS-AD storage** → [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md)
- **Parsing policy (no production LLM API)** → [ADR-0003](decisions/0003-ai-assisted-parsing-policy.md), [PARSING_WORKFLOW.md](PARSING_WORKFLOW.md)
- **Storage of source documents** → [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md)
- **Pre-ingest audit doctrine** → research audits under `docs/research/`

---

## 2. Five Public Pillars → Data Needs (v1 minimum)

Ruthless v1 cut: only feeds that actually fire a Pulse tile, a Money Map flow, or a Fact Ledger claim in Year 1. Aspiration goes to §5.

| Pillar | Pulse tile (v1) | Required feed | Verticals served (STRATEGY §"17 Flagship Verticals") |
|---|---|---|---|
| **1. Money In** | Remittance inflow YTD, Forex reserves (months of import cover) | `nrb-cmefs-monthly`, `nrb-ncpi-table` | V1 Money Pulse, V12 Diaspora Capital |
| **2. Money Out** | Trade deficit, Debt service / revenue | `nrb-cmefs-monthly` (BoP lines), `customs-monthly-trade`, `pdmo-debt-bulletin` | V2 Borrowed Time, V14 Tax State, V15 Migration |
| **3. Money Captured** | Banking concentration (HHI on deposits + loans), NEPSE top-10 share | `nrb-banking-stats`, `nrb-bfi-monthly-xlsx`, `nepse-eod` | V3 Private Capital X-Ray, V5 Sahakari, V16 Collateral State |
| **4. Money Wasted / Destroyed** | Federal capex execution %, Per-municipality fiscal transfer (Local Ledger spotlight) | `fcgo-daily`, `local-fiscal-transfers-cleaned`, `mof-intergovernmental-historical` | V10 Budget Watch + Local Ledger, V4 Public Enterprise X-Ray |
| **5. Where Money Becomes Wealth** | NSO GDP, Tourism arrivals + receipts | `nso-gdp`, `ntb-tourism-monthly` | V9 Digital Export, V11 Hydropower, V13 Soil Economy |

Indicators required to populate the v1 Pulse cards listed above are enumerated in `docs/sources/nrb-cmefs-monthly.md` and the Banking-and-Financial-Statistics profile (to be written when that parser is briefed).

What is **explicitly out** of v1 Pulse: per-tourist leakage %, household ledger archetypes, manpower-company concentration, climate damage tally, IT-services export estimate, NPR/USD interbank-vs-mid-market spread. These appear in STRATEGY's Pulse but are scoped to Phase 2 or to flagship-story support rather than continuous Pulse tiles.

---

## 3. Feed Inventory

Three tier tables. Status reflects commit `f5d3290` (HEAD as of 2026-05-14). "Owner brief" cites the worker brief or future brief that owns shipping the parser.

### Tier 1 — Macro spine + first ingestable corpus (Days 1–28)

| source_id | Agency | Dataset | Period | Format | Confidence target | Status | Owner brief | Blocker |
|---|---|---|---|---|---|---|---|---|
| `nrb-cmefs-monthly` | NRB | Current Macroeconomic and Financial Situation | monthly + nine-month cumulative | PDF (tables) | A | Registered | Future (NRB CMEFs PDF parser) | Surya OCR stack proving on a labelled NRB page (Surya findings §"Devanagari regression at v0.17.1") |
| `nrb-ncpi-table` | NRB | NCPI Table 2(B) | nine-months cumulative | CSV | A | Parser complete | Worker C ([tasks/worker-C-python-scrapers.md](tasks/worker-C-python-scrapers.md)) | Validation job to promote — Worker G in flight at time of writing (brief at [tasks/worker-G-validation-job.md](tasks/worker-G-validation-job.md); implementation will ship in a separate PR after the repositories land) |
| `local-fiscal-transfers-cleaned` | MoF (Cleaned/) | Federal fiscal transfers to 753 local levels FY 2082/83 | annual (one FY) | XLSX (pre-cleaned) | A | Not started (data in repo at `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx`) | Pending (FINANCIAL_DATA_STRATEGY §"Phase A1") | Needs `local_government_fiscal_transfers` ingest script; schema already shipped in migration 0001 (`src/lib/db/schema/fiscal-transfers.ts`) |
| `nrb-bfi-monthly-xlsx` | NRB | Banking & Financial Statistics monthly XLSX (50 files, Shrawan 2078 → Bhadau 2082) | monthly | XLSX | A | Not started (corpus on disk at `Financial Data/nrb_monthly_statistics/`) | Pending (FINANCIAL_DATA_STRATEGY §"Phase A2") | Schema layout drift across 49 months — needs schema-discovery probe before parser write |
| `cbs-nphc-2021` | CBS | National Population & Housing Census 2021 (89 CSVs + 7 Listing XLSX + 1 DEGURBA XLSX) | decadal (one-time) | CSV + XLSX | A | Not started (data in repo at `Financial Data/Census/census_2021_data/`) | Pending (cbs-nphc-2021 ingest brief, see [research/cbs-nphc-2021-audit.md](research/cbs-nphc-2021-audit.md) §6) | Two-mode CSV reader + 27-name municipality-resolver override list need wiring; `census_facts` table already shipped (migration 0001) |

### Tier 2 — Quarterly macro + monthly trade/debt (Days 29–60)

| source_id | Agency | Dataset | Period | Format | Confidence target | Status | Owner brief | Blocker |
|---|---|---|---|---|---|---|---|---|
| `customs-monthly-trade` | Department of Customs | Monthly trade statistics | monthly | HTML + XLSX | A | Not started | Pending (no brief yet) | None — straightforward HTML+XLSX scrape; URL pattern stable |
| `pdmo-debt-bulletin` | PDMO | Quarterly debt bulletin | quarterly | PDF tables | A | Not started | Pending | Surya OCR stack must clear Devanagari benchmark first |
| `fcgo-daily` | FCGO | Daily revenue + expenditure | daily | (TBD — likely HTML/PDF) | B (preliminary) | Not started | Pending | Preliminary-flag handling in validation job (already supported via `confidence_grade_proposed`) |
| `nrb-banking-stats` | NRB | Banking & Financial Statistics quarterly bulletin | quarterly | PDF | A | Not started | Pending | Different cadence from the monthly XLSX corpus; may be reconcilable via the XLSX parser instead — confirm before separate parser |
| `nepse-eod` | NEPSE | End-of-day quotes + market cap | daily | JSON-ish API | A | Not started | Pending | None — JSON endpoint exists; needs registry row |
| `noc-petroleum-monthly` | NOC | Petroleum imports + price-revision notices | monthly | PDF + HTML | A | Not started | Pending | Audit proposal flags as Tier-1 priority for V4 Public Enterprise X-Ray flagship story (NOC) |
| `kalimati-daily-prices` | Kalimati Market | Daily wholesale prices | daily | HTML | A | Not started | Pending | Required for V7 Price Chain Nepal flagship; can drop to Tier-3 if Story #2 slips |
| `nrb-reserves-daily` | NRB | Daily forex reserve disclosure | daily | HTML/PDF | A | Not started | Pending | Disclosure cadence variable; verify before promising "daily" |

### Tier 3 — Sector + sub-national (Days 60–90)

| source_id | Agency | Dataset | Period | Format | Confidence target | Status | Owner brief | Blocker |
|---|---|---|---|---|---|---|---|---|
| `nso-gdp` | NSO | Quarterly GDP estimates | quarterly | PDF/XLSX | A | Not started | Pending | Lagged 1–2 quarters by source |
| `ntb-tourism-monthly` | Nepal Tourism Board | Monthly arrivals + receipts | monthly | HTML | A | Not started | Pending | None |
| `moald-crop-production` | MoALD | Seasonal crop production | seasonal | PDF | B | Not started | Pending | PDF-heavy, variable format; needs Surya stack |
| `mof-intergovernmental-historical` | MoF | 8 historical intergovernmental PDFs (FY 2074/75 → FY 2081/82) | annual × 8 FYs | PDF (scanned) | A (post-OCR review) | Not started (data in repo at `Financial Data/mof_documents/intergovernmental/`) | Pending (FINANCIAL_DATA_STRATEGY §"Phase B1") | Surya OCR + Devanagari normalization (shipped, commit `f5d3290`) + manual review |
| `mof-yellowbook-pe-annual` | MoF / DPM Office | Public Enterprises Annual Status Reviews (6 PDFs) | annual | PDF (scanned) | A (post-OCR review) | Not started (data in repo at `Financial Data/mof_documents/yellowbook/`) | Pending (FINANCIAL_DATA_STRATEGY §"Phase B2") | Surya OCR readiness; needs `pe_annual_financials` domain table — Phase 4 of FINANCIAL_DATA_STRATEGY schema plan |
| `mof-redbook-budget` | MoF | Federal Budget Red Books (latest 3 FYs of 20) | annual | PDF (heavy, mostly Nepali) | A | Not started (data in repo at `Financial Data/mof_documents/redbook/`) | Pending (FINANCIAL_DATA_STRATEGY §"Phase B3") | Heaviest single OCR target; needs budget-code controlled vocabulary preload |
| `mof-whitebook-foreign-aid` | MoF | Foreign Aid Source Books (14 PDFs, FY 2062/63 → FY 2078/79) | annual | PDF (scanned) | A | Not started (data in repo at `Financial Data/mof_documents/whitebook/`) | Pending (FINANCIAL_DATA_STRATEGY §"Phase B4") | Needs `foreign_aid_projects` domain table; lower priority since CMEFs has aggregates |

Reference-only assets (Economic Survey, NPC 16th Plan, NLSS, NDHS, Agriculture Census, World Bank WDI, IMF Article IV, ADB ADO Nepal) are tracked separately per [SOURCE_REGISTRY_AUDIT_PROPOSAL §"Reference-only assets"](SOURCE_REGISTRY_AUDIT_PROPOSAL.md). They are cited from stories and Knowledge Base entries but do not enter `approved_indicator_values`.

---

## 4. Sequencing (next 90 days)

Mapped to [BACKEND_PLAN §"The 90-Day Bootstrap Sequence"](BACKEND_PLAN.md). Each row's "Acceptance gate" is in addition to the universal CI gates (`pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build`, `pnpm exec drizzle-kit check`, `gitleaks detect --staged` — see [CLAUDE.md §"Verification Gates"](../CLAUDE.md)).

### Days 11–28 — First ingestion pipeline + Fact Ledger (BACKEND_PLAN row "11–28")

- **Deliverable (paraphrased):** register `nrb-cmefs-monthly` + `nrb-ncpi-table`; archive existing CSV + PDF to Storage with hash; first parser writes to staging; validation promotes to approved; Fact Ledger schema + clickable `<Claim>` component (BACKEND_PLAN Day 11–28).
- **Feeds consumed:** `nrb-ncpi-table` (primary), `nrb-cmefs-monthly` (registered but parser deferred).
- **Upstream preconditions:** schema foundation landed (commit `bfce676`); Drizzle migration 0001 + safeQuery shipped; date utilities pass FY-boundary tests; source-registry seeded (commit `351a514`); typed claim contract shipped (commit `e611bec`); validation job shipped (Worker G brief, commit `e4e560d`).
- **Acceptance gate:** 23 NCPI subcategories × 3 geographies × 3 periods in `approved_indicator_values` (BACKEND_PLAN row); at least one Fact Ledger claim renders with source PDF + confidence badge + last-verified.

### Days 29–45 — Pulse + Monthly Verdict v1 (BACKEND_PLAN row "29–45")

- **Deliverable:** 5 KPI cards on homepage; Pulse page with all NCPI subcategories; Monthly Verdict MDX template; bilingual scaffold (BACKEND_PLAN Day 29–45).
- **Feeds consumed:** `nrb-ncpi-table` for inflation cards; `nrb-cmefs-monthly` for the other 4 cards (remittance YTD, forex reserves, trade deficit, BoP).
- **Upstream preconditions:** Days 11–28 deliverables green; `nrb-cmefs-monthly` parser running (this is the slip-risk — see §6 OQ-1).
- **Acceptance gate:** homepage shows 5 real Chait 2082 numbers, each with source + confidence + last-verified (BACKEND_PLAN row).

### Days 46–60 — Money Map v0 (BACKEND_PLAN row "46–60")

- **Deliverable:** D3 Sankey at `/lenses/money-map`; sourced FY 2081/82 flows; mobile fallback (BACKEND_PLAN Day 46–60).
- **Feeds consumed:** `nrb-cmefs-monthly` (BoP aggregates), `customs-monthly-trade` (import detail), `pdmo-debt-bulletin` (debt service outflow).
- **Upstream preconditions:** Tier-2 trade + debt feeds parser-complete and at least Staging-only by Day 50.
- **Acceptance gate:** every flow node has source citation + confidence + Knowledge Base link.

### Days 61–75 — First flagship story + first entity profile (BACKEND_PLAN row "61–75")

- **Deliverable:** Kalimati price-chain investigation OR "How Nepal's Economy Actually Works"; Kalimati Market entity profile; second source ingestion (BACKEND_PLAN Day 61–75).
- **Feeds consumed:** `kalimati-daily-prices` (if Story #2), `customs-monthly-trade` (border arbitrage angle), `nrb-cmefs-monthly`.
- **Upstream preconditions:** `entities` table populated with Kalimati Market row (schema exists, migration 0001).
- **Acceptance gate:** flagship article + chart + Fact Ledger claims + Nepali version 1 week later.

### Days 76–90 — Public beta + one signature utility (BACKEND_PLAN row "76–90")

- **Deliverable:** Household Ledger Calculator OR Loan→Project→Asset Tracker v0 (BACKEND_PLAN Day 76–90).
- **Feeds consumed:** `nrb-ncpi-table` (Household Ledger), or `mof-whitebook-foreign-aid` + `pdmo-debt-bulletin` (Loan→Project Tracker v0 on one project).
- **Upstream preconditions:** choice of utility — see §6 OQ-2.
- **Acceptance gate:** calculator/tracker works on mobile; v0.9 tag on `main`.

### Cross-cutting milestone (no fixed week): the Financial Data corpus

The `Financial Data/` corpus (50 NRB BFI XLSX + 64 MoF PDFs + 99 CBS census files + the pre-cleaned FY 2082/83 fiscal transfer XLSX) is **already on disk** ([FINANCIAL_DATA_STRATEGY §"Inventory"](FINANCIAL_DATA_STRATEGY.md)). Its sequencing inside the 90-day plan is:

- **Phase A1** (no OCR) — `local-fiscal-transfers-cleaned` ingest. ~7,500 rows. Can land Days 14–21.
- **Phase A2** (no OCR) — `nrb-bfi-monthly-xlsx` parser. ~3,000+ rows. Can land Days 21–35.
- **Phase A3** (no OCR) — `cbs-nphc-2021` ingest of `Indv01` + `Hhld05–Hhld10` first (research audit §6 sequencing). Can land Days 21–35.
- **Phase B1–B4** (Surya OCR) — `mof-intergovernmental-historical` → Yellow Books → Red Books → White Books. Days 35–75 once Surya Devanagari benchmark passes.

This phasing is **proposed** in FINANCIAL_DATA_STRATEGY (still marked "Draft for user review") — no ADR-locked decision yet. See §6 OQ-3.

---

## 5. Out-of-Scope For Year 1

| Item | Defer reason | Authority |
|---|---|---|
| Cloudflare R2 source-document storage | Payment method not on file; use Supabase Storage Year 1 with S3-compatible seam | [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md) |
| Production LLM API parsing | Cost + provenance fragility; Claude CLI is dev assistant only, production parsers are deterministic Python | [ADR-0003](decisions/0003-ai-assisted-parsing-policy.md), [PARSING_WORKFLOW.md](PARSING_WORKFLOW.md) |
| `ocr-company-register` (OCR — Office of Company Registrar) | Mostly PDF, no structured API; manual phase needed | SOURCE_REGISTRY_AUDIT_PROPOSAL §"Phase 2" |
| `mto-exchange-rates` (per-MTO scraping for FX corridor) | Fragmented per provider; high per-source build cost | SOURCE_REGISTRY_AUDIT_PROPOSAL §"Phase 2" |
| `cib-sectoral-credit` (Credit Information Bureau Nepal) | Partial public release only | SOURCE_REGISTRY_AUDIT_PROPOSAL §"Phase 2" |
| `dols-cadastral` (Department of Land Survey) | Manual / cadastral data not bulk-released | SOURCE_REGISTRY_AUDIT_PROPOSAL §"Phase 2" |
| `hansen-gfc`, `esa-worldcover`, `icimod-glacier-inventory` (geospatial) | Phase 2 — needs raster/tile pipeline not in current stack | SOURCE_REGISTRY §"Tier 4 — Phase 2 candidates" |
| Real-time scraping cadence | GitHub Actions cron is the Year 1 scheduler; sub-hourly cadence not pursued | BACKEND_PLAN §"Scheduled jobs" |
| Migration to Cloudflare Pages (vs. Workers) | Decided in favour of Workers + OpenNext | [ADR-0002](decisions/0002-cloudflare-workers-opennext.md) |
| `regional-wholesale-prices` (Pokhara/Birgunj/Itahari) | Each market publishes differently; Kalimati is the priority for V7 v1 | SOURCE_REGISTRY_AUDIT_PROPOSAL §"Phase 2" |
| `ecn-results` (Election Commission Nepal) | Governance overlay, post-Day 365 | SOURCE_REGISTRY_AUDIT_PROPOSAL §"Phase 2" |
| Ward-level CBS NPHC cross-tabs (beyond DEGURBA) | CBS has not published these | [research/cbs-nphc-2021-audit.md §5](research/cbs-nphc-2021-audit.md) |
| Composite "Wealth Conversion Score" (0–100) | Killed by first-principles review; replaced by Monthly Verdict prose | [STRATEGY §"The Monthly Verdict"](STRATEGY.md) |

---

## 6. Open Questions

These are ambiguities the upstream docs do not resolve. The §6 in the upstream FINANCIAL_DATA_STRATEGY lists author-asked open questions; this section lists only questions a consolidator cannot answer from existing text.

- **OQ-1.** `nrb-cmefs-monthly` parser ship date. BACKEND_PLAN Day 11–28 lists CMEFs *registration* and *archival* but the row's verifiable output cites "23 NCPI subcategories × 3 geographies × 3 periods in `approved_indicator_values`" — that is the NCPI Table 2(B) deliverable, not CMEFs proper. Days 29–45 then assumes CMEFs values flow into Pulse cards. **Is the CMEFs PDF parser a Day 11–28 deliverable or a Day 29–45 deliverable?** STRATEGY and BACKEND_PLAN read inconsistently on this. *(Upstream loci: BACKEND_PLAN rows "11–28" and "29–45".)*

- **OQ-2.** Signature utility choice for Days 76–90. BACKEND_PLAN says "Household Ledger Calculator OR Loan→Project→Asset Tracker v0" — one, not both. STRATEGY §"3 Signature Public Utilities" lists both as Year 1 candidates plus a third ("Cost of Leaving Nepal Calculator"). **Which one ships first?** This determines which Tier-3 OCR phase (B4 White Books for Loan→Project; none for Household Ledger) gets prioritized. *(Upstream loci: BACKEND_PLAN row "76–90", STRATEGY §"Three Signature Public Utilities".)*

- **OQ-3.** FINANCIAL_DATA_STRATEGY status. The doc is explicitly marked "Draft for user review. Not yet codified into ADRs or Source Registry." Its Phase A/B sequencing and the proposed schema additions (`entities`, `local_government_fiscal_transfers`, `pe_annual_financials`, `foreign_aid_projects`) were **partially implemented** in migration 0001 (commit `06efa64`) but no ADR-0008 was filed. **Is FINANCIAL_DATA_STRATEGY locked, or still draft?** This file currently treats Phase A/B as the de facto plan. *(Upstream loci: FINANCIAL_DATA_STRATEGY header + §"Proposed schema additions".)*

- **OQ-4.** SOURCE_REGISTRY_AUDIT_PROPOSAL status. Same shape: "Draft for user review. Not yet codified into `SOURCE_REGISTRY.md`." It proposes a re-tier from 4 tiers → Tier 0 + 1–4 + Phase 2, ~40 new entries, an `ingestion_mode` enum, and a Reference-only category. This file uses the proposal's Tier-1/2/3 buckets as the closest-to-current view, but the canonical SOURCE_REGISTRY.md still shows the original 12-entry / 4-tier layout. **Which is the source of truth?** *(Upstream loci: SOURCE_REGISTRY_AUDIT_PROPOSAL header + §"Summary of changes".)*

- **OQ-5.** District MRI Year 1 districts. SOURCE_REGISTRY_AUDIT_PROPOSAL §"District MRI" lists Kathmandu, Chitwan, Kaski, Jhapa, Morang as STRATEGY's named five. STRATEGY itself mentions "5 districts Year 1" in the glossary but does not enumerate. **Are these five locked?** They drive which district-level slices need disaggregated data Year 1. *(Upstream loci: CLAUDE.md glossary entry "District MRI"; SOURCE_REGISTRY_AUDIT_PROPOSAL §"District MRI".)*

- **OQ-6.** Sahakari Tracker shape (vertical vs. utility). STRATEGY V5 frames it as a vertical with a "Check your cooperative" search. SOURCE_REGISTRY_AUDIT_PROPOSAL OQ-2 flags whether it's a 4th signature utility instead. **No upstream decision recorded.**

---

## 7. Changelog

| Date | Change | Source PR |
|---|---|---|
| 2026-05-14 | Initial consolidation (Worker R) | (this PR) |
