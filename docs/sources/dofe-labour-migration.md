# Source: Department of Foreign Employment — Monthly labour migration (country-wise approvals)

**source_id:** `dofe-labour-migration`
**Status:** active
**Tier:** Tier 2
**Registered at:** 2026-05-14
**Last verified:** 2026-06-11

## Publication

- URL: https://dofe.gov.np/api/category/monthly (GIWMS API, JSON, Content-Type: application/json)
- PDF host: https://giwmscdnone.gov.np/media/pdf_upload/
- Frequency: monthly
- Format: pdf (multi-page, text layer)
- Reporting period type: monthly
- Requires table extraction: yes (pdfplumber automatic table extractor)
- API pagination: DRF-style `count / next / previous / results`
- Months available (as at 2026-06-11): Baisakh 2082 – Chaita 2082 (12 months)

## Data structure

Each monthly PDF contains:
1. **Pages 1–N: Country-wise table** — one row per destination country, columns:
   - S.N., Country, Recruiting Agency (M/F/T), Individual-New (M/F/T),
     G-to-G (M/F/T), Individual-ReEntry (M/F/T), Legalization (M/F/T),
     Total with ReEntry (M/F/T), Total without ReEntry (M/F/T)
   - Grand Total row (S.N. = null, Country = "Grand Total")
2. District-wise table (pages N+1 ...) — parser skips these.
3. RA-wise table — parser skips these.

**Primary metric extracted:** "Total with ReEntry Total" (col index 19 of 23).
This is the most comprehensive count — includes all departure categories.

## Provenance

- Confidence default: A
- License: gov_open
- Ingestion mode: manual_upload (download PDF from `pdf_upload` field in API JSON)

## Registered indicators

- `dofe-departures-malaysia-monthly` — Malaysia Total with ReEntry
- `dofe-departures-qatar-monthly` — Qatar Total with ReEntry
- `dofe-departures-uae-monthly` — UAE Total with ReEntry
- `dofe-departures-saudi-arabia-monthly` — Saudi Arabia Total with ReEntry
- `dofe-departures-kuwait-monthly` — Kuwait Total with ReEntry
- `dofe-departures-bahrain-monthly` — Bahrain Total with ReEntry
- `dofe-departures-oman-monthly` — Oman Total with ReEntry
- `dofe-departures-korea-monthly` — South Korea (Republic of Korea) Total with ReEntry
- `dofe-departures-japan-monthly` — Japan Total with ReEntry
- `dofe-departures-israel-monthly` — Israel Total with ReEntry
- `dofe-departures-australia-monthly` — Australia Total with ReEntry
- `dofe-departures-total-monthly` — Grand Total (all countries) with ReEntry
- Plus auto-generated slugs for all other countries found in the table.

## Known breakage modes

1. **Column count variance (MINOR):** pdfplumber occasionally produces 24 columns on continuation pages (extra trailing `None`). Parser tolerates `>= 23` columns — data extraction is unaffected since "Total with ReEntry Total" is always at col 19.
2. **New country added:** Emits row with auto-generated slug (e.g. `dofe-departures-fictonia-monthly`). No parser error; seed the indicator manually.
3. **Image-only scan:** If DoFE uploads a scanned PDF with no text layer, pdfplumber yields no text → `EncodingError` failure. Observed frequency: never so far.
4. **Title phrasing change:** If the header changes from "Countrywise Labour Approval for <Month> <Year>", `_TITLE_RE` won't match → `PeriodAmbiguous` failure. Bump parser version.

## Revision policy

DoFE does not appear to revise published monthly PDFs. If a URL changes for a given month, re-download and re-parse; the parser is idempotent.

## Notes

Migration Industry vertical. District breakdown present in the same PDF but not extracted (separate table, not a priority for Year 1).

The DoFE only hosts the current fiscal year (12 months). Historical data (FY 2081/82 and earlier) would require archive.org or direct request to DoFE.