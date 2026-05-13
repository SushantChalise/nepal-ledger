# Source: Nepal Rastra Bank — NCPI Table 2(B)

**source_id:** `nrb-ncpi-table`
**Status:** Active
**Last verified:** 2026-05-14

## What this is

NCPI Table 2(B) is the digital companion to NRB's CMEFs PDF — a CSV/XLSX
breakdown of the National Consumer Price Index by sub-group (food and
beverage, non-food and services) and by ecological belt (Hill, Terai,
Mountain, Kathmandu Valley). This is the structured-data feed that powers
Nepal Ledger's inflation lens without forcing a PDF-table extraction round.
The in-repo CSV is `CMEFs_Table_Nine-Months_2082.83(2(B).csv`.

## Publication

- URL: https://www.nrb.org.np/category/current-macroeconomic-situation/
- Frequency: monthly (bundled with the CMEFs release)
- Expected window: bundled with CMEFs release (25th–30th of month following)
- Format: csv

## What we extract

- `ncpi-headline-yoy` — Headline NCPI YoY change (overall)
- `ncpi-food-yoy` — Food and beverage sub-group YoY change
- `ncpi-non-food-yoy` — Non-food and services sub-group YoY change
- `ncpi-hill-yoy` — NCPI YoY change for Hill ecological belt
- `ncpi-terai-yoy` — NCPI YoY change for Terai ecological belt
- `ncpi-mountain-yoy` — NCPI YoY change for Mountain ecological belt
- `ncpi-kathmandu-valley-yoy` — NCPI YoY change for Kathmandu Valley

## Provenance

- Confidence default: A
- License: gov-open (Government of Nepal publication; CC BY-NC-SA applies
  to derivative editorial)
- Reporting period type: nine_months_cumulative — the existing in-repo table
  is for nine months of FY 2082/83. Subsequent releases will be cumulative
  through their reporting horizon; the parser must read the period header
  and emit the correct `period_type` value per CALENDAR_AND_PERIODS.md.

## Known breakage modes

- `header-row-position-shifts` — The header row position has historically
  shifted (sometimes row 3, sometimes row 5, sometimes preceded by a banner
  row). Parser must detect headers by content match, not absolute row index.

## Revision policy

Aligned with CMEFs cycle: provisional values revised in the next release
and considered stable after two cycles. Same revision-handling pattern as
`nrb-cmefs-monthly`.

## Parser

- Path: `scrapers/nrb_ncpi/parser.py`
- Version: 0.0.0 (parser shell exists; will bump to 0.1.0 on first staging
  write per ADR-0003)
- Owner: Mother Opus
- Tested against: `scrapers/nrb_ncpi/fixtures/` (existing in-repo fixtures)

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-ncpi-table/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
