# Source: World Bank — World Development Indicators (Nepal)

**source_id:** `wb-wdi`
**Status:** Active
**Tier:** 1
**Registered at:** 2026-06-07
**Last verified:** 2026-06-11

## What this is

The World Bank's World Development Indicators (WDI) dataset, filtered to Nepal.
Provides long time-series of confirmed historical macro data — GDP growth, inflation,
fiscal balance, current account, public debt, and reserves. Available via the
WDI API (JSON, CC-BY 4.0) with data back to the 1960s.

Used in Nepal Ledger as a **historical baseline** for the six indicators that
IMF Article IV and ADB ADO also cover, enabling retrospective projection-accuracy
scoring: how close were IMF/ADB forecasts to what WDI reports as the eventual outturn?

## Publication

- URL: <https://databank.worldbank.org/source/world-development-indicators>
- API: `https://api.worldbank.org/v2/country/NPL/indicator/{CODE}?format=json`
- Frequency: annual (WDI mid-year refresh; recent years may carry preliminary values)
- Format: json (API response)

## What we extract

From the WDI API for Nepal (NPL), six indicator codes:

| WDI Code | Slug | Unit |
|---|---|---|
| `NY.GDP.MKTP.KD.ZG` | `wdi-gdp-real-growth` | `percent` |
| `FP.CPI.TOTL.ZG` | `wdi-cpi-inflation-avg` | `percent` |
| `GC.BAL.CASH.GD.ZS` | `wdi-fiscal-balance-pct-gdp` | `percent_gdp` |
| `BN.CAB.XOKA.GD.ZS` | `wdi-current-account-pct-gdp` | `percent_gdp` |
| `GC.DOD.TOTL.GD.ZS` | `wdi-public-debt-pct-gdp` | `percent_gdp` |
| `FI.RES.TOTL.MO` | `wdi-gross-reserves-months` | `months` |

WDI reports in calendar years. Each value is mapped to the approximate Nepal
fiscal year using `bs_start = cal_year + 57` (e.g., CY 2023 → FY 2080/81).
No forecast rows — WDI is confirmed historical outturns only.

## Provenance

- Confidence default: A
- License: CC-BY 4.0
- Reporting period: calendar year (mapped to approximate Nepal FY)
- Note: WDI fiscal-balance code (`GC.BAL.CASH.GD.ZS`) is central-government
  net lending/borrowing — may diverge from Nepal's consolidated government
  fiscal balance reported by FCGO. Use for trend comparison, not reconciliation.

## Known breakage modes

- API response shape may change between WDI major versions.
- Recent years (current and prior year) may carry `null` values pending
  national office submission; these are silently skipped by the parser.
- WDI fiscal-balance coverage for Nepal has gaps in some years.

## Two-step ingest process

```powershell
# Step 1 — fetch JSON snapshot (requires internet; ~5 seconds)
python -m scrapers.wb_wdi.fetch --output wb_wdi_snapshot_YYYYMMDD.json

# Step 2 — ingest snapshot (offline, idempotent)
pnpm ingest:wdi --dry-run --input wb_wdi_snapshot_YYYYMMDD.json
pnpm ingest:wdi --input wb_wdi_snapshot_YYYYMMDD.json
```

## Revision policy

WDI revises historical data when national offices submit corrections; revisions
appear in the API without an explicit version number. Re-fetch and re-ingest
annually. Each new ingest creates a new `source_documents` row; prior rows are
retained for provenance (data-continuity protocol).

## Parser

- Fetcher: `scrapers/wb_wdi/fetch.py` (downloads snapshot)
- Parser: `scrapers/wb_wdi/parser.py` v0.1.0 (reads snapshot, emits `ParserResult`)
- Owner: Mother Opus
- Tested against: synthesized snapshot fixture; integration tests require
  a real snapshot at `scrapers/wb_wdi/tests/fixtures/wb_wdi_sample.json`

## Archive policy

- JSON snapshots stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `wb-wdi/<yyyy-mm-dd>/<original-filename>`.
- Hash recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
