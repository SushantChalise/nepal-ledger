# Source: World Bank — World Development Indicators (Nepal)

**source_id:** `wb-wdi`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

The World Bank's World Development Indicators (WDI) dataset, filtered to
Nepal. Provides long time-series on GDP per capita, poverty rates, trade
openness, health, education, and governance indicators. Continuously
available via the WDI DataBank API (JSON). Used as an international
benchmark comparator for editorial stories; not parsed into
`approved_indicator_values` (ingestion mode: reference_only). Confidence
A because WDI aggregates from national statistical offices but applies
its own quality controls.

## Publication

- URL: https://databank.worldbank.org/source/world-development-indicators
- Frequency: annual
- Expected window: TBD (WDI updates typically mid-year)
- Format: json (API)

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.
  Notes from seed: "International benchmark. Continuous availability via API."

## Provenance

- Confidence default: A
- License: cc_by
- Reporting period type: annual

## Known breakage modes

- TBD

## Revision policy

TBD (WDI revises historical data when national offices submit corrections;
revisions are reflected in the API without explicit versioning)

## Parser

- Path: TBD
- Version: TBD (not yet written — reference_only)
- Owner: TBD
- Tested against: TBD

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `wb-wdi/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
