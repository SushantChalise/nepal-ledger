# Source: Nepal Rastra Bank — Database on Nepalese Economy (Real Sector)

**source_id:** `nrb-db-real-sector`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's Database on Nepalese Economy — Real Sector provides ~22 XLSX datasets covering GDP
(quarterly and national accounts), CPI, agriculture production/inputs, manufacturing production
index, energy, industry, tourism, transportation, and WPI. Quarterly GDP datasets are foundational
for the "Where Money Becomes Wealth" pillar and every per-capita comparison in the Household
Ledger Calculator. Confidence is B because NRB compiles from CBS and MoALD.

**Critical note:** "Quarterly GDP (Old)" and "Quarterly GDP (New)" reflect an incompatible
base-year revision. Parsers must handle these as two separate series and must not concatenate
them without adjustment. Provincial GDP is a separate file.

## Publication

- URL: https://www.nrb.org.np/database-on-nepalese-economy/real-sector/
- Frequency: quarterly (GDP); monthly (CPI, energy); yearly (agriculture, national accounts)
- Expected window: files updated in-place; no fixed release date announced
- Format: xlsx

## What we extract

- `quarterly-gdp-new-series` — Quarterly GDP estimates (revised base year; ~2072 onward)
- `quarterly-gdp-old-series` — Quarterly GDP estimates (old base year — kept for historical backfill only)
- `national-accounts-annual` — Annual GDP by expenditure and production approach
- `provincial-gdp-annual` — Province-level GDP (separate file)
- `cpi-monthly` — Monthly Consumer Price Index (all groups)
- `cpi-annual` — Annual Consumer Price Index (calendar year)
- `manufacturing-production-index-quarterly` — MPI by industry class

## Provenance

- Confidence default: B (NRB compiles from CBS/MoALD; preliminary)
- License: gov-open
- Reporting period type: quarterly (mixed — some datasets monthly, some yearly)

## Known breakage modes

- `upload-url-embeds-date-not-hardcodeable` — All XLSX download URLs embed the upload date.
  Parser must scrape the sector page for current links.
- `quarterly-gdp-old-and-new-series-incompatible-base-year-revision` — Two GDP XLSX files with
  incompatible base years. Parser must tag each row with the series name and refuse to merge
  them without explicit reconciliation logic.
- `provincial-gdp-separate-file` — Provincial GDP is a distinct XLSX, not a sheet in the
  national accounts file. Parser must enumerate it separately.

## Revision policy

NRB compiles from CBS/MoALD; preliminary GDP figures revised as CBS finalizes national accounts.
Historical values may be restated at base-year revisions. Archive each downloaded file by date.

## Parser

- Path: `scrapers/nrb-db-real-sector/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-db-real-sector/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-db-real-sector/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
