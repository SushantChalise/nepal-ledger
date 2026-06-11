# Pulse — feature context

**Live macro KPI cards** showing Nepal's latest approved economic indicators grouped by Prices, Money In, and Money Out / Trade.

Lens / pillar: Lens 1 — The Pulse (default lens); serves all 5 Public Pillars but primarily Pillar 1 "Money In" and Pillar 2 "Money Out"
Route(s): `/pulse`
Status: live · NRB CMEFs (85 indicators: 7 macro + 78 NCPI inflation categories)

## Data in
- `approved_indicator_values` joined to `indicators` and `source_documents`, via `listApprovedWithIndicator()` (`src/lib/db/repositories/approved-indicator-values.ts`)
- Reads production only (`approved_indicator_values`); never staging.

## Files
- `components/KpiCard.tsx` — Server Component; renders a single indicator as a card with value, unit, period, and confidence badge (A/B/C)
- `components/KpiGroup.tsx` — Server Component; wraps a set of KpiCards under a titled `<section>`
- `page` at `src/app/pulse/page.tsx` — async Server Component; calls `listApprovedWithIndicator()`, groups rows via `SLUG_TO_GROUP`, formats values via `formatIndicatorValue()` from `src/lib/format/indicator-units.ts`, renders typed empty and error states

## Invariants (don't break these)
- No `'use client'` in this feature. KpiCard and KpiGroup are pure Server Components.
- Unit slug mapping lives in `src/lib/format/indicator-units.ts` (`formatIndicatorValue()`). Handled slugs: `NPR_billion` / `npr_billion` → "NPR X.XX B"; `percent_yoy` / `percent` → "%"; `months_of_imports` / `months` → "months". Unknown slugs fall back to raw slug as the unit label — add new slugs there when new indicator units arrive.
- Indicators not in `SLUG_TO_GROUP` fall into an "Other Indicators" overflow group rather than being silently dropped. Extending the display groups means adding an entry to `SLUG_TO_GROUP` and `GROUP_META` and optionally `GROUP_ORDER` in `page.tsx`.
- Typed empty state (`rows.length === 0`) and typed error state (`!result.ok`) are both rendered — never throw from the page component.
- `listApprovedWithIndicator()` orders by `indicators.category` then `indicators.slug` — presentation order is DB-driven; do not sort client-side.

## Gotchas
- The page currently shows all rows from `approved_indicator_values` in a single pass. If the indicator count grows large (hundreds), consider adding a category filter or pagination — the current JOIN fetches everything.
- `formatIndicatorValue()` is now in `src/lib/format/indicator-units.ts` (shared with homepage). Both Pulse and the homepage import from there — do not copy the logic inline.
- `reportingPeriod` and `sourceAgency` in the header are taken from the first row returned. If the dataset mixes multiple reporting periods, the header label will be misleading. Currently homogeneous (all NRB CMEFs nine-month batch).

## Related
- ADRs: ADR-0003 (no API parsing — data arrives only via approved ingest pipeline)
- Docs: `docs/DATA_PIPELINE.md` (staging → approved flow), `docs/UI_ACCEPTANCE.md` (accessibility gates), `docs/SOURCE_REGISTRY.md` (NRB CMEFs source registration)
- Repository: `src/lib/db/repositories/approved-indicator-values.ts`
