# Source: World Bank — World Development Indicators (Nepal)

**source_id:** `wb-wdi`
**Status:** Active
**Tier:** 2
**Registered at:** 2026-06-07
**Last verified:** 2026-06-11

## What this is

The World Bank's World Development Indicators (WDI) dataset, filtered to Nepal.
Provides long time-series (1960–present) on GDP, GNI, inflation, poverty, Gini,
trade, and capital flows via the WB DataBank REST API (JSON).

Ingested as an **international benchmark layer**: WDI values cross-check our
domestic series (NRB DNE for GDP/inflation/remittances) and fill gaps where NRB
data is not yet ingested (poverty headcount, Gini, central-government-debt-to-GDP).

WB WDI aggregates from national statistical offices (CBS, NRB) and applies its
own quality controls, hence Confidence A.

## Publication

- API base: `https://api.worldbank.org/v2/country/NPL/indicator/<code>?format=json&per_page=100`
- Frequency: annual (WB updates database mid-year, typically June–July)
- Expected window: lag of 1–2 fiscal years for most series; poverty/Gini up to 5 years
- Format: JSON (REST API; no OCR required)

## What we extract

15 indicator codes across 5 domains:

### Real sector
- `wdi-gdp-current-usd` — GDP (current US$), stored in `usd_million` (÷1e6)
- `wdi-gdp-constant-2015-usd` — GDP (constant 2015 US$), `usd_million`
- `wdi-gdp-growth-annual-pct` — GDP growth (annual %) → **cross-checks `dne-gdp-real-growth`**
- `wdi-gdp-per-capita-current-usd` — GDP per capita (current US$) → **cross-checks `dne-gdp-per-capita-usd`**
- `wdi-gdp-per-capita-growth-pct` — GDP per capita growth (annual %)
- `wdi-gni-current-usd` — GNI (current US$), `usd_million`
- `wdi-gni-per-capita-current-usd` — GNI per capita (current US$)
- `wdi-gross-capital-formation-pct-gdp` — Gross capital formation (% of GDP)

### Prices
- `wdi-cpi-inflation-annual-pct` — CPI inflation (annual %) → **cross-checks `dne-inflation-rate`**

### External sector
- `wdi-remittances-received-usd` — Personal remittances received (current US$), `usd_million`
- `wdi-remittances-pct-gdp` — Personal remittances received (% of GDP)
- `wdi-current-account-balance-pct-gdp` — Current account balance (% of GDP)

### Fiscal
- `wdi-central-govt-debt-pct-gdp` — Central government debt, total (% of GDP)

### Demographic / welfare
- `wdi-poverty-headcount-national-pct` — Poverty headcount ratio at national poverty lines (%)
- `wdi-gini-index` — Gini index (stored as `index_points`, scale 0–100)

## Period convention

WB assigns Nepal data on a **fiscal-year** basis starting July 1.  WB `date`
field `"Y"` corresponds to the FY beginning Shrawan of BS year `Y + 57`:

| WB date | Nepal FY | BS FY | AD span (approx) |
|---------|----------|-------|-----------------|
| "2024"  | 2024/25  | 2081/82 | Jul 2024 – Jul 2025 |
| "2023"  | 2023/24  | 2080/81 | Jul 2023 – Jul 2024 |
| "2022"  | 2022/23  | 2079/80 | Jul 2022 – Jul 2023 |

Parser uses `datetime(Y, 7, 15)` and `datetime(Y+1, 7, 15)` as
`reporting_period_ad_start/end` (mid-month placeholder; TS validator tolerates ±2 days).

## Provenance

- Confidence default: A
- License: CC BY 4.0
- Reporting period type: annual

## Known breakage modes

- `api-may-return-null-for-recent-years` — WB may not yet have the latest FY; null observations are skipped silently
- `poverty-gini-only-measured-every-3-5-years` — SI.POV.NAHC and SI.POV.GINI have long null runs
- `date-field-is-fy-start-year-for-nepal` — WB date "2024" = FY starting July 2024; not a calendar year

## Revision policy

WB revises historical data without explicit versioning when national offices
submit corrections.  Each scheduled ingest downloads a full snapshot; updated
values supersede prior approved rows via the `revision_number` flow in the
validation layer.

## Cross-source divergence check

After each ingest, `src/lib/validation/benchmark.ts::checkWdiDneDivergence` runs
three direct comparisons:

| WDI slug | DNE slug | Tolerance |
|----------|----------|-----------|
| `wdi-gdp-growth-annual-pct` | `dne-gdp-real-growth` | ±3 pp absolute |
| `wdi-cpi-inflation-annual-pct` | `dne-inflation-rate` | ±3 pp absolute |
| `wdi-gdp-per-capita-current-usd` | `dne-gdp-per-capita-usd` | ±20% relative |

Findings are written as `ValueOutOfPlausibleRange` / `warning` severity flags
(never blocking).  The generous tolerances reflect genuine methodological
differences (calendar-year vs fiscal-year alignment, different base data).

## Parser

- Path: `scrapers/wb_wdi/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: `scrapers/wb_wdi/tests/fixtures/wdi_npl_2024.json`

## Ingest CLI

```powershell
# Dry-run against saved fixture (no DB):
pnpm ingest:wdi --dry-run

# Live ingest from pre-downloaded combined JSON:
pnpm ingest:wdi --input "path/to/wdi_npl_2025-06-01.json"

# Download fresh from WB API, then ingest:
pnpm ingest:wdi --download

# Download and save to a specific directory:
pnpm ingest:wdi --download --output-dir "C:\WDI"
```

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  under key `wb-wdi/<yyyy-mm-dd>/<filename>`.
- Hash + URL recorded in `source_documents`. Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
