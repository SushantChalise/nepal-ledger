# Source: Nepal Rastra Bank — Financial Stability Report

**source_id:** `nrb-financial-stability-report`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker A catalog audit)

## What this is

NRB's annual Financial Stability Report (FSR) synthesizes systemic risk indicators, non-performing
loan ratios, capital adequacy ratios, stress-test outcomes, and financial system vulnerability
assessment. It is the definitive Money Captured quality signal for the Fact Ledger and carries
high editorial value for the Monthly Verdict. 16 issues published between July 2012 and FY 2023/24.

## Publication

- URL: https://www.nrb.org.np/category/financial-stability-report/
- Frequency: annual (typically published July–October of the following year)
- Expected window: 3–10 months after the FY close (Ashadh end)
- Format: pdf

## What we extract

- `fsr-npl-ratio-banking` — Gross NPL ratio for the banking sector (%)
- `fsr-capital-adequacy-ratio` — System-wide capital adequacy ratio (%)
- `fsr-credit-to-deposit-ratio` — CD ratio across BFI classes
- `fsr-interbank-rate-average` — Average interbank rate for the period (%)
- `fsr-systemic-risk-summary` — Narrative stress-test outcome (cite-only initially)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `url-slug-format-changed-older-issues-at-red-newer-at-bfr` — Older issues (No. 1–10) live
  under `/red/` slugs; newer issues (No. 10 onward) under `/bfr/`. The parser/downloader must
  handle both path prefixes when building the historical archive.
- `no-issue-yet-for-fy-2024-25` — As of May 2026, Issue No. 17 (FY 2024/25) has not been
  published. The FY 2023/24 issue (No. 16) is the latest.

## Revision policy

Annual; one issue per fiscal year. No mid-year revisions. If NRB publishes a corrigendum, it
is typically a separate notice rather than a replacement PDF.

## Parser

- Path: `scrapers/nrb-financial-stability-report/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/nrb-financial-stability-report/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-financial-stability-report/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
