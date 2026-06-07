"""Tests for the NRB DNE XLSX parser (nrb_dne.parser).

All tests run against programmatically-generated XLSX fixtures from conftest.py.
No network. No binary fixtures committed.

Test matrix:
    test_happy_path_*       — main parser logic on the external-reserves fixture
    test_empty_workbook_*   — empty sheet → partial status, NoDataExtracted error
    test_ambiguous_unit_*   — missing unit → UnitAmbiguous error, rows still parsed
    test_bad_period_*       — malformed period header → PeriodUnparseable error
    test_missing_file_*     — non-existent path → failure status
    test_idempotent         — same input → same output
    test_json_serialisable  — asdict output round-trips through json.dumps
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nrb_dne import PARSER_VERSION, SOURCE_ID, parse

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def happy_result(happy_path_xlsx: Path) -> ParserResult:
    return parse(str(happy_path_xlsx), source_document_id="test-doc-happy")


def test_happy_status_success(happy_result: ParserResult) -> None:
    assert happy_result.status == "success", f"errors={happy_result.errors}"


def test_happy_parser_version(happy_result: ParserResult) -> None:
    assert happy_result.parser_version == PARSER_VERSION == "0.1.0"


def test_happy_source_id() -> None:
    assert SOURCE_ID == "nrb-dne-xlsx"


def test_happy_row_count(happy_result: ParserResult) -> None:
    # 3 indicators × (3 annual + 2 monthly) = 15 rows.
    assert len(happy_result.staging_rows) == 15


def test_happy_no_errors(happy_result: ParserResult) -> None:
    assert happy_result.errors == [], f"unexpected errors: {happy_result.errors}"


def test_happy_slugs(happy_result: ParserResult) -> None:
    slugs = {r.indicator_slug_raw for r in happy_result.staging_rows}
    assert "dne-total-foreign-exchange-reserves" in slugs
    assert "dne-gold-reserves" in slugs
    assert "dne-foreign-currency-assets" in slugs


def test_happy_unit_all_usd_million(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert row.unit == "usd_million", f"slug={row.indicator_slug_raw} unit={row.unit}"


def test_happy_annual_periods(happy_result: ParserResult) -> None:
    annual = [r for r in happy_result.staging_rows if r.reporting_period_type == "annual"]
    # 3 indicators × 3 annual columns = 9 annual rows.
    assert len(annual) == 9
    fy_labels = {r.fiscal_year_bs for r in annual}
    assert "2080/81" in fy_labels
    assert "2081/82" in fy_labels
    assert "2082/83" in fy_labels


def test_happy_monthly_periods(happy_result: ParserResult) -> None:
    monthly = [r for r in happy_result.staging_rows if r.reporting_period_type == "monthly"]
    # 3 indicators × 2 monthly columns = 6 monthly rows.
    assert len(monthly) == 6
    bs_labels = {r.reporting_period_bs for r in monthly}
    assert "Shrawan 2082" in bs_labels
    assert "Bhadra 2082" in bs_labels


def test_happy_confidence_grade(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert row.confidence_grade_proposed == "B"


def test_happy_values_correct(happy_result: ParserResult) -> None:
    """Spot-check specific known values from the synthetic fixture."""
    total_rows = [
        r for r in happy_result.staging_rows
        if r.indicator_slug_raw == "dne-total-foreign-exchange-reserves"
    ]
    annual_vals = {
        r.fiscal_year_bs: r.value
        for r in total_rows
        if r.reporting_period_type == "annual"
    }
    assert annual_vals["2080/81"] == pytest.approx(1500.0)
    assert annual_vals["2081/82"] == pytest.approx(2100.0)
    assert annual_vals["2082/83"] == pytest.approx(2300.0)


def test_happy_all_rows_are_staging_drafts(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert isinstance(row, StagingRowDraft)


def test_happy_period_ad_start_before_end(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert row.reporting_period_ad_start < row.reporting_period_ad_end, (
            f"slug={row.indicator_slug_raw} period_bs={row.reporting_period_bs}: "
            f"ad_start >= ad_end"
        )


def test_happy_ad_label_format(happy_result: ParserResult) -> None:
    """fiscal_year_ad_label should be YYYY/YY format for all annual rows."""
    annual = [r for r in happy_result.staging_rows if r.reporting_period_type == "annual"]
    for row in annual:
        parts = row.fiscal_year_ad_label.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit() and len(parts[0]) == 4
        assert parts[1].isdigit() and len(parts[1]) == 2


# ---------------------------------------------------------------------------
# Empty workbook → partial, NoDataExtracted
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def empty_result(empty_workbook_xlsx: Path) -> ParserResult:
    return parse(str(empty_workbook_xlsx), source_document_id="test-doc-empty")


def test_empty_status_partial(empty_result: ParserResult) -> None:
    assert empty_result.status == "partial"


def test_empty_no_rows(empty_result: ParserResult) -> None:
    assert empty_result.staging_rows == []


def test_empty_has_no_data_error(empty_result: ParserResult) -> None:
    detail_texts = " ".join(e.error_detail for e in empty_result.errors)
    assert "NoDataExtracted" in detail_texts, f"errors={empty_result.errors}"


# ---------------------------------------------------------------------------
# Ambiguous unit → UnitAmbiguous error, rows still parsed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ambiguous_result(ambiguous_unit_xlsx: Path) -> ParserResult:
    return parse(str(ambiguous_unit_xlsx), source_document_id="test-doc-ambiguous")


def test_ambiguous_has_rows(ambiguous_result: ParserResult) -> None:
    # Parser should still emit rows even when unit is ambiguous.
    assert len(ambiguous_result.staging_rows) > 0


def test_ambiguous_has_unit_error(ambiguous_result: ParserResult) -> None:
    error_classes = [e.error_class for e in ambiguous_result.errors]
    assert "UnitAmbiguous" in error_classes, f"errors={ambiguous_result.errors}"


def test_ambiguous_status_partial(ambiguous_result: ParserResult) -> None:
    # Errors present → partial.
    assert ambiguous_result.status == "partial"


def test_ambiguous_slug_prefix(ambiguous_result: ParserResult) -> None:
    for row in ambiguous_result.staging_rows:
        assert row.indicator_slug_raw.startswith("dne-")


# ---------------------------------------------------------------------------
# Bad period header → PeriodUnparseable error, valid column still parsed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bad_period_result(bad_period_xlsx: Path) -> ParserResult:
    return parse(str(bad_period_xlsx), source_document_id="test-doc-bad-period")


def test_bad_period_has_error(bad_period_result: ParserResult) -> None:
    error_classes = [e.error_class for e in bad_period_result.errors]
    assert "PeriodUnparseable" in error_classes, f"errors={bad_period_result.errors}"


def test_bad_period_still_parses_valid_column(bad_period_result: ParserResult) -> None:
    # The valid "2081/82" column should still produce a row for "Tax Revenue".
    slugs = {r.indicator_slug_raw for r in bad_period_result.staging_rows}
    assert "dne-tax-revenue" in slugs


def test_bad_period_status_partial(bad_period_result: ParserResult) -> None:
    assert bad_period_result.status == "partial"


# ---------------------------------------------------------------------------
# Missing file → failure
# ---------------------------------------------------------------------------


def test_missing_file_returns_failure() -> None:
    result = parse("nonexistent-dne.xlsx", source_document_id="x")
    assert result.status == "failure"
    assert result.errors
    assert result.staging_rows == []


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotent(happy_path_xlsx: Path) -> None:
    a = parse(str(happy_path_xlsx), source_document_id="x")
    b = parse(str(happy_path_xlsx), source_document_id="x")
    assert a.status == b.status
    assert len(a.staging_rows) == len(b.staging_rows)
    for ra, rb in zip(a.staging_rows, b.staging_rows, strict=True):
        assert ra == rb


# ---------------------------------------------------------------------------
# JSON serialisability (orchestrator contract)
# ---------------------------------------------------------------------------


def test_json_serialisable(happy_result: ParserResult) -> None:
    payload = asdict(happy_result)
    for row in payload.get("staging_rows", []):
        for key in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            val = row.get(key)
            from datetime import datetime

            if isinstance(val, datetime):
                row[key] = val.isoformat()

    dumped = json.dumps(payload)
    assert "staging_rows" in dumped
    assert "parser_version" in dumped
    assert "dne-" in dumped


# ---------------------------------------------------------------------------
# Sample row spot-check (aids debugging when the suite first runs)
# ---------------------------------------------------------------------------


def test_sample_row_shape(happy_result: ParserResult) -> None:
    """Verify one representative row has all required StagingRowDraft fields."""
    row = next(
        r for r in happy_result.staging_rows
        if r.indicator_slug_raw == "dne-total-foreign-exchange-reserves"
        and r.reporting_period_type == "annual"
        and r.fiscal_year_bs == "2082/83"
    )
    assert row.value == pytest.approx(2300.0)
    assert row.unit == "usd_million"
    assert row.confidence_grade_proposed == "B"
    assert row.fiscal_year_ad_label == "2025/26"
    assert row.reporting_period_bs == "2082/83"
