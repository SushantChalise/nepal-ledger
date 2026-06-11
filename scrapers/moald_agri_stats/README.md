# MoALD Statistical Information on Nepalese Agriculture — Parser

**Source ID:** `moald-agri-stats`
**Parser version:** 0.2.0
**Output table:** `dne_facts` (ADR-0015 dimensional facts)

## Source

Ministry of Agriculture and Livestock Development (MoALD) annual statistical
compendium. The FY 2080/81 edition is **224 pages of clean digital text** — every
data page has a perfect text layer; only the blank chapter-divider pages are
empty. **No OCR is used or needed**: pdfplumber text extraction is strictly
higher-fidelity than OCR on a born-digital PDF (ADR-0011 — read the text layer,
don't re-OCR it). Surya/OCR is reserved for genuinely scanned sources.

URL: https://moald.gov.np/publication/statistical-information-on-nepalese-agriculture

Distinct from `moald-crop-production` (seasonal crop bulletins, variable format).

## What is extracted (v0.2.0) — 1546 facts

### National time-series (full historical depth)

| Source | Base slug(s) | Dimension | Years |
|---|---|---|---|
| Table 1.1 | `agri-cereal-{area,production,yield}` | crop_type (6) | 11 (BS 2070/71–2080/81) |
| Table 2.1 | `agri-cashcrop-{area,production,yield}` | crop_type (5) | 10 (BS 2071/72–2080/81) |
| Table 3.1 | `agri-pulse-{area,production,yield}` | crop_type (9) | 12 (BS 2069/70–2080/81) |
| Table 4.1 | `agri-livestock-population` | livestock_category (11) | 10 |
| Table 4.2 | `agri-livestock-production` | livestock_product (15) | 11 |
| Table 6.1 | `agri-fruit-{total-area,productive-area,production,yield}` | crop_type (4) | 10 |
| Table 7.1 | `agri-vegetable-{area,production,yield}` | crop_type (1) | 10 |
| Table 9.1 | `agri-fertilizer-sales` | fertilizer_type (4) | 14 (BS 2067/68–2080/81) |
| §1.6 | `agri-spice-{area,production}` | crop_type (5) | 3 |

### Provincial cross-section (FY 2080/81)

| Source | Base slug | Dimension | Notes |
|---|---|---|---|
| Table 1.2 | `agri-cereal-production` | `province-crop` | composite `province__crop` (ADR-0018) |
| Table 2.2 | `agri-cashcrop-{area,production,yield}` | `province-crop` | oilseed/sugarcane/potato × 7 provinces |
| Table 7.2 | `agri-vegetable-{area,production,yield}` | `province` | 7 provinces |

### District cross-section (FY 2080/81)

| Source | Base slug | Dimension | Notes |
|---|---|---|---|
| Table 1.3 | `agri-cereal-{area,production,yield}` | `district` | all 77 districts (aggregate cereal) |

## Reconciliation (verified)

- **Province → national**: sum of province cereal production per crop equals the
  national series value for FY 2080/81 (diff ≤ 1 from source rounding).
- **District → national**: sum of all 77 districts' cereal production = 11,293,843
  vs the national total 11,293,841 (Δ 2, rounding).
- **Spot checks**: 25 cross-table value checks pass (see test suite).

## Parsing strategy

- **Anchor-driven**: each table is located by a body-unique header string, then
  sliced to the next table heading (case-insensitive — the source mixes
  `Table 2.2` with `TABLE 2.3`). Identical output against the full PDF and the
  11-page test fixture (both 1546 rows, 0 errors).
- **Year-token spacing**: recent years print with an inner space (`2023 /24`);
  a space-tolerant leading-year regex handles both forms.
- **Right-alignment** for transposed tables (livestock, fertilizer): a row with
  fewer numbers than year-columns maps to the most-recent years (e.g. fish
  production, which starts mid-series).
- **Variable columns**: pulses §3.1b omits the Himili-Bean column in early years
  (12 numbers) and includes it later (15) — mapped by count; the `Total`
  aggregate column is never stored as a crop.
- **Period mapping**: AD fiscal year `YYYY/YY` → BS `(YYYY+57)/(YY+57 % 100)`.

## Test fixture

`tests/fixtures/agri_stats_2080_81_excerpt.pdf` — 11-page extract (orig pages
9,10,14,15,16,28,48,58,81,103,152) covering every targeted table.

## Usage

```powershell
$env:PYTHONPATH = "scrapers"
python scrapers/moald_agri_stats/parser.py "<path-to-agri-pdf>"   # JSON to stdout
python -m pytest scrapers/moald_agri_stats/tests/ -v               # 46 tests

pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf" --dry-run
pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf"
```

## Deferred to v0.3.0 (documented, not silently dropped)

- **District matrices**: per-crop districts (1.4–1.6), oilseed-by-commodity (2.4),
  pulses (3.2), livestock (4.3–4.10), fruits (6.2–6.4), vegetables (7.3 — a
  40-page commodity×district transpose), fertilizer (9.2), population (8.2).
- **Macro GDP** (Table 10.x) — overlaps `mof-economic-survey-gva`; needs a
  canonical-source ADR before ingest to avoid Fact-Ledger double-counting.
- **Trade by HS code** (Table 11.x) — overlaps `customs-monthly-trade`.
- **Agri loans by sector** (Table 14.x) — overlaps NRB banking statistics.
- **Seed balance** (12.x), **crop/livestock insurance** (13), **commodity →
  Agri-GVA contribution** (15) — small national tables, low marginal priority.
