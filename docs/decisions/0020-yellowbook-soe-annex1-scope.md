# ADR-0020: Yellow Book SOE parser — Annex-1-only scope, `npr_thousand` unit, `dne_facts` reuse

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, parsing, dne, soe, mof, scope

## Context

The MoF / DPM-Office **Yellow Book** (Annual Performance Review of Public
Enterprises, `source_id: dpm-public-enterprises-annual`) is the canonical
"Public Enterprise X-Ray" — per-SOE equity, loans, revenue, profit/loss, paid-up
capital. It is a primary feed for the *Money Wasted* / *Where Money Becomes
Wealth* pillars. Six editions sit in-repo (`Financial Data/mof_documents/yellowbook/`).

The buildout plan (item #24) scoped three measures — `soe-revenue`,
`soe-net-profit-loss`, `soe-paid-up-capital` — assuming a clean per-sector
summary matrix. On real-PDF inspection that assumption broke:

- Editions are **Devanagari**, not English ("BIG 2080" etc. are *fiscal years*).
- Encoding quality is **mixed page-to-page**: the FY2079 body prose is CID-broken
  (`(cid:N)`, no ToUnicode); **Annex-2/Annex-3 are Preeti legacy-byte font-maps**
  (gibberish under text extraction); one per-sector table is Preeti-encoded.
- The per-sector revenue/profit/capital tables have **ragged merged-cell
  geometry** — column count varies by sector (12/13/21/15/9) — so a single
  deterministic table contract cannot span them without a fragile >300-line,
  per-sector branch tree.
- The **one stable, Unicode, deterministically parseable per-enterprise matrix**
  is **Annex-1** (loan-investment & principal by enterprise) of the **FY 2080/81**
  edition (`Webiste Uploaded Yellow_sdwyi9v.pdf`): 10-column, two pages,
  sector-grouped, ~42 enterprises.

Per ADR-0003 (no production AI/OCR parsing) and CONTEXT_RULES Rule 6 (no fragile
silent-failure patterns), forcing the un-parseable tables was rejected.

## Decision

1. **Scope to Annex-1 only**, FY 2080/81 edition. Extract the two measures that
   table contains cleanly:
   - `soe-government-share` — शेयर (government equity in the enterprise)
   - `soe-loan-principal` — ऋण (loan principal)
2. **Defer** `soe-revenue` / `soe-net-profit-loss` / `soe-paid-up-capital` —
   they live only in the un-parseable per-sector summary tables. Documented as a
   known breakage mode in `docs/sources/dpm-public-enterprises-annual.md`.
   Future approach: coordinate-based (`extract_words` x-clustering) per-sector
   extraction, or a Unicode-clean future edition.
3. **Reuse `dne_facts`** (ADR-0015), not a new table. A per-SOE measure is a
   *base measure sliced by one dimension* — exactly the dimensional model:
   - `dimension_kind = public_enterprise`
   - `dimension_value` = kebab of the enterprise name, **every Devanagari code
     point preserved** (distinct enterprises never collapse to one slug)
   - `dimension_label` = raw extracted text (faithful; glyph-reorder artifacts
     like `दग्ुध` for दुग्ध are preserved, never "corrected"/fabricated)
   - `confidence_grade = B` (Devanagari table extraction)
4. **Unit is `npr_thousand`** (ADR-0011 data-unit verification). The annex header
   states **"(रु. हजारमा)"** — हजार = *thousand*, not million, not lakh.
   Verified by magnitude: NEA government share = 181,330,245 thousand =
   **NPR 181.33 billion**, the correct order for Nepal's largest SOE. The
   per-sector summary tables use "रू. लाखमा" (*lakh*) — a different unit; because
   we parse only Annex-1, **no cross-unit mixing occurs**.
5. **Ingest** via `scripts/ingest-dne-yellowbook.ts` (`pnpm ingest:dne-yellowbook`),
   a sibling of `ingest:dne-dimensional`: spawns the Python parser, validates the
   `dimensional_rows` array against a Zod schema, archives source bytes +
   `source_documents` row, bulk-inserts into `dne_facts` (`ON CONFLICT DO NOTHING`).
   CLI uses `source_id = dpm-public-enterprises-annual` (the registered id — there
   is no separate XLSX-style umbrella id for the Yellow Book).
6. **Edition drift is loud, never silent.** The parser scans every page for the
   Annex-1 markers; if absent (e.g. the FY2081 402-page / 133 MB edition surfaces
   it elsewhere) it emits `PageLayoutChanged` rather than returning empty.

## Alternatives Considered

- **Force the per-sector tables with a branchy column-count parser.** Rejected —
  fragile, >300 lines, one sector is Preeti-encoded (undecodable without
  transliteration → ADR-0003 violation). Would silently mis-map columns on any
  layout drift.
- **OCR the CID-broken / Preeti pages.** Rejected — ADR-0003 (no production AI).
- **New `soe_facts` table.** Rejected — `dne_facts` already models exactly
  "base measure × one dimension"; a parallel table would duplicate the schema,
  repository, and idempotency machinery for no semantic gain.
- **Register each enterprise as an `indicator`.** Rejected for the same reason as
  commodities/countries in ADR-0014/0015 — catalogue pollution.

## Consequences

- 84 `dne_facts` rows land (42 enterprises × 2 measures), provenance-tracked and
  idempotent. The *Money Wasted* pillar gets its first real per-SOE balance-sheet
  slice (equity vs. loan exposure by enterprise).
- Three richer measures (revenue/profit/capital) remain **explicitly deferred and
  documented** — not silently dropped. A follow-up item can add the coordinate-
  based per-sector extractor.
- The `dne_facts` `dimension_kind` vocabulary gains `public_enterprise` alongside
  `commodity` / `country` / `district` / `currency`.
- Re-ingesting the same edition is a no-op; a future Unicode-clean edition adds
  rows under a new `source_document_id` without overwriting (Data Continuity
  Protocol).

## References

- [ADR-0015](0015-dne-dimensional-fact-model.md) — the `dne_facts` model this reuses
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — read the header unit; verify by magnitude
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — no production AI/OCR parsing
- `scrapers/mof_yellowbook/` (parser + README + tests), `scripts/ingest-dne-yellowbook.ts`
- `docs/sources/dpm-public-enterprises-annual.md` — source profile + breakage modes
