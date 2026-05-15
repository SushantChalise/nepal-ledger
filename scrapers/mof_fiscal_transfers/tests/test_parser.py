"""Tests for the MoF Local Fiscal Transfers parser.

Runs against a self-contained fixture XLSX built by conftest.py. The
gitignored real corpus is NEVER touched by these tests — see
``conftest.py::_inject_canonical_table``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mof_fiscal_transfers import PARSER_VERSION, FiscalTransferRow, parse
from mof_fiscal_transfers.tests.conftest import SAMPLE_XLSX

EXPECTED_GRANT_TYPES = {
    "equalization_minimum",
    "equalization_formula",
    "equalization_performance",
    "conditional_current",
    "conditional_capital",
    "special_current",
    "special_capital",
    "complementary_capital",
}
EXPECTED_MUNICIPALITIES = 3


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    assert SAMPLE_XLSX.exists(), f"fixture missing: {SAMPLE_XLSX}"
    return parse(str(SAMPLE_XLSX), source_document_id="test-doc-id")


def test_status_success(result: dict[str, object]) -> None:
    assert result["status"] == "success", (
        f"got status={result['status']!r} errors={result['errors']!r}"
    )


def test_parser_version(result: dict[str, object]) -> None:
    assert result["parser_version"] == PARSER_VERSION == "0.1.0"


def test_row_count(result: dict[str, object]) -> None:
    rows = result["rows"]
    assert isinstance(rows, list)
    # 3 municipalities × 8 grant types (including zero-valued special_current)
    assert len(rows) == EXPECTED_MUNICIPALITIES * len(EXPECTED_GRANT_TYPES)


def test_grant_types_complete(result: dict[str, object]) -> None:
    rows = result["rows"]
    assert isinstance(rows, list)
    grant_types_emitted = {row["grant_type"] for row in rows}
    assert grant_types_emitted == EXPECTED_GRANT_TYPES


def test_kathmandu_equalization_minimum(result: dict[str, object]) -> None:
    rows = result["rows"]
    assert isinstance(rows, list)
    matches = [
        r
        for r in rows
        if r["federal_code"] == "80101101" and r["grant_type"] == "equalization_minimum"
    ]
    assert len(matches) == 1
    assert matches[0]["amount_npr"] == pytest.approx(100000.0)
    assert matches[0]["unit"] == "NPR_thousand"
    assert matches[0]["confidence_grade"] == "A"
    assert matches[0]["fiscal_year_bs"] == "2082/83"


def test_pokhara_conditional_current(result: dict[str, object]) -> None:
    rows = result["rows"]
    assert isinstance(rows, list)
    matches = [
        r
        for r in rows
        if r["federal_code"] == "80201101" and r["grant_type"] == "conditional_current"
    ]
    assert len(matches) == 1
    assert matches[0]["amount_npr"] == pytest.approx(600000.0)
    assert matches[0]["district_en"] == "Kaski"


def test_total_row_skipped(result: dict[str, object]) -> None:
    rows = result["rows"]
    assert isinstance(rows, list)
    # No federal_code maps to "Total"; verify no row has impossibly-large amount
    # belonging to the aggregator row.
    for row in rows:
        assert row["municipality_name_en"] != "Total"


def test_all_row_fields_typed(result: dict[str, object]) -> None:
    rows = result["rows"]
    assert isinstance(rows, list)
    for row in rows:
        # Validate by reconstructing the dataclass — strict type check.
        rebuilt = FiscalTransferRow(**row)
        assert rebuilt.federal_code.isdigit()
        assert len(rebuilt.federal_code) == 8
        assert rebuilt.grant_type in EXPECTED_GRANT_TYPES
        assert rebuilt.amount_npr >= 0
        assert rebuilt.unit == "NPR_thousand"


def test_idempotent() -> None:
    """Per docs/DATA_PIPELINE.md: parsers must be deterministic."""
    first = parse(str(SAMPLE_XLSX), source_document_id="x")
    second = parse(str(SAMPLE_XLSX), source_document_id="x")
    assert first == second


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent.xlsx", source_document_id="x")
    assert res["status"] == "failure"
    errors = res["errors"]
    assert isinstance(errors, list)
    assert len(errors) >= 1


def test_no_unexpected_errors(result: dict[str, object]) -> None:
    assert result["errors"] == [], f"unexpected parser errors: {result['errors']!r}"


def test_fixture_xlsx_is_real_xlsx() -> None:
    """Sanity: openpyxl must accept the fixture (catches binary corruption)."""
    from openpyxl import load_workbook

    wb = load_workbook(SAMPLE_XLSX, read_only=True)
    assert "Sheet1" in wb.sheetnames
    wb.close()


def test_fixture_path_under_tests_dir() -> None:
    """Fixture lives under the tests/ tree, not in the repo root."""
    assert SAMPLE_XLSX.parent == Path(__file__).resolve().parent / "fixtures"
