# Source: Nepal Rastra Bank — Banking & Financial Statistics (Monthly XLSX)

**source_id:** `nrb-bfi-monthly`
**Status:** Active (parser v0.1.0 ships in Worker ζ output)
**Last verified:** 2026-05-14

## What this is

The monthly Banking & Financial Statistics XLSX series published by NRB's Bank and Financial Institutions Regulation Department. Each XLSX contains 25 sheets (C1–C25) covering:
- C2 Table of Contents
- C3 Explanatory Notes
- C4 Major Financial Indicators (headline aggregates)
- C5 Statement of Assets & Liabilities (system aggregate balance sheet)
- C6 Profit & Loss Account aggregates
- C7 Sector-wise, Product-wise, Industry-wise Lending (the Vertical-16 spine)
- C8–C25 Per-bank-class breakdowns (commercial / development / finance / microfinance / infrastructure) — including loan-by-purpose, deposit-by-type, NPL-by-sector

49 continuous months on disk (Shrawan 2078 through Bhadau 2082; Aug 2021 → Sept 2025). The full-history columns in every snapshot mean revision detection across snapshots is mandatory.

## Publication

- URL: <https://www.nrb.org.np/category/economic-research/bafia-publications/> (parent category)
- Frequency: Monthly
- Expected window: Around the 25th–30th of the month FOLLOWING the reporting period (latest snapshot reports through "Mid-month" of the previous Nepali month)
- Format: XLSX (one file per monthly snapshot)

## What we extract (Phase 1 — Worker ζ v0.1.0)

- `bfi-c4-*` — Major Financial Indicators (the Pulse headline numbers)
- `bfi-c5-*` — Assets & Liabilities (capital fund paid-up, reserves, retained earnings, deposits, lending, borrowings)
- `bfi-c6-*` — Profit & Loss aggregates (interest income, fee income, operating profit, taxes, net profit)
- `bfi-c7-*` — Sector-wise lending (real-estate, agriculture, hydropower, manufacturing, services, consumption, SME, etc.)

Phase 2 (parser v0.2.0): per-bank breakdowns from C8–C25, NPL-by-sector trend, microfinance + finance company stress signals.

## Provenance

- Confidence default: **A** (NRB official audited monthly publication)
- License: gov_open (Nepal government open-data convention)
- Reporting period type: monthly (snapshot contains historical columns)

## Known breakage modes

- Column count varies across the 49-month span (C8 jumped from ~36 to ~57 columns somewhere in this span). Parser must detect layout version and route accordingly.
- Some XLSX files use "Rs in Million" header; others "Rs in Crore". Unit parsing must read the header, not assume.
- Each snapshot has historical columns; revision detection compares same period across snapshots.

## Revision policy

NRB occasionally restates historical values in subsequent snapshots (typically when prior-period values were provisional). Our pipeline detects revisions by cross-checking the same `(indicator_slug, period_bs)` value across the 49 snapshots; mismatches generate `revision_number+1` rows per DATA_PIPELINE.md §"Revisions".

## Parser

- Path: `scrapers/nrb_bfi/parser.py`
- Version: 0.1.0 (Worker ζ shipped)
- Owner: Mother Opus (subagent)
- Tested against: 3 snapshots — oldest (Shrawan 2078), middle (Asar 2080), latest (Bhadau 2082) for layout-stability discovery

## Archive policy

XLSX files staged at `Financial Data/nrb_monthly_statistics/` (gitignored). Each file's SHA-256 hash + size recorded in `source_documents` when ingested. Mirror to Supabase Storage `source-archive/nrb-bfi-monthly/<yyyy-mm-dd>/<original-filename>` once storage wrapper integrated.

## Recent ingests

Pending live application of migration 0002 + the BFI ingest script (Worker ζ output).
