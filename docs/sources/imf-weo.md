# Source: IMF — World Economic Outlook (Nepal)

**source_id:** `imf-weo`
**Status:** Active
**Tier:** 2
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11

## What this is

The IMF's World Economic Outlook (WEO) database, filtered to Nepal, via the
public **DataMapper** REST API. WEO is the IMF's flagship macro dataset: GDP,
inflation, fiscal balances, debt, savings/investment, and external balances —
each published as a **historical series plus a 5-year forward projection**.

Ingested as an **international benchmark + forecast layer**. Two distinct values:

1. **Cross-checks** our domestic series (NRB DNE, WB WDI) with the IMF's own
   independent estimates — divergence is a signal worth surfacing.
2. **Projections** — the only source in the ledger that carries forward-looking
   numbers. This powers the "Borrowed Time" pillar (projected debt trajectory)
   and the Monthly Verdict's forward view. Projections are stored with
   `observation_type='projection'` (ADR-0025), never conflated with actuals.

WEO is authoritative IMF research data → Confidence A (projections included —
high-authority forecast, distinguished by `observation_type`, not by a lower
confidence grade).

## Publication

- API base: `https://www.imf.org/external/datamapper/api/v1/<code>/NPL`
- No authentication, no API key, no pagination — one GET per indicator code.
- Frequency: **twice yearly** — April and October WEO vintages.
- Each vintage extends history and the projection path (April 2026 → 2031).
- Format: JSON (REST; no OCR required).

## What we extract

13 indicator codes across 4 domains:

### Real sector
- `weo-gdp-current-usd` — GDP, current prices (US$), `usd_million` (×1000 from WEO billions)
- `weo-gdp-real-growth-pct` — Real GDP growth (annual %) → **cross-checks `dne-gdp-real-growth`, `wdi-gdp-growth-annual-pct`**
- `weo-gdp-per-capita-current-usd` — GDP per capita (current US$), `usd`
- `weo-gdp-ppp-intl-dollar` — GDP, PPP valuation, `intl_dollar_million` (×1000)
- `weo-gross-national-savings-pct-gdp` — Gross national savings (% of GDP)
- `weo-total-investment-pct-gdp` — Total investment (% of GDP)

### Prices
- `weo-inflation-avg-pct` — Inflation, average CPI (annual %) → **cross-checks `wdi-cpi-inflation-annual-pct`, NRB NCPI**

### Fiscal
- `weo-govt-revenue-pct-gdp` — General government revenue (% of GDP)
- `weo-fiscal-balance-pct-gdp` — Govt net lending/borrowing (% of GDP)
- `weo-govt-gross-debt-pct-gdp` — General government gross debt (% of GDP) — **Borrowed Time core**

### External / labour / demographic
- `weo-current-account-pct-gdp` — Current account balance (% of GDP)
- `weo-unemployment-rate-pct` — Unemployment rate (% of labour force)
- `weo-population` — Population, `persons_million`

## Period convention

Identical to `wb-wdi`: the IMF dates Nepal series on the **fiscal year** starting
mid-July. WEO `date` `"Y"` corresponds to the FY beginning Shrawan of BS year
`Y + 57`:

| WEO date | Nepal FY | BS FY | AD span (approx) |
|----------|----------|-------|-----------------|
| "2026"   | 2026/27  | 2083/84 | Jul 2026 – Jul 2027 |
| "2025"   | 2025/26  | 2082/83 | Jul 2025 – Jul 2026 |
| "2023"   | 2023/24  | 2080/81 | Jul 2023 – Jul 2024 |

Parser uses `datetime(Y, 7, 15)` / `datetime(Y+1, 7, 15)` as
`reporting_period_ad_start/end` (mid-month placeholder; TS validator tolerates ±2 days).

## Projections (ADR-0025)

WEO mixes actuals and forecasts in one series, but the DataMapper API does **not**
flag which years are projections. The boundary is vintage-specific (the published
"estimates start after" year + 1). The ingest CLI takes it explicitly:

```
pnpm ingest:imf-weo --download --projection-from-year 2025
```

Every datapoint with year ≥ `projection_from_year` is emitted with
`observation_type='projection'`; earlier years are `'actual'`. **Omitting the
flag stores every row as `'actual'`** — the parser never fabricates the boundary.
Operators must read the boundary off the WEO release (e.g. the April 2026 WEO
marks Nepal estimates starting 2025).

## Provenance

- Confidence default: A
- License: CC BY 4.0 (IMF open data terms)
- Reporting period type: annual

## Known breakage modes

- `datamapper-api-does-not-flag-projection-vs-actual` — boundary supplied at ingest time, not derivable from the response
- `projection-boundary-must-be-supplied-per-vintage` — re-confirm `--projection-from-year` each April/October vintage
- `date-field-is-fy-start-year-for-nepal` — WEO date "2026" = FY starting July 2026, not a calendar year
- `imf-may-omit-recent-years-for-sparse-series-eg-LUR` — unemployment (LUR) is thin for Nepal; null/missing years skipped

## Revision policy

Each WEO vintage revises both history and the forecast path. A scheduled ingest
downloads the full snapshot; updated values supersede prior approved rows via the
`revision_number` flow. Successive vintages of the *same* projected year append
revisions (e.g. the Oct-2026 estimate of FY2027 supersedes the Apr-2026 one).

## Cross-source divergence check

Not yet wired (fast-follow). WEO **actuals** are directly comparable to:

| WEO slug | Counterpart | Note |
|----------|-------------|------|
| `weo-gdp-real-growth-pct` | `dne-gdp-real-growth`, `wdi-gdp-growth-annual-pct` | percent, no conversion |
| `weo-inflation-avg-pct` | `wdi-cpi-inflation-annual-pct` | percent |
| `weo-gdp-per-capita-current-usd` | `wdi-gdp-per-capita-current-usd`, `dne-gdp-per-capita-usd` | USD |

When wired, the check compares **only `observation_type='actual'`** WEO rows
(forecasts are never benchmarked against realised data) and writes
`ValueOutOfPlausibleRange` / warning flags on divergence, mirroring the WDI check.

## Parser

- Path: `scrapers/imf_weo/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: `scrapers/imf_weo/tests/fixtures/weo_npl_2026-04.json`

## Ingest CLI

```powershell
# Dry-run against the saved fixture (no DB, no network):
pnpm ingest:imf-weo --dry-run

# Download fresh from the IMF DataMapper API, marking 2025+ as projections, then ingest:
pnpm ingest:imf-weo --download --projection-from-year 2025

# Download/save without ingesting (inspect first):
pnpm ingest:imf-weo --download --projection-from-year 2025 --output-dir "C:\WEO"

# Live ingest from a pre-downloaded combined JSON:
pnpm ingest:imf-weo --input "path/to/weo_npl_2026-06-11.json"
```

## Archive policy

- Downloaded files stored under archive key `imf-weo/<yyyy-mm-dd>/<filename>`.
- Hash + URL recorded in `source_documents`. Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
