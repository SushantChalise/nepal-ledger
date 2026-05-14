"""Municipality name resolver for Nepali local-level entities.

Ported from ``Financial Data/mof_documents/Cleaned/fuzzy_match_municipalities.py``
into a reusable shape so every future OCR parser can map a possibly-misspelled
municipality name (Devanagari or English) to a canonical entity row.

Doctrine
--------
1. The canonical 753-row table comes from
   ``Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx``
   Sheet2 — the MoF-published, manually-validated ground truth for Nepal's
   753 local levels. Because ``Financial Data/`` is gitignored, the data is
   loaded at runtime ONLY; it is never serialized into the repo.

2. The fuzzy-match thresholds match the upstream cleanup scripts:
   - score >= 85  -> High confidence (auto-accept)
   - 70 <= score < 85 -> Medium (returned, but caller should review)
   - score < 70  -> no match (function returns ``None``)

3. Devanagari inputs are normalized via :mod:`._common.devanagari_normalization`
   BEFORE fuzzy matching. This recovers municipalities whose names contain
   the known OCR typos (e.g. ``पाललका`` -> ``पालिका``).

4. The resolver does NOT mutate the canonical table; it never invents an
   entity. If the best match falls below threshold, it returns ``None`` and
   the caller is responsible for parking the row in the validation queue
   (see ``docs/DATA_PIPELINE.md``).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from _common._common_paths import financial_data_root
from _common.devanagari_normalization import (
    is_devanagari_dominant,
    normalize_devanagari_text,
)

# ---------------------------------------------------------------------------
# Thresholds — keep aligned with fuzzy_match_municipalities.py
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE_THRESHOLD = 85
MEDIUM_CONFIDENCE_THRESHOLD = 70

# ---------------------------------------------------------------------------
# Canonical-table location & column mapping
# ---------------------------------------------------------------------------
CANONICAL_TABLE_RELPATH = Path("mof_documents") / "Cleaned" / "Fiscal Transfer_2082_82.xlsx"
CANONICAL_TABLE_SHEET = "Sheet2"

# Local-level types that represent ACTUAL municipalities (not aggregator rows).
_REAL_LOCAL_LEVEL_TYPES: frozenset[str] = frozenset(
    {
        "Municipality",
        "Rural Municipality",
        "Metropolitan City",
        "Sub-Metropolitan City",
    }
)

_LOCAL_LEVEL_TYPE_TO_SLUG: dict[str, str] = {
    "Municipality": "municipality",
    "Rural Municipality": "rural_municipality",
    "Metropolitan City": "metropolitan_city",
    "Sub-Metropolitan City": "sub_metropolitan_city",
}


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MunicipalityMatch:
    """Resolved canonical municipality row."""

    federal_code: str
    name_en: str
    name_ne: str
    local_level_type: str  # snake_case slug, see _LOCAL_LEVEL_TYPE_TO_SLUG
    district_en: str
    score: float  # 0..100 rapidfuzz ratio


# ---------------------------------------------------------------------------
# Cached table loader
#
# A single-element list is used as a mutable container so the helpers can
# update the cache without resorting to ``global`` (ruff PLW0603).
# ---------------------------------------------------------------------------
_TABLE_CACHE: list[list[MunicipalityMatch] | None] = [None]
_CACHE_LOCK = threading.Lock()


def _resolve_canonical_path() -> Path:
    """Return the absolute path to the canonical xlsx. Raise if absent."""
    root = financial_data_root()
    path = root / CANONICAL_TABLE_RELPATH
    if not path.exists():
        raise FileNotFoundError(
            f"Canonical municipality table not found at {path}. "
            "This file lives under the gitignored Financial Data/ tree and "
            "must be present locally before the resolver can be used.",
        )
    return path


def _is_missing(value: object) -> bool:
    """Robust NaN/None check for opaque pandas cell values."""
    if value is None:
        return True
    # NaN is the only object that does not equal itself.
    return isinstance(value, float) and value != value  # noqa: PLR0124


def _row_to_match(
    code: object,
    district: object,
    name_ne: object,
    name_en: object,
    level_type: object,
) -> MunicipalityMatch | None:
    """Convert primitive cell values to a MunicipalityMatch, or None if invalid."""
    if (
        _is_missing(level_type)
        or not isinstance(level_type, str)
        or level_type not in _REAL_LOCAL_LEVEL_TYPES
    ):
        return None
    if (
        _is_missing(name_en)
        or _is_missing(name_ne)
        or _is_missing(district)
        or _is_missing(code)
    ):
        return None

    # ``Code`` is loaded as float by pandas; render losslessly as 8-digit str.
    if not isinstance(code, int | float):
        return None
    federal_code = f"{int(code):08d}"

    return MunicipalityMatch(
        federal_code=federal_code,
        name_en=str(name_en).strip(),
        name_ne=str(name_ne).strip(),
        local_level_type=_LOCAL_LEVEL_TYPE_TO_SLUG[level_type],
        district_en=str(district).strip(),
        score=0.0,
    )


def load_canonical_municipalities() -> list[MunicipalityMatch]:
    """Load the 753-row canonical local-level table. Cached on first call.

    Raises :class:`FileNotFoundError` if the gitignored source file is absent
    on this machine.
    """
    cached = _TABLE_CACHE[0]
    if cached is not None:
        return cached
    with _CACHE_LOCK:
        cached = _TABLE_CACHE[0]
        if cached is not None:
            return cached
        path = _resolve_canonical_path()
        df = pd.read_excel(path, sheet_name=CANONICAL_TABLE_SHEET)
        rows: list[MunicipalityMatch] = []
        # Extract the columns we care about as plain Python lists so mypy
        # doesn't have to reason about pandas overload variants.
        codes = df["Code"].tolist()
        districts = df["District (English)"].tolist()
        names_ne = df["Local Level Name (Nepali)"].tolist()
        names_en = df["Local Level Name (English)"].tolist()
        types = df["Local Level Type"].tolist()
        for code, district, name_ne, name_en, level_type in zip(
            codes,
            districts,
            names_ne,
            names_en,
            types,
            strict=True,
        ):
            match = _row_to_match(code, district, name_ne, name_en, level_type)
            if match is not None:
                rows.append(match)
        _TABLE_CACHE[0] = rows
        return rows


def _clear_cache_for_tests() -> None:
    """Reset the module-level cache. Test-only helper."""
    with _CACHE_LOCK:
        _TABLE_CACHE[0] = None


def _set_cache_for_tests(rows: list[MunicipalityMatch]) -> None:
    """Inject a fixture canonical table. Test-only helper."""
    with _CACHE_LOCK:
        _TABLE_CACHE[0] = list(rows)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------
def _pick_name_column(query: str) -> str:
    """Return ``"ne"`` if the (normalized) query looks Devanagari, else ``"en"``."""
    normalized = normalize_devanagari_text(query)
    return "ne" if is_devanagari_dominant(normalized) else "en"


def resolve_municipality(
    name: str,
    district_hint: str | None = None,
) -> MunicipalityMatch | None:
    """Resolve a possibly-misspelled municipality name to its canonical row.

    Pipeline:
      1. Strip + normalize OCR errors via
         :func:`devanagari_normalization.normalize_devanagari_text`.
      2. Detect whether the query is Devanagari- or Latin-script; pick the
         matching column from the canonical table as the search space.
      3. Narrow by ``district_hint`` (English) when supplied.
      4. ``rapidfuzz.process.extractOne`` against that space.
      5. Apply confidence thresholds (HIGH >= 85, MEDIUM >= 70, else None).

    Returns ``None`` if the input is empty/whitespace, if no candidates exist
    after district filtering, or if the best score falls below
    ``MEDIUM_CONFIDENCE_THRESHOLD``.
    """
    if not name or not name.strip():
        return None

    cleaned = normalize_devanagari_text(name.strip())
    rows = load_canonical_municipalities()

    if district_hint:
        district_norm = district_hint.strip().lower()
        candidates = [r for r in rows if r.district_en.lower() == district_norm]
        if not candidates:
            # Fall back to the full table — caller hinted wrong / unknown district.
            candidates = rows
    else:
        candidates = rows

    column = _pick_name_column(cleaned)
    if column == "ne":
        choices = {idx: normalize_devanagari_text(r.name_ne) for idx, r in enumerate(candidates)}
    else:
        choices = {idx: r.name_en for idx, r in enumerate(candidates)}

    best = process.extractOne(cleaned, choices, scorer=fuzz.ratio)
    if best is None:
        return None
    _, score, idx = best
    if score < MEDIUM_CONFIDENCE_THRESHOLD:
        return None

    matched = candidates[idx]
    return MunicipalityMatch(
        federal_code=matched.federal_code,
        name_en=matched.name_en,
        name_ne=matched.name_ne,
        local_level_type=matched.local_level_type,
        district_en=matched.district_en,
        score=float(score),
    )
