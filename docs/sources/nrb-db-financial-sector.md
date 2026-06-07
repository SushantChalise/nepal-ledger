# Source: Nepal Rastra Bank — Database on Nepalese Economy (Financial Sector)

**source_id:** `nrb-db-financial-sector`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's Database on Nepalese Economy — Financial Sector provides approximately 40 XLSX datasets
covering BFI assets, deposits, loans (sector-wise and security-wise), monetary survey, interest
rate structure, electronic payment transactions, and NEPSE index/market cap. Core datasets are
monthly; liquidity and NEPSE are daily. These feed the Money Captured pillar. The sector-wise
loan data is a clean XLSX alternative to the complex multi-block BFI monthly XLSX corpus and
should be reconciled with `nrb-bfi-monthly-xlsx` before a separate parser is written.

## Publication

- URL: https://www.nrb.org.np/database-on-nepalese-economy/financial-sector/
- Frequency: monthly (core); daily (liquidity/NEPSE)
- Expected window: files updated in-place; no fixed release date announced
- Format: xlsx

## What we extract

- `bfi-loans-sector-wise-monthly` — Loans and advances by economic sector (NPR billion)
- `monetary-survey-monthly` — Money supply (M1, M2, reserve money)
- `interest-rate-structure-monthly` — Weighted average lending/deposit rates by BFI class
- `bfi-assets-liabilities-monthly` — Total assets and liabilities of BFIs
- `bfi-deposits-monthly` — Deposit mobilization by BFI class
- `electronic-payments-monthly` — Volume and value of digital payment transactions
- `nepse-index-daily` — NEPSE composite index and total market capitalization

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: monthly

## Known breakage modes

- `upload-url-embeds-date-not-hardcodeable` — All XLSX download URLs embed the upload date.
  Parser must scrape the sector page to enumerate all current dataset download links.
- `approx-40-datasets-parser-must-enumerate-all` — ~40 datasets in this sector; the parser
  must enumerate all links from the sector page rather than hardcoding individual URLs.
- `electronic-payment-transactions-structural-break-when-new-payment-rails-introduced` — The
  electronic payments dataset may contain structural breaks at dates when new payment rails
  (QR, mobile banking) were introduced; handle as a series discontinuity, not a data error.

## Revision policy

Files are updated in-place. No explicit revision policy documented by NRB. Treat each downloaded
file as a full historical snapshot; archive with the download date in the storage key.

## Parser

- Path: `scrapers/nrb-db-financial-sector/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-db-financial-sector/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-db-financial-sector/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
