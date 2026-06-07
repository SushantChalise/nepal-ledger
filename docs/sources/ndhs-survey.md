# Source: Ministry of Health and Population — Nepal Demographic & Health Survey

**source_id:** `ndhs-survey`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

The Nepal Demographic and Health Survey (NDHS), conducted approximately
every five years by the Ministry of Health and Population in collaboration
with ICF International (DHS Program). Provides nationally representative
data on fertility, child mortality, maternal health, nutrition, and
family planning. Referenced as a health-outcomes benchmark under the
"Where Money Becomes Wealth" pillar; not parsed into
`approved_indicator_values` (ingestion mode: reference_only).

## Publication

- URL: https://mohp.gov.np/
- Frequency: ad_hoc (quinquennial)
- Expected window: TBD
- Format: pdf

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.
  Notes from seed: "Health reference."

## Provenance

- Confidence default: A
- License: gov_open
- Reporting period type: annual
- Historical coverage: Quinquennial

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
  under key `ndhs-survey/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
