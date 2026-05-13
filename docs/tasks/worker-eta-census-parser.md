# Worker η — Census 2021 (NPHC) CSV/XLSX Parser

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** soft 500 / hard 700 non-test source lines (large surface — 89 CSVs)

---

## Goal

Parse the 89 CSV + 8 Excel files of CBS National Population & Housing Census 2021 (BS 2078) into staging JSON ready for `census_facts` table ingest.

Done = `pytest -q` green on the new tests; running the parser produces one JSON file per source table at `staging-data/census-2021/<source-table-id>.json`. All 97 source files are accounted for in the output (parsed or explicitly marked "deferred").

## Why

Census 2021 is the demographic spine for:
- Vertical 17 (Household Ledger) — household composition, demographics, education, labour
- District MRI — per-municipality population, literacy, education, occupation
- Vertical 13 (Soil Economy) — agriculture-by-municipality household counts
- Vertical 15 (Migration Industry) — absent-population breakdowns by country/reason

The schema target `census_facts` (per `src/lib/db/schema/census-facts.ts`) is long-format per (entity × indicator × census-year × value). Entity for almost all 89 CSVs is `local_level`; for the DEGURBA Excel it's `ward`.

## Setup state

- Working dir: `C:\Users\ACER\Projects\Economy`
- Branch: create `feat/scrapers-census-2021` from main yourself
- 89 CSVs + 8 Excel at `Financial Data/Census/census_2021_data/`
- `CENSUS_DATA_INDEX.json` (244KB) in the same dir already enumerates every file with description + `pokhara_data_rows` count
- File groupings:
  - `Hhld01_...` → `Hhld23_...` — household-level (housing, facilities, deaths, absent population)
  - `Indv01_...` → `Indv71_...` — individual-level (demographic, education, marriage, migration, fertility, employment, occupation, industry)
  - `Listing01_...` → `Listing07_...` — household listing (building, floor, year of construction, bank account, training, loans)
  - `DegurbaUrbanRural.xlsx` — DEGURBA classification (the ONLY ward-level file)
- `_common/devanagari_normalization.py` + `_common/municipality_resolver.py` shipped by Worker ε at `feat/scrapers-common-utils`. **Cherry-pick that branch** (`git cherry-pick <commit-sha>`) onto your branch so you can use these utils for municipality-name normalization on the CSV's first column.

## CSV shape (you'll need to handle each shape)

Per the `CENSUS_DATA_INDEX.json` sample, CSVs have "Unnamed: 0..N" columns with the table title in row 1. Concretely:

- Row 1: table title (e.g. "Table 01: Number of households by type of ownership of housing unit, NPHC 2021")
- Row 2: column header section names
- Row 3: column sub-headers
- Row 4: pandas-parsed header — usually still header
- Row 5+: data rows, one per municipality

**Schema discovery FIRST**: sample 5–10 distinct CSVs (one from each Hhld/Indv/Listing group) and identify the actual table-start row pattern. Document the pattern in `scrapers/census/HEADER_PATTERNS.md`.

## Parser shape

`scrapers/census/parser.py`:

```python
PARSER_VERSION = "0.1.0"
SOURCE_ID_PREFIX = "cbs-nphc-2021"

def parse_csv(source_csv_path: str, source_table_id: str) -> ParserResult:
    """Parse one of the 89 census CSVs. source_table_id is the filename
    without extension, e.g. 'Hhld01_OwnershipOfHouse'."""
    ...

def parse_degurba_excel(path: str) -> ParserResult:
    """Special case: DegurbaUrbanRural.xlsx is ward-level."""
    ...

def parse_listing_excel(path: str, source_table_id: str) -> ParserResult:
    """Listing01–07 Excel files."""
    ...
```

Each produces a stream of `StagingCensusRowDraft`:

```python
@dataclass(frozen=True)
class StagingCensusRowDraft:
    entity_resolver_input: str         # raw municipality name from CSV
    resolved_federal_code: str | None  # 8-digit local-level code, if matched
    entity_kind: Literal['local_level', 'ward']
    indicator_family: str              # household_housing | individual_education | ...
    indicator_slug: str                # e.g. 'household-owned' / 'literate-female-15plus'
    value: float
    unit: str                          # 'households' | 'persons' | 'percent' | ...
    source_table_id: str               # filename stem
    confidence_grade_proposed: ConfidenceGrade
    parser_notes: str | None = None
```

