"""Pytest fixtures for the NRB DNE parser.

Builds synthetic XLSX fixtures via openpyxl — regenerated each run, not
committed as binaries. Fixtures mimic the External Sector "Foreign Exchange
Reserves" DNE file layout (wide format: indicators as rows, FY periods as
columns).

Fixture variants:
    happy_path_xlsx      — valid 3-indicator annual + 2 monthly columns
    empty_workbook_xlsx  — workbook with a blank sheet only
    ambiguous_unit_xlsx  — no unit in preamble; ambiguous row
    bad_period_xlsx      — one unparseable period header column
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _ensure_fixture_dir() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _build_happy_path(path: Path) -> None:
    """External-sector Foreign Exchange Reserves style XLSX.

    Layout (1-indexed openpyxl rows):
      Row 1: title "Foreign Exchange Reserves (in million US$)"
      Row 2: header periods — "2080/81", "2081/82", "2082/83", "Shrawan 2082", "Bhadra 2082"
      Row 3: "Total Foreign Exchange Reserves"   1500.0  2100.0  2300.0  2250.0  2280.0
      Row 4: "Gold Reserves"                      100.0   120.0   130.0   125.0   127.0
      Row 5: "Foreign Currency Assets"            1400.0  1980.0  2170.0  2125.0  2153.0
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "External Sector"

    ws.cell(row=1, column=1, value="Foreign Exchange Reserves (in million US$)")
    # Header row.
    ws.cell(row=2, column=1, value="Indicators")
    ws.cell(row=2, column=2, value="2080/81")
    ws.cell(row=2, column=3, value="2081/82")
    ws.cell(row=2, column=4, value="2082/83")
    ws.cell(row=2, column=5, value="Shrawan 2082")
    ws.cell(row=2, column=6, value="Bhadra 2082")

    # Data rows.
    indicators = [
        ("Total Foreign Exchange Reserves", [1500.0, 2100.0, 2300.0, 2250.0, 2280.0]),
        ("Gold Reserves", [100.0, 120.0, 130.0, 125.0, 127.0]),
        ("Foreign Currency Assets", [1400.0, 1980.0, 2170.0, 2125.0, 2153.0]),
    ]
    for row_offset, (label, values) in enumerate(indicators):
        r = 3 + row_offset
        ws.cell(row=r, column=1, value=label)
        for col_offset, val in enumerate(values):
            ws.cell(row=r, column=2 + col_offset, value=val)

    wb.save(str(path))


def _build_empty_workbook(path: Path) -> None:
    """Workbook with a single blank sheet — no parseable data."""
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Empty"
    # Write only a title row — no period header.
    ws.cell(row=1, column=1, value="This sheet has no data")
    wb.save(str(path))


def _build_ambiguous_unit(path: Path) -> None:
    """XLSX with no unit annotation in preamble and no unit-bearing sheet name.

    The parser should emit UnitAmbiguous and still produce rows.
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Data"

    # No unit hint row — just jump to the header.
    ws.cell(row=1, column=1, value="Indicator")
    ws.cell(row=1, column=2, value="2081/82")
    ws.cell(row=1, column=3, value="2082/83")

    ws.cell(row=2, column=1, value="Remittance Inflows")
    ws.cell(row=2, column=2, value=950.0)
    ws.cell(row=2, column=3, value=1050.0)

    wb.save(str(path))


def _build_bad_period(path: Path) -> None:
    """XLSX with one valid period column and one malformed period column.

    Malformed: "2082/invalid" — looks like a period (contains "2082") but
    won't parse; should emit PeriodUnparseable.
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Fiscal Sector"

    ws.cell(row=1, column=1, value="Government Revenue (Rs. in million)")
    ws.cell(row=2, column=1, value="Indicator")
    ws.cell(row=2, column=2, value="2081/82")       # valid
    ws.cell(row=2, column=3, value="2082/invalid")  # malformed

    ws.cell(row=3, column=1, value="Tax Revenue")
    ws.cell(row=3, column=2, value=500000.0)
    ws.cell(row=3, column=3, value=550000.0)

    wb.save(str(path))


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def happy_path_xlsx() -> Path:
    p = FIXTURE_DIR / "happy_path.xlsx"
    if not p.exists():
        _build_happy_path(p)
    return p


@pytest.fixture(scope="session")
def empty_workbook_xlsx() -> Path:
    p = FIXTURE_DIR / "empty_workbook.xlsx"
    if not p.exists():
        _build_empty_workbook(p)
    return p


@pytest.fixture(scope="session")
def ambiguous_unit_xlsx() -> Path:
    p = FIXTURE_DIR / "ambiguous_unit.xlsx"
    if not p.exists():
        _build_ambiguous_unit(p)
    return p


@pytest.fixture(scope="session")
def bad_period_xlsx() -> Path:
    p = FIXTURE_DIR / "bad_period.xlsx"
    if not p.exists():
        _build_bad_period(p)
    return p
