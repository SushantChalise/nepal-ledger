# MoALD Statistical Information on Nepalese Agriculture — Parser

**Source ID:** `moald-agri-stats`
**Parser version:** 0.1.0
**Output table:** `dne_facts` (ADR-0015 dimensional facts)

## Source

Ministry of Agriculture and Livestock Development (MoALD) publishes an annual
compendium of agricultural statistics. The FY 2080/81 edition (224 pages) has a
clean Latin-script text layer — pdfplumber text extraction, no OCR required.

URL: https://moald.gov.np/publication/statistical-information-on-nepalese-agriculture

Distinct from `moald-crop-production` (seasonal crop bulletins, variable format).

## What is extracted

| Source section | Page (FY 2080/81) | Base slug | Dimension | Years |
|---|---|---|---|---|
| Table 1.1 | 14 | `agri-cereal-{area,production,yield}` | `crop_type` | 11yr (2013/14–2023/24) |
| §1.4 Summary | 9 | `agri-cashcrop-{area,production}` | `crop_type` | 3yr |
| §1.5 Summary | 9–10 | `agri-pulse-{area,production}` | `crop_type` | 3yr |
| §2.2 Summary | 10–11 | `agri-livestock-production` | `livestock_product` | 3yr |
| §3 Summary | 11 | `agri-fertilizer-sales` | `fertilizer_type` | 3yr |

## Parsing strategy

- Page detection: scans for "SUMMARY STATISTICS" and "Table 1.1" anchors across
  the first 30 pages; works against both the full PDF and a 4-page test fixture.
- Summary stats (§1.3–§3) span 3 consecutive pages starting from the summary page.
- Period mapping: Table 1.1 uses AD fiscal years (2013/14…); parser converts to
  BS via `AD_year + 57 = BS_year` (e.g. AD 2023/24 → BS 2080/81).
- `.*?` absorbs units in parentheses between livestock labels and values
  (e.g. `WOOL PRODUCTION(Kg.)`).

## Test fixture

`tests/fixtures/agri_stats_2080_81_excerpt.pdf` — 4-page extract:
- Page 0: orig p9  — §1.3 Cereal, §1.4 Cash, §1.5 Pulses start
- Page 1: orig p10 — §1.5 Pulses cont., §2.2 Livestock start
- Page 2: orig p11 — §2.2 Livestock cont., §3 Fertilizer
- Page 3: orig p14 — Table 1.1 ten-year cereal

## Usage

```powershell
# Dry-run against fixture
$env:PYTHONPATH = "scrapers"
python scrapers/moald_agri_stats/parser.py scrapers/moald_agri_stats/tests/fixtures/agri_stats_2080_81_excerpt.pdf

# Run tests
python -m pytest scrapers/moald_agri_stats/tests/ -v

# Ingest (dry-run)
pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf" --dry-run

# Ingest (live)
pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf"
```

## Known gaps (v0.2.0 backlog)

- §1.5 Pulses: "Himali bean" row (2078/79 data absent)
- §1.6 Other Crops: Fruits/vegetables/spices (sparse rows)
- Table 1.2: Provincial cereal breakdown (FY 2080/81 only)
- Tables 2–15: District-level detail, exports/imports by commodity
