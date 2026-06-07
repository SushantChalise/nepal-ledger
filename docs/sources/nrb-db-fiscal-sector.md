# Source: Nepal Rastra Bank — Database on Nepalese Economy (Fiscal Sector)

**source_id:** `nrb-db-fiscal-sector`
**Status:** Paused
**Tier:** Tier 1
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's Database on Nepalese Economy — Fiscal Sector provides XLSX time-series covering government
revenue, expenditure, and outstanding public debt compiled from MoF data. Key datasets include
a daily government revenue and expenditure series, monthly government budgetary operations, and
monthly outstanding government debt. These populate the Money Out and Money Wasted pillars.
Confidence is B because NRB compiles these figures from MoF; preliminary values are revised monthly.

## Publication

- URL: https://www.nrb.org.np/database-on-nepalese-economy/fiscal-sector/
- Frequency: monthly (core); daily available for revenue/expenditure
- Expected window: files updated in-place; no fixed release date announced
- Format: xlsx

## What we extract

- `govt-revenue-expenditure-daily` — Daily preliminary government revenue and expenditure (NPR billion)
- `govt-budgetary-operation-monthly` — Monthly budget execution against appropriation
- `govt-revenue-monthly` — Monthly revenue by head
- `outstanding-govt-debt-monthly` — Domestic + external debt stock (NPR billion)

## Provenance

- Confidence default: B (NRB compiles from MoF; preliminary figures revised)
- License: gov-open
- Reporting period type: monthly

## Known breakage modes

- `upload-url-embeds-date-not-hardcodeable` — All XLSX download URLs embed the upload date
  (`/contents/uploads/<year>/<month>/`). File paths change with each update cycle. Parser must
  scrape the sector page to resolve the current download link.
- `nrb-compiles-from-mof-preliminary-figures-revised` — Revenue and expenditure figures are
  preliminary; expect revisions in subsequent monthly releases. The parser should record the
  ingest timestamp alongside each value.

## Revision policy

NRB compiles from MoF; preliminary figures revised each subsequent month. Archive each
downloaded file by date; the Fact Ledger pipeline picks the latest non-provisional value per
period and records superseded values in `indicator_revisions`.

## Parser

- Path: `scrapers/nrb-db-fiscal-sector/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-db-fiscal-sector/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-db-fiscal-sector/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
