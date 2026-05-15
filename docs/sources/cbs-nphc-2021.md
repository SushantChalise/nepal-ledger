# Source: CBS National Population & Housing Census 2021 (NPHC 2021)

**source_id:** `cbs-nphc-2021`
**Status:** Active (first batch ingested; 84 CSVs remain — see follow-up brief)
**Last verified:** 2026-05-14

## What this is

The decennial population & housing census of Nepal published by the Central
Bureau of Statistics. The corpus comprises 89 palika-grain cross-tab CSVs
(23 household + 66 individual), 7 palika-grain "Listing" XLSX/XLS tables,
and 1 ward-grain DEGURBA XLSX. See the canonical audit at
[docs/research/cbs-nphc-2021-audit.md](../research/cbs-nphc-2021-audit.md).

## Publication

- URL: https://censusnepal.cbs.gov.np/ (CBS NPHC 2021 microsite)
- Frequency: decennial (next: 2031)
- Format: CSV (89 palika cross-tabs) + XLSX (Listing tables + DEGURBA)
- Reporting period: census reference moment, mid-2021 AD (Asar end BS 2078)

## What we extract (first batch)

Five representative CSVs, chosen to exercise both header layouts and three
indicator families:

| CSV stem                    | Mode | Family                  | Why in batch |
|-----------------------------|------|-------------------------|-------------|
| `Hhld01_OwnershipOfHouse`   | A    | `household_housing`     | Canonical Mode-A title-preamble file |
| `Hhld02_FoundationOfHouse`  | A    | `household_housing`     | Mode-A with a wider value block (5 cols vs 4) |
| `Hhld05_FloorOfHouse`       | B    | `household_housing`     | Mode-B baseline; widely-cited in the audit |
| `Hhld10_HouseholdFacility`  | B    | `household_facility`    | Mode-B with the widest Hhld value block (17 cols) including the `x_NoFacility` / `atleastOne` aggregate columns |
| `Indv01_PopulationBySex`    | B    | `individual_demographic`| Mode-B with a totally different schema (no `rowtotal` / `a_*` cols) — proves the parser doesn't hard-code the Hhld shape |

Each CSV's palika rows (`gapa != 0 AND dist != 0 AND prov != 0`) are
exploded across the per-table value columns into rows in `census_facts`.
Aggregate rows (NEPAL / province / district totals) are skipped — they
belong in roll-up views, not the fact table.

## Provenance

- Confidence default: A (CBS is the highest-tier source for
  population/housing facts).
- License: Government of Nepal open data; no explicit license file shipped
  with the corpus. Treat as public-domain for downstream editorial.
- PII: None. All values are aggregate counts/percentages at province /
  district / palika grain (ward grain only in DEGURBA).

## Parser

- Path: `scrapers/cbs_nphc/parser.py`
- Reader: `scrapers/cbs_nphc/two_mode_reader.py` (auto-detects layout)
- Version: 0.1.0
- Output contract: `CensusFactDraft` (see parser docstring) — distinct from
  the time-series `StagingRowDraft` used by indicator parsers because
  census facts have no time dimension.
- Tested against: `scrapers/cbs_nphc/tests/fixtures/*.csv` (5 trimmed
  fixtures, 3 data rows each).
- Owner: Worker P3 (initial); Mother Opus going forward.

### Two-mode reader

The 89 CSVs come in two header layouts. The reader inspects the first raw
line:

- Mode A (4 files, `Hhld01..Hhld04`): starts with `,,,` AND contains
  `"Table ` — skip 5 prelude rows, header is row 5, data begins row 6.
- Mode B (85 files, everything else): clean row-0 header.

### Municipality resolution

CBS `gapaname` values are mapped to the canonical 8-digit federal code via
`scrapers/_common/municipality_resolver.py`. The audit's Appendix-A list of
27 CBS-vs-MoF spelling drifts is pre-rewritten through `_GAPANAME_OVERRIDES`
in the parser BEFORE the fuzzy resolver runs, so the resolver only sees
high-confidence inputs. Unresolved rows are emitted as
`MunicipalityUnresolved` errors and skipped — no federal codes are
fabricated.

## Known breakage modes

- `header-row-position-shifts` — Mode-A files might in future migrate to
  clean headers (or vice versa). The two-mode reader handles this
  automatically; the test suite locks in the detection rule.
- `gapaname-spelling-drift` — A future CBS revision could introduce a new
  spelling that bypasses both the override map and the resolver's HIGH
  threshold. The parser surfaces such rows as errors rather than silently
  skipping them.

## Revision policy

CBS rarely revises census data after publication; revisions, if any, would
ship as a numbered re-release (e.g. `*_rev1.0` — already seen on Listing05
and Listing06). The parser keys on `(entity_id, indicator_slug,
census_year_ad)`; re-running ingestion with the same CSV is idempotent via
`ON CONFLICT DO NOTHING`.

## Archive policy

- Source files are stored in Supabase Storage bucket `source-archive` (per
  [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md)) under
  key `cbs-nphc-2021/<yyyy-mm-dd>/<original-filename>`.
- Hash + download URL recorded in `source_documents`.

## Next batches

See [docs/tasks/worker-P3-followup-census-batches.md](../tasks/worker-P3-followup-census-batches.md)
for the schedule of the remaining 84 CSVs grouped by topic.
