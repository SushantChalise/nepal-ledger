"""Tests for scrapers/dofe_labour_migration/parser.py.

Uses a real fixture PDF downloaded from DoFE (Chaita 2082).  A synthetic
fixture built inline with openpyxl is NOT applicable here — the source is PDF.
The real fixture is checked into tests/fixtures/ and is small enough (<1 MB).
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pytest

from dofe_labour_migration.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    _country_slug,
    _detect_period,
    _indicator_slug,
    parse,
)
from _common.types import ParserResult

FIXTURES = Path(__file__).parent / "fixtures"
CHAITA_PDF = FIXTURES / "dofe_monthly_chaita_2082.pdf"
MANGSIR_PDF = FIXTURES / "dofe_monthly_mangsir_2082.pdf"


# ── Module-level constants ─────────────────────────────────────────────────────


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


def test_source_id() -> None:
    assert SOURCE_ID == "dofe-labour-migration"


# ── Country slug helper ────────────────────────────────────────────────────────


def test_country_slug_known() -> None:
    assert _country_slug("Qatar") == "qatar"
    assert _country_slug("Saudi Arabia") == "saudi-arabia"
    assert _country_slug("UAE") == "uae"
    assert _country_slug("Republic of Korea") == "korea"
    assert _country_slug("Grand Total") == "total"


def test_country_slug_case_insensitive() -> None:
    assert _country_slug("MALAYSIA") == "malaysia"
    assert _country_slug("Malaysia") == "malaysia"


def test_country_slug_unknown_auto() -> None:
    slug = _country_slug("Fictonia")
    assert slug == "fictonia"
    assert slug.islower()
    assert " " not in slug


# ── Indicator slug format ──────────────────────────────────────────────────────


def test_indicator_slug_format() -> None:
    slug = _indicator_slug("qatar")
    assert slug.startswith("dofe-departures-")
    assert slug.endswith("-monthly")
    assert slug == "dofe-departures-qatar-monthly"


def test_indicator_slug_total() -> None:
    assert _indicator_slug("total") == "dofe-departures-total-monthly"


# ── Period detection ───────────────────────────────────────────────────────────


def test_period_detection_chaita() -> None:
    text = "Countrywise Labour Approval for Chaita- 2082"
    errors: list = []
    period = _detect_period(text, errors)
    assert period is not None
    assert errors == []
    assert period.bs_month == "Chait"
    assert period.bs_year == 2082
    assert period.bs_fy_start == 2082
    assert period.fiscal_year_bs == "2082/83"
    assert "Chait" in period.reporting_period_bs


def test_period_detection_mangsir() -> None:
    text = "Countrywise Labour Approval for Mangsir 2082"
    errors: list = []
    period = _detect_period(text, errors)
    assert period is not None
    assert period.bs_month == "Mangsir"
    assert period.bs_year == 2082
    assert period.bs_fy_start == 2082
    assert period.fiscal_year_bs == "2082/83"


def test_period_detection_shrawan() -> None:
    text = "Countrywise Labour Approval for Shrawan 2082"
    errors: list = []
    period = _detect_period(text, errors)
    assert period is not None
    assert period.bs_month == "Shrawan"
    assert period.bs_fy_start == 2082


def test_period_detection_invalid_month() -> None:
    text = "Countrywise Labour Approval for Octember 2082"
    errors: list = []
    period = _detect_period(text, errors)
    assert period is None
    assert len(errors) == 1
    assert errors[0].error_class == "PeriodAmbiguous"


def test_period_detection_missing_title() -> None:
    text = "Some other document without the countrywise header"
    errors: list = []
    period = _detect_period(text, errors)
    assert period is None
    assert len(errors) == 1
    assert errors[0].error_class == "PeriodAmbiguous"


# ── parse() integration tests — real fixture ──────────────────────────────────


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_status_success_chaita() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    assert result.status == "success"
    assert result.parser_version == PARSER_VERSION


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_row_count_chaita() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    # Expect at least 50 countries + Grand Total row
    assert len(result.staging_rows) >= 50


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_malaysia_value_chaita() -> None:
    """Chaita 2082: Malaysia Total with ReEntry Total = 18649 (from fixture)."""
    result = parse(str(CHAITA_PDF), "doc-001")
    malaysia_rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "dofe-departures-malaysia-monthly"
    ]
    assert len(malaysia_rows) == 1
    assert malaysia_rows[0].value == 18649.0


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_qatar_value_chaita() -> None:
    """Chaita 2082: Qatar Total with ReEntry Total = 8959."""
    result = parse(str(CHAITA_PDF), "doc-001")
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "dofe-departures-qatar-monthly"]
    assert len(rows) == 1
    assert rows[0].value == 8959.0


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_total_row_present_chaita() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    total_rows = [r for r in result.staging_rows if r.indicator_slug_raw == "dofe-departures-total-monthly"]
    assert len(total_rows) == 1
    # Grand Total with ReEntry should be 61819 for Chaita 2082
    assert total_rows[0].value == 61819.0


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_unit_is_count_chaita() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    for row in result.staging_rows:
        assert row.unit == "count"


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_reporting_period_type_monthly() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    for row in result.staging_rows:
        assert row.reporting_period_type == "monthly"


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_confidence_grade_a() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    for row in result.staging_rows:
        # Known countries have grade A; auto-generated slugs may too
        assert row.confidence_grade_proposed == "A"


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_indicator_slugs_format() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    for row in result.staging_rows:
        assert row.indicator_slug_raw.startswith("dofe-departures-")
        assert row.indicator_slug_raw.endswith("-monthly")


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_no_duplicate_slugs() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    slugs = [r.indicator_slug_raw for r in result.staging_rows]
    assert len(slugs) == len(set(slugs)), "Duplicate indicator slugs found"


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_period_bs_chaita() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    for row in result.staging_rows:
        assert "2082" in row.reporting_period_bs
        assert "Chait" in row.reporting_period_bs


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_fiscal_year_bs_chaita() -> None:
    result = parse(str(CHAITA_PDF), "doc-001")
    for row in result.staging_rows:
        # Chaita 2082 is month 9 of BS fiscal year 2082 (FY 2082/83, AD 2025/26)
        assert row.fiscal_year_bs == "2082/83"
        assert row.fiscal_year_ad_label == "2025/26"


@pytest.mark.skipif(
    not CHAITA_PDF.exists(),
    reason="Chaita 2082 fixture PDF not present",
)
def test_idempotent_chaita() -> None:
    """Parsing the same file twice yields identical results."""
    result1 = parse(str(CHAITA_PDF), "doc-001")
    result2 = parse(str(CHAITA_PDF), "doc-001")
    assert result1.status == result2.status
    assert len(result1.staging_rows) == len(result2.staging_rows)
    for r1, r2 in zip(result1.staging_rows, result2.staging_rows):
        assert r1 == r2


def test_missing_file_returns_failure() -> None:
    result = parse("/nonexistent/path/dofe.pdf", "doc-000")
    assert result.status == "failure"
    assert len(result.errors) == 1
    assert result.errors[0].error_class == "Other"
    assert "not found" in result.errors[0].error_detail


@pytest.mark.skipif(
    not MANGSIR_PDF.exists(),
    reason="Mangsir 2082 fixture PDF not present",
)
def test_mangsir_2082_status() -> None:
    result = parse(str(MANGSIR_PDF), "doc-002")
    assert result.status == "success"


@pytest.mark.skipif(
    not MANGSIR_PDF.exists(),
    reason="Mangsir 2082 fixture PDF not present",
)
def test_mangsir_2082_period() -> None:
    result = parse(str(MANGSIR_PDF), "doc-002")
    for row in result.staging_rows:
        assert "Mangsir" in row.reporting_period_bs
        assert row.fiscal_year_bs == "2082/83"
        assert row.fiscal_year_ad_label == "2025/26"


@pytest.mark.skipif(
    not MANGSIR_PDF.exists(),
    reason="Mangsir 2082 fixture PDF not present",
)
def test_mangsir_saudi_arabia_value() -> None:
    """Mangsir 2082: Saudi Arabia Total with ReEntry Total = 14330."""
    result = parse(str(MANGSIR_PDF), "doc-002")
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "dofe-departures-saudi-arabia-monthly"]
    assert len(rows) == 1
    assert rows[0].value == 14330.0