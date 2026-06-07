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


def _build_bs_fy_suffix(path: Path) -> None:
    """Fixture: BS FY column headers with NRB revision/provisional suffixes.

    Mirrors the real BoP BPM6 pattern but using BS-era years (2079/80R,
    2080/81P, 2081/82) so the parser can detect them.

    Layout:
      Row 1: title "External Debt (Rs. in million)"
      Row 2: "Indicator", "2079/80R", "2080/81P", "2081/82"
      Row 3: "Total External Debt",  5000.0,  5500.0,  6000.0
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "External Debt"
    ws.cell(row=1, column=1, value="External Debt (Rs. in million)")
    ws.cell(row=2, column=1, value="Indicator")
    ws.cell(row=2, column=2, value="2079/80R")   # revised suffix
    ws.cell(row=2, column=3, value="2080/81P")   # provisional suffix
    ws.cell(row=2, column=4, value="2081/82")    # plain
    ws.cell(row=3, column=1, value="Total External Debt")
    ws.cell(row=3, column=2, value=5000.0)
    ws.cell(row=3, column=3, value=5500.0)
    ws.cell(row=3, column=4, value=6000.0)
    wb.save(str(path))


def _build_ad_year_sheet(path: Path) -> None:
    """Fixture: AD-calendar-year FY column headers (2021/22, 2022/23).

    Mirrors the Migrant Workers / Foreign Trade real-file pattern where NRB
    uses AD fiscal years instead of BS. The parser should emit PeriodUnparseable
    with an explicit AD-year diagnostic rather than a bare NoDataExtracted.

    Layout:
      Row 1: "Migrant Workers by Country"
      Row 2: blank
      Row 3: "Country", "2021/22", "2022/23"
      Row 4: "Qatar", 45000, 50000
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Country"
    ws.cell(row=1, column=1, value="Migrant Workers by Country")
    ws.cell(row=3, column=1, value="Country")
    ws.cell(row=3, column=2, value="2021/22")
    ws.cell(row=3, column=3, value="2022/23")
    ws.cell(row=4, column=1, value="Qatar")
    ws.cell(row=4, column=2, value=45000)
    ws.cell(row=4, column=3, value=50000)
    wb.save(str(path))


@pytest.fixture(scope="session")
def bs_fy_suffix_xlsx() -> Path:
    p = FIXTURE_DIR / "bs_fy_suffix.xlsx"
    if not p.exists():
        _build_bs_fy_suffix(p)
    return p


@pytest.fixture(scope="session")
def ad_year_sheet_xlsx() -> Path:
    p = FIXTURE_DIR / "ad_year_sheet.xlsx"
    if not p.exists():
        _build_ad_year_sheet(p)
    return p


# ---------------------------------------------------------------------------
# v0.4.0 fixtures — non-standard AD layouts (ADR-0013 follow-up)
# ---------------------------------------------------------------------------


def _build_year_month_header(path: Path) -> None:
    """Fixture: the Foreign-exchange-reserves two-row monthly header.

    Layout (1-indexed openpyxl rows; data starts at col 3 = openpyxl col index 3):
      Row 1: title "Gross Foreign Assets of the Banking Sector"
      Row 2: unit "(Rs in Million)"
      Row 3: cols 3..: integer AD YEARS — 2001 spans Aug-Dec, 2002 spans Jan-Mar.
             The year cell appears only on the first month of each year-block
             (sparse) to exercise the forward-fill; remaining cells blank.
      Row 4: cols 3..: AD MONTH names (mixed abbreviated/full) — Aug, Sep, Oct,
             Nov, Dec, Jan, Feb, March. (8 months ≥ _MIN_MONTH_HEADER_CELLS=6.)
      Rows 5-6: indicator label in col 1 (a sub-item label in col 2 is joined),
             values across the month columns.
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "FX Reserves"
    ws.cell(row=1, column=1, value="Gross Foreign Assets of the Banking Sector")
    ws.cell(row=2, column=1, value="(Rs in Million)")
    # Year row (row 3): partially populated — enough year cells to pass detection
    # (≥ _MIN_YEAR_HEADER_CELLS), with gaps to exercise the forward-fill.
    # Columns 3..10 carry 8 monthly periods: Aug2001..Mar2002.
    ws.cell(row=3, column=3, value=2001)  # over "Aug"
    ws.cell(row=3, column=4, value=2001)  # over "Sep"
    # cols 5-7 (Oct, Nov, Dec) blank → forward-filled to 2001.
    ws.cell(row=3, column=8, value=2002)  # over "Jan"
    ws.cell(row=3, column=9, value=2002)  # over "Feb"
    # col 10 (March) blank → forward-filled to 2002.
    # Month row (row 4): mixed abbreviated/full names.
    months = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "March"]
    for i, m in enumerate(months):
        ws.cell(row=4, column=3 + i, value=m)
    # Data rows.
    rows_data = [
        ("A. Nepal Rastra Bank", None, [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0]),
        ("Gold Reserves", None, [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]),
    ]
    for r_off, (label, sub, vals) in enumerate(rows_data):
        r = 5 + r_off
        ws.cell(row=r, column=1, value=label)
        if sub is not None:
            ws.cell(row=r, column=2, value=sub)
        for i, v in enumerate(vals):
            ws.cell(row=r, column=3 + i, value=v)
    wb.save(str(path))


def _build_year_month_dup(path: Path) -> None:
    """Fixture: two-row monthly header with a REPEATED (year, month) column.

    Mirrors the real FX-reserves quirk of two adjacent "Oct 2025" columns holding
    different values. The parser must emit both (no data loss), flag the duplicate
    in parser_notes, and emit a single PeriodAmbiguous error.

    Months row: Aug Sep Oct Nov Dec Jan Oct  (the trailing "Oct" repeats Oct 2025).
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "FX Reserves"
    ws.cell(row=1, column=1, value="Gross Foreign Assets (Rs in Million)")
    # Year row: 2025 on the first three month cells (≥ _MIN_YEAR_HEADER_CELLS),
    # remaining cells blank → forward-filled to 2025 across the whole row.
    ws.cell(row=3, column=3, value=2025)
    ws.cell(row=3, column=4, value=2025)
    ws.cell(row=3, column=5, value=2025)
    months = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Oct"]
    for i, m in enumerate(months):
        ws.cell(row=4, column=3 + i, value=m)
    ws.cell(row=5, column=1, value="Total Reserves")
    # The two "Oct" columns (index 2 and 6) carry DIFFERENT values.
    vals = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 999.0]
    for i, v in enumerate(vals):
        ws.cell(row=5, column=3 + i, value=v)
    wb.save(str(path))


