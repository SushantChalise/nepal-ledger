# Source: National Statistics Office — Nepal Living Standards Survey (NLSS)

**source_id:** `nlss-survey`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

The Nepal Living Standards Survey (NLSS), a decadal household survey
conducted by the National Statistics Office that measures consumption
expenditure, income sources, poverty, and living conditions at national
and regional levels. Provides the household-level baseline for the
"Household Ledger Calculator" signature utility and poverty/inequality
editorials. Not parsed into `approved_indicator_values` (ingestion mode:
reference_only).

## Publication

- URL: https://nsonepal.gov.np/
- Frequency: ad_hoc (decadal)
- Expected window: TBD
- Format: pdf

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.
  Notes from seed: "Household Ledger reference."

## Provenance

- Confidence default: A
- License: gov_open
- Reporting period type: annual
- Historical coverage: Decadal; last 2010/11, next pending

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
  under key `nlss-survey/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
