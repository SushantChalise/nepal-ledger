# Source: International Monetary Fund — Article IV Consultation Reports (Nepal)

**source_id:** `imf-article-iv`
**Status:** Active
**Tier:** 1
**Registered at:** 2026-06-07
**Last verified:** 2026-06-11

## What this is

IMF Article IV consultation reports on Nepal, published annually after the IMF's
bilateral surveillance visit. The Statistical Appendix contains a "Selected
Economic Indicators" table covering 5–7 years of Nepal's macro data — both
historical outturns and IMF projections for 1–3 forward years. This is the
primary international benchmark for cross-checking Nepal Ledger's DNE/CMEFs
actuals and framing the Monthly Verdict's "vs IMF view" comparison.

## Publication

- URL: <https://www.imf.org/en/Countries/NPL>
- Frequency: annual (typically Q1–Q2 of the AD calendar year following the
  consultation)
- Expected window: March–July each year
- Format: pdf

## What we extract

From the "Selected Economic Indicators" appendix table:

| Slug | Description | Unit |
|------|-------------|------|
| `imf-gdp-real-growth-actual` | Real GDP growth — outturn | `percent` |
| `imf-gdp-real-growth-forecast` | Real GDP growth — IMF projection | `percent` |
| `imf-cpi-inflation-avg-actual` | CPI inflation, annual average — outturn | `percent` |
| `imf-cpi-inflation-avg-forecast` | CPI inflation, annual average — projection | `percent` |
| `imf-fiscal-balance-pct-gdp-actual` | Overall fiscal balance (% of GDP) — outturn | `percent_gdp` |
| `imf-fiscal-balance-pct-gdp-forecast` | Overall fiscal balance (% of GDP) — projection | `percent_gdp` |
| `imf-current-account-pct-gdp-actual` | Current account balance (% of GDP) — outturn | `percent_gdp` |
| `imf-current-account-pct-gdp-forecast` | Current account balance (% of GDP) — projection | `percent_gdp` |
| `imf-public-debt-pct-gdp-actual` | Public sector debt (% of GDP) — outturn | `percent_gdp` |
| `imf-public-debt-pct-gdp-forecast` | Public sector debt (% of GDP) — projection | `percent_gdp` |
| `imf-gross-reserves-months-actual` | Gross official reserves (months of imports) — outturn | `months` |
| `imf-gross-reserves-months-forecast` | Gross official reserves (months of imports) — projection | `months` |

Column-marker classification: `E`/`Est` → estimate → forecast; `P`/`Proj` →
projection → forecast; no marker → historical outturn → actual.

## Provenance

- Confidence default: A
- License: proprietary (IMF owns the report; data reproduced for editorial
  cross-check only, not bulk redistribution)
- Reporting period type: annual (Nepal FY, mid-July → mid-July)

## Known breakage modes

- Table layout shifts between Article IV editions (column heading format,
  row label wording). Parser emits `PageLayoutChanged` errors and continues
  with partial extraction.
- Some editions prefix FY year columns with "FY" (e.g., `FY2023/24P`); handled.
- Bracketed negatives `(6.2)` used for fiscal/current account values;
  converted to `-6.2` automatically.
- Table occasionally spans two pages with a mid-table section header row
  (e.g., "Balance of payments") — these header-only rows are silently skipped.

## Revision policy

Each Article IV edition supersedes prior-year projections with either
confirmed outturns (those years become `-actual` rows) or revised projections
(stay as `-forecast`). The data continuity protocol records both the old
projection and the new outturn as separate `source_documents` rows.

## Parser

- Path: `scrapers/imf_article_iv/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: synthesized table fixture (integration tests require real PDF)

## Archive policy

- All downloaded PDFs stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `imf-article-iv/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
