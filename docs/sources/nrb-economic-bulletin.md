# Source: Nepal Rastra Bank — Economic Bulletin & Indicators (Quarterly)

**source_id:** `nrb-economic-bulletin`
**Status:** Paused
**Tier:** Tier 3
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's quarterly Economic Bulletin is the richest single-PDF compilation of macroeconomic
time-series tables in the NRB catalog: approximately 200 tables spanning all economic sectors
(real, fiscal, external, financial). It partially overlaps the monthly CMEFs bulletin but carries
deeper historical tables and is released quarterly. It is useful for filling monthly-statistics
gaps between CMEFs releases and for building long-run historical baselines. Approximately 35
issues published from Mid-April 2003 to Mid-January 2026 (latest confirmed).

## Publication

- URL: https://www.nrb.org.np/category/quarterly-economic-bulletin/
- Frequency: quarterly (January / April / July / October)
- Expected window: 2–4 months after the quarter reference period
- Format: pdf

## What we extract

- `eb-ncpi-yoy-quarterly` — NCPI year-on-year for the quarter
- `eb-govt-revenue-ytd` — Cumulative government revenue (NPR billion)
- `eb-govt-expenditure-ytd` — Cumulative government expenditure (NPR billion)
- `eb-trade-deficit-ytd` — Trade deficit cumulative (NPR billion)
- `eb-remittance-ytd` — Remittance inflows cumulative (NPR billion)
- `eb-credit-private-sector-yoy` — Private sector credit growth YoY (%)
- (additional indicator list to be finalized in parser PR)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: quarterly

## Known breakage modes

- `pdf-size-approx-8mb-dense-tables` — Each issue is approximately 8 MB with dense
  multi-column tables. pdfplumber page-splitting strategy required; do not attempt single-pass
  extraction on the full document.
- `url-slug-format-year-month-mid-month-name` — URL slugs follow the pattern
  `economic-bulletin-<year>-<month>-mid-<month-name>` (e.g., `economic-bulletin-2026-mid-jan`).
  The pattern is semi-regular but has varied across years; use the category index page as the
  reliable source for URLs rather than constructing slugs.

## Revision policy

Quarterly; each issue is a compilation snapshot of available data at that point in time.
No revision to prior issues; later issues may carry corrected figures for overlapping periods.

## Parser

- Path: `scrapers/nrb-economic-bulletin/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-economic-bulletin/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-economic-bulletin/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
