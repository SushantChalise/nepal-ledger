"""Pytest fixtures for wb_knomad_bilateral parser tests.

Creates a minimal synthetic KNOMAD bilateral XLSX in memory so tests
can run offline without downloading the real KNOMAD file.

Matrix structure (matching real KNOMAD format):
  - Sheet "Bilateral_Remittance"
  - Row 0 (header): [None, "China", "Nepal", "India", "World"]
      (receiving countries; Nepal is at column index 2)
  - Row 1: "China"   — [None, 0.0,   50.0,   30.0,  ...]
  - Row 2: "India"   — [None, 200.0, 1200.0, 0.0,   ...]
  - Row 3: "Qatar"   — [None, 0.0,   700.0,  0.0,   ...]
  - Row 4: "United Arab Emirates" — [None, 0.0, 600.0, 0.0, ...]
  - Row 5: "Malaysia"— [None, 0.0,   200.0,  0.0,   ...]
  - Row 6: "United States" — [None, 0.0, 150.0, 0.0, ...]
  - Row 7: "World"   — [None, 500.0, 3200.0, 80.0,  ...]
      (grand total column; Nepal = 3200 = sum of all inflows)

All values in USD millions.
"""

from __future__ import annotations

import io
import pathlib

import openpyxl
import pytest


_FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"

# The year embedded in the synthetic fixture filename
SYNTHETIC_YEAR = 2024

# Expected values (USD millions) for assertions in tests
EXPECTED_INDIA = 1200.0
EXPECTED_QATAR = 700.0
EXPECTED_UAE = 600.0
EXPECTED_MALAYSIA = 200.0
EXPECTED_USA = 150.0
EXPECTED_TOTAL = 3200.0


def _make_synthetic_xlsx(year: int = SYNTHETIC_YEAR) -> bytes:
    """Return bytes of a minimal synthetic KNOMAD bilateral XLSX."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bilateral_Remittance"  # type: ignore[union-attr]

    # Row 0: receiving-country headers (col 0 = None / blank)
    ws.append([None, "China", "Nepal", "India", "World"])  # type: ignore[union-attr]

    # Sending-country rows: [sending_country, china_col, nepal_col, india_col, world_col]
    ws.append(["China", None, 50.0, 30.0, None])  # type: ignore[union-attr]
    ws.append(["India", 200.0, EXPECTED_INDIA, None, None])  # type: ignore[union-attr]
    ws.append(["Qatar", None, EXPECTED_QATAR, None, None])  # type: ignore[union-attr]
    ws.append(["United Arab Emirates", None, EXPECTED_UAE, None, None])  # type: ignore[union-attr]
    ws.append(["Malaysia", None, EXPECTED_MALAYSIA, None, None])  # type: ignore[union-attr]
    ws.append(["United States", None, EXPECTED_USA, None, None])  # type: ignore[union-attr]
    ws.append(["World", 500.0, EXPECTED_TOTAL, 80.0, None])  # type: ignore[union-attr]

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="session")
def synthetic_xlsx_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Write a synthetic KNOMAD bilateral XLSX to a temp path and return it.

    The filename embeds the year so the parser's year-inference works.
    """
    tmp = tmp_path_factory.mktemp("knomad_fixture")
    path = tmp / f"knomad-bilateral-{SYNTHETIC_YEAR}.xlsx"
    path.write_bytes(_make_synthetic_xlsx(SYNTHETIC_YEAR))
    return path


@pytest.fixture(scope="session")
def fixture_dir() -> pathlib.Path:
    """Return the fixtures directory (for optional real-file tests)."""
    return _FIXTURE_DIR
