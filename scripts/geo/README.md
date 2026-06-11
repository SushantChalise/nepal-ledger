# `scripts/geo/` — choropleth base geometry pipeline

Builds the committed palika (753 local-level) choropleth geometry asset that
every map in the app renders data onto. See [ADR-0025](../../docs/decisions/0025-choropleth-geo-adapter.md)
for the design and [docs/sources/nepal-admin-boundaries.md](../../docs/sources/nepal-admin-boundaries.md)
for the registered source + provenance.

## What it produces

`src/lib/viz/geo/palikas-753.geo.json` — a static, versioned asset:

```json
{ "viewBox": "0 0 1000 578",
  "features": [ { "code": "80101011", "nameEn": "Biratnagar Metropolitan City",
                  "nameNe": "…", "district": "Morang", "type": "metropolitan_city",
                  "d": "M…Z" }, … 753 ] }
```

`code` is the MoFAGA 8-digit `federal_code` — the join key to
`entities.slug` / `administrative_units.federal_code`. `d` is a Mercator-projected,
RDP-simplified, viewBox-normalized SVG path, rendered directly (no runtime geo
library — ADR-0025).

## Files

| File | Role |
|---|---|
| `extract_crosswalk.py` | Emits `crosswalk.csv` — the canonical 753 `(federal_code, name_en, name_ne, district_en, type)` from the MoF fiscal-transfer workbook (the same table that seeds local-level entities). openpyxl only (no pandas). |
| `crosswalk.csv` | The committed join-key table (753 rows). |
| `build_palika_geo.py` | Downloads the source GeoJSON, resolves every feature to its `federal_code` (4-phase deterministic match → 753/753), projects + simplifies, writes the asset. Refuses to write a partial asset. |
| `_source/` | Cached download of the source GeoJSON (gitignored; re-fetched on demand). |

## Reproduce

```bash
# 1. (Re)generate the crosswalk from the MoF workbook — only needed if the
#    canonical local-level list changes:
python scripts/geo/extract_crosswalk.py "Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx"

# 2. Build the asset (downloads the source GeoJSON if absent):
python scripts/geo/build_palika_geo.py
```

The build prints the match tally and asset size, and exits non-zero (writing
nothing) if it cannot resolve all 753 federal codes.

## Invariants

- **753/753 or nothing.** A partial match never writes an asset (silent gaps in
  a national map are worse than a failed build).
- **Never fabricate a join.** Non-romanization renames are resolved by
  pigeonhole (elimination) or an explicit, web-verified `RENAME_OVERRIDE` — not
  by guessing (Data Continuity Protocol).
- **Deterministic.** No `Date.now()`/randomness; same inputs → byte-identical
  asset.
