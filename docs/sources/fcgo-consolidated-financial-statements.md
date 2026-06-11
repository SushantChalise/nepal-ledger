# Source: Financial Comptroller General Office — Consolidated Financial Statements

**source_id:** `fcgo-consolidated-financial-statements`
**Status:** Active (parser v1.1.0 — pymupdf backend; 64 indicators: 9 prose + 55 overview-table; FY 2018/19 → 2023/24 available)
**Tier:** Tier 1
**Registered at:** 2026-06-07
**Last verified:** 2026-06-11 (fcgo.gov.np; FY 2023/24 now available; no monthly CFS found at fcgo.gov.np)

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
- `fcgo-financing-disbursements-outturn-annual` — Consolidated financing disbursements, Σ across 3 tiers, **gross** (npr_million; FY22/23 = 196,225.41)
- `fcgo-federal-expenditure-outturn-annual` — **Derived:** total-expenditure minus provincial minus local (npr_million; FY22/23 = 1,013,632.49)
- `fcgo-fiscal-balance-outturn-annual` — **Derived:** total-revenue minus total-expenditure; negative = deficit (npr_million; FY22/23 = −165,807.38)

> **Basis caveat:** `total-revenue` / `total-expenditure` are *after-elimination*
> figures; `recurrent` / `capital` are *gross* consolidated sums (before
> eliminating intergovernmental transfers). So recurrent + capital + financing
> (NPR 2,079,823.31 million) ≠ total-expenditure (NPR 1,672,128.84 million). The
> parser records this in each row's `parser_notes`.

> **Extraction strategy (v1.1.0):** pymupdf replaced pdfplumber (v1.0.0) —
> pdfplumber reversed text on 165/325 landscape-rotated pages. pymupdf reads
> them correctly, enabling full table extraction. The parser extracts:
> - **Prose (9 indicators):** anchors on Executive Summary narrative text
>   (page numbers drift across editions); 7 extracted + 2 derived.
> - **Overview tables (55 indicators):** pymupdf `find_tables()` extracts 5
>   overview tables, each with 5 FY columns. Tables are located by text-anchor
>   matching (not page numbers), with whitespace normalization and TOC
>   false-match protection. Total: ~248 staging rows from one PDF.

### Overview table indicators (v1.1.0)

**Table 28: Macro Economic Indicators** (16 indicators, CBS national accounts via FCGO)
- `fcgo-macro-gdp-nominal-annual` — Nominal GDP (npr_million)
- `fcgo-macro-gni-nominal-annual` — Gross National Income (npr_million)
- `fcgo-macro-gndi-nominal-annual` — Gross National Disposable Income (npr_million)
- `fcgo-macro-consumption-pct-gdp-annual` — Final Consumption Expenditure (% of GDP)
- `fcgo-macro-domestic-saving-pct-gdp-annual` — Gross Domestic Saving (% of GDP)
- `fcgo-macro-national-saving-pct-gdp-annual` — Gross National Saving (% of GDP)
- `fcgo-macro-exports-pct-gdp-annual` — Exports of Goods & Services (% of GDP)
- `fcgo-macro-imports-pct-gdp-annual` — Imports of Goods & Services (% of GDP)
- `fcgo-macro-gfcf-pct-gdp-annual` — Gross Fixed Capital Formation (% of GDP)
- `fcgo-macro-resources-gap-pct-gdp-annual` — Resources Gap (% of GDP)
- `fcgo-macro-remittances-pct-gdp-annual` — Workers Remittances (% of GDP)
- `fcgo-macro-product-tax-pct-gdp-annual` — Product Tax (% of GDP)
- `fcgo-macro-total-tax-pct-gdp-annual` — Total Tax (% of GDP)
- `fcgo-macro-per-capita-gdp-annual` — Per Capita GDP (npr)
- `fcgo-macro-per-capita-gni-annual` — Per Capita GNI (npr)
- `fcgo-macro-per-capita-gndi-annual` — Per Capita GNDI (npr)

**Table 29: Macro-Level Budget Operation** (18 indicators, % of GDP)
- `fcgo-budget-expenditure-pct-gdp-annual` through `fcgo-budget-investment-loan-pct-gdp-annual`
- Covers: expenditure, recurrent, capital, financing, revenue, grants, debt received/repayment (domestic+external), outstanding debt, total investment (share+loan)

**Table 10: COFOG-wise Expenditure** (10 indicators, % of total)
- `fcgo-cofog-general-public-services-pct-annual` through `fcgo-cofog-social-security-pct-annual`
- All 10 COFOG functional sectors

**Table 16: Outstanding Debt** (3 indicators, npr_million)
- `fcgo-debt-domestic-outstanding-annual`, `fcgo-debt-external-outstanding-annual`, `fcgo-debt-total-outstanding-annual`

**Table 37: Debt Ratio** (8 indicators, percent)
- `fcgo-debt-external-share-pct-annual` through `fcgo-debt-servicing-pct-exports-annual`
- Debt composition (external/domestic share) + sustainability ratios (debt/GDP, servicing/GDP, servicing/revenue, servicing/exports)

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
- Version: 1.1.0 (2026-06-11 — pymupdf backend; 9 prose + 55 overview-table indicators; FY auto-detection)
- Owner: Mother Opus (built by Sonnet worker W2, 2026-06-07; v0.2.0 2026-06-11; v1.0.0 2026-06-11; v1.1.0 2026-06-11)
- Unit: `npr_million`; reporting period: `annual`; confidence: `A`
- Tested against: `Financial Data/fcgo_consolidated/FCGO_CFS_2022-23.pdf` (FY 2022/23, 325 pp) + synthesized text fixtures in `scrapers/fcgo_consolidated/tests/`; FY 2023/24 variant tested via fixture
- Period mapping: AD fiscal year → BS via +57 on the lead year (ADR-0013); FY 2022/23 → BS 2079/80; FY 2023/24 → BS 2080/81

## Availability

English CFS editions at https://fcgo.gov.np/category/consolidated-us (verified 2026-06-11):

| AD FY   | BS FY   | Available |
|---------|---------|-----------|
| 2018/19 | 2075/76 | Yes       |
| 2019/20 | 2076/77 | Yes       |
| 2020/21 | 2077/78 | Yes       |
| 2021/22 | 2078/79 | Yes       |
| 2022/23 | 2079/80 | Yes       |
| 2023/24 | 2080/81 | Yes (newest; not yet ingested as of 2026-06-11) |

## Cross-validation

**NRB CMEFs alignment:** NRB sources its government-finance indicators from FCGO/MoF. CMEFs
Table 9 "Government Finance" rows for FY 2079/80 should align within rounding with the FCGO CFS
totals. The FY 2022/23 FCGO total revenue outturn (NPR 1,506,321.46 million) is consistent with
NRB CMEFs government revenue for the same period. Expect ≤1% variance due to CMEFs rounding to
the nearest NPR million versus FCGO's two decimal precision.

**Red Book estimate vs. outturn:** The MoF Red Book publishes revenue and expenditure *estimates*
at the start of each fiscal year. The FCGO CFS outturn figure minus the Red Book estimate gives
the estimate-vs-actual variance — itself a valuable signal for fiscal credibility tracking.
When both sources are ingested, compute:
  `estimate_variance_pct = (fcgo_outturn - redbook_estimate) / redbook_estimate * 100`
Nepal typically undershoots capital expenditure estimates by 20–40%.

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `fcgo-consolidated-financial-statements/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
