# Source: International Monetary Fund — Article IV Consultation Reports (Nepal)

**source_id:** `imf-article-iv`
**Status:** Active
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** TBD

> Stub profile — rich profile lands with the parser PR (per ADR-0009).

## What this is

IMF Article IV consultation reports on Nepal, published annually after the
IMF's bilateral surveillance visit. Contains macroeconomic assessments,
fiscal sustainability analysis, financial sector reviews, and policy
recommendations. Cited as an international benchmark; proprietary license
means data cannot be reproduced verbatim — editorial citation only.

## Publication

- URL: https://www.imf.org/en/Countries/NPL
- Frequency: annual
- Expected window: TBD
- Format: pdf

## What we extract

- Reference only. No indicator ingestion planned; cited from stories via Fact Ledger.

## Provenance

- Confidence default: A
- License: proprietary
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
  under key `imf-article-iv/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
