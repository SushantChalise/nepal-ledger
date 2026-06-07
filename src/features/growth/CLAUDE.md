# Growth — feature context

**Nepal's headline macro at a glance.** Renders the six core annual series that answer the mission question — *is the economy growing, and is it becoming wealth per person?* — as a KPI strip, a nominal-vs-real GDP trajectory chart, and an inflation rate table, each ~50 fiscal years deep.

Lens / pillar: serves the mission headline ("Where Money Becomes Wealth"); per-capita GDP is the wealth-per-person denominator.
Route(s): `/growth`
Status: live · Nepal Rastra Bank — Database on Nepalese Economy (six DNE indicator slugs, Grade B, annual)

## Data in
- `approved_indicator_values` joined to `indicators` WHERE `slug IN (six growth slugs)`, via `getGrowthData()` (`src/features/growth/server/queries.ts`). One query loads all six series.
- Reads production only (`approved_indicator_values`); never staging.
- Slugs: `dne-gdp-nominal`, `dne-gdp-real` (both `npr_billion`); `dne-gdp-real-growth`, `dne-inflation-rate` (both `percent`); `dne-gdp-per-capita-usd` (`usd`); `dne-cpi` (`index_points`). All source `nrb-dne-xlsx`, confidence B, reporting period `annual` with BS fiscal-year labels like `2081/82`.

## Files
- `server/queries.ts` — `getGrowthData()` returns `Result<GrowthData>` (six `IndicatorSeries`, each with full ascending `points` + `latest` + name/unit/confidence/source). Single JOIN query over all six slugs, Zod-validated at the DB boundary, ordered by `slug, reporting_period_ad_end ASC`, then grouped in TS by `buildSeries()`. Typed `NotFound` (none of the six slugs has any row) / `QueryFailed`; never throws.
- `format.ts` — `formatNprFromBillion` ("NPR X.XX trillion" ≥1000 bn, else "NPR X billion"), `formatNprTrillionCompact` ("NPR 6.1T", axis), `formatUsd` ("USD 1,496"), `formatPercent` ("4.61%"), `formatIndex` ("166.2"), `formatFiscalYear` ("FY 2081/82"), `billionToTrillion`. **Not** `'use client'` — plain module imported by both the Server page and the client chart.
- `components/GdpTrajectoryChart.tsx` — `'use client'`; inline SVG two-line chart (nominal vs real GDP) with a ResizeObserver-driven responsive width, end-of-line text labels, a reduced-motion-aware draw-in per line, a visible text+colour legend, and an always-present visually-hidden `<table>`. Uses `buildTimeScale`/`buildLinearScale`/`buildLinePath` from `src/lib/viz/adapters/d3-shape.ts`.
- `components/RateSeriesTable.tsx` — **Server Component** (no `'use client'`); accessible `<table>` of a percent series (used for CPI inflation) with a decorative (`aria-hidden`) magnitude bar; shows the most-recent N years descending.
- `page` at `src/app/growth/page.tsx` — async Server Component; reuses Pulse `KpiCard` for a four-card strip (nominal GDP, real growth, per-capita USD, inflation); "what this shows" prose tying growth↔per-capita to the mission; GDP chart; inflation table; per-series `SeriesUnavailable` placeholders; source/confidence (Grade B)/unit footer. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Unit honesty (ADR-0011).** Nominal & real GDP are `npr_billion` → display as **NPR trillion** (÷ 1,000); never print bare billions as "trillion" below 1,000 bn. Per-capita is **USD per person** — always dollar-labelled, never NPR. Growth & inflation are **percent**. CPI is an **index level** (base ≈ 2014/15 = 100), labelled as an index, never currency. A bare number is never shown without its unit. All conversion lives in `format.ts` — do not inline a different divisor.
  - Worked example: nominal GDP `6107` npr_billion ÷ 1000 = 6.107 → **"NPR 6.11 trillion"**; per-capita `1496` usd → **"USD 1,496"**.
- **Per-capita USD is featured prominently** — it is the "wealth per person" number central to the mission; it gets its own KPI card and is named in the prose.
- A **single empty series must not blank the page**: `getGrowthData()` returns each series independently (empty `points` / null `latest`), and the page renders `SeriesUnavailable` for any missing one. The page's empty state fires only when *none* of the four headline series has a latest value; `NotFound` fires only when *no* slug has any row.
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map/tourism-rupee gotcha).
- D3 type-bridging `as` casts belong ONLY in `src/lib/viz/adapters/d3-shape.ts` (ADR-0012). `GdpTrajectoryChart.tsx` has zero `as` casts.
- Typed empty state and typed error state (`!result.ok`) must remain; never throw from the page. Never zero-fill or fabricate a missing series/year (Data Continuity Protocol).

## Gotchas
- These are **annual** series, so the BS fiscal-year label (`2081/82`) is the canonical period (unlike the monthly tourism series where the AD month-end is canonical to dodge a parser skew). The chart still *plots* on `reporting_period_ad_end` for correct spacing but *labels* x-ticks with the BS fiscal-year string; the accessible table is keyed on the fiscal year.
- `approved_indicator_values.value` is `numeric(24,6)` → postgres-js returns it as a string (e.g. `"6107.000000"`); coerced with `Number()` after a `Number.isFinite` guard. Non-finite values are skipped, never zero-filled.
- The GDP chart joins nominal+real on `fiscalYearBs` in its sr-only table; if a fiscal year exists in one series but not the other, the missing cell renders `NaN`→"—"-like (the join Map lookup falls back to `NaN`). Both DNE series are co-published per year, so this is not expected in practice.
- The nominal/real lines are told apart by an in-SVG end label AND the legend (text + colour), never colour alone (WCAG AA). The whole SVG is effectively decorative — every value is also in a table on the page.
- No `cn()` helper exists in this repo; className strings are plain template literals, matching the other route pages.

## Related
- ADRs: ADR-0012 (viz adapter cast location), ADR-0011 (data-unit identity / magnitude verification), ADR-0013 (BS fiscal-year period dating), ADR-0003 (no API parsing).
- Docs: `docs/UI_ACCEPTANCE.md` (accessibility + content gates), `src/lib/viz/adapters/d3-shape.ts`.
- Pattern reference: `src/features/tourism-rupee/*` (closest analog — long annual/periodic series with a line chart) and `src/features/state-enterprises/*` (Server-Component accessible table + decorative bar). Repository helpers: `src/lib/db/repositories/approved-indicator-values.ts` (consulted; not extended — see queries.ts "WHY A LOCAL QUERY").
