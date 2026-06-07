# Source: Financial Comptroller General Office — Consolidated Financial Statements

**source_id:** `fcgo-consolidated-financial-statements`
**Status:** Paused
**Tier:** Tier 1
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker B catalog audit)

## What this is

FCGO's Consolidated Financial Statements (CFS) are the audited all-of-government fiscal
outturn: final actual revenue, expenditure, and capital spending for the entire government
including federal, 7 provinces, and 753 local governments in consolidated form. This is the
highest-confidence fiscal data (A grade) because it is audited. The English edition is
available from FY 2018/19 (2075/76 BS) onward; the Nepali edition from FY 2074/75.

## Publication

- URL (English): https://fcgo.gov.np/category/consolidated-us
- URL (Nepali, central account): https://fcgo.gov.np/category/con-fin-statements/
- Frequency: annual (published approximately Chaitra of the following FY)
- Expected window: Chaitra of the following fiscal year (~9 months after FY close)
- Format: pdf

## What we extract

- `total-revenue-outturn-annual` — Final actual total revenue (NPR billion)
- `total-expenditure-outturn-annual` — Final actual total expenditure (NPR billion)
- `capital-expenditure-outturn-annual` — Capital spending actual (NPR billion)
- `recurrent-expenditure-outturn-annual` — Recurrent spending actual (NPR billion)
- `provincial-expenditure-consolidated-annual` — Sum of 7 province expenditures (NPR billion)
- `local-level-expenditure-consolidated-annual` — Sum of 753 local government expenditures (NPR billion)

## Provenance

- Confidence default: A (audited outturn)
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `nepali-url-at-category-con-fin-statements-english-at-category-consolidated-us` — The
  Nepali (central account) CFS and the English consolidated CFS are at different category URLs.
  The parser must handle both to build a unified outturn series.
- `pdf-filenames-use-opaque-cdn-tokens-at-giwmscdnone-gov-np` — Actual PDF files are served
  from the Government Integrated Web Management System CDN (`giwmscdnone.gov.np`) with opaque
  filename tokens (e.g., `fy-2080-81-01_kbdjr2r.pdf`). The downloader must resolve current
  links by scraping the FCGO category page, not by constructing URLs from FY patterns.

## Revision policy

Annual; audited outturn — no subsequent revision expected after publication. If FCGO publishes
a corrected edition, it appears as a new file at the same category URL.

## Parser

- Path: `scrapers/fcgo-consolidated-financial-statements/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/fcgo-consolidated-financial-statements/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `fcgo-consolidated-financial-statements/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
