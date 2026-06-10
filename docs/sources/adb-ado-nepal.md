# Source: Asian Development Bank — Asian Development Outlook (Nepal)

**source_id:** `adb-ado-nepal`
**Status:** Active
**Tier:** 1
**Registered at:** 2026-06-07
**Last verified:** 2026-06-11

## What this is

ADB's flagship annual regional economic outlook (ADO) — Nepal chapter. Provides
GDP growth projections, CPI inflation, current-account, and fiscal-balance
forecasts alongside historical outturns. Published each April (main ADO) with
a Supplement in September. The Nepal chapter contains a "Selected Economic
Indicators" summary table with 3–5 years of data + 2 forward projections.

Used in Nepal Ledger as a second international benchmark alongside IMF Article IV,
enabling the Monthly Verdict "vs the ADB view" framing and cross-checking
DNE/CMEFs actuals.

## Publication

- URL: <https://www.adb.org/countries/nepal/economy>
- Frequency: annual (main edition: April; supplement: September)
- Expected window: April (main), September (supplement)
- Format: pdf

## What we extract

From the Nepal chapter "Selected Economic Indicators" table:

| Slug | Description | Unit |
|------|-------------|------|
| `adb-ado-gdp-real-growth-actual` | Real GDP growth — outturn | `percent` |
| `adb-ado-gdp-real-growth-forecast` | Real GDP growth — ADB forecast | `percent` |
| `adb-ado-cpi-inflation-avg-actual` | CPI inflation, annual average — outturn | `percent` |
| `adb-ado-cpi-inflation-avg-forecast` | CPI inflation, annual average — forecast | `percent` |
| `adb-ado-fiscal-balance-pct-gdp-actual` | Fiscal balance (% of GDP) — outturn | `percent_gdp` |
| `adb-ado-fiscal-balance-pct-gdp-forecast` | Fiscal balance (% of GDP) — forecast | `percent_gdp` |
| `adb-ado-current-account-pct-gdp-actual` | Current account balance (% of GDP) — outturn | `percent_gdp` |
| `adb-ado-current-account-pct-gdp-forecast` | Current account balance (% of GDP) — forecast | `percent_gdp` |
| `adb-ado-gross-reserves-months-actual` | Gross reserves (months of imports) — outturn | `months` |
| `adb-ado-gross-reserves-months-forecast` | Gross reserves (months of imports) — forecast | `months` |

Column-marker classification: `e`/`est` → estimate → forecast; `f`/`fct` →
forecast; no marker → historical outturn → actual.

## Provenance

- Confidence default: A
- License: CC BY 4.0 (ADB open data policy)
- Reporting period type: annual (Nepal FY or calendar year depending on edition)

## Known breakage modes

- ADB alternates between Nepal fiscal year (`2022/23`) and calendar year
  (`2023`) notation across editions; both handled by the column-year parser.
- Nepal chapter page number drifts; parser scans all pages for the Nepal anchor.
- Bare "Inflation" row (no qualifier) classified as CPI annual average.
- September Supplement tables may have fewer historical columns than the main
  April edition; partial extraction is expected and emits `ColumnMissing` errors.

## Revision policy

Each ADO edition introduces new projections and confirms/revises prior estimates
as outturns. Prior projections become `-forecast` rows tagged with the report
year; confirmed outturns become `-actual` rows on next ingest.

## Parser

- Path: `scrapers/adb_ado/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: synthesized FY + calendar-year table fixtures; integration
  tests require real PDF at `scrapers/adb_ado/tests/fixtures/adb_ado_nepal_sample.pdf`

## Archive policy

- All downloaded PDFs stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `adb-ado-nepal/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
