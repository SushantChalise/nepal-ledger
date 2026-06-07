# Source: Nepal Rastra Bank — Database on Nepalese Economy (External Sector)

**source_id:** `nrb-db-external-sector`
**Status:** Paused
**Tier:** Tier 1
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's Database on Nepalese Economy — External Sector provides seven monthly XLSX time-series
covering Nepal's balance of payments, foreign exchange reserves, exchange rates, foreign trade,
migrant worker remittances, and tourist arrivals. These are structured XLSX files — no PDF
extraction required — making them the most parse-friendly data in the entire NRB catalog. They
directly feed the Money In and Money Out pillars of Pulse v1.

## Publication

- URL: https://www.nrb.org.np/database-on-nepalese-economy/external-sector/
- Frequency: monthly (key files); yearly editions also available
- Expected window: files updated in-place; no fixed release date announced
- Format: xlsx

## What we extract

- `forex-reserves-monthly` — Gross foreign exchange reserve (NPR + USD)
- `bop-bpm5-monthly` — Balance of Payments (BPM5 methodology)
- `bop-bpm6-monthly` — Balance of Payments (BPM6 methodology)
- `exchange-rate-monthly` — NPR per major currencies (USD, INR, EUR, GBP)
- `foreign-trade-monthly` — Exports + imports (NPR billion)
- `remittance-inflows-monthly` — Migrant worker remittance inflows (NPR billion)
- `tourist-arrivals-monthly` — Arrivals by nationality/mode

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: monthly

## Known breakage modes

- `upload-url-embeds-date-not-hardcodeable` — All XLSX download URLs embed the upload date
  (`/contents/uploads/<year>/<month>/`). File paths change with each update cycle. Parser must
  scrape the sector page to resolve the current download link; hardcoding a static URL will break
  within one month.
- `sector-page-must-be-scraped-for-current-link` — The sector page at the URL above lists the
  current download link for each dataset. This is the reliable extraction target.

## Revision policy

Files are updated in-place at each release cycle. No explicit revision policy documented by NRB.
Treat each downloaded file as a snapshot; archive with the download date in the storage key.

## Parser

- Path: `scrapers/nrb-db-external-sector/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-db-external-sector/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-db-external-sector/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
