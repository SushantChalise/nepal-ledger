# Pulse — feature context

**Live macro KPI cards** — two sections:
1. **Current Flow** (NRB CMEFs, 9-months YTD/YoY): Prices · Money In · Money Out · Fiscal · Banking
2. **Structural Benchmarks** (World Bank WDI, annual): Economy · Inequality · Fiscal Ratios

Lens / pillar: Lens 1 — The Pulse; serves all 5 Public Pillars
Route(s): `/pulse`
Status: live · CMEFs v0.2.0 (14 indicators) + WDI v0.1.0 (15 indicators)

## Data in
- `approved_indicator_values` joined to `indicators` and `source_documents`, via `listApprovedWithIndicator()` (`src/lib/db/repositories/approved-indicator-values.ts`)
- Reads production only (`approved_indicator_values`); never staging.

## Files
- `components/KpiCard.tsx` — Server Component; renders a single indicator as a card with value, unit, period, and confidence badge (A/B/C)
- `components/KpiGroup.tsx` — Server Component; wraps a set of KpiCards under a titled `<section>`
- `page` at `src/app/pulse/page.tsx` — async Server Component; calls `listApprovedWithIndicator()`, groups rows via `SLUG_TO_GROUP`, formats values inline with `formatValue()`, renders typed empty and error states

## Invariants (don't break these)
- No `'use client'` in this feature. KpiCard and KpiGroup are pure Server Components.
- Unit slug mapping is inline in `page.tsx` (`formatValue()`). Handled: `npr_billion` → "NPR B"; `percent_yoy`/`percent` → "%"; `months_of_imports` → "months"; `usd_million` → "USD M/B" (auto-scales ≥ 1 000 M); `usd` → raw USD; `index_points` → Gini. Unknown slugs fall back to raw slug.
- Two separate SLUG maps: `FLOW_SLUG_TO_GROUP` (CMEFs → FlowGroupKey) and `BENCHMARK_SLUG_TO_GROUP` (WDI → BenchmarkGroupKey). When a new source arrives, add its slugs to the appropriate map; don't conflate flow (YTD) and benchmark (annual) data in the same section.
- Indicators not in either map fall into an "Other Indicators" overflow group — they are never dropped silently.
- Typed empty state (`rows.length === 0`) and typed error state (`!result.ok`) are both rendered — never throw from the page component.
- `listApprovedWithIndicator()` orders by `indicators.category` then `indicators.slug` — presentation order is DB-driven; do not sort client-side.

## Gotchas
- The page currently shows all rows from `approved_indicator_values` in a single pass. If the indicator count grows large (hundreds), consider adding a category filter or pagination — the current JOIN fetches everything.
- `formatValue()` lives inline in `page.tsx` (not in a shared module). If Money Map or other features need the same NPR-billion / percent / months formatting, extract to `src/lib/format/indicator-units.ts` to avoid drift — currently not shared.
- `flowPeriod` is derived from the first CMEFs row; `benchmarkPeriod` from the first WDI row. Each section shows its own period label so mixed-vintage data is accurately represented.

## Related
- ADRs: ADR-0003 (no API parsing — data arrives only via approved ingest pipeline)
- Docs: `docs/DATA_PIPELINE.md` (staging → approved flow), `docs/UI_ACCEPTANCE.md` (accessibility gates), `docs/SOURCE_REGISTRY.md` (NRB CMEFs source registration)
- Repository: `src/lib/db/repositories/approved-indicator-values.ts`
