# ADR-0025: Choropleth Geometry Layer — TopoJSON Boundaries + `d3-geo` Adapter

- **Status:** Accepted (implemented 2026-06-11 — see Implementation Note)
- **Date:** 2026-06-11
- **Deciders:** Mother Opus (user-approved 2026-06-11)
- **Tags:** ui, viz, geo, conventions, data-source

## Implementation Note (2026-06-11) — built as precomputed SVG paths

The Phase-1 implementation **kept the load-bearing decisions** of this ADR — geometry is a static, versioned asset (not PostGIS); it is a registered source (`nepal-admin-boundaries`) with a recorded license; every feature is resolved to its MoFAGA 8-digit `federal_code` by a deterministic crosswalk baked in at build time; the asset lives under `src/lib/viz/geo/` — but **changed two format choices** for a simpler, lighter result:

1. **Precomputed SVG paths, not runtime TopoJSON + `d3-geo`.** The build (`scripts/geo/build_palika_geo.py`) Mercator-projects, RDP-simplifies, and viewBox-normalises the geometry into ready-to-render SVG `d` strings (`palikas-753.geo.json`, ~99 KB gzipped). The runtime is a **plain Server Component** rendering `<path>` elements — **zero client JS, no `d3-geo`, no `topojson-client`, no `src/lib/viz/geo/d3-geo.ts` adapter** (so ADR-0012 does not apply here — there is nothing to type-bridge). This was driven by (a) avoiding a cross-worktree npm-dependency install for a static asset, and (b) a strictly smaller mobile payload than shipping TopoJSON + a client geo library.
2. **Mercator projection** (simple, dependency-free, computed in the Python build) rather than `geoConicConformal`. At Nepal's latitude band the shape fidelity is more than adequate for a thematic fill — render-verified against the known national outline.

Everything below is the originally-accepted design; items §1 (TopoJSON), §4 (`d3-geo.ts` adapter) and §5's projection are **superseded by this note**. TopoJSON + runtime `d3-geo` remain the documented upgrade path **if** we later need interactive client-side reprojection or zoom-dependent reprojection that precomputed paths cannot serve.

## Context

Nepal Ledger's largest unrendered asset is **geographic**: `census_facts` holds 531,618 rows at 753-palika grain (11 NPHC-2021 tables), and `administrative_units` carries the full 7→77→753→ward hierarchy with MoFAGA federal codes. Multiple planned surfaces are choropleths — the migration atlas (`MIGRATION_ATLAS_PLAN.md`, ~11 of 28 maps reproducible from census data alone), the census asset/entrepreneurship map (`DATA_BUILDOUT_PLAN.md` #29), the Land Use Atlas, and District MRI locators.

Every one of these is **blocked on the same missing primitive**: there is no Nepal boundary geometry in the repo and no `d3-geo` adapter. `src/features/migration-source/CLAUDE.md` records the deferral explicitly ("no Nepal district GeoJSON / `d3-geo` in repo, and district identity is not derivable from the federal code"). `package.json` has `d3-sankey`, `d3-scale`, `d3-shape` but **not** `d3-geo` or `topojson-client`. `src/lib/viz/adapters/` holds `d3-sankey.ts` and `d3-shape.ts` — the established home for charting type-bridges (ADR-0012).

Three questions must be answered before any choropleth ships, and they are architectural (cross-feature, long-lived), so they belong in an ADR rather than a feature PR:

1. **Where does boundary geometry live** — in Postgres (PostGIS), or as a static versioned asset?
2. **What is the join key** between a geometry feature and a `census_facts` / `administrative_units` row, given the Atlas's own warning that district identity is not derivable from the federal code?
3. **How is 753-palika geometry served to a mobile-first audience** (65%+ Android) without blowing the performance budget (UI_ACCEPTANCE.md, Lighthouse > 90)?

The user has decided **palika (753) granularity first** (2026-06-11), which raises the performance stakes and makes (3) load-bearing.

## Decision

### 1. Geometry is a static, versioned TopoJSON asset — not in the database
Boundaries are reference geometry that change only on federal restructuring (last: 2017). They do not belong in the transactional fact store. We ship **TopoJSON** (not raw GeoJSON) as a build-time asset under `src/lib/viz/geo/` (or `public/geo/` for client fetch), at three dissolved levels generated from one palika source: `palikas-753.topojson`, `districts-77.topojson`, `provinces-7.topojson`. TopoJSON is chosen over GeoJSON for its shared-arc topology (typically 5–10× smaller) and clean dissolve/merge to higher levels via `topojson-client.merge`. PostGIS is rejected for Year-1 (ADR-0006 local-Postgres posture; no spatial queries are needed — we render, not intersect).

### 2. The boundary set is a **registered source** with a recorded license
Geometry provenance is held to the same bar as any data feed (ADR-0009). A new registry row `nepal-admin-boundaries` records the chosen provider, license, and the admin vintage (2017 federal structure, 753 units). Provider preference order: (a) Survey Department official, (b) OCHA/HDX **COD-AB** (Common Operational Dataset — Administrative Boundaries, openly licensed, MoFAGA-aligned codes), (c) a community GeoJSON only if (a)/(b) are unavailable, license permitting. The chosen file is archived on download (Data Continuity Protocol); the simplification/quantization recipe is committed so the asset is reproducible.

