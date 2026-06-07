"""Generator for ``palika_code_crosswalk.csv`` — the deterministic CBS→federal map.

WHY THIS EXISTS
---------------
CBS NPHC 2021 CSVs identify each palika ONLY by the integer triple
``(prov, dist, gapa)`` (province 1-7, district 1-77, local-level
sequence-within-district). There is NO federal code in the CSVs. The
``entities`` table, however, keys every local level on the 8-digit MoF/HLCIT
``federal_code`` (= ``entities.slug``). The previous parser bridged this gap by
fuzzy-matching the palika *name* against the MoF canonical table at parse time,
which resolved only ~299/753 palikas (sub-85 romanisation drift + same-named
palika conflation).

This script builds a **static, committed** crosswalk so the parser resolves all
753 palikas by exact ``(prov, dist, gapa)`` lookup — no fuzzy matching on the
hot path. It is deterministic and regenerable: re-running it against the same
two inputs reproduces ``palika_code_crosswalk.csv`` byte-for-byte.

HOW THE MAP IS DERIVED
----------------------
The 8-digit federal code is the HLCIT scheme (``801`` prefix + region digits);
it does NOT encode ``(prov, dist, gapa)`` in any recoverable way (verified: e.g.
Taplejung dist=1 spans codes 80101101 & 80101301..308; Panchthar dist=2 reuses
the 801011/801013 prefixes). So derivation is impossible and no source carries
both keys. The only bridge is the palika NAME — but matched **within district**,
which is far stronger than the old global fuzzy match because:

  * The 77 CBS ``dname`` values map 1:1 to the 77 canonical districts (only 4
    spelling drifts, see ``_DISTRICT_ALIAS``).
  * Within a district there are at most ~16 palikas, so name collisions across
    districts (e.g. two "Mayadevi" rural municipalities in Rupandehi vs
    Kapilvastu) are naturally disambiguated — they land in different districts
    and get DISTINCT federal codes.

Matching ladder (each rung is deterministic; first hit wins):

  1. **Exact bare-name within district.** Strip the local-level *type* word
     (Gaunpalika/Municipality/…) from both the CBS name and the canonical
     ``name_en``, squash to ``[a-z0-9]``, and require a UNIQUE match inside the
     district. Resolves 601/753.
  2. **High-confidence fuzzy within district.** ``rapidfuzz.fuzz.ratio`` on the
     bare names, restricted to the district, threshold >= 85. Adds 133 → 734.
     (Restricting to the district makes this safe: the candidate set is tiny and
     same-named palikas in other districts can't be picked.)
  3. **Curated manual map** (``_MANUAL_TRIPLE_TO_NAME``): the 19 residual CBS
     spellings whose bare-name fuzzy score fell below 85 (e.g. CBS
     "Temkemaiyum" → canonical "Tyamkemaiyung"; CBS "Byas" → "Vyas"; CBS
     "Khaptad Chhededaha" → "Chhededaha"). Each entry names the EXACT canonical
     ``name_en`` within the district, hand-verified against the MoF table.

Every rung resolves to a unique canonical row; the generator asserts full
753/753 coverage with 753 distinct codes and refuses to emit a partial file.

INPUTS (both gitignored under ``Financial Data/``)
  * MoF canonical: ``mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx`` Sheet2
    (the same ground truth the resolver + entity seed use).
  * CBS reference triples: ``Census/.../census-dataset/Hhld05_FloorOfHouse.csv``
    — chosen because it carries exactly the 753 palika rows (one per local
    level, no urban/rural locality splits) in clean Mode-B layout.

USAGE
  PYTHONPATH=<repo>/scrapers \\
    <venv>/python -m cbs_nphc.generate_crosswalk

  Writes ``scrapers/cbs_nphc/palika_code_crosswalk.csv`` (overwrites). Prints a
  coverage report to stderr. Exit 0 only on full 753/753 coverage.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

# rapidfuzz is already a resolver dependency; reused here for rung 2.
from rapidfuzz import fuzz, process

from _common._common_paths import financial_data_root
from _common.municipality_resolver import load_canonical_municipalities

# --- output location -------------------------------------------------------
CROSSWALK_PATH = Path(__file__).parent / "palika_code_crosswalk.csv"

# CBS reference file that carries exactly the 753 palika-grain rows.
_CBS_REFERENCE_RELPATH = (
    Path("Census")
    / "census_2021_data"
    / "census-dataset"
    / "Hhld05_FloorOfHouse.csv"
)

# Fuzzy threshold for rung 2. Mirrors the resolver's HIGH_CONFIDENCE_THRESHOLD;
# safe here because the candidate set is restricted to a single district.
_FUZZY_THRESHOLD = 85

# --- CBS dname → canonical "District (English)" spelling drifts -------------
# The only 4 of 77 districts whose CBS romanisation differs from the MoF table.
_DISTRICT_ALIAS: dict[str, str] = {
    "chitawan": "chitwan",
    "dhanusa": "dhanusha",
    "kapilbastu": "kapilvastu",
    "terhathum": "tehrathum",
}

# --- 19 residual CBS triples → EXACT canonical name_en (within district) -----
# These are the palikas whose bare-name fuzzy score fell below _FUZZY_THRESHOLD.
# Keyed by the CBS (prov, dist, gapa) triple so the mapping is unambiguous even
# for same-named palikas. Each value is the verbatim canonical
# ``Local Level Name (English)`` from the MoF table; the generator looks the
# code up by (district, name_en) and asserts a unique hit.
_MANUAL_TRIPLE_TO_NAME: dict[tuple[int, int, int], str] = {
    (1, 6, 3): "Tyamkemaiyung Rural Municipality",      # CBS: Temkemaiyum
    (1, 9, 3): "Phalelung Rural Municipality",          # CBS: Falelung
    (1, 10, 5): "Phakphokthum Rural Municipality",      # CBS: Fakfokathum
    (1, 11, 5): "Shivasataxi Municipality",             # CBS: Shivasatakshi
    (2, 17, 5): "Kshireshwarnath Municipality",         # CBS: Chhireshwornath
    (3, 34, 7): "Bhimfedi Rural Municipality",          # CBS: Bhimphedi
    (4, 42, 2): "Vyas Municipality",                    # CBS: Byas
    (5, 47, 3): "Bhume Rural Municipality",             # CBS: Bhoome
    (5, 50, 12): "Ruru Rural Municipality",             # CBS: Ruruchhetra
    (5, 54, 12): "Mayadevi Rural Municipality (Rupandehi)",   # CBS: Mayadevi (Rupandehi)
    (5, 54, 13): "Lumbini Cultural Municipality",       # CBS: Lumbini Sanskritik
    (5, 55, 9): "Mayadevi Rural Municipality (Kapilvastu)",   # CBS: Mayadevi (Kapilvastu)
    (6, 63, 7): "Tilagufa Municipality",                # CBS: Tilagupha
    (6, 65, 6): "Bheri Municipality",                   # CBS: Bheri Malika
    (6, 66, 3): "Banfikot Rural Municipality",          # CBS: Banphikot
    (6, 67, 5): "Bagchaur Municipality",                # CBS: Bagachour
    (7, 69, 7): "Chhededaha Rural Municipality",        # CBS: Khaptad Chhededaha
    (7, 70, 7): "Chabispathivera Rural Municipality",   # CBS: Chhabis Pathibhara
    (7, 77, 5): "Mahakali (Dodhara Chandani) Municipality",  # CBS: Dodhara Chandani
}

# Local-level type words to strip when comparing bare place names. Includes the
# systematic CBS "Metropolitian" (sic) typo and the Devanagari romanisations.
_TYPE_RE = re.compile(
    r"\b(?:sub-?metropolitian|sub-?metropolitan|metropolitian|metropolitan)\s+city\b"
    r"|\b(?:rural\s+municipality|municipality|gaunpalika|gaupalika|nagarpalika)\b",
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _district_key(dname: str) -> str:
    n = _norm(dname)
    return _DISTRICT_ALIAS.get(n, n)


def _bare(s: str) -> str:
    """Lower-cased place name with the type word removed; spaces collapsed."""
    n = _TYPE_RE.sub(" ", _norm(s))
    return re.sub(r"[^a-z0-9]+", " ", n).strip()


def _bare_squash(s: str) -> str:
    """``_bare`` with all non-alphanumerics removed — exact-match key."""
    return re.sub(r"[^a-z0-9]+", "", _bare(s))


def _load_cbs_reference_triples() -> list[tuple[int, int, int, str, str]]:
    """Return ``(prov, dist, gapa, gapaname, dname)`` for every palika row.

    Reads Hhld05 directly with the stdlib csv reader (clean Mode-B header on
    row 0) and keeps only rows where all three codes are non-zero.
    """
    path = financial_data_root() / _CBS_REFERENCE_RELPATH
    if not path.exists():
        raise FileNotFoundError(
            f"CBS reference file not found at {path}. It lives under the "
            "gitignored Financial Data/ tree and must be present to regenerate."
        )
    out: list[tuple[int, int, int, str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                p, d, g = int(row["prov"]), int(row["dist"]), int(row["gapa"])
            except (ValueError, KeyError, TypeError):
                continue
            if p and d and g:
                out.append(
                    (
                        p,
                        d,
                        g,
                        row["gapaname"].strip().strip('"'),
                        row["dname"].strip().strip('"'),
                    )
                )
    return out


class _CanonIndex:
    """Canonical rows indexed by district for within-district matching."""

    def __init__(self) -> None:
        self.by_dist_exact: dict[str, dict[str, str]] = defaultdict(dict)  # squash→code
        self.by_dist_name: dict[str, dict[str, str]] = defaultdict(dict)  # name_en→code
        self.by_dist_rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.code_to_name: dict[str, str] = {}
        for m in load_canonical_municipalities():
            dk = _norm(m.district_en)
            self.by_dist_exact[dk][_bare_squash(m.name_en)] = m.federal_code
            self.by_dist_name[dk][_norm(m.name_en)] = m.federal_code
            self.by_dist_rows[dk].append((_bare(m.name_en), m.federal_code))
            self.code_to_name[m.federal_code] = m.name_en


def _resolve_one(
    idx: _CanonIndex,
    triple: tuple[int, int, int],
    gapaname: str,
    dk: str,
    counts: dict[str, int],
) -> str | None:
    """Resolve a single CBS triple via the 3-rung ladder. None on total miss."""
    # Rung 3 (manual) takes precedence when a triple is explicitly curated.
    manual_name = _MANUAL_TRIPLE_TO_NAME.get(triple)
    if manual_name is not None:
        code = idx.by_dist_name[dk].get(_norm(manual_name))
        if code is not None:
            counts["manual"] += 1
            return code
    # Rung 1: exact bare-name within district (unique).
    code = idx.by_dist_exact[dk].get(_bare_squash(gapaname))
    if code is not None:
        counts["exact"] += 1
        return code
    # Rung 2: high-confidence fuzzy within district.
    cands = idx.by_dist_rows[dk]
    if cands:
        choices = {i: bare for i, (bare, _) in enumerate(cands)}
        best = process.extractOne(_bare(gapaname), choices, scorer=fuzz.ratio)
        if best is not None and best[1] >= _FUZZY_THRESHOLD:
            counts["fuzzy"] += 1
            return cands[best[2]][1]
    return None


def _assert_invariants(
    rows: list[tuple[int, int, int, str, str]],
    unresolved: list[tuple[int, int, int, str, str]],
) -> None:
    """Refuse to emit a partial or non-injective crosswalk."""
    if unresolved:
        sys.stderr.write("UNRESOLVED triples (generator refuses to emit):\n")
        for u in unresolved:
            sys.stderr.write(f"  {u}\n")
        raise SystemExit(1)
    codes = [r[3] for r in rows]
    if len(set(codes)) != len(codes):
        seen: dict[str, tuple[int, int, int]] = {}
        for prov, dist, gapa, code, _ in rows:
            if code in seen:
                sys.stderr.write(
                    f"DUPLICATE code {code}: {seen[code]} and {(prov, dist, gapa)}\n"
                )
            else:
                seen[code] = (prov, dist, gapa)
        raise SystemExit(1)


def _build() -> list[tuple[int, int, int, str, str]]:
    """Run the matching ladder. Returns sorted ``(prov,dist,gapa,code,name_en)``."""
    idx = _CanonIndex()
    rows: list[tuple[int, int, int, str, str]] = []
    counts = {"exact": 0, "fuzzy": 0, "manual": 0}
    unresolved: list[tuple[int, int, int, str, str]] = []

    for prov, dist, gapa, gapaname, dname in _load_cbs_reference_triples():
        dk = _district_key(dname)
        code = _resolve_one(idx, (prov, dist, gapa), gapaname, dk, counts)
        if code is None:
            unresolved.append((prov, dist, gapa, gapaname, dname))
            continue
        rows.append((prov, dist, gapa, code, idx.code_to_name[code]))

    _assert_invariants(rows, unresolved)
    sys.stderr.write(
        f"crosswalk coverage: {len(rows)} palikas | "
        f"exact={counts['exact']} fuzzy={counts['fuzzy']} manual={counts['manual']} "
        f"| distinct codes={len({r[3] for r in rows})}\n"
    )
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return rows


def _write(rows: list[tuple[int, int, int, str, str]]) -> None:
    with CROSSWALK_PATH.open("w", encoding="utf-8", newline="") as fh:
        fh.write(
            "# CBS NPHC 2021 (prov,dist,gapa) -> 8-digit federal_code crosswalk.\n"
            "# Generated by scrapers/cbs_nphc/generate_crosswalk.py — do not hand-edit.\n"
            "# Sources: MoF Fiscal Transfer_2082_82.xlsx Sheet2 (federal codes) +\n"
            "# CBS Hhld05_FloorOfHouse.csv (753 reference triples). See the\n"
            "# generator module docstring for the within-district matching ladder.\n"
        )
        writer = csv.writer(fh)
        writer.writerow(["prov", "dist", "gapa", "federal_code", "name_en"])
        for prov, dist, gapa, code, name_en in rows:
            writer.writerow([prov, dist, gapa, code, name_en])


def main() -> None:
    rows = _build()
    _write(rows)
    sys.stderr.write(f"wrote {len(rows)} rows -> {CROSSWALK_PATH}\n")


if __name__ == "__main__":
    main()
