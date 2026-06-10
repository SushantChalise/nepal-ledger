# Source: Nepal Rastra Bank — NRB Summarized Balance Sheet (Daily)

**source_id:** `nrb-central-bank-balance-sheet-daily`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB publishes a summarized central bank balance sheet for every working day. Each PDF (~38 KB)
shows NRB's assets and liabilities including reserve money, foreign exchange assets, government
securities held, and interbank liquidity injections/withdrawals from open market operations.
This source corrects and supersedes the vague `nrb-reserves-daily` stub — the cadence is
confirmed daily (not weekly as the stub speculated). The daily sheets feed the Pulse interbank
rate tile and validate the Database on Nepalese Economy daily liquidity XLSX.

## Publication

- URL: https://www.nrb.org.np/category/central-bank-survey-and-liquidity-position/?department=red
- Frequency: daily (each working day of each BS month)
- Expected window: Same working day or next working day
- Format: pdf

## What we extract

- `nrb-reserve-money-daily` — Reserve money (monetary base) outstanding (NPR million)
- `nrb-nfa-daily` — Net foreign assets of NRB (NPR million)
- `nrb-nda-daily` — Net domestic assets of NRB (NPR million)
- `nrb-omo-injection-daily` — Open market operation liquidity injection (NPR million)
- `nrb-omo-absorption-daily` — OMO liquidity absorption (NPR million)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: daily

## Known breakage modes

- `page-uses-month-fy-filter-navigation-no-direct-archive-list` — The category page uses
  month + FY filter navigation. No direct archive list is available; the downloader must
  navigate the monthly filter to enumerate working-day PDFs.
- `url-pattern-consistent-red-yyyy-mm-dd-nrb-summarized-balance-sheet` — Individual post
  slugs follow the pattern `/red/YYYY-MM-DD-nrb-summarized-balance-sheet/` (confirmed stable).
  This is the reliable extraction target once the list page yields the slug.

## Revision policy

Daily preliminary sheets. No explicit revision policy documented. A corrected sheet for a given
day may be published the next working day; treat the most recently published sheet for a given
date as the authoritative value and archive both if a correction appears.

## Parser

- Path: `scrapers/nrb-central-bank-balance-sheet-daily/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-central-bank-balance-sheet-daily/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-central-bank-balance-sheet-daily/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Notes

The existing `nrb-reserves-daily` source stub (registered Tier 1, status: paused) covers
overlapping conceptual territory but with incorrect cadence assumption ("may be weekly"). This
source (`nrb-central-bank-balance-sheet-daily`) is the confirmed, correctly-specified entry.
Mother should assess whether to deprecate `nrb-reserves-daily` on the next parser PR.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
