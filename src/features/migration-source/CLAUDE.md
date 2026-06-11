# Migration Source — feature context

**View A — absent-population-by-destination ranking.** Renders Nepal's absent population (household members living abroad on census night 2021) ranked by destination region as a horizontal bar chart.

**View B — migration-intensity choropleth (palika).** The same census table mapped to each of the 753 local levels as the **share of the local population living abroad** (absent ÷ total population) — a 6-class quantile choropleth (`PalikaChoropleth`) matching the NDRI Atlas's headline "% of absentee population" map. Server-rendered SVG, **zero client JS**, native `<title>` tooltips (show both % and headcount). Geometry: the shared `src/lib/viz/geo/palikas-753.geo.json` asset, joined on `federal_code` (ADR-0025). Still **people, not rupees** underneath.

Lens / pillar: labour-migration view; serves Pillar 2 "Money Out" (people leaving to work abroad — the census complement to the remittance/migration story)
Route(s): `/migration`
Status: live · CBS National Population & Housing Census 2021 (`census_facts`, source_table_id `Hhld19_AbsentPopnByCountry`, Grade A) · base geometry source `nepal-admin-boundaries` (Grade A, ADR-0025)

## CRITICAL semantic correction (read before touching this feature)
`Hhld19_AbsentPopnByCountry` is **absent population (migrant workers) by DESTINATION region** — it is a **person COUNT, NOT remittance NPR**. The unit is people (count). Never label this page "remittance" or imply a rupee flow. (See `docs/research/DATA_BUILDOUT_PLAN.md` §6 — the plan flags that the named deliverable "remittance source map" does not exist as money; only the headcount does.)

## Data in
- View A: `census_facts` WHERE `source_table_id = 'Hhld19_AbsentPopnByCountry'`, via `getMigrationByCountrySeries()` (`src/features/migration-source/server/queries.ts`)
- View B: same table summed **per origin palika**, LEFT JOINed to the total-population denominator, via `getAbsenteeShareByPalika()` — joins `census_facts` → `entities` (kind=`local_level`, `slug` = 8-digit `federal_code`) and returns `byCode: Record<federal_code, {people, population, pct}>`. Denominator = `Indv01_PopulationBySex` `total` column (slug `indv01-populationbysex-total`, verified by the cbs_nphc parser test). Geometry comes from the static `src/lib/viz/geo/palikas-753.geo.json` asset (no DB).
- Reads production only (`census_facts`); no staging equivalent. No repository edits.

## Aggregation (the non-double-counting slice — verified against live DB)
Slug shape: `hhld19-absentpopnbycountry-<sex>-<agegrp>-<countrycode>-<countryname>`
- sex ∈ {`total`, `male`, `female`}; agegrp ∈ {`00-14`, `15-24`, `25-34`, `35-44`, `45-54`, `55-64`, `65` (=65+), `all-ages`, `not-stated`}; country ∈ {`a-india` … `m-notstd`, `rowtotal`}.
- **We take exactly one marginal slice:** `sex='total'` AND `agegrp='all-ages'` AND `country <> 'rowtotal'`, i.e. slug `LIKE 'hhld19-absentpopnbycountry-total-all-ages-%'` excluding the `…-rowtotal` country marginal. Then `SUM(value)` over all 753 palikas, grouped by destination code.
- This avoids double-counting across sex (total already = male+female) and across age (all-ages already = the sum of age bands). Verified three ways against the table's own marginals — the 13 country sums, the age-band sums, and male+female all equal **2,190,592** (the published 2021 absent-population total).
- `rowtotal` (across-country marginal) is excluded from the per-destination bars; it equals the national total.

## Destination granularity (don't mislabel)
The census groups destinations by **region**, with India broken out alone. Individual countries roll up: Saudi Arabia / Qatar / UAE → "Middle East"; Malaysia → "ASEAN". The `DESTINATION_LABELS` map in `queries.ts` reflects this (e.g. `d-midleast` → "Middle East (incl. Saudi Arabia, Qatar, UAE)"). Do not relabel these as single countries — the source does not provide a per-country split.

