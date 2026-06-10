# Source: Public Debt Management Office — Monthly Government Debt Statistics

**source_id:** `pdmo-monthly-debt-statistics`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker B catalog audit)

## What this is

PDMO publishes monthly government debt statistics covering the outstanding stock of domestic
debt (Treasury bills, development bonds, savings certificates) and external (foreign) debt.
This is an active monthly series — Chaitra 2082 (April 2026) is the most recent confirmed
release. It is distinct from the existing quarterly `pdmo-debt-bulletin` and provides finer
cadence for the Borrowed Time vertical's monthly debt-stock monitoring.

## Publication

- URL: https://pdmo.gov.np/pages/monthlyrepo
- Frequency: monthly
- Expected window: Approximately 15th of the following month
- Format: pdf

## What we extract

- `domestic-debt-outstanding-monthly` — Total internal debt stock (T-bills + development bonds + savings certs) (NPR billion)
- `external-debt-outstanding-monthly` — Total foreign debt stock (NPR billion / USD million)
- `total-public-debt-outstanding-monthly` — Combined internal + external debt (NPR billion)
- `debt-to-gdp-ratio-monthly` — Debt-to-GDP ratio if published in the report (%)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: monthly

## Known breakage modes

- `filename-pattern-varies-bs-month-name-nepali-or-english-inconsistent` — PDF filenames
  embed the BS month name in inconsistent transliteration or Nepali text
  (e.g., "2082 chaitra", "Falgun (1)", "GDS Report 2082 Magh"). The downloader must enumerate
  files by navigating the PDMO page rather than constructing expected filenames.

## Revision policy

Monthly. No explicit revision cycle documented by PDMO. Treat each release as the final
figure for that month-end snapshot. Archive each file by download date.

## Parser

- Path: `scrapers/pdmo-monthly-debt-statistics/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/pdmo-monthly-debt-statistics/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `pdmo-monthly-debt-statistics/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
