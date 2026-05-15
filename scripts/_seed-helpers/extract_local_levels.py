"""Emit the 753 canonical Nepal local-level rows as JSON to stdout.

Reads Sheet2 of the MoF "Fiscal Transfer_2082_82.xlsx" pre-cleaned workbook
— the same authoritative ground-truth table consumed by
``scrapers._common.municipality_resolver``. We deliberately do NOT import
the resolver here because it couples to the gitignored ``Financial Data/``
tree via ``_common._common_paths``; the seed CLI passes an explicit XLSX
path so it can run from any working directory (including a worktree where
``Financial Data/`` is not symlinked).

Output contract (stdout, JSON):
    [
        {
            "federal_code": "08-digit string",
            "name_en": str,
            "name_ne": str,
            "local_level_type": "metropolitan_city" | "sub_metropolitan_city"
                                | "municipality" | "rural_municipality",
            "district_en": str
        },
        ...
    ]

Exit codes:
    0 — success, JSON emitted
    1 — catastrophic crash
    2 — usage error

Aggregator rows (District Total, Municipality (Total), etc.) are filtered
out so the emitted list contains exactly the 753 real local levels.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd

CANONICAL_SHEET: Final[str] = "Sheet2"

# Mirrors scrapers/_common/municipality_resolver.py — keep aligned. The
# resolver is the source of truth; this list is duplicated only because
# importing the resolver would force ``Financial Data/`` path coupling.
_REAL_LOCAL_LEVEL_TYPES: Final[frozenset[str]] = frozenset(
    {
        "Municipality",
        "Rural Municipality",
        "Metropolitan City",
        "Sub-Metropolitan City",
    },
)

_LOCAL_LEVEL_TYPE_TO_SLUG: Final[dict[str, str]] = {
    "Municipality": "municipality",
    "Rural Municipality": "rural_municipality",
    "Metropolitan City": "metropolitan_city",
    "Sub-Metropolitan City": "sub_metropolitan_city",
}


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, float) and value != value  # NaN-only check


def _emit(path: Path) -> list[dict[str, Any]]:
    df = pd.read_excel(path, sheet_name=CANONICAL_SHEET)
    out: list[dict[str, Any]] = []
    codes = df["Code"].tolist()
    districts = df["District (English)"].tolist()
    names_ne = df["Local Level Name (Nepali)"].tolist()
    names_en = df["Local Level Name (English)"].tolist()
    types = df["Local Level Type"].tolist()
    for code, district, name_ne, name_en, level_type in zip(
        codes, districts, names_ne, names_en, types, strict=True,
    ):
        if not isinstance(level_type, str) or level_type not in _REAL_LOCAL_LEVEL_TYPES:
            continue
        if _is_missing(code) or _is_missing(district) or _is_missing(name_en) or _is_missing(name_ne):
            continue
        if not isinstance(code, int | float):
            continue
        out.append(
            {
                "federal_code": f"{int(code):08d}",
                "name_en": str(name_en).strip(),
                "name_ne": str(name_ne).strip(),
                "local_level_type": _LOCAL_LEVEL_TYPE_TO_SLUG[level_type],
                "district_en": str(district).strip(),
            },
        )
    return out


def _main() -> None:
    expected_argc = 2
    if len(sys.argv) != expected_argc:
        sys.stderr.write("usage: extract_local_levels.py <xlsx_path>\n")
        sys.exit(2)
    path = Path(sys.argv[1])
    if not path.exists():
        sys.stderr.write(f"file not found: {path}\n")
        sys.exit(2)
    rows = _emit(path)
    json.dump(rows, sys.stdout)


if __name__ == "__main__":
    _main()
