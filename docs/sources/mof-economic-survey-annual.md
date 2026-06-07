# Source: Ministry of Finance — Economic Survey (Annual)

**source_id:** `mof-economic-survey-annual`
**Status:** Active (`ingestionMode: reference_only`)
**Tier:** Reference
**Registered at:** 2026-06-07
**Last verified:** 2026-06-07 (parser PR — annex-only assessment, ADR-0016)

> Parser PR landed: `scrapers/mof_economic_survey/` extracts the one
> cleanly-parseable high-value annex table — **Annex 6.1 (Number of Workers
> having Foreign Employment Permit)** — from the English 2023/24 edition as three
> annual single-series indicators (Total/Female/Male, unit `count`). The headline
> MACRO annex (GDP/prices/fiscal/trade) is **RTL-mirrored** and the two Nepali
> editions' annex is **CID-broken** — both DEFERRED with typed diagnostics
> (ADR-0016). EN dry-run: 24 rows (8 full FYs × 3 measures), `status=partial`.
> The reference-only registry posture is unchanged (the macro series remain
> deferred). Three indicator slugs to seed — see the parser README / worker report.

## What this is

The Ministry of Finance's flagship annual review of Nepal's macroeconomic
performance, published alongside the federal budget each Jestha. Covers
GDP growth, sectoral output, fiscal outturn, monetary developments,
balance of payments, and social indicators. Used as the primary
macro-narrative reference for editorial stories; not parsed into
`approved_indicator_values` (ingestion mode: reference_only).

## Publication

- URL: https://mof.gov.np/
- Frequency: annual
- Expected window: Jestha (May/June), coinciding with budget presentation
- Format: pdf

## What we extract (ADR-0016)

From the English 2023/24 edition only — **Annex 6.1: Number of Workers having
Foreign Employment Permit** (a clean `Fiscal Year | Female | Male | Total`
table). Three annual single-series indicators, unit `count`, confidence **B**:

| indicator slug | source column |
|----------------|---------------|
| `economic-survey-foreign-employment-permits-total`  | Total  |
| `economic-survey-foreign-employment-permits-female` | Female |
| `economic-survey-foreign-employment-permits-male`   | Male   |

`reporting_period_type = annual`; rows labelled by AD fiscal year, mapped to BS
via +57 (ADR-0013). Cumulative ("Upto …") and partial/starred ("2023/24*") rows
are skipped. EN dry-run: **24 rows** (8 full FYs 2015/16–2022/23 × 3 measures),
`status=partial`. The headline MACRO series (GDP/CPI/fiscal/trade) are **deferred**
(RTL-mirrored annex — below), so the source's reference-only posture stands.

**Magnitude check (ADR-0011):** FY2022/23 total = 494,224 permits — the right
order for Nepal's annual labour outflow; Female + Male reconcile to Total.

## Known breakage modes

Page numbers are 0-based pdfplumber indices for the EN edition.

- **RTL-mirrored MACRO annex — DEFERRED (English 2023/24, pp 299–303 + 313+).**
  The Macroeconomic Indicators summary and numbered Annex 1.1… macro tables
  (GDP/GVA/prices/fiscal/trade — the brief's headline targets) are free of
  `(cid:N)` but **right-to-left mirrored**: every cell is character-reversed (GDP
  `8.4075` = `"5704.8"` reversed; year `P42/3202` = `"2023/24P"`), the column
  order is reversed (row-label column lands LAST), the row order is reversed, and
  multi-line labels are word-reversed AND line-wrap-fragmented
  (`"noitacifissalC\nlai"`). Numbers decode by string-reversal but the
  label↔value geometry is not deterministically reconstructable; un-mirroring is
  the reverse-engineering ADR-0003 forbids. The parser emits a typed
  `PageLayoutChanged` naming the page ranges.
  - *Magnitude proof the numbers are real:* reversing the GDP cell `8.4075` →
    `5704.8` ⇒ nominal GDP FY2023/24 ≈ NPR 5.7 trillion (ADR-0011 NPR 5–6
    trillion band). The deferral is a geometry problem, not a masked parse bug.
- **CID-broken pages — DEFERRED.** EN narrative chapters (pp ~3–298) and the
  **entire annex of both Nepali editions** (`Economic_Survey_2080-81_NP.pdf`
  p ~410+; `Economic_Survey_2081-82.pdf` p ~258+) render with `(cid:N)`
  placeholders and no ToUnicode map → gibberish. Not parseable without OCR
  (forbidden, ADR-0003). The two Nepali editions thus have **no clean Annex 6.1**
  and the parser returns `status=failure` (`NoCleanAnnexTable`) for them — a
  documented per-edition infeasibility. The parser emits a typed `EncodingError`.
- **Other clean social-sector annex tables — DEFERRED (EN).** Hotels (Annex
  8.14), medical specialists (Annex 11.7), education (Annex 11.x) are genuinely
  clean but have heterogeneous merged-cell / multi-row-header geometry; a robust
  extractor spanning them exceeds the diff budget and is fragile. Future scope:
  coordinate-based per-table extraction.
- **Future approach for the macro annex:** a coordinate-based (`extract_words`
  x/y-clustering) un-mirror, or a Unicode-clean future edition. The parser's
  diagnostic `classify_annex_text` already recognises a clean macro annex.

## Revision policy

Annual editions supersede prior years' figures. Each edition is a separate
`source_documents` row; re-running the parser on a future edition re-extracts
Annex 6.1 if present and re-emits the typed deferrals otherwise. Outcomes are
re-derivable from source + parser version — never silently assumed (Data
Continuity Protocol). Never merge across editions on `(slug, period)` alone.

## Parser

- Path: `scrapers/mof_economic_survey/parser.py`
- Version: `0.1.0` — anchor-based Annex-6.1 extractor + macro/CID deferral
  diagnostics (ADR-0016)
- Output contract: `_common` `ParserResult` / `staging_rows` (same as
  `fcgo_consolidated`)
- Ingest CLI: `scripts/ingest-economic-survey.ts` (`pnpm ingest:economic-survey`)
- Tested against: a synthesized Annex-6.1 table (full-year/cumulative/starred
  rows, preserved zero, dropped blank, typed `ValueUnparseable`) + the diagnostic
  classifier; optional integration tests against the three real PDFs (EN →
  `partial` with 24 rows; Nepali editions → documented `failure`)

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `mof-economic-survey-annual/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
