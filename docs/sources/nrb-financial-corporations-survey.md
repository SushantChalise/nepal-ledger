# Source: Nepal Rastra Bank — Financial Corporations Survey (FCS)

**source_id:** `nrb-financial-corporations-survey`
**Status:** Paused
**Tier:** Tier 3
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's Financial Corporations Survey (FCS) follows the IMF Monetary and Financial Statistics
Manual (MFSM) methodology — the standard-compliant view of Nepal's financial system used in
IMF Article IV consultations. It complements the BFI monthly XLSX corpus (which uses NRB's own
format) by providing an internationally comparable view. FY 2076/77–2079/80 confirmed; later
years expected once published. FY-filtered category pages return "No posts" even when data
exists; the un-filtered category index or direct post slugs are required.

## Publication

- URL: https://www.nrb.org.np/category/financial-corporations-survey/
- Frequency: annual (published in FY groupings; e.g., one publication covering 4 FYs)
- Expected window: Variable; no stated release calendar
- Format: pdf

## What we extract

- `fcs-broad-money-annual` — Broad money (M2) per IMF MFSM (NPR million)
- `fcs-credit-to-private-sector-annual` — Credit to the private sector (NPR million)
- `fcs-net-claims-on-govt-annual` — Net claims on government (NPR million)
- `fcs-net-foreign-assets-annual` — Net foreign assets of the financial system (NPR million)
- (complete indicator list to be finalized in parser PR)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `fy-filtered-category-pages-return-no-posts-use-unfiltered-category` — The FY-parameterized
  category URLs (e.g., `?fy=2082-83`) return "No posts" even when data exists. Use the
  un-filtered category index page or search by post slug.
- `multi-fy-groupings-in-single-release` — NRB releases FCS for multiple fiscal years in one
  publication (e.g., "FY 2076/77–2079/80" as a single PDF). The parser must handle multi-year
  tables within a single document and emit correctly-keyed rows per FY.

## Revision policy

Annual; groupings of multiple FYs in one release. No mid-year revisions. If NRB later publishes
a corrected edition, it appears as a new post in the same category.

## Parser

- Path: `scrapers/nrb-financial-corporations-survey/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-financial-corporations-survey/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-financial-corporations-survey/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
