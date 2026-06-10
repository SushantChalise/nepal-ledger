# Fact Ledger — feature context

**The visible claims database.** A browsable, grouped table of every approved indicator value — indicator, value+unit, period, confidence grade (A/B/C), and source feed — making Nepal Ledger's "auditable economic truth" tangible.

Lens / pillar: Fact Ledger (see STRATEGY.md glossary); underpins all 5 Public Pillars by exposing the provenance behind every published number.
Route(s): `/fact-ledger`
Status: live · NRB feeds — DNE XLSX (tourist arrivals), NCPI table (inflation), CMEFs (macro). Render-only over data already live in `approved_indicator_values`.

## Data in
- `approved_indicator_values` ⋈ `indicators` ⋈ `source_documents` ⋈ `source_registry`, via `listFactLedgerEntries()` (`src/lib/db/repositories/approved-indicator-values.ts`). The `source_registry` join is what makes the Source column meaningful — `indicators.source_agency` is uniformly "Nepal Rastra Bank", so the three feeds are distinguished only by `agency_short` + `dataset_name`.
- Coverage strip: `getFactTableCounts()` (same repo file) — `COUNT(*)` of `dne_facts` / `banking_sector_facts` / `local_government_fiscal_transfers` / `census_facts`.
- Reads production only (`approved_*` + registry/dimensional tables); never staging.

## Files
- `server/queries.ts` — `getFactLedgerView(): Result<FactLedgerView>`; composes the two repo reads into category groups + summary stats (indicator/source counts, confidence breakdown, per-category counts). No raw DB access — repo-only.
- `format.ts` — `formatIndicatorValue()` / `formatRowCount()` + `CATEGORY_LABELS` / `CATEGORY_DESCRIPTIONS` / `FACT_TABLE_LABELS`. **Plain module, NOT `'use client'`** (see Gotchas).
- `components/ConfidenceBadge.tsx` — Server Component; A/B/C pill, colours mirror Pulse `KpiCard` exactly.
- `components/LedgerTable.tsx` — Server Component; one category section = semantic `<table>` (≥640px) + stacked-card fallback (<640px).
- `page` at `src/app/fact-ledger/page.tsx` — async Server Component; typed empty/error states, summary strip, category groups, granular-fact-table coverage strip, source/confidence footer.

## Invariants (don't break these)
- No `'use client'` anywhere in this feature — pure Server Components (render-only; no interactivity in v1).
- `format.ts` MUST stay a plain (non-`'use client'`) module — imported by Server page + components. Making it client would 500 the server page (money-map gotcha).
- Typed empty state (`totalEntries === 0`) and typed error state (`!result.ok`) both rendered — never throw from the page.
- Presentation order is DB-driven: `listFactLedgerEntries()` orders by `indicators.category` then `slug`; the view builder preserves first-seen order. Do NOT sort client-side.
- The Source column shows `agency_short · dataset_name` (from `source_registry`), never the monolithic `indicators.source_agency`.
- Confidence badge colours/labels stay in sync with Pulse `KpiCard` and the `ConfidenceGrade` enum.

## Gotchas
- **`indicators.source_agency` is useless as a source label here** — all 492 rows are "Nepal Rastra Bank". The real provenance lives in `source_registry` (`nrb-dne-xlsx` 407, `nrb-ncpi-table` 78, `nrb-cmefs-monthly` 7). That is why `listFactLedgerEntries()` adds the extra join rather than reusing `listApprovedWithIndicator()`.
- Tourism arrivals (407 rows, the bulk of the ledger) are **Grade B** and unit `count`; inflation/macro are Grade A. The confidence summary will therefore show B ≫ A — that is correct, not a bug.
- The coverage strip is **best-effort**: if `getFactTableCounts()` fails, the view degrades to `factTableCounts: []` and the strip is hidden rather than failing the whole page.
- No click-through to source PDFs yet — `source_documents.storage_key` exists but signed-URL plumbing is a follow-up. v1 shows the source-agency + dataset label only (per task brief).

## Related
- ADRs: ADR-0003 (no API parsing — data arrives only via approved ingest), ADR-0011 (data-unit identity), ADR-0009/0010 (source registry).
- Docs: `docs/UI_ACCEPTANCE.md` (table fallback + accessibility), `docs/research/DATA_BUILDOUT_PLAN.md` §"Render Track" + item #30, `docs/DOCUMENTATION_STANDARD.md`.
- Repository: `src/lib/db/repositories/approved-indicator-values.ts` (`listFactLedgerEntries`, `getFactTableCounts`).
- Reuses patterns from: `src/features/pulse/*` (confidence badge, value formatting), `src/features/money-map/*` (Result + typed states + plain `format.ts`).
