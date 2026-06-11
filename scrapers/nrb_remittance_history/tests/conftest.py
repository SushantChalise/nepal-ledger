"""Programmatically-generated XLSX fixtures (no committed binaries) — mirrors
the nrb_dne test convention. Builds a minimal 'BOP 2000-' sheet with the same
shape as the real NRB Trade-and-Balance-of-Payments workbook: a title/unit
preamble, a fiscal-year header row, and a 'Workers' remittances' data row.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

# (AD fiscal year header, Workers'-remittances value) — a few real anchor points.
_SERIES: list[tuple[str, float]] = [
    ("2000/01", 47216.1),
    ("2001/02", 47536.3),
    ("2019/20", 875027.0),
    ("2020/21", 961054.5773),
]


def _write_bop_workbook(path: Path, *, include_remittance: bool = True) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "BOP 2000-"
    ws.append(["Summary of Balance of Payments"])
    ws.append([])
    ws.append([])
    ws.append(["In Million Rupees"])
    ws.append([])
    # Header row: label cols 0-2 blank-ish, FY tokens from col 3.
    ws.append(["Particulars", None, None, *[fy for fy, _ in _SERIES]])
    ws.append(["A. Current Account", None, None, *[0 for _ in _SERIES]])
    ws.append(["Goods: exports", None, None, *[1 for _ in _SERIES]])
    ws.append([None, "Grants", None, *[100 for _ in _SERIES]])
    if include_remittance:
        # Label in col 1 (indented), values aligned to the FY columns (col 3+).
        ws.append([None, "Workers' remittances", None, *[v for _, v in _SERIES]])
    # A blank trailing row, like the real sheet.
    ws.append([None] * (3 + len(_SERIES)))
    # A second sheet so sheet-selection is exercised.
    wb.create_sheet("Direction of Foreign Trade")
    wb.save(path)


@pytest.fixture
def bop_xlsx(tmp_path: Path) -> Path:
    path = tmp_path / "trade-bop.xlsx"
    _write_bop_workbook(path)
    return path


@pytest.fixture
def bop_xlsx_no_remittance(tmp_path: Path) -> Path:
    path = tmp_path / "trade-bop-no-remit.xlsx"
    _write_bop_workbook(path, include_remittance=False)
    return path


# The expected (BS fiscal year, value) the parser should emit from the fixture.
EXPECTED: list[tuple[str, float]] = [
    ("2057/58", 47216.1),
    ("2058/59", 47536.3),
    ("2076/77", 875027.0),
    ("2077/78", 961054.5773),
]
