# Source: MoALD Statistical Information on Nepalese Agriculture

**source_id:** `moald-agri-stats`
**Status:** Active
**Tier:** 3
**Agency:** Ministry of Agriculture and Livestock Development (MoALD)
**Registered at:** 2026-06-11

## What this is

Annual compendium of Nepalese agricultural statistics published by MoALD: crop,
livestock, fisheries, horticulture, and agri-input time-series plus district- and
province-level cross-sections, agricultural trade, and macro/GVA tables. The
FY 2080/81 edition covers data through 2023/24 AD.

Distinct from [`moald-crop-production`](moald-crop-production.md) — the seasonal
crop bulletin (variable format, Surya OCR required). This publication is a
**born-digital clean text layer**, so it is parsed with pdfplumber text
extraction (no OCR — higher fidelity than re-OCR per ADR-0011).

## Publication

- URL: https://moald.gov.np/publication/statistical-information-on-nepalese-agriculture
- Frequency: annual (published in the following fiscal year)
- Format: PDF (clean text layer, no OCR required)
- Archive path: `Financial Data/moald_agri_stats/`

## What we extract (v0.2.0) → `dne_facts` (ADR-0015) — 1546 facts

### National time-series (full historical depth)

| Section | Base slug(s) | Dimension | Years |
|---|---|---|---|
| Table 1.1 | `agri-cereal-{area,production,yield}` | `crop_type` (paddy/maize/millet/buckwheat/wheat/barley) | 11 (BS 2070/71–2080/81) |
| Table 2.1 | `agri-cashcrop-{area,production,yield}` | `crop_type` (oilseed/potato/sugarcane/jute/cotton) | 10 (BS 2071/72–2080/81) |
| Table 3.1 | `agri-pulse-{area,production,yield}` | `crop_type` (lentil/chickpea/pigeon-pea/black-gram/grass-pea/horse-gram/soyabean/himili-bean/others) | 12 (BS 2069/70–2080/81) |
| Table 4.1 | `agri-livestock-population` | `livestock_category` (cattle/buffaloes/sheep/goat/pigs/fowl/duck/milking-cow/milking-buffalo/laying-hen/laying-duck) | 10 |
| Table 4.2 | `agri-livestock-production` | `livestock_product` (milk/meat/eggs/wool/fish, 15 series) | 11 |
| Table 6.1 | `agri-fruit-{total-area,productive-area,production,yield}` | `crop_type` (citrus/winter/summer/total-fruit) | 10 |
| Table 7.1 | `agri-vegetable-{area,production,yield}` | `crop_type` (fresh-vegetable) | 10 |
| Table 9.1 | `agri-fertilizer-sales` | `fertilizer_type` (urea/dap/potash/total) | 14 (BS 2067/68–2080/81) |
| §1.6 | `agri-spice-{area,production}` | `crop_type` (large-cardamom/ginger/garlic/turmeric/dry-chili) | 3 |

### Provincial + district cross-sections (FY 2080/81)

| Section | Base slug | Dimension | Notes |
|---|---|---|---|
| Table 1.2 | `agri-cereal-production` | `province-crop` | composite `province__crop` (ADR-0018) |
| Table 2.2 | `agri-cashcrop-{area,production,yield}` | `province-crop` | oilseed/sugarcane/potato × 7 provinces |
| Table 7.2 | `agri-vegetable-{area,production,yield}` | `province` | 7 provinces |
| Table 1.3 | `agri-cereal-{area,production,yield}` | `district` | all 77 districts (aggregate cereal) |

**Unit semantics** (ADR-0011, read off the source headers): area = `hectare`;
production = `metric_tonne`; yield = `metric_tonne_per_hectare`; livestock
population = `number`; eggs = `thousand_units`; wool = `kg`; fertilizer =
`metric_tonne`. The pulses table header mislabels yield "Kg./Ha" but the printed
values are Mt/Ha (production ÷ area), so they are stored as
`metric_tonne_per_hectare`.

## Reconciliation (verified at parse time)

- Province cereal-production sums equal the national series per crop (Δ ≤ 1, rounding).
- District cereal-production sums to 11,293,843 vs national 11,293,841 (Δ 2, rounding).
- 25 cross-table spot checks pass (test suite).

## Provenance

- Confidence default: **B** — MoALD compiles from provincial/local administrative
  reports; not independently audited (cf. FCGO/customs grade A).
- License: gov_open
- Reporting period type: annual

## Deferred to v0.3.0 (documented, not silently dropped)

- **District matrices**: per-crop districts (1.4–1.6), oilseed-by-commodity (2.4),
  pulses (3.2), livestock (4.3–4.10), fruits (6.2–6.4), vegetables (7.3, 40-page
  transpose), fertilizer (9.2), population (8.2).
- **Macro GDP** (10.x) — overlaps `mof-economic-survey-gva`; needs a
  canonical-source ADR before ingest (Fact-Ledger double-counting risk).
- **Trade by HS code** (11.x) — overlaps `customs-monthly-trade`.
- **Agri loans by sector** (14.x) — overlaps NRB banking statistics.
- Seed balance (12.x), insurance (13), commodity→Agri-GVA contribution (15).

## Parser

- Path: `scrapers/moald_agri_stats/parser.py`
- Version: 0.2.0 (anchor-driven; identical output on full PDF + fixture)
- Fixture: `scrapers/moald_agri_stats/tests/fixtures/agri_stats_2080_81_excerpt.pdf` (11 pages)
- Tests: 46 passing

## Archive policy

Files stored in `Financial Data/moald_agri_stats/` (local filesystem per ADR-0006).
Filename convention: `StatInfo_AgriNepal_<FY_BS>.pdf` (e.g. `StatInfo_AgriNepal_2080_81.pdf`).

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