## Staging output

One JSON per source table at `staging-data/census-2021/<source-table-id>.json`:

```json
{
  "source_file": "Financial Data/Census/census_2021_data/census-dataset/Hhld01_OwnershipOfHouse.csv",
  "source_hash_sha256": "...",
  "source_bytes": 12345,
  "source_table_id": "Hhld01_OwnershipOfHouse",
  "indicator_family": "household_housing",
  "parser_version": "0.1.0",
  "row_count": 753,
  "rows": [
    {
      "entity_resolver_input": "Kathmandu Metropolitan City",
      "resolved_federal_code": "30101001",
      "entity_kind": "local_level",
      "indicator_slug": "household-owned",
      "value": 158724,
      "unit": "households",
      "confidence_grade_proposed": "A"
    }
  ]
}
```

## Critical implementation notes

1. **Municipality resolution.** Use `_common/municipality_resolver.resolve_municipality()` to resolve raw names to canonical 753-local-level entities. The CBS NPHC uses different transliterations than the MoF fiscal-transfer XLSX (e.g. "Pokhara Metropolitian City" vs "Pokhara Metropolitan City"). Threshold-based matching with the fuzzy resolver handles this.

2. **Indicator-slug naming.** Deterministic + descriptive. Pattern: `<family-prefix>-<axis-1>-<axis-2>`. E.g.:
   - `household-ownership-owned` (Hhld01)
   - `household-cooking-fuel-lpg` (Hhld07)
   - `population-literate-female-15plus` (Indv17)
   Document the slug taxonomy in `scrapers/census/SLUG_TAXONOMY.md`.

3. **Indicator family** values must match `census_indicator_family` enum:
   `household_housing | household_facility | household_economic | household_demographic | individual_demographic | individual_education | individual_economic | individual_migration | individual_fertility`.
   Map each source table to its family in `scrapers/census/FAMILY_MAPPING.md`.

4. **Some CSVs have unusual shapes.** E.g. tables with breakdown axes that explode rows. For v0.1.0, focus on:
   - Total counts (single value per municipality)
   - Single-axis breakdowns (e.g. count by sex)
   Defer 2D and 3D tables (axis × axis) to v0.2.0 — write the parser scaffolding but mark them "deferred" in the `FAMILY_MAPPING.md` table.

5. **DEGURBA Excel is ward-level.** The municipality resolver is for local-level; ward resolution needs the 8-digit-plus-ward-number lookup. For v0.1.0, defer DEGURBA — note in handoff.

6. **Listing01–07 Excel files** are also at municipality (palika) level per filename. Parse with the same approach as CSVs.

## Acceptance criteria

- [ ] Files only in `scrapers/census/` + `staging-data/census-2021/` (gitignored)
- [ ] `cd scrapers && pytest -q` — existing 79 + new tests pass
- [ ] `ruff check scrapers/census/` clean
- [ ] `mypy scrapers/census/` clean under strict
- [ ] Schema-discovery doc `scrapers/census/HEADER_PATTERNS.md` with sample of each shape
- [ ] Slug taxonomy doc `scrapers/census/SLUG_TAXONOMY.md`
- [ ] Family mapping doc `scrapers/census/FAMILY_MAPPING.md` with status per source table
- [ ] At least 30 source tables produce staging JSON in v0.1.0; remaining are explicitly marked "deferred"
- [ ] Total `census_facts` row count emitted in your final report
- [ ] Branch `feat/scrapers-census-2021`. Commit message: `feat(scrapers): NPHC 2021 census parser v0.1.0 (Hhld + Indv + Listing tables)`
- [ ] **Use a git stash before any branch switch** — there are other workers in the filesystem. Do NOT `git add -A` — target only `scrapers/census/` + `staging-data/census-2021/`. The Worker ε report flagged this defensive pattern; follow it.

## What to return

≤15-bullet summary including:
- Number of source tables parsed in v0.1.0 vs deferred
- Per-family row counts
- Municipality-resolution stats: how many distinct municipality names did you encounter, how many resolved with ≥85 score, how many fuzzy ≥70, how many unmatched
- DEGURBA status (deferred or attempted)
- The slug taxonomy doc URL/path
- Any source CSVs that completely failed to parse (file-level failures)
- Commit SHA on `feat/scrapers-census-2021`

Begin.