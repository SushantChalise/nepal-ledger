# Source: Office of the Prime Minister (DPM Office) — Annual Performance Review of Public Enterprises (Yellow Book)

**source_id:** `dpm-public-enterprises-annual`  
**Status:** paused (parser landed for Annex-1; flip to `active` on first live ingest — pending Mother)  
**Tier:** Tier 3  
**Registered at:** 2026-05-14  
**Last verified:** 2026-06-07 (parser PR — Annex-1, FY 2080/81 edition)

> Parser PR landed: `scrapers/mof_yellowbook/` emits ADR-0015 dimensional facts
> (dimension = public enterprise) from **Annex-1** of the FY 2080/81 edition.
> Ingest via `scripts/ingest-dne-yellowbook.ts` → `dne_facts`.

## Publication

- URL: https://opmcm.gov.np/
- Frequency: annual
- Format: pdf
- Reporting period type: annual
- Requires table extraction: yes

## Provenance

- Confidence default: A
- License: gov_open
- Ingestion mode: manual_upload

## Notes

Public Enterprise X-Ray. In-repo corpus at Financial Data/mof_documents/yellowbook/ (6 PDFs).

### Extracted indicators (ADR-0015 dimensional, `dne_facts`)

From **Annex-1** (loan-investment & principal-recovery by enterprise) of the
FY 2080/81 edition (`Webiste Uploaded Yellow_sdwyi9v.pdf`):

| base_indicator_slug    | source column | unit          | confidence |
|------------------------|---------------|---------------|:----------:|
| `soe-government-share` | शेयर (equity) | `npr_thousand`| B          |
| `soe-loan-principal`   | ऋण (loan)     | `npr_thousand`| B          |

`dimension_kind = public_enterprise`; `dimension_value` = kebab of the enterprise
name; `reporting_period_type = annual`; BS FY from the annex header. Real-PDF
dry-run: 84 rows (42 enterprises × 2 measures).

**Unit (ADR-0011):** the annex header states "(रु. हजारमा)" = NPR **thousand**
(not million, not lakh). Verified: NEA government share = 181,330,245 thousand =
NPR 181.33 billion. The per-sector summary tables (not parsed) use "रू. लाखमा"
(lakh) — a different unit; no cross-unit mixing occurs.

## Known breakage modes

- **Mixed encodings, page-to-page.** The FY2079 edition body prose is CID-broken
  (`(cid:N)`, no ToUnicode). **Annex-2/Annex-3 are Preeti legacy-font byte-maps**
  (gibberish under text extraction) — not transliterated (no OCR, ADR-0003).
- **Per-sector summary tables are not parseable deterministically.** Revenue /
  net-profit / admin-cost tables have ragged merged-cell geometry (column count
  varies by sector: 12/13/21/15/9) and one Preeti-encoded sector. The intended
  `soe-revenue` / `soe-net-profit-loss` / `soe-paid-up-capital` measures live
  there and are **deferred** until a more robust per-sector extractor exists.
- **Edition layout drift.** The FY2081 edition (402 pp, 133 MB) does not surface
  Annex-1 in the same location; the parser scans every page for the annex
  markers and emits `PageLayoutChanged` if absent (never silently empty).
- **Glyph-reordering artifacts** in some Unicode names (e.g. `दग्ुध` for दुग्ध).
  `dimension_label` preserves the raw extracted text faithfully; we never
  fabricate. `dimension_value` keeps every Devanagari code point so distinct
  enterprises never collapse to one slug.

## Revision policy

Annual editions supersede prior years' figures (enterprises restate). Each
edition is a separate `source_documents` row; `dne_facts` is keyed by
`source_document_id`, so re-ingesting the same edition is idempotent
(`ON CONFLICT DO NOTHING`) and a new edition adds rows without overwriting —
preserving the revision trail (Data Continuity Protocol). Never merge across
editions on `(slug, dimension, period)` alone.
