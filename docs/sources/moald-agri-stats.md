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

## What we extract (v0.3.0) → `dne_facts` (ADR-0015) — 4383 facts

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

### Provincial cross-section (FY 2080/81)

| Section | Base slug | Dimension | Notes |
|---|---|---|---|
| Table 1.2 | `agri-cereal-production` | `province-crop` | composite `province__crop` (ADR-0018) |
| Table 2.2 | `agri-cashcrop-{area,production,yield}` | `province-crop` | oilseed/sugarcane/potato × 7 provinces |
| Table 7.2 | `agri-vegetable-{area,production,yield}` | `province` | 7 provinces |

### District cross-section (FY 2080/81) — every extractor reconciles to national

| Section | Base slug | Dimension | Notes |
|---|---|---|---|
| Table 1.3 | `agri-cereal-{area,production,yield}` | `district` | all 77 districts (aggregate cereal) |
| Table 1.5 | `agri-cereal-{area,production,yield}` | `district-crop` | maize + wheat × 77 districts |
| Table 2.3 | `agri-cashcrop-{area,production,yield}` | `district-crop` | oilseed/sugarcane/potato × 77 districts |
| Table 4.3 | `agri-livestock-population` | `district-livestock-category` | 7 categories × 77 districts |
| Table 4.5 | `agri-livestock-production` | `district-livestock-product` | 6 meat types × district |
| Table 4.6 | `agri-livestock-production` | `district-livestock-product` | laying birds + egg production × district |
| Table 4.7 | `agri-livestock-production` | `district-livestock-product` | wool (+ wool-flock sheep) × district |
| Table 9.2 | `agri-fertilizer-sales` | `district-fertilizer-type` | grand-total urea/dap/potash × district |

District composites use `district__member` `dimension_value` (ADR-0018). A
distinct `dimension_kind` per table keeps district rows from colliding with the
national series that shares the same `base_indicator_slug`.

**Unit semantics** (ADR-0011, read off the source headers): area = `hectare`;
production = `metric_tonne`; yield = `metric_tonne_per_hectare`; livestock
population = `number`; eggs = `thousand_units`; wool = `kg`; fertilizer =
`metric_tonne`. The pulses table header mislabels yield "Kg./Ha" but the printed
values are Mt/Ha (production ÷ area), so they are stored as
`metric_tonne_per_hectare`.

## Reconciliation (verified at parse time)

- Province cereal-production sums equal the national series per crop (Δ ≤ 1, rounding).
- **Every district extractor sums to the national total** (the gate for keeping it):
  cereal aggregate 11,293,843 vs 11,293,841; maize 3,193,873 vs 3,193,869; cattle
  5,198,388 (exact); fowl 56,916,567 (exact); meat-buffalo 138,271; eggs-total
  1,645,407; wool 389,742; urea 259,542 (exact); dap 184,046 (exact).
- Tables whose district sums did NOT reconcile (e.g. Table 1.6 buckwheat ≈ 76 %
  of national, due to mid-row column collapse) are deferred, not emitted.

## Provenance

- Confidence default: **B** — MoALD compiles from provincial/local administrative
  reports; not independently audited (cf. FCGO/customs grade A).
- License: gov_open
- Reporting period type: annual

## Still deferred after v0.3.0 (documented, not silently dropped)

Source layout not reliably reconstructable from the text layer (would fail the
reconciliation gate):

- **Table 1.6** (millet/buckwheat/barley by district): minor-cereal column
  collapses to a single `0.00` mid-row, breaking positional alignment.
- **Table 3.2** (pulses by district): crops omitted in some rows, dash-filled in
  others — positionally ambiguous.
- **Table 2.13** (spices) / **2.4** (oilseed by commodity): rotated headers
  and/or the same omitted-vs-dashed sparse-column ambiguity as 3.2.
- **Tables 6.2–6.4** (fruit by district): rotated headers + 4-col-per-fruit
  sparse layout. **7.3** (vegetables — 40-pp. transpose).
- **Table 8.2** (population by district) — overlaps `cbs-nphc-2021`.

(Table 2.3 cash crops had a collapsing column too but ships — its sparse column
is a single middle crop bracketed by two near-universal ones, so it reconciles.)

Republish another agency's data — **cross-reference only, NOT ingested**, per
[ADR-0026](../decisions/0026-agri-stats-overlapping-tables-cross-reference-only.md):

- **Macro GDP/GVA** (10.x) — NSO national accounts (held via Economic Survey).
- **Trade by HS code** (11.x) — Customs (held via `customs-monthly-trade`).
- **Agri loans by sector** (14.x) — NRB (held via NRB banking statistics).
- Low priority: seed balance (12.x), insurance (13), commodity→Agri-GVA (15).

## Parser

- Path: `scrapers/moald_agri_stats/parser.py`
- Version: 0.3.0 (anchor-driven; identical output on full PDF + fixture)
- Fixture: `scrapers/moald_agri_stats/tests/fixtures/agri_stats_2080_81_excerpt.pdf` (28 pages)
- Tests: 66 passing

## Archive policy

Files stored in `Financial Data/moald_agri_stats/` (local filesystem per ADR-0006).
Filename convention: `StatInfo_AgriNepal_<FY_BS>.pdf` (e.g. `StatInfo_AgriNepal_2080_81.pdf`).

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
