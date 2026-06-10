# Source: National Statistics Office — Nepal Living Standards Survey (NLSS)

**source_id:** `nlss-survey`
**Status:** Active
**Tier:** Tier 2 (welfare flagship; decadal cadence)
**Ingestion mode:** `manual_upload`
**Registered at:** 2026-06-07
**Last verified:** 2026-06-11

## What this is

The Nepal Living Standards Survey (NLSS) is a nationally-representative
household welfare survey conducted decadally by the National Statistics Office
(NSO, formerly CBS). It is the primary source for Nepal's official poverty
headcount rates, per-capita consumption aggregates, Gini inequality measures,
and consumption composition (food vs. non-food). It uses the cost-of-basic-needs
methodology with an official poverty line.

**NLSS-IV** (2022/23, published February 2024) is the most recent round. It
surveyed approximately 6,000 households across all 7 provinces and is the first
round using the 7-province administrative structure (NLSS-III used 5 development
regions).

## Publication

- **Official data portal:** https://data.nsonepal.gov.np/dataset/poverty-status-2023
- **Mirror PDF:** https://giwmscdnone.gov.np/media/app/public/36/posts/1707800524_89.pdf
- **Archive path:** `Financial Data/nso_nlss/NLSS_IV_Summary_2022-23.pdf`
- **Frequency:** ad_hoc (decadal — NLSS-I 1995/96, II 2003/04, III 2010/11, IV 2022/23)
- **Format:** pdf (summary report — typeset text layer, no OCR needed)

## What we extract

14 NLSS-IV indicators (FY 2079/80 BS = 2022/23 AD) and 6 NLSS-III comparison
values (FY 2067/68 BS = 2010/11 AD) from the NLSS-IV Summary Report.

| Slug | Unit | NLSS-IV | NLSS-III |
|---|---|---|---|
| `nlss-poverty-headcount-national` | percent | 20.27 | 25.16 |
| `nlss-poverty-headcount-urban` | percent | 18.34 | 15.46 |
| `nlss-poverty-headcount-rural` | percent | 24.66 | 27.43 |
| `nlss-poverty-headcount-koshi` | percent | 17.19 | — |
| `nlss-poverty-headcount-madhesh` | percent | 22.53 | — |
| `nlss-poverty-headcount-bagmati` | percent | 12.59 | — |
| `nlss-poverty-headcount-gandaki` | percent | 11.88 | — |
| `nlss-poverty-headcount-lumbini` | percent | 24.35 | — |
| `nlss-poverty-headcount-karnali` | percent | 26.69 | — |
| `nlss-poverty-headcount-sudurpaschim` | percent | 34.16 | — |
| `nlss-per-capita-consumption-annual` | npr | 130,853 | — |
| `nlss-gini-consumption` | ratio (0–1) | 0.300 | 0.328 |
| `nlss-food-share-consumption` | percent | 53.0 | 62.0 |
| `nlss-non-food-share-consumption` | percent | 47.0 | 38.0 |

Provincial NLSS-III values are not available in comparable form because
NLSS-III used 5 development regions (not the current 7-province structure).

## Parsing strategy

The Summary Report has a clean Latin-script text layer (no OCR needed).
`pdfplumber.extract_tables()` returns empty for NLSS pages because values are
typeset as fixed-width aligned text, not PDF table objects. The parser uses
`page.extract_text()` with section-anchored regex patterns:

| Indicator set | Source page (0-indexed) | Anchor |
|---|---|---|
| Per-capita consumption | 13 | `Figure 1. Average annual per capita` |
| Food/non-food shares | 16 | `Figure 2. Food and non-food share` |
| National/urban/rural headcount + Gini | 21 | `Table 9. Poverty profile` |
| Provincial headcounts | 22 | `Table 11. Provincial poverty` |
| Historical headcount + Gini trend | 27 | `Table A1: Poverty headcount` / `Table A4: Gini index` |

Note: `requiresTableExtraction: true` in the registry reflects that pdfplumber
IS used for extraction, even though `extract_tables()` itself returns empty.

## Provenance

- **Confidence default:** A — primary NSO published survey report, official poverty line
- **License:** gov_open
- **Reporting period type:** annual (full fiscal year)
- **Scale note:** Gini is stored on the 0–1 scale. Table 9 in the source already
  uses 0–1 (e.g. 0.300). Table A4 uses the 0–100 scale (e.g. 30.0); the parser
  divides by 100 before emitting.

## Known breakage modes

- If NSO revises the report, check Table 9 / Table A4 Gini-scale consistency.
- The `Figure 2` food/non-food pairing uses a sum-to-100 checksum; any layout
  change that adds/removes percentage values will trigger a `PageLayoutChanged`
  error rather than emitting wrong data.
- Provincial headcounts are extracted from Table 11 by province name. If NSO
  renames a province (Karnali / Far-Western history), bump `PARSER_VERSION`.

## Revision policy

NSO occasionally revises NLSS-III 2010/11 comparators when applying the updated
2022 methodology. If revised values appear in a new edition of the summary report,
re-ingest with the new file; the `onConflictDoNothing` staging logic will insert
new rows; old approved rows are immutable (revision tracking: see DATA_PIPELINE.md).

## Parser

- **Path:** `scrapers/nso_nlss/parser.py`
- **Version:** 0.1.0
- **Owner:** Mother (data platform)
- **Tested against:** `scrapers/nso_nlss/tests/fixtures/nlss_iv_summary_excerpt.pdf`
  (5-page excerpt: pages 13, 16, 21, 22, 27 of the 57-page summary report)

## Archive policy

Downloaded files stored under `Financial Data/nso_nlss/` (gitignored; local
filesystem storage per ADR-0006). Key: `nso_nlss/NLSS_IV_Summary_2022-23.pdf`.
Hash + source URL recorded in `source_documents`. Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
