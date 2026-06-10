# Source: National Planning Commission — 16th Five-Year Plan

**source_id:** `npc-16th-plan`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

The Government of Nepal's 16th Five-Year Plan (FY 2081/82–2085/86),
published by the National Planning Commission. Sets national development
targets across GDP growth, poverty reduction, infrastructure, and social
sectors. Referenced for project-pipeline context and as a policy framework
for editorial analysis; not parsed into `approved_indicator_values`
(ingestion mode: reference_only).

## Publication

- URL: https://npc.gov.np/
- Frequency: ad_hoc (quinquennial plan cycle)
- Expected window: TBD
- Format: pdf

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.
  Notes from seed: "Reference + project pipeline."

## Provenance

- Confidence default: A
- License: gov_open
- Reporting period type: annual

## Known breakage modes

- TBD

## Revision policy

TBD (plan documents are occasionally revised mid-cycle; NPC publishes mid-term reviews)

## Parser

- Path: TBD
- Version: TBD (not yet written — reference_only)
- Owner: TBD
- Tested against: TBD

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `npc-16th-plan/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
