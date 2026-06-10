# Tourism Rupee — feature context

**34-year monthly tourist-arrivals line chart.** Renders Nepal's tourist-arrivals series (the tourism economy's leading foreign-currency indicator) from 1992 to the latest month.

Lens / pillar: Lens 6 — Tourism Rupee; serves Pillar 1 "Money In" (tourism foreign-currency inflows)
Route(s): `/tourism-rupee`
Status: live · Nepal Rastra Bank — Database on Nepalese Economy (indicator `dne-tourist-arrival`, ~407 monthly rows, Grade B)

## Data in
- `approved_indicator_values` joined to `indicators` WHERE `slug = 'dne-tourist-arrival'`, via `getTouristArrivalsSeries()` (`src/features/tourism-rupee/server/queries.ts`)
- Reads production only (`approved_indicator_values`); never staging.

## Files
- `server/queries.ts` — `getTouristArrivalsSeries()` returns `Result<ArrivalsSeries>` (`points`, `latest`, `yoyPct`, plus indicator name/unit/confidence/source); single JOIN query, Zod-validated at the DB boundary, ordered by `reporting_period_ad_end`.
- `format.ts` — `formatCount` (compact "116.6K"), `formatCountFull` (grouped "116,553"), `formatYoyPct`, `formatMonthLabel`. **Not** `'use client'` — plain module imported by both the Server page and the client chart.
- `components/ArrivalsLineChart.tsx` — `'use client'`; inline SVG line chart with a ResizeObserver-driven responsive width, a COVID reference marker, a reduced-motion-aware draw-in, and an always-present visually-hidden `<table>`. Uses `buildTimeScale`/`buildLinearScale`/`buildLinePath` from `src/lib/viz/adapters/d3-shape.ts`.
- `page` at `src/app/tourism-rupee/page.tsx` — async Server Component; reuses Pulse `KpiCard`; "what this shows" prose, source/confidence/unit footer, and a disabled "Corridor leakage — coming soon" placeholder. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Plot on `reporting_period_ad_end` (the AD month-end), NOT `reporting_period_bs`.** The BS labels skew near COVID (the DNE transposed-layout parser approximates them mid-month). The AD end date is the trustworthy time axis. `point.x` is always the AD instant; the BS label is display-only (shown in the accessible table).
- Unit is **tourist arrivals (count)**, not currency. Source label is exactly "Nepal Rastra Bank — Database on Nepalese Economy"; confidence is the value's stored grade (B). Do NOT attribute to the paused `ntb-tourism-monthly` stub.
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map gotcha).
- D3 type-bridging `as` casts belong ONLY in `src/lib/viz/adapters/d3-shape.ts` (ADR-0012). `ArrivalsLineChart.tsx` has zero `as` casts.
- Typed empty state (`points.length === 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- The "Corridor leakage" section is a deliberate disabled placeholder — never fabricate or zero-fill leakage data to fill it (Data Continuity Protocol).

## Gotchas
- `yoyPct` compares the latest month to the observation nearest 12 months earlier within a ±45-day window (BS→AD month-ends are not evenly spaced). Returns `null` (rendered "—") when no prior-year match exists or the prior value is zero — never a fabricated band.
- `d3-scale` was added as a dependency for this feature (`scaleTime`/`scaleLinear`); `d3-shape` (for `line()`) was already present. Both are wrapped in `d3-shape.ts`.
- The chart renders the same SVG at all viewports (it is a single hero viz that scales via `viewBox`); the sr-only `<table>` is the non-visual fallback. There is no separate <640px layout because a line chart degrades gracefully where a Sankey does not.

## Related
- ADRs: ADR-0012 (viz adapter cast location), ADR-0003 (no API parsing), ADR-0011 (data-unit identity), ADR-0013 (BS/AD fiscal labels)
- Docs: `docs/research/DATA_BUILDOUT_PLAN.md` §#27 (spec + the AD-vs-BS gotcha), `docs/UI_ACCEPTANCE.md`, `src/lib/viz/adapters/d3-shape.ts`
- Repository pattern reference: `src/features/money-map/server/queries.ts` (Result + safeQuery + Zod-at-boundary)
