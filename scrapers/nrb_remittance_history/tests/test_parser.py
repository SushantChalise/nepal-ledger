"""Tests for the NRB historical Workers'-Remittances parser.

Runs against a programmatically-generated 'BOP 2000-' fixture (conftest.py) —
no committed binaries, mirroring the nrb_dne convention. The real-file
extraction (FY2000/01 = 47,216.1 → FY2020/21 = 961,054.6 npr_million, 21 points)
is verified manually via `parser.py <real_xlsx> --verify`; see the README.
"""

from __future__ import annotations

import json
from pathlib import Path

from nrb_remittance_history import PARSER_VERSION, parse
from nrb_remittance_history.tests.conftest import EXPECTED


def test_happy_path_extracts_annual_series(bop_xlsx: Path) -> None:
    result = parse(bop_xlsx)
    assert result.status == "success"
    assert result.parser_version == PARSER_VERSION
    assert len(result.staging_rows) == len(EXPECTED)
    assert not result.errors


def test_values_and_bs_conversion(bop_xlsx: Path) -> None:
    rows = parse(bop_xlsx).staging_rows
    got = [(r.reporting_period_bs, r.value) for r in rows]
    assert got == EXPECTED  # AD→BS (+57) + values preserved exactly


def test_row_contract(bop_xlsx: Path) -> None:
    row = parse(bop_xlsx).staging_rows[0]
    assert row.indicator_slug_raw == "dne-remittance-workers-historical"
    assert row.unit == "npr_million"
    assert row.reporting_period_type == "annual"
    assert row.confidence_grade_proposed == "B"
    # FY2000/01 AD → BS 2057/58; AD period spans mid-Jul 2000 → mid-Jul 2001.
    assert row.fiscal_year_ad_label == "2000/01"
    assert row.reporting_period_ad_start.year == 2000
    assert row.reporting_period_ad_end.year == 2001
    # One publication date for the whole compilation (latest FY end).
    assert row.publication_date_bs == "2077/78"


def test_missing_remittance_row_fails_loud(bop_xlsx_no_remittance: Path) -> None:
    result = parse(bop_xlsx_no_remittance)
    assert result.status == "failure"
    assert any(e.error_class == "RowMissing" for e in result.errors)
    assert not result.staging_rows  # never fabricate


def test_missing_sheet_fails(tmp_path: Path) -> None:
    from openpyxl import Workbook

    p = tmp_path / "wrong.xlsx"
    wb = Workbook()
    wb.active.title = "Something Else"
    wb.save(p)
    result = parse(p)
    assert result.status == "failure"
    assert any(e.error_class == "SheetMissing" for e in result.errors)


def test_idempotent(bop_xlsx: Path) -> None:
    a = parse(bop_xlsx).to_json_dict()
    b = parse(bop_xlsx).to_json_dict()
    assert json.dumps(a) == json.dumps(b)


def test_json_serialisable(bop_xlsx: Path) -> None:
    json.dumps(parse(bop_xlsx).to_json_dict())  # must not raise
