# Source: MoALD Statistical Information on Nepalese Agriculture

**source_id:** `moald-agri-stats`
**Status:** Active
**Tier:** 3
**Agency:** Ministry of Agriculture and Livestock Development (MoALD)
**Registered at:** 2026-06-11

## What this is

Annual compendium of Nepalese agricultural statistics published by MoALD. Contains
time-series data on cereal crops, cash crops, pulses, other crops, livestock, fisheries,
and agri-inputs (fertilizer). The FY 2080/81 edition covers data up to 2023/24 AD.

Distinct from [`moald-crop-production`](moald-crop-production.md) which is the
seasonal crop bulletin (variable format, Surya OCR required). This publication has
a clean Latin-script text layer suitable for pdfplumber text extraction.

## Publication

- URL: https://moald.gov.np/publication/statistical-information-on-nepalese-agriculture
- Frequency: annual (published in the following fiscal year)
- Format: PDF (clean text layer, no OCR required)
- Archive path: `Financial Data/moald_agri_stats/`

## What we extract

Parser: `scrapers/moald_agri_stats/parser.py` v0.1.0 → `dne_facts` (ADR-0015)

| Section | Pages | Base Indicator Slug | Dimension Kind | Dimension Values | Unit | Years |
|---|---|---|---|---|---|---|
| Table 1.1 | p14 | `agri-cereal-area` | `crop_type` | paddy/maize/millet/buckwheat/wheat/barley | hectare | 11yr |
| Table 1.1 | p14 | `agri-cereal-production` | `crop_type` | (same 6) | metric_tonne | 11yr |
| Table 1.1 | p14 | `agri-cereal-yield` | `crop_type` | (same 6) | metric_tonne_per_hectare | 11yr |
| §1.4 Summary | p9 | `agri-cashcrop-area` | `crop_type` | oilseeds/potato/sugarcane/jute/cotton | hectare | 3yr |
| §1.4 Summary | p9 | `agri-cashcrop-production` | `crop_type` | (same 5) | metric_tonne | 3yr |
| §1.5 Summary | p9–10 | `agri-pulse-area` | `crop_type` | lentil/chickpea/pigeon-pea/black-gram/grass-pea/horse-gram/soyabean/others | hectare | 3yr |
| §1.5 Summary | p9–10 | `agri-pulse-production` | `crop_type` | (same 8) | metric_tonne | 3yr |
| §2.2 Summary | p10–11 | `agri-livestock-production` | `livestock_product` | milk-total/milk-cow/milk-buffalo/meat-total/meat-buffalo/meat-sheep/meat-goat/meat-pork/meat-chicken/eggs-total/eggs-hen/eggs-duck/wool | mixed | 3yr |
| §3 Summary | p11 | `agri-fertilizer-sales` | `fertilizer_type` | urea/dap/potash/total | metric_tonne | 3yr |

**Livestock units:** milk/meat = metric_tonne; eggs = thousand_units; wool = kg

**Table 1.1 note:** The table is titled "Last Ten Years" but covers 11 rows
(AD 2013/14 through 2023/24 inclusive). The BS FY mapping is `AD YYYY → BS (YYYY+57)`.

## Period coverage

- **Table 1.1 (cereal):** BS 2070/71 (AD 2013/14) through BS 2080/81 (AD 2023/24) — 11 years
- **Summary §1.4–§3:** BS 2078/79 / BS 2079/80 / BS 2080/81 — rolling 3-year window

## Provenance

- Confidence default: B (MoALD administrative census of district-level reports; not independently audited)
- License: gov_open
- Reporting period type: annual

## Known issues / deferred

- **§1.5 Pulses:** "Himali bean" row has no FY 2078/79 data — skipped in v0.1.0; deferred to v0.2.0.
- **§1.6 Other Crops:** Fruits/vegetables/spices — sparse rows (Honey, Fish, Mushroom lack area); deferred to v0.2.0.
- **Table 1.2:** Provincial breakdown for FY 2080/81 only — deferred to v0.2.0.
- **Tables 2–15:** District-level, export/import commodity breakdown — out of scope Year 1.

## Parser

- Path: `scrapers/moald_agri_stats/parser.py`
- Version: 0.1.0
- Fixture: `scrapers/moald_agri_stats/tests/fixtures/agri_stats_2080_81_excerpt.pdf` (4 pages)
- Tests: 36 passing

## Archive policy

Files stored in `Financial Data/moald_agri_stats/` (local filesystem per ADR-0006).
Filename convention: `StatInfo_AgriNepal_<FY_BS>.pdf`, e.g. `StatInfo_AgriNepal_2080_81.pdf`.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
