# Source: Nepal administrative boundaries — 753 local levels (palika choropleth geometry)

**source_id:** `nepal-admin-boundaries`
**Status:** active
**Tier:** Reference (tier null — base geometry, not a fact feed)
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11 (render-verified as Nepal; 753/753 federal-code match)

> Choropleth base geometry registered under [ADR-0025](../decisions/0025-choropleth-geo-adapter.md). This is reference geometry — it produces no `*_facts` rows; it is the shared base map every choropleth (migration, census, land-use, District MRI) renders data onto.

## Publication

- URL: https://github.com/younginnovations/nepal-locallevel-map (file: `out/municipalities.simplified.geojson`)
- Underlying authority: Survey Department, Government of Nepal (official admin boundaries, 2017 federal structure)
- Frequency: ad_hoc (changes only on federal restructuring)
- Format: GeoJSON → built into a precomputed-SVG-path JSON asset
- Requires table extraction: no

## Provenance

- Confidence default: A (authoritative administrative geometry)
- License: gov_open — official Survey Department boundaries; the GitHub repackaging is MIT-licensed
- Ingestion mode: reference_only
- Coverage: 7 provinces / 77 districts / 753 local levels (6 metro, 11 sub-metro, 276 municipality, 460 rural municipality)

## The federal_code join (the crux — ADR-0025 §3)

The source carries its **own** codes (`locallevel_fullcode` = province+district+local), **not** the MoFAGA 8-digit `federal_code` that `entities.slug` / `administrative_units.federal_code` use. The build resolves every feature to its `federal_code` deterministically against [`scripts/geo/crosswalk.csv`](../../scripts/geo/crosswalk.csv) (the canonical 753 from the MoF fiscal-transfer workbook — the same table that seeds the local-level entities):

1. **Exact** (599) — `(district-alias, type, normalized-name)` match.
2. **Fuzzy** (≈141) — confidence-ordered romanization match within the same district (e.g. Aamchowk→Aamchok, Janakpur→Janakpurdham); audited.
3. **Pigeonhole** (≈10) — a district left with exactly one unmatched polygon and one unassigned code must be that pair (correct by elimination).
4. **Explicit renames** (3) — web-verified 2017→2025 renames not romanization-similar: Gangadev←Sukidaha, Sunil Smriti←Suwarnawati, Paribartan←Duikholi (all Rolpa).

Result: **753/753** matched. The built asset embeds the resolved `federal_code` per feature, so runtime joins on `code` only.

## Build

- Pipeline: [`scripts/geo/`](../../scripts/geo/) — `extract_crosswalk.py` (canonical codes) → `build_palika_geo.py` (match + Mercator project + RDP simplify + emit).
- Output asset: `src/lib/viz/geo/palikas-753.geo.json` (~384 KB raw, ~99 KB gzipped; viewBox-normalized SVG paths).
- Reproduce: `python scripts/geo/build_palika_geo.py` (downloads the source GeoJSON if absent).

## Known breakage modes

- `source-repo-removed` — the younginnovations GitHub repo disappears (archive a pinned copy under `scripts/geo/_source/`).
- `local-level-rename-drifts-crosswalk` — a local level is renamed, breaking the name match (update `crosswalk.csv` + `RENAME_OVERRIDE`).
- `federal-restructuring` — a new constitutional restructuring changes the 753 partition (full re-derive).

## Revision policy

Static. Re-run the `scripts/geo/` pipeline only on administrative restructuring or a confirmed boundary/name change. The asset is versioned in git; the match must always be 753/753 or the build refuses to write (no partial asset).

## Notes

Migration Industry vertical + every future choropleth. First consumer: the `/migration` palika choropleth (absent population by origin, View B). Next consumers: census asset/entrepreneurship choropleth (`DATA_BUILDOUT_PLAN.md` #29), Land Use Atlas, District MRI locators.
