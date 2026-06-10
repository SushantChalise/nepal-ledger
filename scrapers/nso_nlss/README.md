# scrapers/nso_nlss — NSO Nepal Living Standards Survey IV

Parser for the **National Statistics Office Nepal Living Standards Survey IV
(NLSS-IV) 2022/23 Summary Report**. Extracts 14 welfare indicators (poverty
headcount by geography + per-capita consumption + Gini + food/non-food shares)
and 6 NLSS-III comparison values for trend capture.

## Source

- **Report:** NLSS-IV Summary Report 2022-23 (NSO, February 2024)
- **Official data portal:** https://data.nsonepal.gov.np/dataset/poverty-status-2023
- **Mirror PDF:** https://giwmscdnone.gov.np/media/app/public/36/posts/1707800524_89.pdf
- **Archive path:** `Financial Data/nso_nlss/NLSS_IV_Summary_2022-23.pdf`

## Usage

```powershell
# Dry-run (no DB writes):
pnpm ingest:nlss --dry-run --input "C:\Users\ACER\Projects\Economy\Financial Data\nso_nlss\NLSS_IV_Summary_2022-23.pdf"

# Live ingest:
pnpm ingest:nlss --input "C:\Users\ACER\Projects\Economy\Financial Data\nso_nlss\NLSS_IV_Summary_2022-23.pdf"
```

## Parsing strategy

The NLSS-IV Summary Report has a clean Latin-script text layer (no OCR needed).
`pdfplumber` `extract_tables()` returns no rows for these pages (data is
typeset as aligned text, not PDF table objects). The parser uses
`page.extract_text()` and section-anchored regex patterns:

| Indicator set | Source page (0-indexed) | Anchor regex |
|---|---|---|
| Per-capita consumption | 13 | `Figure 1. Average annual per capita` |
| Food/non-food shares | 16 | `Figure 2. Food and non-food share` |
| Poverty profile + Gini | 21 | `Table 9. Poverty profile` |
| Provincial headcounts | 22 | `Table 11. Provincial poverty` |
| Historical trend (NLSS-III) | 27 | `Table A1: Poverty headcount` / `Table A4: Gini index` |

## Indicators produced

| Slug | Unit | Survey | Value |
|---|---|---|---|
| `nlss-poverty-headcount-national` | percent | NLSS-IV | 20.27 |
| `nlss-poverty-headcount-urban` | percent | NLSS-IV | 18.34 |
| `nlss-poverty-headcount-rural` | percent | NLSS-IV | 24.66 |
| `nlss-poverty-headcount-koshi` | percent | NLSS-IV | 17.19 |
| `nlss-poverty-headcount-madhesh` | percent | NLSS-IV | 22.53 |
| `nlss-poverty-headcount-bagmati` | percent | NLSS-IV | 12.59 |
| `nlss-poverty-headcount-gandaki` | percent | NLSS-IV | 11.88 |
| `nlss-poverty-headcount-lumbini` | percent | NLSS-IV | 24.35 |
| `nlss-poverty-headcount-karnali` | percent | NLSS-IV | 26.69 |
| `nlss-poverty-headcount-sudurpaschim` | percent | NLSS-IV | 34.16 |
| `nlss-per-capita-consumption-annual` | npr | NLSS-IV | 130,853 |
| `nlss-gini-consumption` | ratio | NLSS-IV | 0.300 |
| `nlss-food-share-consumption` | percent | NLSS-IV | 53.0 |
| `nlss-non-food-share-consumption` | percent | NLSS-IV | 47.0 |
| `nlss-poverty-headcount-national` | percent | NLSS-III | 25.16 |
| `nlss-poverty-headcount-urban` | percent | NLSS-III | 15.46 |
| `nlss-poverty-headcount-rural` | percent | NLSS-III | 27.43 |
| `nlss-gini-consumption` | ratio | NLSS-III | 0.328 |
| `nlss-food-share-consumption` | percent | NLSS-III | 62.0 |
| `nlss-non-food-share-consumption` | percent | NLSS-III | 38.0 |

## Tests

```powershell
# From the repo root scrapers/ directory:
python -m pytest nso_nlss/tests/ -v
```

The test fixture is a 5-page excerpt of the summary report (pages 13, 16, 21,
22, 27 of the original 57-page PDF), covering all indicator-producing sections.
