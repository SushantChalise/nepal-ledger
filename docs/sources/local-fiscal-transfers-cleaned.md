# Source: Ministry of Finance — Federal fiscal transfers to 753 local levels, FY 2082/83 (pre-cleaned XLSX)

**source_id:** `local-fiscal-transfers-cleaned`
**Status:** active
**Tier:** Tier 1
**Registered at:** 2026-05-15
**Last verified:** TBD

> Tier-1 first ingestable domain-fact corpus. Pre-cleaned by editorial team before commit. Parser is the canonical example for the domain-fact (skip-staging) ingestion path.

## Publication

- URL: https://mof.gov.np/
- Frequency: annual (one fiscal year per file)
- Format: xlsx (already cleaned; not the raw MoF PDF)
- Reporting period type: annual
- Requires table extraction: no

## Provenance

- Confidence default: A (authoritative MoF data; cleaning was structural only — no value transformation)
- License: gov_open
- Ingestion mode: manual_upload
- Files in repo: `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx`
- Consumer: `scrapers/mof_fiscal_transfers/` (Worker P1)

## Notes

The "cleaned" qualifier matters: the MoF publishes annual fiscal-transfer schedules in PDF + accompanying XLSX. The XLSX version in this repo was post-processed by an editorial pass that normalized column headers and removed presentational rows. Future ingest workers targeting the raw MoF PDFs would be a separate source (`mof-fiscal-transfers-raw` or similar), since the cleaning history is opaque from the raw side.

## Known breakage modes

- **Municipality name drift across years.** The 27-name override list (see Worker P3's `_GAPANAME_OVERRIDES` for the canonical mapping) is required.
- **Grant-type column renames.** MoF publishes 4 grant types (Equalization, Conditional, Complementary, Special); the column headers have historically drifted in casing and abbreviation. Parser uses a normalized lookup table.

## Revision policy

One-shot per fiscal year. If MoF re-publishes the cleaned XLSX with corrections, a new `source_document` row is created (revision_number incremented), and the same `(local_level_entity_id, fiscal_year_bs, grant_type)` rows get re-inserted under ON CONFLICT DO NOTHING semantics. Conflict resolution if values differ: open ticket; do not auto-overwrite.
