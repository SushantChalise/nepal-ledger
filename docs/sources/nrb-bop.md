# Source: Nepal Rastra Bank — Historical Balance of Payments (BPM5)

**source_id:** `nrb-bop`
**Status:** Active
**Tier:** Tier 1
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11

## What this is

NRB's historical Balance of Payments back-series, compiled under **BPM5 methodology**,
covering FY2000/01 → FY2023/24P. Hosted in the `Financial Data/nrb_dne_historical/`
corpus under the filename `Trade-and-Balance-of-Payments.xlsx` (sheet `BOP 2000-`).

This is **distinct from the current BPM6 series** (`Balance-of-Payments-BPM6.xlsx`,
source `nrb-dne-xlsx`). The two series are **not directly comparable** — NRB adopted
BPM6 from approximately FY2069/70 (AD 2012/13). Any visualisation that joins both
series **must show a methodology break** at that boundary.

The parser promotes a single series: Workers' remittances (BPM5 concept), emitted as
`remittance-inflow-bpm5`, annual (one row per fiscal year).

> **Overlap note.** The BPM5 back-series extends through FY2023/24P, which overlaps
> with the BPM6 series (FY2022/23–FY2024/25). The values happen to match closely
> (NRB appears to update both). They are kept as separate indicators so consumers can
> choose which methodology to use and so the break is always visible.

## Publication

- File: `Financial Data/nrb_dne_historical/Trade-and-Balance-of-Payments.xlsx`
- Sheet: `BOP 2000-`
- Also in the same directory: `Balance-of-Payments-BPM5.xlsx` (monthly cumulative
  panel for the same BPM5 era — deferred; annual series from this file is sufficient
  for back-series extension).
- Format: xlsx (structured annual panel; no PDF extraction needed)
- Frequency: static historical corpus (no scheduled release)
- Expected release window: n/a — static file; update when NRB publishes a new edition

## What we extract

| Indicator slug | Row label | Unit |
|---|---|---|
| `remittance-inflow-bpm5` | `Workers' remittances` | `npr_million` |

The `Workers' remittances` row corresponds to the "Current transfers: credit → Workers'
remittances" line in the BPM5 current-account framework. Under BPM6 this concept maps
approximately to "Personal transfers (1.C.2.1) Credit" — but the two are NOT
interchangeable without a BPM5→BPM6 reconciliation pass (deferred).

Other BoP lines in the sheet (Goods, Services, Capital Account, Financial Account) are
NOT promoted by this parser (ADR-0014: no catalogue pollution).

## Coverage

| FY (AD) | FY (BS) | Note |
|---|---|---|
| 2000/01 | 2057/58 | — |
| … | … | — |
| 2021/22 | 2078/79 | Revised (R suffix) |
| 2022/23 | 2079/80 | Revised (R suffix) |
| 2023/24 | 2080/81 | Provisional (P suffix) |

## Methodology break

NRB adopted BPM6 from approximately FY2069/70 (AD 2012/13). From that year onward the
BPM5 "Workers' remittances" line in this file is a **back-cast** — computed under BPM5
concepts for historical continuity, not the primary BPM6 publication. The authoritative
current series for the remittance inflow is `dne-remittance-inflow` (BPM6, source
`nrb-dne-xlsx`).

**Do not silently splice the two series.** Any time series that spans the break must
carry a discontinuity annotation at FY2069/70.

## Provenance

- Confidence default: B (historical, BPM5 concept, some years provisional/revised)
- License: gov-open (NRB public data)
- Reporting period type: annual

## Known breakage modes

- `two-panel-layout` — the sheet is formatted as two side-by-side panels (years 2000/01–
  2011/12 in columns 3–14; years 2012/13–2023/24P in columns 18–29). Parser scans
  dynamically for the header row and both panel column ranges.
- `formula-precision-in-xlsx` — some cells contain Excel formula results with excessive
  decimal precision (e.g. `665064.3482211164`), not clean round numbers. Values are
  stored as-is; the validation layer rounds to 2 dp for display.
- `revision-suffix-in-year-labels` — year headers carry 'R' (revised) or 'P'
  (provisional) suffixes that must be stripped before FY parsing. Suffixes are captured
  in `parser_notes`.

## Parser

- Path: `scrapers/nrb_bop/parser.py`
- Version: 0.1.0
- Owner: Mother Opus

## Archive policy

Source file archived in-repo at `Financial Data/nrb_dne_historical/`. No Supabase
Storage key required for Year 1 (ADR-0006: local-first storage strategy).