## Files
- `server/queries.ts` — `getMigrationByCountrySeries(topN = 15)` returns `Result<MigrationByCountry>` (`destinations` ranked desc, `totalPeople`, `palikaCount`, `censusYearAd`); single GROUP BY query, Zod-validated at the DB boundary; typed `NotFound`/`QueryFailed` states, never throws.
- `format.ts` — `formatPeople` (compact "804.6K"), `formatPeopleFull` (grouped "8,04,614"), `formatSharePct`. **Not** `'use client'` — plain module imported by both the Server page and the client chart.
- `components/DestinationBarChart.tsx` — `'use client'`; ≥640px inline SVG horizontal bar chart (ResizeObserver width, reduced-motion-aware grow-in), <640px stacked bar list, and an always-present visually-hidden `<table>`. Uses `buildLinearScale` from `src/lib/viz/adapters/d3-shape.ts` for the count→width scale only.
- `components/PalikaChoropleth.tsx` (View B) — **Server Component, no `'use client'`.** Renders 753 `<path>` from the geometry asset, filled by a 6-class quantile scale of `byCode[federal_code].pct` (share abroad); native `<title>` tooltips show both % and headcount; a legend (with national %) + a visually-hidden top-30 `<table>`. No D3 / no viz-adapter cast (projection precomputed, classification is plain numeric — ADR-0012 N/A here).
- `choropleth-scale.ts` — pure, testable `quantileBreaks` + `classOf` (no JSX/React) used by the choropleth. Covered by `choropleth-scale.test.ts`.
- `src/lib/viz/geo/palikas.ts` — Zod-validated loader for the geometry asset (`palikas-753.geo.json`); exports `palikaGeometry` + `PALIKA_COUNT`. Asset invariants covered by `palikas.test.ts` (753 features, unique 8-digit codes, 77 districts, 6/11/276/460 type split).
- `page` at `src/app/migration/page.tsx` — async Server Component; reuses Pulse `KpiCard`; "what this shows" prose, source/confidence/unit footer (Grade A), View A chart + View B choropleth (each with its own typed fallback), and a disabled "Remittance by recipient district — coming soon" placeholder. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Unit is people (count), never currency.** Source label is exactly "CBS National Population & Housing Census 2021"; confidence is **A** (official census enumeration). Never phrase any figure as remittance / NPR.
- The aggregation slice is **sex=total + age=all-ages + per-country (exclude rowtotal)**. Changing it (e.g. summing across age bands *and* all-ages, or across sexes) double-counts. If you must change it, re-run the three marginal checks (see scratch verification in the build report).
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map/tourism-rupee gotcha).
- D3 type-bridging `as` casts belong ONLY in `src/lib/viz/adapters/d3-shape.ts` (ADR-0012). `DestinationBarChart.tsx` has zero `as` casts.
- Typed empty state (`destinations.length === 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- The "Remittance by recipient district" section is a deliberate disabled placeholder — never fabricate or zero-fill a rupee figure to fill it (Data Continuity Protocol). This is **money**; we have only the people-count, so it stays disabled until real flow data is ingested.
- **View B (palika choropleth) is implemented** (ADR-0025) as **migration intensity** — share of population abroad (absent ÷ total), matching the Atlas's headline map. NOT a rupee map. Palikas with no absent value, or no population denominator, render in the neutral "no data" fill with `pct = null` — never zero-filled or fabricated. Geometry join is on `federal_code`; the build guarantees 753/753 or refuses to ship (see `scripts/geo/`).

## Gotchas
- The census uses **regional** destination buckets, not individual countries (see "Destination granularity" above). The bar labels say "Middle East", "ASEAN", etc. — matching the underlying data — not "Saudi Arabia"/"Malaysia".
- `census_facts.value` is a numeric string from postgres-js; coerced with `Number()` after a `Number.isFinite` guard.
- The chart shares the same SVG at ≥640px and swaps to a flex bar list <640px because the region labels are long and do not fit a narrow SVG left gutter; the sr-only `<table>` is the non-visual fallback at every viewport.

## Related
- ADRs: ADR-0012 (viz adapter cast location), ADR-0003 (no API parsing), ADR-0011 (data-unit identity)
- Docs: `docs/research/DATA_BUILDOUT_PLAN.md` §#28 (View A spec) + §6 (the count-not-remittance correction), `docs/UI_ACCEPTANCE.md`, `src/lib/viz/adapters/d3-shape.ts`
- Pattern reference: `src/features/tourism-rupee/*` and `src/features/money-map/server/queries.ts` (Result + safeQuery + Zod-at-boundary)
