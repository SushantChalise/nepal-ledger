"""Build the committed palika choropleth geometry asset (ADR-0025).

Pipeline (pure-Python, no geo/npm deps so it runs in a bare worktree):

  source GeoJSON (775 features, younginnovations) ──┐
                                                    ├─► 4-phase federal_code match
  crosswalk.csv (753 MoFAGA codes ↔ names) ─────────┘        (exact → fuzzy → pigeonhole → rename overrides)
        │
        ├─► dissolve multipart features by source fullcode (753 units)
        ├─► Mercator-project + fit to a fixed viewBox
        ├─► Ramer–Douglas–Peucker simplify + integer quantize
        └─► emit src/lib/viz/geo/palikas-753.geo.json  ({viewBox, features:[{code,nameEn,nameNe,district,d}]})

Why precomputed SVG paths (not runtime TopoJSON + d3-geo): the geometry is
static (changes only on federal restructuring), the audience is mobile-first
(no client-side geo library), and this keeps the runtime dependency-free.
ADR-0025 records this choice. d3-geo/TopoJSON remain a future option if we add
interactive reprojection / zoom.

The federal_code join is the crux (ADR-0025 §3): the source carries its own
codes + names, NOT MoFAGA's 8-digit federal_code, so we resolve every feature
to federal_code by (district, type, name) against the canonical crosswalk. The
3 phases below are fully deterministic and auditable; the only hand-curated
input is RENAME_OVERRIDE (3 Rolpa units whose 2017→2025 renames are not
romanization-similar — web-verified, see module docstring of build report).

Usage:
    python scripts/geo/build_palika_geo.py            # downloads source if absent
    python scripts/geo/build_palika_geo.py --source <path.geojson>

Exit 0 on success (753/753 matched); non-zero (and no asset written) otherwise.
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

HERE: Final = Path(__file__).resolve().parent
REPO: Final = HERE.parent.parent
CROSSWALK_CSV: Final = HERE / "crosswalk.csv"
SOURCE_GEOJSON: Final = HERE / "_source" / "municipalities.simplified.geojson"
SOURCE_URL: Final = (
    "https://raw.githubusercontent.com/younginnovations/nepal-locallevel-map/"
    "master/out/municipalities.simplified.geojson"
)
OUT_ASSET: Final = REPO / "src" / "lib" / "viz" / "geo" / "palikas-753.geo.json"

EXPECTED_UNITS: Final = 753

# Source `locallevel_type` → our canonical slug. Anything else (National Park,
# Wildlife Reserve, Hunting Reserve, …) is NOT a local level and is dropped.
TYPE_MAP: Final[dict[str, str]] = {
    "Gaunpalika": "rural_municipality",
    "Nagarpalika": "municipality",
    "Mahanagarpalika": "metropolitan_city",
    "Upamahanagarpalika": "sub_metropolitan_city",
}

# Source district spelling → crosswalk district spelling (normalized keys).
# NOTE: this is intentionally SEPARATE from the census district-alias map in
# `scrapers/cbs_nphc/generate_crosswalk.py` / `scrapers/_common/municipality_resolver.py`
# — those normalize the NPHC *CSV* gapaname spellings, whereas this normalizes
# the younginnovations *GeoJSON* district spellings (a different upstream), so
# the two alias sets legitimately differ. The canonical target names come from
# the shared MoF workbook (via `crosswalk.csv`), so codes stay consistent.
DISTRICT_ALIAS: Final[dict[str, str]] = {
    "chitawan": "chitwan",
    "kabhrepalanchok": "kavrepalanchok",
    "kapilbastu": "kapilvastu",
    "makawanpur": "makwanpur",
    "nawalparasie": "nawalparasibardaghatsustaeast",
    "nawalparasiw": "nawalparasibardaghatsustawest",
    "rukume": "rukumeast",
    "rukumw": "rukumwest",
    "terhathum": "tehrathum",
}

# Phase-4 explicit renames: source unit (district, source-name) → crosswalk
# name_en, for 2017→2025 renames that are NOT romanization-similar and occur in
# districts with >1 unmatched unit (so pigeonhole can't disambiguate them).
# Web-verified (Rolpa, Lumbini Province): Gangadev←Sukidaha, Sunil Smriti←
# Suwarnawati, Paribartan←Duikholi.
RENAME_OVERRIDE: Final[dict[tuple[str, str], str]] = {
    ("rolpa", "duikholi"): "Paribartan Rural Municipality",
    ("rolpa", "sukidaha"): "Gangadev Rural Municipality",
    ("rolpa", "suwarnabati"): "Sunil Smriti Rural Municipality",
}

_SUFFIX_RE: Final = re.compile(
    r"\s+(rural municipality|sub-metropolitan city|metropolitan city|municipality)$",
    re.IGNORECASE,
)


def _ndist(s: object) -> str:
    k = re.sub(r"[^a-z0-9]", "", str(s).strip().lower())
    return DISTRICT_ALIAS.get(k, k)


def _nname(s: object) -> str:
    s2 = re.sub(r"\(.*?\)", "", str(s)).strip().lower()  # drop parentheticals first
    return re.sub(r"[^a-z0-9]", "", _SUFFIX_RE.sub("", s2))


# ── crosswalk ─────────────────────────────────────────────────────────────


def _load_crosswalk() -> list[dict[str, str]]:
    with CROSSWALK_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ── source download ───────────────────────────────────────────────────────


def _ensure_source(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[geo] source absent; downloading {SOURCE_URL}\n")
    subprocess.run(["curl", "-sL", "-o", str(path), SOURCE_URL], check=True)


# ── 4-phase federal_code match ────────────────────────────────────────────


def _match(features: list[dict], cw: list[dict[str, str]]) -> dict[object, dict[str, str]]:
    """Return {source_fullcode: crosswalk_row} for all 753 local-level units."""
    # dissolve source multiparts: one representative per fullcode, local levels only
    by_fc: dict[object, dict] = {}
    for f in features:
        t = TYPE_MAP.get(str(f["properties"].get("locallevel_type")))
        if not t:
            continue
        by_fc.setdefault(f["properties"].get("locallevel_fullcode"), f["properties"])
    units = list(by_fc.values())

    exact_idx: dict[tuple[str, str], dict[str, dict]] = collections.defaultdict(dict)
    for r in cw:
        exact_idx[(_ndist(r["district_en"]), r["local_level_type"])][_nname(r["name_en"])] = r

    assigned: dict[str, dict] = {}      # federal_code → cw row
    fc_to_row: dict[object, dict] = {}  # source fullcode → cw row

    # phase 4 first (explicit overrides win, lock their targets)
    cw_by_name = collections.defaultdict(dict)
    for r in cw:
        cw_by_name[_ndist(r["district_en"])][_nname(r["name_en"])] = r
    for u in units:
        key = (_ndist(u["district"]), _nname(u["locallevel_name"]))
        tgt = RENAME_OVERRIDE.get(key)
        if tgt:
            r = cw_by_name[_ndist(u["district"])][_nname(tgt)]
            fc_to_row[u["locallevel_fullcode"]] = r
            assigned[r["federal_code"]] = r

    # phase 1: exact (district-alias + type + normalized name)
    for u in units:
        if u["locallevel_fullcode"] in fc_to_row:
            continue
        r = exact_idx[(_ndist(u["district"]), TYPE_MAP[str(u["locallevel_type"])])].get(
            _nname(u["locallevel_name"])
        )
        if r and r["federal_code"] not in assigned:
            fc_to_row[u["locallevel_fullcode"]] = r
            assigned[r["federal_code"]] = r

    # phase 2: fuzzy within district, confidence-ordered (strong matches win)
    pairs = []
    for u in units:
        if u["locallevel_fullcode"] in fc_to_row:
            continue
        d = _ndist(u["district"])
        for r in cw:
            if _ndist(r["district_en"]) != d:
                continue
            sim = difflib.SequenceMatcher(
                None, _nname(u["locallevel_name"]), _nname(r["name_en"])
            ).ratio()
            if sim >= 0.55:
                pairs.append((sim, u["locallevel_fullcode"], r["federal_code"]))
    pairs.sort(key=lambda p: p[0], reverse=True)
    cw_by_code = {r["federal_code"]: r for r in cw}
    for _sim, fc_u, fc in pairs:
        if fc_u in fc_to_row or fc in assigned:
            continue
        fc_to_row[fc_u] = cw_by_code[fc]
        assigned[fc] = cw_by_code[fc]

    # phase 3: pigeonhole — a district left with exactly one unmatched unit and
    # one unassigned code must be that pair (correct by elimination).
    ubd = collections.defaultdict(list)
    for u in units:
        ubd[_ndist(u["district"])].append(u)
    for d, us in ubd.items():
        ug = [u for u in us if u["locallevel_fullcode"] not in fc_to_row]
        uc = [r for r in cw if _ndist(r["district_en"]) == d and r["federal_code"] not in assigned]
        if len(ug) == 1 and len(uc) == 1:
            fc_to_row[ug[0]["locallevel_fullcode"]] = uc[0]
            assigned[uc[0]["federal_code"]] = uc[0]

    return fc_to_row


# ── geometry: project, simplify, emit ─────────────────────────────────────


def _mercator(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon)
    lat = max(min(lat, 89.5), -89.5)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def _rdp_open(pts: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    """Ramer–Douglas–Peucker on an OPEN polyline (endpoints always kept)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        dmax, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            dist = abs((px - ax) * dy - (py - ay) * dx) / norm
            if dist > dmax:
                dmax, idx = dist, i
        if dmax > eps and idx != -1:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [p for p, k in zip(pts, keep) if k]


