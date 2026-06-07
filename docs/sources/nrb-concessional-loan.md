# Source: Nepal Rastra Bank — Interest-Subsidized / Concessional Loan Monthly Statistics

**source_id:** `nrb-concessional-loan`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's monthly concessional and interest-subsidized loan statistics capture the stock and flow
of directed credit — loans extended at below-market rates under government policy programs.
These data are central to the Money Captured pillar: directed credit subsidies are the primary
mechanism by which the government shapes where private capital flows. The series covers
approximately 75 monthly XLSX releases from Jeth 2078 (May/June 2021) to present.

## Publication

- URL: https://www.nrb.org.np/category/concessional-loan/
- Frequency: monthly
- Expected window: ~15th of the following month (approximate; no stated release calendar)
- Format: xlsx (primary); pdf companion available for most issues

## What we extract

- `concessional-loan-outstanding-total` — Total outstanding concessional loan stock (NPR billion)
- `concessional-loan-by-sector` — Sectoral breakdown (agriculture, SME, tourism, etc.)
- `subsidized-interest-rate` — Weighted average subsidized interest rate applicable

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: monthly

## Known breakage modes

- `filename-uses-nepali-month-names-inconsistent-transliteration` — Filenames embed the BS
  month name in Roman transliteration with inconsistent spelling (e.g., "Badau" vs "Bhadau"
  for Bhadra). The downloader must tolerate transliteration variants when matching filenames.
- `older-entries-pre-xlsx-transition-are-pdf-only` — Some entries before the XLSX transition
  (~Jeth 2078) are PDF-only. These require `requiresTableExtraction: true` handling; confirm
  exact cutoff before writing the parser.

## Revision policy

Monthly. No revision cycle explicitly documented by NRB. Treat each release as final for that
month-end snapshot. Archive each file by download date.

## Parser

- Path: `scrapers/nrb-concessional-loan/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-concessional-loan/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-concessional-loan/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
