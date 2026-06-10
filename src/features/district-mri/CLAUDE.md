# District MRI — feature context

**Per-district economic dashboard** rolling federal fiscal transfers and 2021 census household indicators up to the district level for Nepal's 5 Year-1 launch districts.

Lens / pillar: District MRI (STRATEGY.md §"District MRI"); primarily serves Pillar 5 "Money Becomes Wealth" (census asset/entrepreneurship indicators) and Pillar 2 "Money Out" (fiscal transfers received)
Route(s): `/districts` (index) · `/districts/[district]` (5 static pages)
Status: live · MoF Intergovernmental Fiscal Transfers FY 2082/83 + CBS NPHC 2021 census

## Data in

- `local_government_fiscal_transfers` and `census_facts`, both joined to `entities` (kind = 'local_level'), aggregated by `getDistrictMriData(districtEn)` (`src/features/district-mri/server/queries.ts`)
- Reads production only; no staging equivalent. No scraper, no migration — pure render over live data.

## Files

- `launch-districts.ts` — the 5-district registry (`LAUNCH_DISTRICTS`); each `districtEn` is the EXACT `entities.metadata->>'district_en'` join key
- `server/queries.ts` — `getDistrictMriData(districtEn): Promise<Result<DistrictMriData>>`; two Zod-at-boundary `safeQuery` aggregations (fiscal grants-by-type; census via an explicit slug allowlist). Also exports `CENSUS_METRICS` (the allowlist) and `MISSING_PILLAR_FIELDS`
- `format.ts` — `formatNprCrore` / `formatPercent` / `formatCount`; **not** `'use client'` — intentionally a plain module
- `components/MetricBar.tsx` — Server Component; one census ratio as a labelled bar
- `components/MissingDataPanel.tsx` — Server Component; honest list of un-ingested Pillar fields
- `page` at `src/app/districts/page.tsx` — index; `src/app/districts/[district]/page.tsx` — detail with `generateStaticParams` + typed empty/error states

## Invariants (don't break these)

- **Roll-up is via `entities.metadata->>'district_en'` (a NAME string), NOT `federal_code`.** The 8-digit code does NOT encode district (see `scrapers/cbs_nphc/generate_crosswalk.py`); there are NO `kind='district'` entities (verified: count = 0). Every aggregation joins palika → entities and filters on the name string. A worker who joins on `federal_code` builds a broken, empty result.
- `LAUNCH_DISTRICTS[].districtEn` MUST equal the live `district_en` byte-for-byte (canonical MoF spelling: `Kathmandu`, `Chitwan`, `Kaski`, `Jhapa`, `Morang` — note "Chitwan", not the CBS "Chitawan").
- Census ratios derive their denominator from **that table's own `rowtotal`** slug, summed across the district — never another table, never hard-coded.
- Census slugs are matched via an explicit **allowlist** (`CENSUS_METRICS`). NEVER LIKE-match `indicator_slug` — a stray dimensional slug would silently corrupt the aggregate.
- Fiscal `unit` is `npr_crore` (verified for all 5 districts) — format via `formatNprCrore()`. (The fiscal-transfers table's column *default* is `NPR_thousand`, but the cleaned MoF ingest stored crore; trust the row's `unit`, which is read in the header.)
- `format.ts` MUST remain a plain (non-`'use client'`) module — see Money Map gotcha; a client-exported fn imported by a Server page 500s the page.
- Typed empty state (no data) and typed error state (`!result.ok`) must remain; never throw from a page. Unknown slug → `notFound()`; known slug with no rows → in-page empty state.
- Un-ingested Pillar fields go to `MissingDataPanel` — never fabricated or zero-filled (Data Continuity Protocol).

## Gotchas

- **`= ANY(<js array>)` does not work inside a drizzle `sql` template.** postgres-js expands the JS array into a tuple `($2,$3,…)` and `= ANY(tuple)` is a Postgres type error. Use `IN (${sql.join(slugs.map(s => sql\`${s}\`), sql\`, \`)})` — each slug is its own bind param (injection-safe).
- The census numerator for **household entrepreneurship** is derived as `rowtotal − nobusiness` (the only subtractive metric; encoded in `SUBTRACTIVE_NUMERATOR_SLUGS`). All current census metrics come from single-row-per-palika tables (Hhld01/10/11/12), so no `sexname='Total'` filter is needed. A future metric from a multi-row table (Hhld18/19/20) MUST pin `sexname='Total'` dimension slugs explicitly in its allowlist entry.
- Label census wealth metrics precisely — "female house & land ownership", "household entrepreneurship", "internet access". There is NO census bank-account/loan table; do NOT say "financial inclusion".
- `palikaCount` uses `COUNT(DISTINCT e.id)` because the count query LEFT JOINs `census_facts` (one entity has many fact rows); a plain `COUNT(*)` over-counts by ~700x.

## Related

- ADRs: ADR-0011 (data-unit verification — read the federal code, don't fuzzy-match), ADR-0009 (entities/source registry)
- Docs: `docs/UI_ACCEPTANCE.md` (mobile/accessibility/required content gates), `docs/research/DATA_BUILDOUT_PLAN.md` §"#26" (full spec + the load-bearing correction), `scrapers/cbs_nphc/parser.py` (census slug convention), `src/features/money-map/CLAUDE.md` (the patterns this feature mirrors)
