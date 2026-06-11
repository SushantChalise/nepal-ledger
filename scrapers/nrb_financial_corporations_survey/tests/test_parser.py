"""Tests for nrb_financial_corporations_survey parser v0.1.0.

Fixture files (committed to the repo):
    fcs_q1_2082-83.xlsx  -- Q1 FY2082/83 (most recent; 13 date columns)
    fcs_q2_2082-83.xlsx  -- Q2 FY2082/83 (14 date columns)
    fcs_q3q4_2080-81.xlsx -- FY2080/81 (older; 8 date columns)

Known values from scout findings (fcs_q1_2082-83.xlsx, 2025 October col):
    nrb-fcs-m2-annual:                7 011 781.58  Rs. million
    nrb-fcs-credit-private-annual:    6 540 851.82  Rs. million
    nrb-fcs-net-foreign-assets-annual: 3 003 994.67  Rs. million
"""

from pathlib import Path

import pytest

from nrb_financial_corporations_survey.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    _TARGET_ROWS,
    parse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_Q1 = FIXTURE_DIR / "fcs_q1_2082-83.xlsx"
FIXTURE_Q2 = FIXTURE_DIR / "fcs_q2_2082-83.xlsx"
FIXTURE_Q3Q4 = FIXTURE_DIR / "fcs_q3q4_2080-81.xlsx"

TARGET_SLUGS = {slug for _, slug, _ in _TARGET_ROWS}


@pytest.fixture(scope="module")
def result_q1():
    return parse(str(FIXTURE_Q1), "test-q1")


@pytest.fixture(scope="module")
def result_q2():
    return parse(str(FIXTURE_Q2), "test-q2")


@pytest.fixture(scope="module")
def result_q3q4():
    return parse(str(FIXTURE_Q3Q4), "test-q3q4")


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


def test_parser_version():
    assert PARSER_VERSION == "0.1.0"


def test_source_id():
    assert SOURCE_ID == "nrb-financial-corporations-survey"


# ---------------------------------------------------------------------------
# Status + row count tests (Q1 fixture)
# ---------------------------------------------------------------------------


def test_status_success(result_q1):
    assert result_q1.status == "success", f"errors: {result_q1.errors}"


def test_no_errors(result_q1):
    assert result_q1.errors == []


def test_row_count_at_least_target_slugs(result_q1):
    """Each target slug should appear in at least one row."""
    assert len(result_q1.staging_rows) >= len(TARGET_SLUGS)


def test_all_target_slugs_present(result_q1):
    found_slugs = {r.indicator_slug_raw for r in result_q1.staging_rows}
    assert TARGET_SLUGS <= found_slugs


# ---------------------------------------------------------------------------
# Required fields non-null
# ---------------------------------------------------------------------------


def test_required_fields_populated(result_q1):
    for row in result_q1.staging_rows:
        assert row.indicator_slug_raw, "indicator_slug_raw is empty"
        assert row.value is not None, "value is None"
        assert row.unit, "unit is empty"
        assert row.reporting_period_type, "reporting_period_type is empty"
        assert row.reporting_period_bs, "reporting_period_bs is empty"
        assert row.reporting_period_ad_start is not None
        assert row.reporting_period_ad_end is not None
        assert row.publication_date_ad is not None
        assert row.publication_date_bs, "publication_date_bs is empty"
        assert row.fiscal_year_bs, "fiscal_year_bs is empty"
        assert row.fiscal_year_ad_label, "fiscal_year_ad_label is empty"
        assert row.confidence_grade_proposed in ("A", "B", "C")


# ---------------------------------------------------------------------------
# Specific known values (Q1 fixture, 2025 October column)
# ---------------------------------------------------------------------------


def test_m2_known_value(result_q1):
    """Liquid Liabilities at 2025 October (Ashwin 2082) = 7 011 781.58."""
    m2_rows = [
        r for r in result_q1.staging_rows
        if r.indicator_slug_raw == "nrb-fcs-m2-annual"
        and "Ashwin" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(m2_rows) >= 1, "no M2 row for Ashwin 2082"
    assert abs(m2_rows[0].value - 7_011_781.58) < 1.0


def test_credit_private_known_value(result_q1):
    """Credit to Private Sector at 2025 October (Ashwin 2082) = 6 540 851.82."""
    rows = [
        r for r in result_q1.staging_rows
        if r.indicator_slug_raw == "nrb-fcs-credit-private-annual"
        and "Ashwin" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(rows) >= 1, "no credit row for Ashwin 2082"
    assert abs(rows[0].value - 6_540_851.82) < 1.0


def test_net_foreign_assets_known_value(result_q1):
    """Foreign Assets Net at 2025 October (Ashwin 2082) = 3 003 994.67."""
    rows = [
        r for r in result_q1.staging_rows
        if r.indicator_slug_raw == "nrb-fcs-net-foreign-assets-annual"
        and "Ashwin" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(rows) >= 1, "no NFA row for Ashwin 2082"
    assert abs(rows[0].value - 3_003_994.67) < 1.0


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_unit_is_npr_million(result_q1):
    for row in result_q1.staging_rows:
        assert row.unit == "npr_million"


# ---------------------------------------------------------------------------
# Period type correctness
# ---------------------------------------------------------------------------


def test_ashadh_rows_are_annual(result_q1):
    ashadh_rows = [r for r in result_q1.staging_rows if "Ashadh" in r.reporting_period_bs]
    assert ashadh_rows, "no Ashadh (annual) rows found"
    for row in ashadh_rows:
        assert row.reporting_period_type == "annual", (
            f"expected annual for {row.reporting_period_bs}, got {row.reporting_period_type}"
        )


def test_ashwin_rows_are_quarterly(result_q1):
    ashwin_rows = [r for r in result_q1.staging_rows if "Ashwin" in r.reporting_period_bs]
    assert ashwin_rows
    for row in ashwin_rows:
        assert row.reporting_period_type == "quarterly"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotent(result_q1):
    result2 = parse(str(FIXTURE_Q1), "test-q1-2")
    assert result2.status == result_q1.status
    assert len(result2.staging_rows) == len(result_q1.staging_rows)
    for a, b in zip(result_q1.staging_rows, result2.staging_rows):
        assert a.value == b.value
        assert a.indicator_slug_raw == b.indicator_slug_raw
        assert a.reporting_period_bs == b.reporting_period_bs


# ---------------------------------------------------------------------------
# Missing file returns failure
# ---------------------------------------------------------------------------


def test_missing_file_returns_failure():
    result = parse("/nonexistent/path/fcs.xlsx", "missing")
    assert result.status == "failure"
    assert len(result.errors) >= 1
    assert result.errors[0].error_class == "Other"


# ---------------------------------------------------------------------------
# Multi-fixture smoke tests
# ---------------------------------------------------------------------------


def test_q2_status_success(result_q2):
    assert result_q2.status == "success", f"errors: {result_q2.errors}"


def test_q2_more_columns_than_q1(result_q1, result_q2):
    """Q2 has one additional date column vs Q1."""
    assert len(result_q2.staging_rows) > len(result_q1.staging_rows)


def test_q3q4_status_success(result_q3q4):
    assert result_q3q4.status == "success", f"errors: {result_q3q4.errors}"


def test_q3q4_all_slugs_present(result_q3q4):
    found_slugs = {r.indicator_slug_raw for r in result_q3q4.staging_rows}
    assert TARGET_SLUGS <= found_slugs