def _rdp_ring(pts: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    """RDP for a CLOSED ring. A closed ring's first==last point makes the
    plain endpoint-anchored RDP degenerate (zero-length baseline collapses the
    whole ring), so we split the ring at the vertex farthest from pt0 and RDP
    the two arcs independently — the standard closed-curve treatment."""
    if len(pts) < 4:
        return pts
    closed = pts[0] == pts[-1]
    core = pts[:-1] if closed else pts
    if len(core) < 4:
        return pts
    ax, ay = core[0]
    far_i = max(range(1, len(core)), key=lambda i: math.hypot(core[i][0] - ax, core[i][1] - ay))
    arc1 = _rdp_open(core[: far_i + 1], eps)
    arc2 = _rdp_open(core[far_i:] + [core[0]], eps)
    merged = arc1[:-1] + arc2[:-1]  # drop shared joints; ring is implicitly closed
    return merged


def _rings(geom: dict) -> list[list[list[float]]]:
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        return [ring for poly in geom["coordinates"] for ring in poly]
    return []


def build(source: Path) -> int:
    cw = _load_crosswalk()
    gj = json.loads(source.read_text(encoding="utf-8"))
    features = gj["features"]
    fc_to_row = _match(features, cw)

    matched_codes = {r["federal_code"] for r in fc_to_row.values()}
    if len(matched_codes) != EXPECTED_UNITS:
        sys.stderr.write(
            f"[geo] FATAL: matched {len(matched_codes)}/{EXPECTED_UNITS} federal codes — "
            "refusing to write a partial asset.\n"
        )
        missing = [r for r in cw if r["federal_code"] not in matched_codes]
        for r in missing[:30]:
            sys.stderr.write(f"   NO-GEOMETRY: {r['district_en']} | {r['name_en']}\n")
        return 1

    # collect projected rings per federal_code (merge multiparts)
    raw: dict[str, dict] = {}
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for f in features:
        props = f["properties"]
        row = fc_to_row.get(props.get("locallevel_fullcode"))
        if not row:
            continue
        code = row["federal_code"]
        slot = raw.setdefault(code, {"row": row, "rings": []})
        for ring in _rings(f["geometry"]):
            proj = [_mercator(float(p[0]), float(p[1])) for p in ring]
            slot["rings"].append(proj)
            for x, y in proj:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)

    # fit to a 1000-wide viewBox (y flipped for SVG), preserving aspect
    pad = 6.0
    span_x = maxx - minx
    span_y = maxy - miny
    if span_x <= 0 or span_y <= 0:
        sys.stderr.write(
            f"[geo] FATAL: degenerate projected extent (span_x={span_x}, span_y={span_y}); "
            "cannot fit a viewBox.\n"
        )
        return 1
    width = 1000.0
    scale = (width - 2 * pad) / span_x
    height = round(span_y * scale + 2 * pad, 1)

    def to_px(x: float, y: float) -> tuple[float, float]:
        return (pad + (x - minx) * scale, pad + (maxy - y) * scale)

    eps = 0.35  # simplification tolerance in viewBox px (visually lossless)
    out_features = []
    total_pts_in = total_pts_out = 0
    for code in sorted(raw):
        slot = raw[code]
        row = slot["row"]
        subpaths = []
        for ring in slot["rings"]:
            px = [to_px(x, y) for x, y in ring]
            total_pts_in += len(px)
            simp = _rdp_ring(px, eps)
            # Quantize to integer viewBox px FIRST, then drop consecutive
            # duplicates: an RDP ring can keep >=3 float points that collapse to
            # <3 DISTINCT pixels after rounding, which would otherwise emit a
            # degenerate zero-area subpath. The <3 check must run on the rounded,
            # deduped points, not the float ones.
            rounded: list[tuple[int, int]] = []
            for x, y in simp:
                pt = (round(x), round(y))
                if not rounded or rounded[-1] != pt:
                    rounded.append(pt)
            if len(rounded) > 1 and rounded[0] == rounded[-1]:
                rounded.pop()  # drop the closing duplicate; the ring is implicitly closed
            total_pts_out += len(rounded)
            if len(rounded) < 3:
                continue  # degenerate after quantization — skip, never emit
            coords = " ".join(f"{x},{y}" for x, y in rounded)
            first, rest = coords.split(" ", 1)  # >=3 points ⇒ always splittable
            subpaths.append(f"M{first} L{rest} Z")
        if not subpaths:
            continue
        out_features.append(
            {
                "code": code,
                "nameEn": row["name_en"],
                "nameNe": row["name_ne"],
                "district": row["district_en"],
                "type": row["local_level_type"],
                "d": " ".join(subpaths),
            }
        )

    # The 753/753 guard above validates the MATCH; this guards the EMIT — a
    # palika whose every ring collapsed below 3 points would otherwise ship a
    # silently incomplete asset. Geometry loss is as fatal as match loss.
    if len(out_features) != EXPECTED_UNITS:
        sys.stderr.write(
            f"[geo] FATAL: emitted {len(out_features)}/{EXPECTED_UNITS} features after "
            "simplification — a palika lost all geometry. Refusing to write.\n"
        )
        return 1

    asset = {
        "_meta": {
            "doc": "Palika (753 local level) choropleth geometry — ADR-0025. "
            "Mercator-projected, RDP-simplified, federal_code-keyed.",
            "source": SOURCE_URL,
            "projection": "mercator",
            "units": len(out_features),
            "viewBox": f"0 0 {round(width)} {height}",
        },
        "viewBox": f"0 0 {round(width)} {height}",
        "features": out_features,
    }
    OUT_ASSET.parent.mkdir(parents=True, exist_ok=True)
    OUT_ASSET.write_text(json.dumps(asset, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT_ASSET.stat().st_size / 1024
    sys.stderr.write(
        f"[geo] OK: {len(out_features)} palikas → {OUT_ASSET.relative_to(REPO)} "
        f"({size_kb:.0f} KB; vertices {total_pts_in:,}→{total_pts_out:,}; "
        f"viewBox {asset['viewBox']})\n"
    )
    return 0


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=SOURCE_GEOJSON)
    args = ap.parse_args()
    _ensure_source(args.source)
    sys.exit(build(args.source))


if __name__ == "__main__":
    _main()
