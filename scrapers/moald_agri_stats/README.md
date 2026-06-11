# MoALD Statistical Information on Nepalese Agriculture — Parser

**Source ID:** `moald-agri-stats`
**Parser version:** 0.3.0
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

## What is extracted (v0.3.0) — 4383 facts

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

### District cross-section (FY 2080/81) — v0.3.0, all reconcile to national

| Source | Base slug | Dimension | Notes |
|---|---|---|---|
| Table 1.3 | `agri-cereal-{area,production,yield}` | `district` | all 77 districts (aggregate cereal) |
| Table 1.5 | `agri-cereal-{area,production,yield}` | `district-crop` | maize + wheat × 77 districts (`district__crop`) |
| Table 2.3 | `agri-cashcrop-{area,production,yield}` | `district-crop` | oilseed/sugarcane/potato × 77 districts |
| Table 4.3 | `agri-livestock-population` | `district-livestock-category` | 7 categories × 77 districts (`district__category`) |
| Table 4.5 | `agri-livestock-production` | `district-livestock-product` | 6 meat types × district |
| Table 4.6 | `agri-livestock-production` | `district-livestock-product` | laying hen/duck + hen/duck/total egg × district |
| Table 4.7 | `agri-livestock-production` | `district-livestock-product` | wool (+ wool-flock sheep) × district |
| Table 9.2 | `agri-fertilizer-sales` | `district-fertilizer-type` | grand-total urea/dap/potash × district |

Total: **4383 facts** (1546 national/provincial + 2837 district).

## Reconciliation (verified — every district extractor sums to the national series)

- **Province → national**: sum of province cereal production per crop equals the
  national series value for FY 2080/81 (diff ≤ 1 from source rounding).
- **District → national (exact to the unit)**:
  - Cereal aggregate (1.3): 77 districts → 11,293,843 vs national 11,293,841 (Δ 2).
  - Maize/wheat (1.5): maize 3,193,873 vs 3,193,869; wheat 2,035,564 vs 2,035,559.
  - Cash crops (2.3): oilseed/potato/sugarcane area + production all reconcile
    (sugarcane 55,442 vs 55,440 — validates the collapsing-column heuristic).
  - Livestock population (4.3): cattle 5,198,388 / goat 15,289,954 / fowl 56,916,567
    — all exact.
  - Meat/egg/wool (4.5–4.7): meat-buffalo 138,271, eggs-total 1,645,407, wool
    389,742 — all match to ±2.
  - Fertilizer (9.2): urea 259,542 / dap 184,046 — exact.
- **Spot checks**: cross-table value checks pass (see 66-test suite).

## Parsing strategy

- **Anchor-driven**: each table is located by a body-unique header string, then
  sliced to the next table heading (case-insensitive — the source mixes
  `Table 2.2` with `TABLE 2.3`). Identical output against the full PDF and the
  28-page test fixture (both 4383 rows, 0 errors).
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

`tests/fixtures/agri_stats_2080_81_excerpt.pdf` — 28-page extract covering every
targeted national, provincial, and district table. The parser produces identical
output (4383 rows, 0 errors) against the fixture and the full 224-page PDF, so the
committed tests exercise the real reconciliation, not a toy subset.

## Usage

```powershell
$env:PYTHONPATH = "scrapers"
python scrapers/moald_agri_stats/parser.py "<path-to-agri-pdf>"   # JSON to stdout
python -m pytest scrapers/moald_agri_stats/tests/ -v               # 66 tests

pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf" --dry-run
pnpm ingest:moald-agri --input "Financial Data/moald_agri_stats/StatInfo_AgriNepal_2080_81.pdf"
```

## Still deferred after v0.3.0 (documented, not silently dropped)

Tables whose source layout cannot be reconstructed from the text layer reliably
enough to pass the reconciliation gate — emitting them would mean storing wrong
numbers, which the doctrine forbids:

- **Table 1.6** (millet/buckwheat/barley by district): a minor-cereal column
  collapses to a single `0.00` MID-row while later crops still have data, so
  positional alignment breaks (district buckwheat sum ≈ 76 % of national).
- **Table 3.2** (pulses by district): crops are *omitted* in some rows and
  *dash-filled* in others — positionally ambiguous, no reliable mapping.
- **Table 2.13** (spices) / **2.4** (oilseed by commodity): rotated headers
  and/or the same omitted-vs-dashed sparse-column ambiguity as 3.2.
- **Tables 6.2–6.4** (fruit by district): rotated headers + 4-column-per-fruit
  sparse layout. **7.3** (vegetables — 40-pp. commodity×district transpose).
- **Table 8.2** (population by district) — overlaps `cbs-nphc-2021` (census).

Note: 2.3 (cash crops) had a collapsing column too but, unlike the above, the
sparse column is a single middle crop (sugarcane) bracketed by two near-universal
crops, so the heuristic reconciles — that's why it ships and these don't.

Tables that **republish another agency's data** — cross-reference only, NOT
ingested, per [ADR-0026](../../docs/decisions/0026-agri-stats-overlapping-tables-cross-reference-only.md):

- **Macro GDP/GVA** (Table 10.x) — NSO national accounts; held via Economic Survey.
- **Trade by HS code** (Table 11.x) — Customs; held via `customs-monthly-trade`.
- **Agri loans by sector** (Table 14.x) — NRB; held via NRB banking statistics.

Low-priority small national tables: seed balance (12.x), crop/livestock
insurance (13), commodity → Agri-GVA contribution (15).
