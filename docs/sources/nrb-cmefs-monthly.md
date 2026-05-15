# Source: Nepal Rastra Bank — Current Macroeconomic and Financial Situation

**source_id:** `nrb-cmefs-monthly`
**Status:** Active (parser v0.1.0 — headline indicators only, English edition; Path B1)
**Last verified:** 2026-05-15

## What this is

NRB's flagship monthly bulletin synthesizing the macroeconomic and financial
situation of Nepal. Each release covers a cumulative period (e.g. nine months
of the fiscal year) and is the canonical English-language source for headline
indicators: NCPI, monetary aggregates, BoP, remittances, reserves, government
finance, banking sector indicators, and a NEPSE snapshot. The release sets the
tempo for Nepal Ledger's Pulse + Monthly Verdict cycle.

## Publication

- URL: https://www.nrb.org.np/category/current-macroeconomic-situation/
- Frequency: monthly
- Expected window: 25th–30th of the month following the reporting period
- Format: pdf

## What we extract

The v0.1.0 parser extracts seven **headline** indicators from the English
edition of the bulletin — the figures NRB itself foregrounds in the
executive summary and the body's narrative paragraphs. These feed Pulse
v0 (BoP, forex reserves, remittances, trade, NCPI). Additional indicators
in the enumerative list below are slated for v0.2.0+ as Pulse expands.

**v0.1.0 (shipped):**

| Slug | Unit | Period type | Narrative anchor |
| --- | --- | --- | --- |
| `cmefs-ncpi-yoy-overall` | percent_yoy | nine_months_cumulative (end-of-period) | "The y-o-y consumer price inflation in Nepal remained at X percent in mid-Month YYYY" |
| `cmefs-remittance-inflow-ytd` | npr_billion | nine_months_cumulative | "Remittance inflows increased N percent to Rs.X billion" |
| `cmefs-merchandise-imports-ytd` | npr_billion | nine_months_cumulative | "mercandise imports increased N percent to Rs.X billion" (NRB typo for "merchandise"; both spellings accepted) |
| `cmefs-trade-deficit-ytd` | npr_billion | nine_months_cumulative | "Total trade deficit increased N percent to Rs.X billion" |
| `cmefs-bop-surplus-ytd` | npr_billion | nine_months_cumulative | "Balance of Payments (BOP) remained at a surplus of Rs.X billion" (deficit qualifier noted in `parser_notes`) |
| `cmefs-gross-forex-reserves` | npr_billion | end-of-period | "Gross foreign exchange reserves increased N percent to Rs.X billion" |
| `cmefs-forex-reserves-months-of-import-cover` | months | end-of-period | "merchandise and services imports of X months" |

**v0.2.0+ (planned):**

- `cmefs-ncpi-food-yoy`, `cmefs-ncpi-non-food-yoy` — sub-group YoY
- `cmefs-merchandise-exports-ytd`
- `cmefs-m2-yoy`
- `cmefs-private-sector-credit-yoy`
- `cmefs-bfi-deposits-yoy`
- USD-denominated counterparts where NRB publishes paired figures

The cross-validation hook: `cmefs-ncpi-yoy-overall` should match the
`ncpi-overall-index-overall-yoy` row produced by the NCPI parser within
±0.01pp; mismatch surfaces as a validation-layer reconciliation flag.

## Provenance

- Confidence default: A
- License: gov-open (Government of Nepal publication, freely redistributable
  for non-commercial use; CC BY-NC-SA applies to derivative editorial)
- Reporting period type: monthly (each release is one report; values are
  cumulative within the fiscal year — the parser must interpret the period
  metadata and emit `period_type` accordingly per CALENDAR_AND_PERIODS.md)

## Known breakage modes

- `url-changes-each-fy` — NRB rotates the slug at FY boundaries
  (e.g. `.../current-macroeconomic-situation-based-on-nine-months-of-202223/`).
  Downloader (not parser) must use a search-page fallback rather than a
  hardcoded URL.
- `pdf-format-shifts-at-fy-boundary` — Column headings, table page numbers,
  and "Table N(B)" labels have historically shifted at FY 2080/81 and
  FY 2081/82 boundaries. The v0.1.0 parser deliberately reads NRB's
  **narrative prose** rather than the tables, because the prose phrasings
  have been stable across the last three FY releases and the tables have
  not. The Worker H sequel may add table-based extraction once we have
  more years of fixtures to verify column stability.
- `chart-text-interleaved-with-narrative` — pdfplumber's column-aware
  text extraction occasionally interleaves chart-axis labels (e.g.
  `Chart 3: Gross Foreign Exchange Reserves\n3500\n3000\n…`) between
  narrative tokens. The v0.1.0 patterns tolerate up to ~250 chars of
  intervening noise via non-greedy DOTALL gaps. If NRB redesigns the
  charts or the layout, the patterns will fail open with typed
  `PageLayoutChanged` errors rather than emit phantom values.
- `mercandise-typo` — NRB's own narrative has historically misspelled
  "merchandise" as "mercandise" in the imports paragraph (verified in
  FY 2082/83 nine-month release). The parser accepts both spellings; if
  NRB corrects the typo the pattern still matches.
- `provisional-marker` — when NRB tags a value with an inline ``P``
  (provisional) marker in the prose (rare in nine-month releases; common
  in monthly first-cut releases), the parser downgrades that row's
  confidence from A to B and records the reason in `parser_notes`. The
  `P=Provisional` table legend itself is **not** treated as an inline
  marker — only adjacent ``\dP`` patterns.

## Editions covered

- **English** — full coverage (v0.1.0). All headline indicators above.
- **Nepali (Devanagari)** — **out of scope**. Path B1 (approved
  2026-05-15) defers Devanagari parsing because Surya OCR's
  Devanagari-numeral accuracy is unverified and the English edition
  carries the same headline figures. The Nepali edition may be revisited
  later for fact-ledger labels (not ingestion).

## Revision policy

Provisional values are revised in the next release (typically by 1–3% on
headline indicators). Historical values are considered stable after 2 cycles.
The parser writes each release as a new row in `staging_indicator_values`
keyed on `(indicator_id, period_start, period_end, source_document_id)`; the
Fact Ledger pipeline picks the latest non-provisional value per period and
records superseded values in `indicator_revisions` (Worker C-sequel).

## Parser

- Path: `scrapers/nrb_cmefs/parser.py`
- Version: 0.1.0 (Path B1 — English headline indicators)
- Owner: Mother Opus
- Tested against: `scrapers/nrb_cmefs/tests/fixtures/cmefs_nine_months_excerpt.pdf`
  — first 6 pages of the in-repo
  `Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf` (sufficient
  to exercise every headline pattern; full PDF lives outside the worktree
  and is archived in Supabase Storage per the archive policy below)

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `nrb-cmefs-monthly/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
