# Source: Nepal Rastra Bank — NRB Annual Report (English + Nepali)

**source_id:** `nrb-annual-report`
**Status:** Paused
**Tier:** Tier 3
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's Annual Report is the gold standard for historical macro-economic baselines: it carries
official audited figures for each fiscal year covering monetary policy, financial system
performance, external sector, government finance, and real sector. The English edition spans
FY 2003/04 to FY 2024/25 (22 editions). It is required for back-filling Pulse indicators in
periods before the monthly XLSX corpus begins (pre-FY 2078). FIU, bank supervision, non-bank
FI supervision, and money-laundering prevention supervision sub-reports are published separately
but appear in the same archive category under different department slugs.

## Publication

- URL: https://www.nrb.org.np/category/annual-reports (note: plural, no trailing slash)
- Frequency: annual (published May–June of the following year)
- Expected window: May–June after FY close (Ashadh end)
- Format: pdf

## What we extract

- `nrb-ar-ncpi-annual` — Annual average NCPI inflation (%)
- `nrb-ar-gdp-growth` — Real GDP growth rate for the FY (%)
- `nrb-ar-bop-annual` — Annual BoP position (NPR billion)
- `nrb-ar-remittance-annual` — Annual remittance inflows (NPR billion)
- `nrb-ar-forex-reserves-endfy` — Gross forex reserves at FY end (NPR billion + months of import cover)
- `nrb-ar-credit-to-private-sector-annual` — Annual credit to private sector growth (%)
- (complete indicator list to be finalized in parser PR)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `category-slug-annual-reports-plural-no-trailing-slash` — The correct category URL is
  `/category/annual-reports` (plural, no trailing slash). The variant `/category/annual-report/`
  returns 404.
- `fiu-bsd-nbfisd-mlpsd-sub-reports-mixed-into-same-archive-category` — FIU Nepal Annual
  Reports, Annual Bank Supervision Reports, Non-Bank FI Supervision Reports, and Money Laundering
  Prevention Supervision Reports appear in the same category under different department slugs
  (`fiu/`, `bsd/`, `nbfisd/`, `mlpsd/`). The downloader must filter to the main NRB Annual
  Report (`red/` department slug) to avoid ingesting supervision sub-reports.

## Revision policy

Annual; each report carries the final audited figures for that FY. Occasional corrigenda are
published as separate notices. Historical time-series tables in the Appendix are the most
stable; narrative figures in the body may be revised between preliminary and final releases.

## Parser

- Path: `scrapers/nrb-annual-report/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-annual-report/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-annual-report/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