### 3. Join key = MoFAGA federal code, via an explicit crosswalk baked into the asset
At asset-build time, each geometry feature is tagged with the canonical 8-digit (local-level) / 3-digit (district) / 1-digit (province) MoFAGA `federal_code`, matching `administrative_units.federal_code`. Where the provider's codes differ (HDX `ADM3_PCODE`, etc.), the build step resolves them to MoFAGA codes once and writes the resolved code into the TopoJSON `properties`. This makes the Atlas's "district identity not derivable from federal code" problem a **solved, one-time build concern**, not a runtime join risk. Features carry `{ code, nameEn, nameNe }`; data joins on `code` only.

### 4. Type-bridges live in `src/lib/viz/adapters/d3-geo.ts` (ADR-0012 extended)
A new adapter `src/lib/viz/adapters/d3-geo.ts` exposes the projection + path generation behind narrow, cast-contained functions (e.g. `buildChoroplethPaths({ topology, objectName, accessor })` returning `{ code, d, value }[]` plus the projection for hit-testing). Any `d3-geo`/`topojson-client` generic-type bridges are confined here per ADR-0012; feature components stay cast-free and import only the adapter's output types. Projection: **`geoConicConformal`** fitted to Nepal's bounds (better shape fidelity for an east-west-elongated country than `geoMercator`); `fitSize` to the SVG viewport.

### 5. Mobile performance strategy for 753 palikas
- **Quantize + simplify** the palika TopoJSON to a target ≤ ~250 KB gzipped (tune via `topojson` `-q` quantization and `toposimplify` weight); districts/provinces are far smaller.
- **Level-gated detail:** default national view renders the **district (77)** layer; palika geometry loads on zoom/drill-in, not on first paint. This keeps initial payload small while honoring "palika-first" as the *data* grain.
- **Inline SVG `<path>`** (consistent with existing chart components), reduced-motion-aware, with an always-present visually-hidden `<table>` fallback (the `DestinationBarChart` accessibility pattern). No map-tile/runtime-GIS dependency.

## Alternatives Considered

- **PostGIS + geometry in Postgres.** Adds a spatial extension, migration surface, and query complexity for zero analytical benefit — we only need to draw, not spatially query. Rejected for Year-1; revisit if a "which projects fall in a flood polygon" feature appears.
- **Raw GeoJSON instead of TopoJSON.** Simpler tooling, but 5–10× larger and no free dissolve-to-district/province. Fails the mobile budget at 753 features. Rejected.
- **A mapping library (Leaflet / MapLibre / react-simple-maps).** Heavyweight (tiles, runtime, bundle) for what is a static thematic fill. Conflicts with the lean inline-SVG charting pattern and the Lighthouse budget. `react-simple-maps` is the closest but still wraps `d3-geo` we can call directly. Rejected; we own a thin adapter instead.
- **Geometry unversioned / fetched from a CDN at runtime.** Breaks provenance (ADR-0009) and the Data Continuity Protocol, and adds a runtime external dependency. Rejected — geometry is archived + registered like any source.
- **District-77 only, defer palika.** Lighter, but the user explicitly chose palika-first and `census_facts` is palika-native; district is a dissolve of palika, so building palika gives district for free. We adopt palika as the source-of-truth geometry with district as a generated, default-rendered dissolve.

## Consequences

### Positive
- Unblocks ~11 migration maps + the census choropleth (#29) + Land Use Atlas + District MRI locators with **one** reusable primitive.
- Geometry provenance is first-class (registered, licensed, archived) — consistent with the project's truth-layer discipline.
- The federal-code crosswalk is solved once at build time; every future choropleth joins on `code` with no per-feature ambiguity.
- `d3-geo.ts` becomes the reference adapter for all thematic-map work, mirroring `d3-sankey.ts`.

### Negative
- Adds two runtime deps (`d3-geo`, `topojson-client`) + a build-time dep (`topojson-server`/`topojson-simplify` or the `topojson` CLI) and a generated asset to maintain.
- The asset-build (download → reproject → simplify → quantize → tag federal codes → dissolve) is a one-time scripted pipeline that must itself be documented (a `scripts/geo/` README per the Documentation Gate).
- Palika geometry, even simplified, is the single largest static asset in the repo; the ≤250 KB target needs verification on real boundary data and may force a stricter simplification weight.

### Neutral / unknown
- Exact provider (Survey Dept vs HDX COD-AB) is pending the registry decision (`MIGRATION_ATLAS_PLAN.md` §9.2); the adapter and join design are provider-independent.
- Whether to serve the asset from `public/` (client fetch, cacheable) or import it into a Server Component (inlined, no extra request) is a Phase-1 implementation call, not an architectural one.

## References

- [`MIGRATION_ATLAS_PLAN.md`](../research/MIGRATION_ATLAS_PLAN.md) — the plan this unblocks (§1 "the unlock", §6 geometry decision).
- [ADR-0012](0012-viz-adapter-cast-location.md) — viz type-bridges live in `src/lib/viz/adapters/`; this ADR extends it with `d3-geo.ts`.
- [ADR-0006](0006-nextjs-16-not-15.md) / local-Postgres posture — why not PostGIS in Year-1.
- [ADR-0009](0009-source-registry-single-source-of-truth.md) — geometry is a registered source (`nepal-admin-boundaries`).
- `src/features/migration-source/CLAUDE.md` — the explicit GeoJSON deferral resolved here.
- `docs/research/DATA_BUILDOUT_PLAN.md` #29 — `census-asset-entrepreneurship-choropleth` (the second consumer of `d3-geo.ts`).
- `docs/UI_ACCEPTANCE.md` — mobile/performance gates the 753-palika asset must pass.
- `src/lib/db/schema/administrative-units.ts` — the `federal_code` join target.
