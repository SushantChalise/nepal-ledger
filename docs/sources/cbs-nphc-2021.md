# Source: CBS — National Population & Housing Census 2021

**source_id:** `cbs-nphc-2021`
**Status:** Active (parser v0.1.0 ships in Worker η output; pending spawn)
**Last verified:** 2026-05-14

## What this is

Nepal's decennial National Population & Housing Census conducted by the Central Bureau of Statistics in 2021 (BS 2078). The most authoritative dataset for:
- Population per municipality (and ward, in the DEGURBA Excel only)
- Household composition (ownership, materials, facilities, fuel, lighting, water, toilet)
- Demographic structure (sex, age, marital status, disability, literacy)
- Education (level, field, school attendance)
- Migration (absent population by country, reason, length-of-stay)
- Fertility (children-ever-born)
- Economic (occupation, industry, employment status, work-month)

97 source files: 89 CSVs + 8 Excel.

This is the **demographic spine** for:
- Vertical 17 (Household Ledger) — household composition / income / spending archetypes
- District MRI — per-municipality population + literacy + education + occupation
- Vertical 13 (Soil Economy) — agriculture-by-municipality household counts
- Vertical 15 (Migration Industry) — absent-population breakdowns

## Publication

- URL: <https://censusnepal.cbs.gov.np> (or successor URL)
- Frequency: Decennial (next: 2031)
- Format: CSV (89 tables) + Excel (8 tables, including the ward-level DEGURBA)

## On-disk corpus

- `Financial Data/Census/census_2021_data/CENSUS_DATA_INDEX.json` — 244KB metadata index of every file
- `Financial Data/Census/census_2021_data/census-dataset/Hhld[01-23]_*.csv` — household tables
- `Financial Data/Census/census_2021_data/census-dataset/Indv[01-71]_*.csv` — individual tables
- `Financial Data/Census/census_2021_data/household-results/Listing[01-07]_*.xls{x}` — household listing Excel
- `Financial Data/Census/census_2021_data/degurba-report/DegurbaUrbanRural.xlsx` — ward-level urban/rural

Pokhara identifier (per CENSUS_DATA_INDEX.json): `prov=4, dist=40, gapa=4, gapaname='Pokhara Metropolitian City'` (note the typo "Metropolitian" — handled by `_common/municipality_resolver.py` rapidfuzz).

## What we extract (Phase 1 — Worker η v0.1.0)

For each CSV/Excel table, one staging row per (municipality × indicator-slug × value). Indicator family enum:
- `household_housing` (Hhld01–05, Listing01–04)
- `household_facility` (Hhld06–10, Listing06)
- `household_economic` (Hhld11–12, Listing05, Listing07)
- `household_demographic` (Hhld13–23 — death, absent population)
- `individual_demographic` (Indv01–10, Indv16)
- `individual_education` (Indv17–22)
- `individual_migration` (Indv22–32)
- `individual_fertility` (Indv33–48)
- `individual_economic` (Indv49–68)

Phase 2 (parser v0.2.0):
- 2D / 3D breakdown tables (axis × axis)
- DEGURBA ward-level Excel

## Provenance

- Confidence default: **A** (CBS authoritative; decennial census)
- License: gov_open
- Reporting period type: annual (one-time snapshot per census; reference geography)

## Known breakage modes

- CSV "Unnamed: 0..N" headers — title in row 1, real headers around row 4. Needs per-table header-detection pass. Worker η documents the patterns in `scrapers/census/HEADER_PATTERNS.md`.
- Municipality names have transliteration variants vs. MoF's naming (e.g. "Pokhara Metropolitian" with one i). `_common/municipality_resolver.py` rapidfuzz resolves with ≥85 score for high-confidence; ≥70 for medium.
- Some tables have very wide categorical breakdowns (e.g. occupation × industry). Worker η defers these to v0.2.0.

## Revision policy

CBS occasionally publishes corrected tables after the main release. Re-ingest replaces values with `(census_year, indicator_slug)` unique constraint enforcing one canonical row per concept.

## Parser

- Path: `scrapers/census/parser.py` (Worker η pending spawn)
- Version: 0.1.0 target
- Owner: Worker η (Mother subagent)
- Tested against: 5–10 representative tables from each family

## Archive policy

CSVs at `Financial Data/Census/census_2021_data/` (gitignored). Each file's hash + size recorded in `source_documents` on ingest. Mirror to Supabase Storage `source-archive/cbs-nphc-2021/2021/<filename>`.

## Recent ingests

Awaiting Worker η spawn (queued after Worker ζ + Worker δ completion to avoid filesystem contention).