def _build_long_panel(path: Path) -> None:
    """Fixture: the Exchange-rate long panel.

    Layout:
      Row 1: title
      Row 2-3: sub-header rows naming the value columns
      Row 4: "Fiscal Year", "Month", "Buying", "Selling", "Middle Rate"
      Row 5..: FY in col 1 (sparse — only first month of each FY), AD month in
               col 2, three numeric value columns. Includes one aggregate
               "Annual Average" row that must be SKIPPED (not a calendar month).
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Time series"
    ws.cell(row=1, column=3, value="Nepalese Exchange Rate (Rupee per USD)")
    ws.cell(row=2, column=3, value="Month End")
    ws.cell(row=4, column=1, value="Fiscal Year")
    ws.cell(row=4, column=2, value="Month")
    ws.cell(row=4, column=3, value="Buying")
    ws.cell(row=4, column=4, value="Selling")
    ws.cell(row=4, column=5, value="Middle Rate")
    # FY 2022/23: July (AD 2022) .. August (AD 2022); FY label only on first month.
    panel = [
        ("2022/23", "July", 130.0, 130.6, 130.3),
        (None, "August", 131.0, 131.6, 131.3),
        (None, "Annual Average", 130.5, 131.1, 130.8),  # aggregate → skipped
        ("2023/24", "January", 132.0, 132.6, 132.3),  # AD 2024 (Jan of FY 2023/24)
    ]
    for r_off, (fy, month, buy, sell, mid) in enumerate(panel):
        r = 5 + r_off
        if fy is not None:
            ws.cell(row=r, column=1, value=fy)
        ws.cell(row=r, column=2, value=month)
        ws.cell(row=r, column=3, value=buy)
        ws.cell(row=r, column=4, value=sell)
        ws.cell(row=r, column=5, value=mid)
    wb.save(str(path))


def _build_transposed(path: Path) -> None:
    """Fixture: the Tourist-arrivals transposed layout.

    Layout:
      Row 1: title "Tourist Arrivals"
      Row 2: "Year", "Jan", "Feb", "Mar", ... "Dec", "Total"
      Row 3..: integer AD year in col 1, 12 monthly values + an annual Total
               column (which must be ignored — it is not a month).
    """
    _ensure_fixture_dir()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Tourist Arrival"
    ws.cell(row=1, column=1, value="Tourist Arrivals (Number)")
    header = ["Year", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total"]
    for i, h in enumerate(header):
        ws.cell(row=2, column=1 + i, value=h)
    years = [
        (1992, [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210], 1860),
        (1993, [101, 111, 121, 131, 141, 151, 161, 171, 181, 191, 201, 211], 1872),
    ]
    for r_off, (yr, vals, total) in enumerate(years):
        r = 3 + r_off
        ws.cell(row=r, column=1, value=yr)
        for i, v in enumerate(vals):
            ws.cell(row=r, column=2 + i, value=v)
        ws.cell(row=r, column=14, value=total)  # Total column — must be ignored
    wb.save(str(path))


@pytest.fixture(scope="session")
def year_month_header_xlsx() -> Path:
    p = FIXTURE_DIR / "year_month_header.xlsx"
    if not p.exists():
        _build_year_month_header(p)
    return p


@pytest.fixture(scope="session")
def year_month_dup_xlsx() -> Path:
    p = FIXTURE_DIR / "year_month_dup.xlsx"
    if not p.exists():
        _build_year_month_dup(p)
    return p


@pytest.fixture(scope="session")
def long_panel_xlsx() -> Path:
    p = FIXTURE_DIR / "long_panel.xlsx"
    if not p.exists():
        _build_long_panel(p)
    return p


@pytest.fixture(scope="session")
def transposed_xlsx() -> Path:
    p = FIXTURE_DIR / "transposed.xlsx"
    if not p.exists():
        _build_transposed(p)
    return p
