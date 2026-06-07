# Source: Nepal Rastra Bank — Database on Nepalese Economy (Real Sector)

**source_id:** `nrb-db-real-sector` (catalog row) — ingested under the umbrella
`nrb-dne-xlsx` (the `scrapers/nrb_dne` parser's `SOURCE_ID`, already `active`).
**Status:** catalog row Paused; umbrella `nrb-dne-xlsx` is **active** — no status
flip is needed for a live ingest. Tag the ingest with `--source-id nrb-dne-xlsx`.
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-06-07 (parser `scrapers/nrb_dne` v0.6.0 — GDP/CPI single series + Provincial GDP dimensional)

> **Parser update (v0.6.0):** the real-sector files are parsed by the shared DNE
> parser `scrapers/nrb_dne/parser.py` (NOT the placeholder `scrapers/nrb-db-real-
> sector/parser.py`, which was never built). It handles National-Accounts + CPI via
> the **annual column-series** layout (single series → `approved_indicator_values`
> via `ingest:dne`) and Provincial GDP via a **province-dimensional** path
> (`dne_facts` via `ingest:dne-dimensional`). See `scrapers/nrb_dne/README.md`
> §"v0.6.0 changes" and the extracted-indicator tables below.

## What this is

NRB's Database on Nepalese Economy — Real Sector provides ~22 XLSX datasets covering GDP
(quarterly and national accounts), CPI, agriculture production/inputs, manufacturing production
index, energy, industry, tourism, transportation, and WPI. Quarterly GDP datasets are foundational
for the "Where Money Becomes Wealth" pillar and every per-capita comparison in the Household
Ledger Calculator. Confidence is B because NRB compiles from CBS and MoALD.

**Critical note:** "Quarterly GDP (Old)" and "Quarterly GDP (New)" reflect an incompatible
base-year revision. Parsers must handle these as two separate series and must not concatenate
them without adjustment. Provincial GDP is a separate file.

## Publication

- URL: https://www.nrb.org.np/database-on-nepalese-economy/real-sector/
- Frequency: quarterly (GDP); monthly (CPI, energy); yearly (agriculture, national accounts)
- Expected window: files updated in-place; no fixed release date announced
- Format: xlsx

## What we extract (v0.6.0 — promoted)

Promoted ONLY an **explicit allowlist** of clean headline columns (no catalogue
pollution, ADR-0014). All annual, confidence B, agency Nepal Rastra Bank. Units
**ADR-0011-verified** (magnitude checks below).

### Single series (ADR-0014 → `approved_indicator_values`, via `ingest:dne`)

From `National-Accounts.xlsx`:

| slug | source column | unit | category |
|------|---------------|------|----------|
| `dne-gdp-nominal` | "Nominal GDP (Rs. in billion)" (GDP Series_Nominal) | `npr_billion` | real_sector |
| `dne-gdp-real` | "Real GDP (at purchasers' price) (Rs. in billion)" (GDP Series_Real) | `npr_billion` | real_sector |
| `dne-gdp-real-growth` | "Real GDP Growth Rate (at purchasers' price)" (GDP Series_Real) | `percent` | real_sector |
| `dne-gdp-per-capita-usd` | "Per Capita GDP (in USD)" (GDP Series_Real) | `usd` | real_sector |
| `dne-gdp-deflator` | "GDP Deflator" (GDP Series_Real) | `index_points` | real_sector |

From `Consumer-Price-Index.xlsx` (CPI_National, base 2014/15 = 100):

| slug | source column | unit | category |
|------|---------------|------|----------|
| `dne-cpi` | "Index" → "Overall" | `index_points` | price |
| `dne-inflation-rate` | "Percentage Change" → "Overall" | `percent` | price |

### Dimensional facts (ADR-0015 → `dne_facts`, via `ingest:dne-dimensional`)

From `Provincial-GDP-2024-25.xlsx` ("Tables", Table 1 nominal / current prices):

| base_indicator_slug | dimension_kind | dimension_value | unit | confidence |
|---------------------|----------------|-----------------|------|:----------:|
| `dne-provincial-gdp` | `province` | kebab province name (`koshi`, `madhes`, `bagamati`, `gandaki`, `lumbini`, `karnali`, `sudur-pashchim`) | `npr_million` | B |

`reporting_period_type = annual`; the headline "Gross Domestic Product (GDP)" total
row per province (NOT the "at basic prices" sub-row). 49 facts (7 provinces × 7 FY,
FY 2075/76 → 2081/82). "Total GVA" is excluded (not a province).

### ADR-0011 magnitude verification (ran on the real files, 2026-06-07)

- **Nominal GDP** FY2080/81 (AD 2023/24) = **5,709.097** "Rs. in billion" →
  **NPR 5.71 trillion** ✓ (matches NRB's published ~NPR 5.7 trillion). Unit
  `npr_billion`; `npr_million` would be off by 10³.
- **Per-capita GDP** FY2081/82 = **USD 1,496** ✓.
- **CPI** FY2080/81 = **166.22 index_points** (base 2014/15 = 100) ✓.
- **Inflation rate** FY2080/81 = **5.44%** ✓.
- **Provincial GDP** AD 2024/25: Σ(7 provinces) ≈ NPR 5.4 trillion, same order of
  magnitude as national nominal GDP (NPR 6.1 trillion; ~12% gap = taxes-less-
  subsidies + statistical discrepancy at the national level). Bagamati (largest) =
  NPR 2.23 trillion; Sudur Pashchim (smallest) = NPR 0.38 trillion ✓.

### Deferred (next round)

- National-Accounts **GVA-by-industry** (a second dimension — `industry`; same
  dimensional model as Provincial GDP).
- Provincial-GDP **real** table (Table 2, constant prices).
- `Quarterly-GDP.xlsx` (old + new base-year series — ADR-0011 discontinuity).
- `Energy.xlsx`, `Agriculture-production.xlsx` (many per-row `UnitAmbiguous`).
- `Direction-of-foreign-trade.xlsx` (by-partner trade matrix — dimensional).
- Manufacturing/WPI/transportation datasets (not yet downloaded).

## Provenance

- Confidence default: B (NRB compiles from CBS/MoALD; preliminary)
- License: gov-open
- Reporting period type: quarterly (mixed — some datasets monthly, some yearly)

## Known breakage modes

- `upload-url-embeds-date-not-hardcodeable` — All XLSX download URLs embed the upload date.
  Parser must scrape the sector page for current links.
- `quarterly-gdp-old-and-new-series-incompatible-base-year-revision` — Two GDP XLSX files with
  incompatible base years. Parser must tag each row with the series name and refuse to merge
  them without explicit reconciliation logic.
- `provincial-gdp-separate-file` — Provincial GDP is a distinct XLSX, not a sheet in the
  national accounts file. Parser must enumerate it separately.

## Revision policy

NRB compiles from CBS/MoALD; preliminary GDP figures revised as CBS finalizes national accounts.
Historical values may be restated at base-year revisions. Archive each downloaded file by date.

## Parser

- Path: `scrapers/nrb_dne/parser.py` (the shared DNE parser — the placeholder
  `scrapers/nrb-db-real-sector/parser.py` named in the seed was never built; the
  seed `parserOwner` is stale and should be updated to `scrapers/nrb_dne/parser.py`).
- Version: 0.6.0
- Owner: Mother Opus
- Tested against: synthetic fixtures in `scrapers/nrb_dne/tests/conftest.py`
  (`National-Accounts.xlsx`, `Consumer-Price-Index.xlsx`, `Provincial-GDP-2024-25.xlsx`);
  dry-run-verified against the real files in `Financial Data/nrb_dne/`.
- Ingest: `pnpm ingest:dne --source-id nrb-dne-xlsx --input "Financial Data/nrb_dne/National-Accounts.xlsx"`
  (single series) and `pnpm ingest:dne-dimensional --source-id nrb-dne-xlsx --input "Financial Data/nrb_dne/Provincial-GDP-2024-25.xlsx"` (province facts).

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-db-real-sector/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
