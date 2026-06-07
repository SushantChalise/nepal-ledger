# Migration Source — feature context

**Absent-population-by-destination ranking (View A).** Renders Nepal's absent population (household members living abroad on census night 2021) ranked by destination region as a horizontal bar chart.

Lens / pillar: labour-migration view; serves Pillar 2 "Money Out" (people leaving to work abroad — the census complement to the remittance/migration story)
Route(s): `/migration`
Status: live · CBS National Population & Housing Census 2021 (`census_facts`, source_table_id `Hhld19_AbsentPopnByCountry`, Grade A)

## CRITICAL semantic correction (read before touching this feature)
`Hhld19_AbsentPopnByCountry` is **absent population (migrant workers) by DESTINATION region** — it is a **person COUNT, NOT remittance NPR**. The unit is people (count). Never label this page "remittance" or imply a rupee flow. (See `docs/research/DATA_BUILDOUT_PLAN.md` §6 — the plan flags that the named deliverable "remittance source map" does not exist as money; only the headcount does.)

## Data in
- `census_facts` WHERE `source_table_id = 'Hhld19_AbsentPopnByCountry'`, via `getMigrationByCountrySeries()` (`src/features/migration-source/server/queries.ts`)
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
- `page` at `src/app/migration/page.tsx` — async Server Component; reuses Pulse `KpiCard`; "what this shows" prose, source/confidence/unit footer (Grade A), and a disabled "Remittance by recipient district — coming soon" placeholder. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Unit is people (count), never currency.** Source label is exactly "CBS National Population & Housing Census 2021"; confidence is **A** (official census enumeration). Never phrase any figure as remittance / NPR.
- The aggregation slice is **sex=total + age=all-ages + per-country (exclude rowtotal)**. Changing it (e.g. summing across age bands *and* all-ages, or across sexes) double-counts. If you must change it, re-run the three marginal checks (see scratch verification in the build report).
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map/tourism-rupee gotcha).
- D3 type-bridging `as` casts belong ONLY in `src/lib/viz/adapters/d3-shape.ts` (ADR-0012). `DestinationBarChart.tsx` has zero `as` casts.
- Typed empty state (`destinations.length === 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- The "Remittance by recipient district" section is a deliberate disabled placeholder — never fabricate or zero-fill a rupee figure to fill it (Data Continuity Protocol). View B (the district choropleth) is deferred: no Nepal district GeoJSON / `d3-geo` in repo, and district identity is not derivable from the federal code (see plan §6).

## Gotchas
- The census uses **regional** destination buckets, not individual countries (see "Destination granularity" above). The bar labels say "Middle East", "ASEAN", etc. — matching the underlying data — not "Saudi Arabia"/"Malaysia".
- `census_facts.value` is a numeric string from postgres-js; coerced with `Number()` after a `Number.isFinite` guard.
- The chart shares the same SVG at ≥640px and swaps to a flex bar list <640px because the region labels are long and do not fit a narrow SVG left gutter; the sr-only `<table>` is the non-visual fallback at every viewport.

## Related
- ADRs: ADR-0012 (viz adapter cast location), ADR-0003 (no API parsing), ADR-0011 (data-unit identity)
- Docs: `docs/research/DATA_BUILDOUT_PLAN.md` §#28 (View A spec) + §6 (the count-not-remittance correction), `docs/UI_ACCEPTANCE.md`, `src/lib/viz/adapters/d3-shape.ts`
- Pattern reference: `src/features/tourism-rupee/*` and `src/features/money-map/server/queries.ts` (Result + safeQuery + Zod-at-boundary)
