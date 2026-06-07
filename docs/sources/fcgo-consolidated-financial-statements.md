# Source: Financial Comptroller General Office — Consolidated Financial Statements

**source_id:** `fcgo-consolidated-financial-statements`
**Status:** Active (parser v0.1.0 — 6 headline aggregates extract from FY 2022/23 PDF)
**Tier:** Tier 1
**Registered at:** 2026-06-07
**Last verified:** 2026-06-07 (parser built + run against FY 2022/23 CFS PDF)

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

> **UNIT CORRECTION (2026-06-07):** the figures are **`npr_million`**, NOT "NPR
> billion" as originally written here. Verified against the FY 2022/23 CFS:
> total revenue utilization = NPR **1,506,321.46 million** (≈ NPR 1.5 trillion),
> the correct order of magnitude for Nepal's 3-tier consolidated revenue. The
> parser stamps `unit = "npr_million"` on every row (see ADR-0011 unit-verification
> protocol).

Slugs are prefixed `fcgo-` to match the `SOURCE_ID` family (consistent with the
NRB CMEFs convention where `cmefs-…` slugs map to `nrb-cmefs-monthly`). Values
shown are the verified FY 2022/23 (BS 2079/80) outturn.

- `fcgo-total-revenue-outturn-annual` — Total revenue utilization of 3 tiers, after revenue-sharing settlements (npr_million; FY22/23 = 1,506,321.46)
- `fcgo-total-expenditure-outturn-annual` — Total expenditure after eliminating intergovernmental transfers, excl. EBUs (npr_million; FY22/23 = 1,672,128.84)
- `fcgo-capital-expenditure-outturn-annual` — Consolidated capital expenditure, Σ across 3 tiers, **gross** (npr_million; FY22/23 = 527,447.04)
- `fcgo-recurrent-expenditure-outturn-annual` — Consolidated recurrent expenditure, Σ across 3 tiers, **gross** (npr_million; FY22/23 = 1,356,150.86)
- `fcgo-provincial-expenditure-consolidated-annual` — Sum of 7 province expenditures (npr_million; FY22/23 = 204,678.62)
- `fcgo-local-level-expenditure-consolidated-annual` — Sum of 753 local government expenditures (npr_million; FY22/23 = 453,817.73)

> **Basis caveat:** `total-revenue` / `total-expenditure` are *after-elimination*
> figures; `recurrent` / `capital` are *gross* consolidated sums (before
> eliminating intergovernmental transfers). So recurrent + capital + financing
> (NPR 2,079,823.31 million) ≠ total-expenditure (NPR 1,672,128.84 million). The
> parser records this in each row's `parser_notes`.

> **Extraction strategy:** the detailed statement tables render with reversed
> glyph order under pdfplumber and are NOT machine-read. The parser anchors on the
> clean forward-text Executive Summary (pp. 12–13) + Treasury-Position prose
> (p. 31) and scans all pages (page numbers drift across editions).

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

- Path: `scrapers/fcgo_consolidated/parser.py` (underscore dir — Python-importable; the on-disk folder is NOT the hyphenated profile name)
- Version: 0.1.0
- Owner: Mother Opus (built by Sonnet worker W2, 2026-06-07)
- Unit: `npr_million`; reporting period: `annual`; confidence: `A`
- Tested against: `Financial Data/fcgo_consolidated/FCGO_CFS_2022-23.pdf` (FY 2022/23, 325 pp) + synthesized text fixtures in `scrapers/fcgo_consolidated/tests/`
- Period mapping: AD fiscal year → BS via +57 on the lead year (ADR-0013); FY 2022/23 → BS 2079/80

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `fcgo-consolidated-financial-statements/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
