# Source: World Bank / KNOMAD — Bilateral Remittance Estimates

**source_id:** `wb-knomad-bilateral-remittance`
**Status:** Active (parser v0.2.0) — manual upload required; archive.org recovery used for CY2021 fixture
**Tier:** 2
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11

## What this is

The World Bank / KNOMAD Bilateral Remittance Estimates matrix is an annual
Excel file covering remittance flows (in USD millions) between every pair of
countries. It directly fills **Gap 1** in Nepal Ledger's Fact Ledger: NRB's
Balance of Payments data (BPM6) gives Nepal's total remittance inflow but
provides **no corridor breakdown** — it cannot distinguish India from Gulf or
Malaysia flows. KNOMAD fills this gap with per-corridor bilateral estimates
derived from the IMF Balance of Payments database, central bank reports, and
World Bank staff modelling.

The matrix is published once per year, typically in June. KNOMAD (the Global
Knowledge Partnership on Migration and Development) was hosted by the World
Bank; as of 2024 the dataset continues to be updated under World Bank auspices.

## Publication

- URL: https://www.knomad.org/data/remittances
- Alternate page: https://www.worldbank.org/en/topic/migration/brief/remittances-knomad
- Frequency: annual (typically released in June, covering the prior calendar year)
- Expected window: June of year Y+1 for calendar year Y data
- Format: xlsx
- **Authentication required:** The KNOMAD site requires a login/account to
  download the bilateral Excel. Use `ingestion_mode: manual_upload` — a human
  must download and supply the file.

## What we extract

Nepal column (remittances received BY Nepal FROM each source country):

- `knomad-remittance-to-nepal-from-india-annual` — India corridor (USD million)
- `knomad-remittance-to-nepal-from-qatar-annual` — Qatar corridor (USD million)
- `knomad-remittance-to-nepal-from-uae-annual` — UAE corridor (USD million)
- `knomad-remittance-to-nepal-from-saudi-arabia-annual` — Saudi Arabia corridor (USD million)
- `knomad-remittance-to-nepal-from-kuwait-annual` — Kuwait corridor (USD million)
- `knomad-remittance-to-nepal-from-bahrain-annual` — Bahrain corridor (USD million)
- `knomad-remittance-to-nepal-from-oman-annual` — Oman corridor (USD million)
- `knomad-remittance-to-nepal-from-malaysia-annual` — Malaysia corridor (USD million)
- `knomad-remittance-to-nepal-from-usa-annual` — USA corridor (USD million)
- `knomad-remittance-to-nepal-from-australia-annual` — Australia corridor (USD million)
- `knomad-remittance-to-nepal-from-japan-annual` — Japan corridor (USD million)
- `knomad-remittance-to-nepal-from-korea-annual` — South Korea corridor (USD million)
- `knomad-remittance-to-nepal-total-annual` — Total inflow to Nepal (World row, USD million)

## Provenance

- Confidence default: A (World Bank methodology, IMF BOP data + staff modelling)
- License: public-domain / gov-open (World Bank Open Data policy)
- Reporting period type: annual (calendar year Jan–Dec)
- Ingestion mode: `manual_upload` (annual, user downloads from KNOMAD page)

> **Calendar year vs. Nepal fiscal year:** KNOMAD publishes calendar-year
> (Jan–Dec) estimates. Nepal's fiscal year runs Shrawan–Ashadh (mid-July to
> mid-July). The parser maps AD year Y to BS FY (Y+57)/(Y+58)%100 as an
> approximation and records the calendar-year nature in `parser_notes`. The TS
> validation layer applies a loose tolerance (±1 FY) for cross-checks against
> NRB BOP data.

## Cross-validation hooks

- `knomad-remittance-to-nepal-total-annual` (USD million) ↔
  `dne-remittance-inflow` (NPR million, via NRB BOP BPM6) — unit-convert using
  NRB exchange rate of that FY. Expect ~10–15% gap due to calendar-year vs.
  FY misalignment and methodological differences.
- India corridor magnitude check: KNOMAD India→Nepal typically exceeds any
  single Gulf corridor but may be understated (informal hawala channels). Flag
  if India corridor < 20% of total (implausible given labour migration data).

## Known breakage modes

- `url-changes-annually` — The KNOMAD bilateral Excel URL embeds the release
  year and month (e.g. `sites/default/files/2024-06/bilateralremittancematrix2024.xlsx`).
  Each year the path changes. The parser infers the year from the filename.
- `nepal-column-name-may-vary` — The Nepal column header may appear as "Nepal",
  "Nepal, Fed. Dem. Rep.", or similar. The parser matches on `"nepal"` substring
  (case-insensitive).
- `site-requires-login` — As of 2026-06-11, the KNOMAD site returns HTML (login
  redirect) for all direct file downloads, even for previously-working URLs.
  Manual authenticated download is required; automated scraping is blocked.
- `sheet-name-may-vary` — Sheet name has been observed as "Bilateral_Remittance"
  and "Bilateral_Remittance_Estimates". Parser matches on `"bilateral"` substring.
- `values-may-be-blank-for-small-corridors` — Some country pairs have `None`
  cells (suppressed or zero). Parser skips `None` values silently.

## Revision policy

KNOMAD publishes revised matrices; prior years are updated in-place on the
KNOMAD page. Each downloaded file should be archived with its download date
in the storage key. Historical values are treated as provisional until a
subsequent year's release confirms them.

## Parser

- Path: `scrapers/wb_knomad_bilateral/parser.py`
- Version: 0.2.0
- Owner: Mother Opus
- Tested against: synthetic XLSX fixture () AND real CY2021 fixture ()

## Archive policy

- All downloaded files stored in local filesystem archive
  (see [ADR-0006](../decisions/0006-db-storage-local-postgres.md)) under key
  `wb-knomad-bilateral-remittance/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once  is wired to a monitoring view._

### CY2021 fixture recovery (2026-06-11)

- Source: archive.org snapshot 20230804120528 of KNOMAD Dec-2022 release
- File:  (301 KB)
- Sheet:  (single sheet, no "bilateral" in name — parser uses single-sheet fallback)
- Header structure: row 0 = title "Bilateral Remittance", row 1 = country headers (parser v0.2.0 scans up to 5 rows)
- Nepal column: index 136 of 217 columns
- India→Nepal: 1,583.40 USD million
- Total Nepal inflow (World row): 8,203.26 USD million
- FY mapping: CY2021 → BS FY 2078/79
