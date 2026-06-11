"""Tests for nrb_db_external_sector parser v0.1.0.

Three fixture files are tested independently:
    MIgrant-Workers_.xlsx  → nrb-ext-migrant-departures-monthly
    Tourist-arrivals.xlsx  → nrb-ext-tourist-arrivals-monthly
    Balance-of-Payments-BPM6.xlsx → nrb-ext-bop-remittance-workers-monthly

Known reference values verified against the fixture:
    Migrant departures:
        2025-11 (Mangsir 2082 ~ Kartik 2082 per AD-month-11→Kartik):
            Total Worker's Outflow = 73094
    Tourist arrivals:
        2025 Oct = 128443
        2024 Jan = 79100
    BOP workers remittances (cumulative Credit, NPR million):
        FY 2025/26 Aug (first month) = 177411.58 (approx)
        FY 2025/26 Nov (4th month cumulative) = 687128.68 (approx)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from nrb_db_external_sector.parser import (
    PARSER_VERSION,
    SLUG_BOP_REMITTANCE,
    SLUG_MIGRANT_DEPARTURES,
    SLUG_TOURIST_ARRIVALS,
    parse,
)
from _common.types import ParserResult

# ── Fixture paths ──────────────────────────────────────────────────────────────

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MIGRANT_FIXTURE = FIXTURES / "MIgrant-Workers_.xlsx"
TOURIST_FIXTURE = FIXTURES / "Tourist-arrivals.xlsx"
BOP_FIXTURE = FIXTURES / "Balance-of-Payments-BPM6.xlsx"

TEST_ID = "test-source-doc-id"

# ── Migrant Worker tests ───────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def migrant_result() -> ParserResult:
    return parse(str(MIGRANT_FIXTURE), TEST_ID)


def test_migrant_parser_version(migrant_result: ParserResult) -> None:
    assert migrant_result.parser_version == PARSER_VERSION


def test_migrant_status_success(migrant_result: ParserResult) -> None:
    # ColumnMissing errors for remittance corridors are expected; should not
    # degrade status to partial/failure.
    assert migrant_result.status == "success"


def test_migrant_row_count(migrant_result: ParserResult) -> None:
    rows = [r for r in migrant_result.staging_rows if r.indicator_slug_raw == SLUG_MIGRANT_DEPARTURES]
    assert len(rows) >= 100, f"expected >= 100 migrant rows, got {len(rows)}"


def test_migrant_required_fields_populated(migrant_result: ParserResult) -> None:
    for row in migrant_result.staging_rows:
        assert row.indicator_slug_raw
        assert row.value >= 0
        assert row.unit == "count"
        assert row.reporting_period_type == "monthly"
        assert row.reporting_period_bs
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs
        assert row.fiscal_year_bs
        assert row.fiscal_year_ad_label
        assert row.confidence_grade_proposed in ("A", "B", "C")


def test_migrant_specific_value_nov2025(migrant_result: ParserResult) -> None:
    """2025-11 fixture row: Total Worker's Outflow = 73094."""
    # AD month=11 (Nov) → BS month Kartik, bs_year = 2025+57 = 2082
    matches = [
        r for r in migrant_result.staging_rows
        if r.indicator_slug_raw == SLUG_MIGRANT_DEPARTURES
        and "Kartik" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(matches) >= 1, "expected Kartik 2082 migrant row"
    assert matches[-1].value == pytest.approx(73094.0)


def test_migrant_specific_value_oct2025(migrant_result: ParserResult) -> None:
    """2025-10 fixture row: Total Worker's Outflow = 64634."""
    # AD month=10 (Oct) → BS month Ashwin, bs_year = 2082
    matches = [
        r for r in migrant_result.staging_rows
        if r.indicator_slug_raw == SLUG_MIGRANT_DEPARTURES
        and "Ashwin" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(matches) >= 1, "expected Ashwin 2082 migrant row"
    assert matches[-1].value == pytest.approx(64634.0)


def test_migrant_column_missing_errors_present(migrant_result: ParserResult) -> None:
    """ColumnMissing errors for remittance-india and remittance-gulf must be present."""
    cm_errors = [e for e in migrant_result.errors if e.error_class == "ColumnMissing"]
    slugs_mentioned = " ".join(e.error_detail for e in cm_errors)
    assert "nrb-ext-remittance-india-monthly" in slugs_mentioned
    assert "nrb-ext-remittance-gulf-monthly" in slugs_mentioned


def test_migrant_idempotent() -> None:
    result1 = parse(str(MIGRANT_FIXTURE), TEST_ID)
    result2 = parse(str(MIGRANT_FIXTURE), TEST_ID)
    assert len(result1.staging_rows) == len(result2.staging_rows)
    assert result1.status == result2.status


def test_missing_file_returns_failure() -> None:
    result = parse(str(FIXTURES / "nonexistent.xlsx"), TEST_ID)
    assert result.status == "failure"
    assert result.parser_version == PARSER_VERSION


# ── Tourist Arrival tests ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tourist_result() -> ParserResult:
    return parse(str(TOURIST_FIXTURE), TEST_ID)


def test_tourist_parser_version(tourist_result: ParserResult) -> None:
    assert tourist_result.parser_version == PARSER_VERSION


def test_tourist_status_success(tourist_result: ParserResult) -> None:
    assert tourist_result.status == "success"


def test_tourist_row_count(tourist_result: ParserResult) -> None:
    rows = [r for r in tourist_result.staging_rows if r.indicator_slug_raw == SLUG_TOURIST_ARRIVALS]
    # 1992–2025 ≈ 34 years × ~12 months each = 400+ rows
    assert len(rows) >= 200, f"expected >= 200 tourist rows, got {len(rows)}"


def test_tourist_required_fields_populated(tourist_result: ParserResult) -> None:
    for row in tourist_result.staging_rows:
        assert row.indicator_slug_raw == SLUG_TOURIST_ARRIVALS
        assert row.value >= 0
        assert row.unit == "count"
        assert row.reporting_period_type == "monthly"
        assert row.reporting_period_bs
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert row.fiscal_year_bs
        assert row.confidence_grade_proposed in ("A", "B", "C")


def test_tourist_specific_value_oct2025(tourist_result: ParserResult) -> None:
    """2025 Oct fixture value = 128443."""
    # AD Oct (month=10) → BS Ashwin, bs_year = 2025+57 = 2082
    matches = [
        r for r in tourist_result.staging_rows
        if r.indicator_slug_raw == SLUG_TOURIST_ARRIVALS
        and "Ashwin" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(matches) >= 1, "expected Ashwin 2082 tourist row"
    assert matches[-1].value == pytest.approx(128443.0)


def test_tourist_specific_value_jan2024(tourist_result: ParserResult) -> None:
    """2024 Jan fixture value = 79100."""
    # AD Jan (month=1) → BS Magh, bs_year = 2024 + 57 - 1 = 2080
    # Wait: 2024 Jan → ad_month=1 < 7 → bs_year = 2024 + 57 - 1 = 2080
    # Magh 2080: FY start = 2080 (pos 7 <= 9) → FY "2080/81"
    matches = [
        r for r in tourist_result.staging_rows
        if r.indicator_slug_raw == SLUG_TOURIST_ARRIVALS
        and "Magh" in r.reporting_period_bs
        and "2080" in r.reporting_period_bs
    ]
    assert len(matches) >= 1, "expected Magh 2080 tourist row (AD 2024 Jan)"
    # Find the one closest to 79100
    assert any(abs(r.value - 79100.0) < 1.0 for r in matches), (
        f"expected value 79100 in Magh 2080 rows, got {[r.value for r in matches]}"
    )


def test_tourist_idempotent() -> None:
    result1 = parse(str(TOURIST_FIXTURE), TEST_ID)
    result2 = parse(str(TOURIST_FIXTURE), TEST_ID)
    assert len(result1.staging_rows) == len(result2.staging_rows)


# ── BOP Workers Remittance tests ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def bop_result() -> ParserResult:
    return parse(str(BOP_FIXTURE), TEST_ID)


def test_bop_parser_version(bop_result: ParserResult) -> None:
    assert bop_result.parser_version == PARSER_VERSION


def test_bop_status_success(bop_result: ParserResult) -> None:
    assert bop_result.status == "success"


def test_bop_row_count(bop_result: ParserResult) -> None:
    rows = [r for r in bop_result.staging_rows if r.indicator_slug_raw == SLUG_BOP_REMITTANCE]
    # 4 FYs × up to 12 months = up to 48 rows
    assert len(rows) >= 20, f"expected >= 20 BOP remittance rows, got {len(rows)}"


def test_bop_required_fields_populated(bop_result: ParserResult) -> None:
    for row in bop_result.staging_rows:
        assert row.indicator_slug_raw == SLUG_BOP_REMITTANCE
        assert row.value > 0
        assert row.unit == "npr_million"
        assert row.reporting_period_type == "year_to_date"
        assert row.reporting_period_bs
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert row.fiscal_year_bs
        assert row.confidence_grade_proposed in ("A", "B", "C")


def test_bop_fy2025_aug_value(bop_result: ParserResult) -> None:
    """FY 2025/26P Aug (first month) workers remittances Credit ≈ 177411.58."""
    # FY AD start = 2025, Aug → Shrawan, bs_year = 2025+57 = 2082
    # FY BS start = 2082, FY label = "2082/83"
    matches = [
        r for r in bop_result.staging_rows
        if r.indicator_slug_raw == SLUG_BOP_REMITTANCE
        and "Shrawan" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(matches) >= 1, "expected Shrawan 2082 BOP row"
    assert matches[-1].value == pytest.approx(177411.58, abs=1.0)


def test_bop_fy2025_nov_value(bop_result: ParserResult) -> None:
    """FY 2025/26P Nov (4th month cumulative) workers remittances Credit ≈ 687128.68."""
    # AD Nov → Kartik, bs_year = 2025+57 = 2082
    matches = [
        r for r in bop_result.staging_rows
        if r.indicator_slug_raw == SLUG_BOP_REMITTANCE
        and "Kartik" in r.reporting_period_bs
        and "2082" in r.reporting_period_bs
    ]
    assert len(matches) >= 1, "expected Kartik 2082 BOP row"
    assert matches[-1].value == pytest.approx(687128.68, abs=1.0)


def test_bop_idempotent() -> None:
    result1 = parse(str(BOP_FIXTURE), TEST_ID)
    result2 = parse(str(BOP_FIXTURE), TEST_ID)
    assert len(result1.staging_rows) == len(result2.staging_rows)
    assert result1.status == result2.status
