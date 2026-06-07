# Source: Public Debt Management Office — Annual Report on Public Debt and Share Investment

**source_id:** `pdmo-annual-debt-report`
**Status:** Paused
**Tier:** Tier 3
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker B catalog audit)

> **Low-confidence registration** — only FY 2080/81 and FY 2081/82 editions confirmed. No
> stable category URL found; historical depth and full URL pattern are uncertain. Flagged for
> Mother review before parser work begins.

## What this is

PDMO's Annual Report on Public Debt and Share Investment is the comprehensive annual review
of Nepal's public debt portfolio: domestic and external debt composition, debt service,
government share investments, and debt sustainability indicators. Two editions confirmed
(FY 2080/81 and FY 2081/82). Published in Nepali; no confirmed English edition.

## Publication

- URL: https://pdmo.gov.np/ (content pages vary by year; no stable category URL confirmed)
- Frequency: annual
- Expected window: Unknown; no stated release calendar
- Format: pdf

## What we extract

- `public-debt-composition-annual` — Domestic vs. external debt share (%)
- `debt-service-ratio-annual` — Debt service as % of revenue
- `govt-share-investment-annual` — Government equity in public enterprises (NPR billion)
- (complete indicator list to be finalized in parser PR; pending sample PDF review)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `content-pages-vary-by-year-no-stable-category-url` — No stable category listing found for
  this series on pdmo.gov.np. Files must be located by navigating the PDMO site manually or
  searching the CDN (giwmscdnone.gov.np) for the known filename patterns. Resolve before
  writing parser.
- `pdf-filenames-use-nepali-unicode-in-cdn-path` — Filename includes Nepali Unicode characters
  in the CDN URL path (observed in FY 2081/82 URL). URL-encode carefully when constructing
  download requests.

## Revision policy

Annual. No revision cycle documented. Treat each published edition as final for that FY.

## Parser

- Path: `scrapers/pdmo-annual-debt-report/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/pdmo-annual-debt-report/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `pdmo-annual-debt-report/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
