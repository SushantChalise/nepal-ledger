# Source: Asian Development Bank — Asian Development Outlook (Nepal)

**source_id:** `adb-ado-nepal`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

ADB's flagship regional economic outlook publication covering the Nepal section.
Provides GDP growth projections, inflation, current-account, and fiscal-balance
forecasts alongside historical outturns. Referenced in editorial stories as an
international benchmark comparator; not parsed into `approved_indicator_values`.

## Publication

- URL: https://www.adb.org/countries/nepal/economy
- Frequency: annual
- Expected window: TBD
- Format: pdf

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.

## Provenance

- Confidence default: A
- License: cc_by
- Reporting period type: annual

## Known breakage modes

- TBD

## Revision policy

TBD

## Parser

- Path: TBD
- Version: TBD (not yet written — reference_only)
- Owner: TBD
- Tested against: TBD

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `adb-ado-nepal/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
