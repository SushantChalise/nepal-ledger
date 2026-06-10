# Source: Ministry of Finance — Budget Speech (बजेट वक्तव्य)

**source_id:** `mof-budget-speech`
**Status:** Paused
**Tier:** Tier 2
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker B catalog audit)

## What this is

The annual Budget Speech is the Finance Minister's address delivered on Jestha 15 (the first
day of the budget session). It contains headline revenue and expenditure targets, the financing
gap and its sources, capital expenditure allocations by sector, and policy priorities for the
coming fiscal year. It is the primary source for budget target indicators in the Budget Watch
vertical and for tagging stories against announced policy commitments.

## Publication

- URL: https://mof.gov.np/en/publication/budget-speech-315
- Frequency: annual (Jestha 15 each year = late May/early June)
- Expected window: Jestha 15 (Nepali); English translation ~1 week later
- Format: pdf

## What we extract

- `budget-revenue-target` — Annual revenue target (NPR billion)
- `budget-expenditure-target` — Total planned expenditure (NPR billion)
- `budget-capital-target` — Capital expenditure allocation (NPR billion)
- `budget-recurrent-target` — Recurrent expenditure allocation (NPR billion)
- `budget-deficit-financing` — Financing gap and sources (NPR billion)

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `mof-gov-np-ssl-cert-chain-incomplete-add-mof-ca-to-trust-store` — mof.gov.np has an
  incomplete SSL certificate chain. Add the MoF CA certificate to the scraper's trust store.
  Do NOT disable TLS verification. Note: actual PDF files are served from `giwmscdnone.gov.np`
  (Government Integrated Web Management System CDN), which has a valid certificate.
- `url-structure-changes-each-fy` — The publication URL at mof.gov.np changes structure each
  FY; use the stable category ID (`budget-speech-315`) with a search-pattern fallback.
- `english-translation-released-approx-1-week-after-nepali` — The Nepali edition is released
  on Jestha 15; the English translation follows approximately one week later. Do not attempt
  to extract English text from Nepali PDFs; wait for the English edition or flag as out-of-scope.

## Revision policy

Annual; no revision after presentation to Parliament. Supplementary appropriations are separate
documents (not part of this source). Actual outturn figures come from FCGO — see
`fcgo-consolidated-financial-statements`.

## Parser

- Path: `scrapers/mof-budget-speech/parser.py`
- Version: 0.0.0
- Owner: Mother Opus
- Tested against: `docs/sources/mof-budget-speech/samples/`

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `mof-budget-speech/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
