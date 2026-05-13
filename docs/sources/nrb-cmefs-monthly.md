# Source: Nepal Rastra Bank — Current Macroeconomic and Financial Situation

**source_id:** `nrb-cmefs-monthly`
**Status:** Active (parser pending)
**Last verified:** 2026-05-14

## What this is

NRB's flagship monthly bulletin synthesizing the macroeconomic and financial
situation of Nepal. Each release covers a cumulative period (e.g. nine months
of the fiscal year) and is the canonical English-language source for headline
indicators: NCPI, monetary aggregates, BoP, remittances, reserves, government
finance, banking sector indicators, and a NEPSE snapshot. The release sets the
tempo for Nepal Ledger's Pulse + Monthly Verdict cycle.

## Publication

- URL: https://www.nrb.org.np/category/current-macroeconomic-situation/
- Frequency: monthly
- Expected window: 25th–30th of the month following the reporting period
- Format: pdf

## What we extract

NRB CMEFs is the umbrella publication. Indicator slugs below are the targets
for the parser; they will be registered alongside the parser PR (Worker C
sequel). This profile is intentionally enumerative — promote slugs to
`indicators` only when the parser actually populates them.

- `ncpi-headline-yoy` — Year-on-year change in National Consumer Price Index (headline)
- `ncpi-food-yoy` — YoY change in NCPI food and beverage sub-group
- `ncpi-non-food-yoy` — YoY change in NCPI non-food and services sub-group
- `remittance-inflows-cumulative` — Cumulative remittance inflows (NPR, USD)
- `gross-foreign-exchange-reserves` — Gross forex reserves at period end (NPR, USD)
- `merchandise-exports-cumulative` — Cumulative merchandise exports
- `merchandise-imports-cumulative` — Cumulative merchandise imports
- `bop-balance-cumulative` — Cumulative balance of payments
- `m2-yoy` — Broad money supply YoY growth
- `private-sector-credit-yoy` — Banks-and-FIs credit to private sector YoY growth

## Provenance

- Confidence default: A
- License: gov-open (Government of Nepal publication, freely redistributable
  for non-commercial use; CC BY-NC-SA applies to derivative editorial)
- Reporting period type: monthly (each release is one report; values are
  cumulative within the fiscal year — the parser must interpret the period
  metadata and emit `period_type` accordingly per CALENDAR_AND_PERIODS.md)

## Known breakage modes

- `url-changes-each-fy` — NRB rotates the slug at FY boundaries
  (e.g. `.../current-macroeconomic-situation-based-on-nine-months-of-202223/`).
  Parser must use a search-page fallback rather than a hardcoded URL.
- `pdf-format-shifts-at-fy-boundary` — Column headings, table page numbers,
  and "Table N(B)" labels have historically shifted at FY 2080/81 and
  FY 2081/82 boundaries. Parser must locate tables by header text, not by
  page number.

## Revision policy

Provisional values are revised in the next release (typically by 1–3% on
headline indicators). Historical values are considered stable after 2 cycles.
The parser writes each release as a new row in `staging_indicator_values`
keyed on `(indicator_id, period_start, period_end, source_document_id)`; the
Fact Ledger pipeline picks the latest non-provisional value per period and
records superseded values in `indicator_revisions` (Worker C-sequel).

## Parser

- Path: `scrapers/nrb-cmefs/parser.py`
- Version: 0.0.0 (not yet implemented; Worker C-sequel will land 0.1.0)
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-cmefs-monthly/samples/` (sample PDF is
  the in-repo `Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf`,
  copied into the samples directory on parser PR)

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-cmefs-monthly/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
