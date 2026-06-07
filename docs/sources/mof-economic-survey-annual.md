# Source: Ministry of Finance — Economic Survey (Annual)

**source_id:** `mof-economic-survey-annual`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

The Ministry of Finance's flagship annual review of Nepal's macroeconomic
performance, published alongside the federal budget each Jestha. Covers
GDP growth, sectoral output, fiscal outturn, monetary developments,
balance of payments, and social indicators. Used as the primary
macro-narrative reference for editorial stories; not parsed into
`approved_indicator_values` (ingestion mode: reference_only).

## Publication

- URL: https://mof.gov.np/
- Frequency: annual
- Expected window: Jestha (May/June), coinciding with budget presentation
- Format: pdf

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.
  Notes from seed: "Macro narrative reference. Not parsed into approved_indicator_values; cited from stories."

## Provenance

- Confidence default: A
- License: gov_open
- Reporting period type: annual

## Known breakage modes

- TBD (likely same CDN pattern as other MoF PDFs: giwmscdnone.gov.np with opaque tokens)

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
  under key `mof-economic-survey-annual/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
