# Source: Ministry of Finance / NNRFC — Intergovernmental Fiscal Transfer

**source_id:** `mof-intergovernmental-fiscal-transfer`
**Status:** Active (FY 2082/83 ingestable as-is; prior FYs require Surya OCR)
**Last verified:** 2026-05-14

## What this is

The annual fiscal-transfer allocations from the federal government to Nepal's 753 local governments + 77 districts. Published by the Ministry of Finance, allocations are determined by the National Natural Resources & Fiscal Commission (NNRFC) per the fiscal-federalism law.

Eight grant categories per the standard chart of accounts:
1. **Equalization Grant** — Minimum (26331-min) + Formula-Based (26331-form) + Performance-Based (26331-perf)
2. **Conditional Grant** — Current (26332) + Capital (26336)
3. **Special Grant** — Current (26333) + Capital (26337)
4. **Complementary Grant** — Capital (26334)

This is the **spine of Vertical 10 (Local Ledger / Budget Watch)** and **District MRI** Pulse tiles.

## Publication

- URL: <https://mof.gov.np/intergovernmental> (parent index — annual release per FY)
- Frequency: Annual (each FY's allocations published around the budget release in Asar)
- Expected window: Late Asar / early Shrawan (June–July)
- Format: PDF (historical) + XLSX (recent, sometimes)

## On-disk corpus

| File | FY | Format | Notes |
|------|----|---|---|
| `Cleaned/Fiscal Transfer_2082_82.xlsx` | 2082/83 | XLSX | Pre-cleaned; 990 rows = 753 local levels + 77 districts + aggregates; canonical local-level table; English + Nepali names |
| `intergovernmental/208283.pdf` | 2082/83 | PDF | Original; will be OCR'd to validate Cleaned/ |
| `intergovernmental/208182.pdf` | 2081/82 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/208081.pdf` | 2080/81 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/207980.pdf` | 2079/80 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/207879.pdf` | 2078/79 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/207778.pdf` | 2077/78 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/207677.pdf` | 2076/77 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/207576.pdf` | 2075/76 | PDF | Requires Surya OCR (Phase B1) |
| `intergovernmental/207475.pdf` | 2074/75 | PDF | Requires Surya OCR (Phase B1); FIRST year after federal restructuring |

## What we extract

- `fiscal-transfer-equalization-minimum`
- `fiscal-transfer-equalization-formula-based`
- `fiscal-transfer-equalization-performance-based`
- `fiscal-transfer-conditional-current`
- `fiscal-transfer-conditional-capital`
- `fiscal-transfer-special-current`
- `fiscal-transfer-special-capital`
- `fiscal-transfer-complementary-capital`

One row per `(local_level_entity_id, fiscal_year_bs, grant_type)`. Schema target: `local_government_fiscal_transfers` (migration 0002).

## Provenance

- Confidence default: **A** (MoF official allocations, legally binding)
- License: gov_open
- Reporting period type: annual (FY = Shrawan–Ashadh)

## Known breakage modes

- Local-level codes occasionally change (mergers, name changes — federal restructure). The canonical 753-row table from FY 2082/83 serves as the matching reference for prior years.
- PDF tables are dense; Surya OCR needed for prior-FY ingestion per ADR-0008.
- Devanagari numerals routinely appear alongside Arabic in the same row. Worker ε's `devanagari_normalization.py` handles both losslessly.
- Municipality name variants between MoF and EC sources — `_common/municipality_resolver.py` (Worker ε) bridges with rapidfuzz scoring.

## Revision policy

NNRFC sometimes revises mid-year allocations (special grant top-ups, formula recomputation). Each FY's published allocation is the "approved budget" snapshot; mid-year revisions are tracked as supplementary entries when published.

## Parser

- Path: `scripts/ingest-fiscal-transfer-canonical.ts` (XLSX path; Mother-owned)
- Path (PDF path, Phase B1): `scrapers/mof_intergovernmental/parser.py` (TBD — Surya OCR)
- Version: 0.1.0 (XLSX path, FY 2082/83 confirmed)
- Owner: Mother Opus + (TBD Worker for prior-FY OCR)

## Archive policy

Files at `Financial Data/mof_documents/intergovernmental/` and `Financial Data/mof_documents/Cleaned/` (gitignored). Each FY's source PDF/XLSX hashed and mirrored to Supabase Storage on ingest.

## Recent ingests

FY 2082/83 ingest staged at `staging-data/fiscal-transfer-canonical/fy-2082-83.json`. 753 local levels + 77 districts + 7 provinces confirmed. Awaiting `pnpm exec tsx scripts/apply-all.ts` to land in production.
