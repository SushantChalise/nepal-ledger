# Financial Data — Inventory, Extraction Strategy, Intelligence Plan

**Status:** Draft for user review. Not yet codified into ADRs or Source Registry.

The `Financial Data/` directory in the repo root holds two pre-staged corpuses you flagged. This document inventories what's there, proposes an extraction strategy that respects the Surya/Claude-CLI doctrine, and lays out what intelligence we can extract for which Nepal Ledger vertical.

---

## Inventory

### Dataset A — NRB Monthly Banking & Financial Statistics (`nrb_monthly_statistics/`)

- **50 XLSX files**, monthly cadence, **continuous from Shrawan 2078 (Aug 2021) to Bhadau 2082 (Sept 2025)** — **49 months**.
- **1 PDF** (`bfi_niyamabali.pdf`) — BFI regulatory framework. Reference asset.
- **Source URL pattern:** `nrb.org.np/contents/uploads/<yyyy>/<mm>/<filename>.xlsx` (captured in `metadata.json`).

**Structure per XLSX (sample: `Saun-2082-Publish.xlsx`):**
- **25 sheets** (`C1`–`C25`), each a distinct statistical table.
- Sheet C2 is the Table of Contents:
  - `C3` Explanatory Notes
  - `C4` Major Financial Indicators
  - `C5` Statement of Assets & Liabilities
  - `C6` Profit & Loss Account of Banks
  - `C7` Sector-wise, Product-wise, Industry-wise lending
  - `C8`–`C25` — bank-class breakdowns (commercial, development, finance, micro-finance, infrastructure), cooperative-by-class, NPL by sector, lending purposes, etc.
- Heavy use of Excel whitespace padding for human readability (rows 1–2 blank, headers around row 4).
- Each sheet contains FULL HISTORICAL columns plus the latest-month snapshot. E.g. `C5` columns: `Mid-July 2022 | Mid-July 2023 | Mid-July 2024 | Mid-July 2025 | Mid-Aug 2025`. New monthly file = same historical columns + one new month column.
- Values are floats stored with full precision; no truncation issues.
- **Implication:** the **latest file has the most data**. We don't need to parse all 50 to bootstrap — parse the latest, then earlier files **only for revision detection** (if NRB restated a 2022 number in a 2024 file, we want to flag it).

### Dataset B — MoF Documents (`mof_documents/`)

64 files across 6 subdirectories, plus a `documents_metadata.json` index, plus a `Cleaned/` working directory.

| Subdir | Files | Format | What it is |
|---|---|---|---|
| `redbook/` | 20 | PDF | **Budget Red Books**, FY 2062/63 → FY 2080/81 (some FYs duplicated; some in English, some Nepali). The federal annual budget line items + Knowledge Base for budget process. |
| `whitebook/` | 14 | PDF | **Foreign Aid Source Books**. Bilateral + multilateral project pipeline, FY 2062/63 → FY 2078/79. |
| `yellowbook/` | 6 | PDF | **Public Enterprises Annual Status Reviews** (DPM Office), FYs around 2079, 2080, 2081. Directly feeds Vertical 4 (Public Enterprise X-Ray). |
| `agreement/` | 6 | PDF | Foreign loan + grant agreements with progress reports. Feeds Vertical 2 (Borrowed Time). |
| `intergovernmental/` | 9 | PDF | FY-named (`207475.pdf` → `208283.pdf`). NNRFC fiscal transfer source documents (FY 2074/75 → FY 2082/83). Directly feeds Vertical 10 (Local Ledger) + District MRI. |
| `Cleaned/` | 8 | XLSX + .py | **Pre-cleaned FY 2082/83 fiscal transfer data** + municipality fuzzy-matching scripts + intermediate artifacts. |

### The `Cleaned/` find — pre-extracted gold

`Fiscal Transfer_2082_82.xlsx` is the FY 2082/83 inter-governmental fiscal transfer dataset **already cleaned to canonical form**:

- **990 rows = 753 local levels + 77 districts + summary rows** (the constitutional count of Nepal's local governments)
- **21 columns** including the 8-digit federal local-level code (`80101101` etc.), district + local-level name in **both Nepali and English** (the Nepali-side is OCR-cleaned), local-level type, and the 4 federal grant categories with their budget head codes:
  - **Equalization Grant** (Min / Formula-Based / Performance-Based) — code 26331
  - **Conditional Grant** (Current 26332 + Capital 26336)
  - **Special Grant** (Current 26333 + Capital 26337)
  - **Complementary Grant** (Capital 26334)
  - Plus Total Current / Total Capital / Grand Total

The Python scripts in `Cleaned/`:
- **`fuzzy_match_municipalities.py`** — uses `rapidfuzz` to match municipality names across two columns (likely federal-list vs. report-list). High/Medium/Low confidence tiers.
- **`manual_match_reasoning.py`** — contains a **manually-curated dictionary of Devanagari OCR substitutions** (e.g. `पाललका → पालिका`, `अथराई → आठराई`, `तुव → तुम्`). This is the exact pain point Surya OCR will produce; the dictionary is **directly reusable** as a post-processing layer.

> **Key insight:** someone has already paid the OCR-cleanup tax for one FY. We inherit that intelligence and apply it to the 8 historical FYs once we OCR them.

---

## Extraction strategy

### Phase A — Immediate value, NO OCR needed (Week 1–2 work)

#### A1. Reuse the Cleaned FY 2082/83 fiscal transfer XLSX as-is
- One-shot ingest script reading `Cleaned/Fiscal Transfer_2082_82.xlsx`.
- Writes to a NEW table `local_government_fiscal_transfers` (schema below) — this row shape doesn't fit `approved_indicator_values` because it's keyed on (local_level_code, fiscal_year, grant_type) not (indicator, period).
- Estimated 753 × ~10 columns = ~7500 (local_level, fiscal_year, grant_type, amount) rows for FY 2082/83 alone.
- **Verifiable output:** District MRI Pulse tile for Kathmandu can show "Kathmandu Metropolitan received Rs X in equalization grants FY 2082/83" as a real number, sourced.

#### A2. Parse all 50 NRB BFI XLSX files
- Python parser using `openpyxl` (already specified in scrapers/pyproject.toml).
- **Schema-discovery first:** before writing extraction code, sample the C4–C10 sheets across 3 files spanning 49 months (oldest, middle, latest) to confirm the column layout is stable. Layout DOES occasionally shift (the C2 TOC shows the same logical tables, but the column count varies — `C8` jumped from 36 to 57 cols somewhere in this span). The parser version-stamps each file's layout.
- **One parser run per file = one `parser_runs` row.** 50 parser runs after the bootstrap pass.
- **Latest-first ingest order:** parse `Bhadau_2082_Publish.xlsx` first; it has the maximum history. Parse earlier files only for revision detection — if a 2022 value in the 2024 snapshot doesn't match the value in the 2022 snapshot, write a revision row per `DATA_PIPELINE.md` §"Revisions".
- **Estimated total rows landed:** ~3,000 indicator-value rows just from C4 + C5 + C7 (the headline tables) × 49 months. Per-bank-class breakdowns (C8–C20) multiply this.
- **Verifiable output:** the entire Vertical 16 (Collateral State) and Vertical 3 (Private Capital X-Ray banking-concentration tile) Pulse data, real, retro to Aug 2021.

#### A3. Source-archive the entire `Financial Data/` corpus to Supabase Storage
- Each file gets a `source_documents` row (per Worker B's storage wrapper).
- Hash + content-address. Idempotent re-runs.
- Storage key: `<source-id>/<yyyy-mm-dd>/<filename>`.

### Phase B — Surya OCR territory (Week 3–6 work)

> **Surya findings landed during this drafting** (`docs/research/surya-ocr-findings.md`, on `docs/surya-research` branch). Three findings directly change Phase B design:
>
> 1. **`surya_table` defaults to pulling cell text from the PDF text layer, NOT OCR.** For scanned NRB/MoF PDFs this yields blank cells unless `--detect_boxes` is passed — **the exact failure mode of the prior chat**. Our parser invocation must pass `--detect_boxes` always for the MoF corpus.
> 2. **`TABLE_REC_MAX_BOXES=150` silent truncation** — Red Books, intergovernmental, and Yellow Books have tables far larger. Must bump this env var per parser run.
> 3. **Devanagari regression open at v0.17.1 (issue #475).** We pin v0.17.1 but must run an **empirical micro-benchmark** on a labelled NRB page before trusting Devanagari numeral output. The Cleaned/ `manual_match_reasoning.py` substitution dictionary becomes our **mandatory post-Surya pass**.
> 4. **Surya does zero preprocessing.** We add an OpenCV (already a Surya transitive dep) deskew + denoise + binarize step before Surya for Devanagari scans.
> 5. **DPI cap at 192** — segfault on 300/600 DPI (issue #389). Render PDFs to PIL at exactly 192 DPI.



Drive in this order, picking off the lowest-OCR-difficulty + highest-vertical-value first:

#### B1. The 8 historical intergovernmental PDFs (`intergovernmental/207475.pdf` → `208182.pdf`)
- Target: the same row shape as `Cleaned/Fiscal Transfer_2082_82.xlsx` for 8 prior FYs.
- Surya extracts tables; the `manual_match_reasoning.py` Devanagari substitution dictionary becomes our **mandatory post-processing pass**.
- Claude CLI spot-check: load 30 random local-levels × grant-type rows; reviewer eyeballs against the source PDF.
- **Verifiable output:** 9 fiscal years of per-local-level grants = the spine of Vertical 10 + District MRI.

#### B2. The 6 yellowbook PDFs (Public Enterprises)
- Yellow Books contain per-PE financial summaries (revenue, profit/loss, net worth, government investment, outstanding loans).
- Each Yellow Book is one annual snapshot; 6 files ≈ 6 FYs of per-PE financials.
- Vertical 4 ("Public Enterprise X-Ray") is unblocked.
- Story #4 — "The Company Behind Every Fuel Price Hike (NOC)" — uses this directly.

#### B3. The redbook PDFs (Federal Budget Line Items)
- 20 files, FY 2062/63 → FY 2080/81. Mostly Nepali, some English. **Several hundred pages each.** This is the heaviest single OCR target.
- Strategy: don't OCR all 20 at once. Start with the latest 3 FYs (we'd want budget-vs-actual for recent years). Pre-load the budget code dictionary (the 5-digit chart-of-accounts codes — 26331, 26332, etc.) so OCR has a controlled vocabulary to match against.
- Verifiable output: federal budget allocation series per sector, FY 2078/79 → FY 2080/81.

#### B4. The whitebook PDFs (Foreign Aid Source Books)
- 14 files, FY 2062/63 → FY 2078/79. Project-by-project foreign aid pipeline.
- Vertical 2 (Borrowed Time) deep coverage. Loan→Project signature utility uses this.
- Lower priority than B2 because the headline aggregates are already in NRB CMEFs.

#### B5. The agreement PDFs (parse-on-demand for stories)
- 6 files. Not a regular ingestion — these are specific-investigation source documents. Reference assets in the Fact Ledger sense.

### Phase C — Continuous ingestion (Month 2+)

Once Phase A+B land, monthly cadence:
- NRB publishes new monthly XLSX → parser runs automatically (GitHub Actions cron) → new month's row inserted.
- MoF publishes new annual Yellow / Red / White / Intergovernmental book → manual upload → Surya parse → Claude CLI review → promote.

---

## Intelligence extracted (what we can build on top of the raw data)

### From NRB BFI Monthly XLSX

| Intelligence product | Feeds | Computation |
|---|---|---|
| **Banking sector concentration (HHI)** | Vertical 3 (Private Capital X-Ray) Pulse tile | Σ(market_share²) over commercial banks, monthly, on deposits / loans / capital |
| **Sector credit allocation series** | Vertical 16 (Collateral State) — "Credit by sector" Pulse | C7 sheet × 49 months → time-series per sector |
| **Real-estate-vs-productive credit ratio** | Vertical 16 flagship story | Real estate + housing share of total loans, vs. SME + manufacturing + agri share |
| **NPL trend by sector** | Vertical 16 + Vertical 5 (Sahakari) | C-series sheets disclose NPL; trend over time |
| **Banking profitability (ROA / ROE / NIM aggregates)** | Story: "Are Nepal's banks healthy?" | C6 P&L + C5 balance sheet → aggregate ratios |
| **Microfinance + cooperative stress signal** | Vertical 5 (Sahakari) Pulse | Separate sheets cover microfinance + finance companies; capital adequacy + NPL trend |
| **Bank capital adequacy trend** | Vertical 16 + Vertical 5 | Capital fund / Risk-weighted-assets where disclosed |
| **Deposit composition trend** | Money In + Vertical 16 | Savings vs. fixed vs. current deposit share over time |

### From MoF Yellow Books (Public Enterprises)

| Intelligence product | Feeds | Computation |
|---|---|---|
| **Per-PE financial dossier (5–6 year time-series)** | Vertical 4 (Public Enterprise X-Ray) entity profiles | Revenue, profit/loss, net worth, government investment, subsidies, outstanding loans — one row per PE per FY |
| **PE solvency cluster: solvent vs. structurally loss-making** | Story: "Which public enterprises actually deserve to exist?" | Sum of cumulative losses ÷ government investment |
| **PE subsidy burden on federal budget** | Money Wasted Pulse | Total PE subsidies / federal budget total |

### From Intergovernmental + Cleaned

| Intelligence product | Feeds | Computation |
|---|---|---|
| **Per-local-level fiscal transfer time-series (753 × 9 FYs once OCR done)** | Local Ledger (Vertical 10) — entire vertical | One row per (local_level, FY, grant_type) — the canonical fiscal-federalism dataset |
| **Per-district aggregate transfer trend (77 × 9 FYs)** | District MRI Pulse tile | Roll up local levels by district |
| **Equalization / Conditional / Special / Complementary grant share over time** | Vertical 10 flagship story | Composition by grant type, system-wide |
| **Transfer-to-population ratio per local-level** | District MRI + Vertical 10 deep-dive | Requires joining with Census 2078 population data (separately ingested) |
| **Sahakari spotlight: which municipalities received the most fiscal-transfer money?** | Story: "Where federal money goes (and doesn't)" | Top/bottom 10 by per-capita transfer, with maps |

### From Red Books + White Books (when OCRed)

| Intelligence product | Feeds | Computation |
|---|---|---|
| **Federal budget allocation by sector × FY** | Vertical 10 (Budget Watch) + Vertical 14 (Tax State) | Long-form Red Book extraction |
| **Budget vs. actual execution gap** | Story: "Why Nepal Doesn't Build" | Join Red Book (budget) with FCGO (actual) |
| **Foreign-aid project pipeline by donor** | Vertical 2 (Borrowed Time) + Loan→Project signature utility | White Book per-project rows |
| **Donor concentration over time** | Borrowed Time + Money In | ADB vs WB vs JICA vs China EXIM share of total commitments |

---

## Schema impact

The current schema (`source_registry`, `source_documents`, `indicators`, `staging_indicator_values`, `approved_indicator_values`, `fact_ledger_claims`, `leads`) was designed for time-series indicators. The corpus reveals **three row shapes the current schema doesn't naturally fit**:

### 1. Entity-keyed facts (per-bank, per-PE, per-local-level)
The current `indicators` table is for *concepts* (NCPI inflation YoY, NEPSE index, etc.). It doesn't naturally hold per-entity facts like "NOC Net Profit FY 2080/81 = Rs X."

**Two options:**
- **A. Overload `indicators` with entity-scoped slugs.** Slug like `noc-net-profit` for NOC; `kasthamandap-municipality-equalization-grant`. Pro: zero schema change. Con: 753 municipalities × ~10 grant types = 7,530 indicator slugs just for fiscal transfers. The Knowledge Base "entity profile" page has to query by string prefix.
- **B. Add an `entities` table** (entity_id, kind, name_en, name_ne, parent_entity_id) and an optional FK `indicators.entity_id`. Banks, public enterprises, local levels, cooperatives, business groups all become entities. Pro: clean entity-profile queries; natural fit for Vertical 4 (PE X-Ray) and Vertical 10 (Local Ledger). Con: small schema migration.

**Recommendation: Option B** — modest schema addition, much cleaner downstream. ADR worthy.

### 2. Geographic-keyed facts (per-district, per-local-level)
The `local_government_fiscal_transfers` row shape is (local_level_code, fiscal_year, grant_type_code, amount, unit). This is fundamentally a different table from `approved_indicator_values` and doesn't even need calendar/period machinery beyond `fiscal_year_bs`.

**Recommendation:** add a `local_government_fiscal_transfers` table directly. Don't try to squeeze it into the indicator-values shape.

### 3. Document-derived structured rows that aren't really indicators
The white-book project pipeline is rows of (project_name, donor, sector, commitment_amount, disbursed_to_date, ...) — closer to a CRM-like fact pattern. Same for PE financials.

**Recommendation:** create domain tables per major shape — `public_enterprises`, `pe_annual_financials`, `foreign_aid_projects`, `loan_agreements`. These join naturally to the `entities` table from (1).

---

## Proposed schema additions (ADR-0008 candidate)

```sql
-- Phase 1: entities (the master entity dimension)
entities (
  id uuid PK,
  kind enum ('bank','public_enterprise','local_level','district','province',
             'cooperative','business_group','ministry','department','donor'),
  slug text UNIQUE,
  name_en text NOT NULL,
  name_ne text,
  parent_entity_id uuid REF entities(id),
  metadata jsonb,             -- type-specific extras: 8-digit code, license number, etc.
  created_at timestamptz,
  updated_at timestamptz
)

-- Phase 2: extend indicators
ALTER TABLE indicators ADD COLUMN entity_id uuid REF entities(id);
-- macro indicators (NCPI YoY etc.) leave entity_id NULL
-- entity-scoped indicators (NOC Net Profit) reference an entity row

-- Phase 3: Local Ledger fact table (the immediate Phase A1 ingest target)
local_government_fiscal_transfers (
  id uuid PK,
  local_level_id uuid REF entities(id),  -- entity.kind = 'local_level'
  fiscal_year_bs text NOT NULL,
  grant_type enum ('equalization_minimum','equalization_formula',
                   'equalization_performance','conditional_current',
                   'conditional_capital','special_current',
                   'special_capital','complementary_capital'),
  amount_npr numeric(20,2) NOT NULL,
  source_document_id uuid REF source_documents(id),
  confidence_grade enum ('A','B','C'),
  promoted_at timestamptz,
  UNIQUE (local_level_id, fiscal_year_bs, grant_type)
)

-- Phase 4: domain tables — added when their parser ships
public_enterprises_annual_financials  -- per Yellow Book
foreign_aid_projects                  -- per White Book
loan_agreements                       -- per agreement/
```

The `entities` table absorbs everything that's currently homeless: banks (with NRB BFI as data feed), public enterprises (Yellow Books), local levels (Cleaned + intergovernmental), business groups (Vertical 3), donors (White Books).

---

## Open questions for you

1. **Schema additions: ADR-0008?** I'd land an ADR proposing the `entities` table + 3 domain tables (`local_government_fiscal_transfers`, `pe_annual_financials`, `foreign_aid_projects`). Once accepted, generate a migration alongside the parser PRs. Acceptable, or prefer to keep schema migration in lockstep with each parser?
2. **Cleaned FY 2082/83 ingest priority.** A1 above can land **this week, no OCR needed**. Just an ingest script. Worth doing in the next worker batch?
3. **NRB BFI XLSX parser priority.** A2 is also no-OCR. 49 months of banking data on disk. Worth doing in the next worker batch?
4. **OCR phasing.** Phase B's order proposed: B1 intergovernmental (8 PDFs) → B2 Yellow Books (6 PDFs) → B3 Red Books (latest 3) → B4 White Books → B5 agreements on demand. Accept, or reorder?
5. **`Cleaned/`-style normalization dictionary.** The `manual_match_reasoning.py` Devanagari substitution map is gold. Should I extract it into `scrapers/_common/devanagari_normalization.py` as a reusable post-Surya step? Lean **yes**.
6. **Reuse vs. rewrite the fuzzy-matching pipeline.** The existing `rapidfuzz` scripts work; I'd port them into `scrapers/_common/municipality_resolver.py` rather than rewrite. Confirm OK?
7. **`Financial Data/` location.** Currently in repo root, gitignored implicitly via `source-data/` rule? Let me check — actually no, the current `.gitignore` covers `source-data/` and the legacy `NRB Current/`, `Stastical Information/`, `Framework/` folders, but **NOT `Financial Data/`**. Should add to `.gitignore`. Confirm.

---

## What I'd execute next (subject to your edits)

1. Add `Financial Data/` to `.gitignore` (it's not currently ignored — risk of committing).
2. Write **ADR-0008: entities table + domain fact tables**.
3. Write the migration adding `entities`, `local_government_fiscal_transfers`, `public_enterprises_annual_financials`, `foreign_aid_projects` (skeleton — fields will fill in as parsers ship).
4. Worker brief: `scripts/ingest-cleaned-fiscal-transfer.ts` (Phase A1 — uses the Cleaned XLSX directly).
5. Worker brief: `scrapers/nrb_bfi/parser.py` (Phase A2 — the 50-XLSX monthly parser).
6. Worker brief: `scrapers/_common/devanagari_normalization.py` + `municipality_resolver.py` (port the Cleaned/ scripts).
7. Wait on Surya findings → write `scrapers/nrb_intergovernmental/parser.py` brief (Phase B1).
8. Yellow Books parser brief (Phase B2) once Surya stack is proven.

Each step is one worker, scope-fenced, returns a PR.
