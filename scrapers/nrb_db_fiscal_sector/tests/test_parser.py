"""Tests for nrb_db_fiscal_sector.parser — deterministic XLSX parser.

Fixtures are real NRB files committed at:
  scrapers/nrb_db_fiscal_sector/tests/fixtures/

Each of the 4 XLSX files is tested independently; the top-level parse()
function is called once per file.  Tests verify:
  - parser_version constant
  - status == "success" (for well-formed fixtures)
  - staging_row count >= expected minimum
  - all required StagingRowDraft fields are non-None
  - known specific values from the most recent data period
  - missing file → failure (no crash)
  - idempotency (same result on second call)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nrb_db_fiscal_sector.parser import PARSER_VERSION, SOURCE_ID, parse

FIXTURES = Path(__file__).resolve().parent / "fixtures"

REVENUE_FIXTURE = FIXTURES / "Government-revenue-1.xlsx"
EXPENDITURE_FIXTURE = FIXTURES / "Government-budgetary-operation.xlsx"
DOMESTIC_DEBT_FIXTURE = FIXTURES / "Outstanding-government-debt-1.xlsx"
FOREIGN_DEBT_FIXTURE = FIXTURES / "Loan-and-debt-servicing-1.xlsx"

TARGET_SLUGS = [
    "nrb-fiscal-revenue-cumulative-ytd",
    "nrb-fiscal-expenditure-cumulative-ytd",
    "nrb-fiscal-debt-domestic-outstanding",
    "nrb-fiscal-debt-external-outstanding",
]


# ── Module-scoped fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def revenue_result():
    return parse(str(REVENUE_FIXTURE), "test-revenue-id")


@pytest.fixture(scope="module")
def expenditure_result():
    return parse(str(EXPENDITURE_FIXTURE), "test-expenditure-id")


@pytest.fixture(scope="module")
def domestic_debt_result():
    return parse(str(DOMESTIC_DEBT_FIXTURE), "test-domestic-debt-id")


@pytest.fixture(scope="module")
def foreign_debt_result():
    return parse(str(FOREIGN_DEBT_FIXTURE), "test-foreign-debt-id")


# ── Parser version + source ID ────────────────────────────────────────────────

def test_parser_version():
    assert PARSER_VERSION == "0.1.0"


def test_source_id():
    assert SOURCE_ID == "nrb-db-fiscal-sector"


# ── Revenue ───────────────────────────────────────────────────────────────────

class TestRevenue:
    def test_status_success(self, revenue_result):
        assert revenue_result.status == "success", (
            f"errors: {[e.error_detail for e in revenue_result.errors]}"
        )

    def test_parser_version(self, revenue_result):
        assert revenue_result.parser_version == "0.1.0"

    def test_row_count(self, revenue_result):
        # FY 2024-25 has up to 12 month columns; fixture ends at May (11 months)
        assert len(revenue_result.staging_rows) >= 10

    def test_slug(self, revenue_result):
        slugs = {r.indicator_slug_raw for r in revenue_result.staging_rows}
        assert "nrb-fiscal-revenue-cumulative-ytd" in slugs

    def test_required_fields_populated(self, revenue_result):
        for row in revenue_result.staging_rows:
            assert row.indicator_slug_raw
            assert row.value is not None
            assert row.unit
            assert row.reporting_period_type
            assert row.reporting_period_bs
            assert row.reporting_period_ad_start
            assert row.reporting_period_ad_end
            assert row.publication_date_ad
            assert row.publication_date_bs
            assert row.fiscal_year_bs
            assert row.fiscal_year_ad_label
            assert row.confidence_grade_proposed

    def test_unit_is_npr_million(self, revenue_result):
        for row in revenue_result.staging_rows:
            assert row.unit == "npr_million"

    def test_reporting_period_type(self, revenue_result):
        for row in revenue_result.staging_rows:
            assert row.reporting_period_type == "year_to_date"

    def test_known_value_aug(self, revenue_result):
        # Aug (Bhadra) 2024/25 Total Revenue = 94742.97607648998
        aug_rows = [
            r for r in revenue_result.staging_rows
            if "Bhadra" in r.reporting_period_bs
        ]
        assert len(aug_rows) >= 1
        assert abs(aug_rows[0].value - 94742.976) < 0.01

    def test_known_value_may(self, revenue_result):
        # May (Jestha) 2024/25 Total Revenue = 922431.97...
        may_rows = [
            r for r in revenue_result.staging_rows
            if "Jestha" in r.reporting_period_bs
        ]
        assert len(may_rows) >= 1
        assert abs(may_rows[0].value - 922431.97) < 0.01

    def test_confidence_grade(self, revenue_result):
        for row in revenue_result.staging_rows:
            assert row.confidence_grade_proposed == "B"

    def test_fiscal_year_label(self, revenue_result):
        # Sheet "Rev Col 2024-25" → AD 2024/25 → BS 2081/82
        for row in revenue_result.staging_rows:
            assert row.fiscal_year_bs == "2081/82"
            assert row.fiscal_year_ad_label == "2024/25"

    def test_idempotent(self):
        r1 = parse(str(REVENUE_FIXTURE), "test-id")
        r2 = parse(str(REVENUE_FIXTURE), "test-id")
        assert r1.status == r2.status
        assert len(r1.staging_rows) == len(r2.staging_rows)
        for a, b in zip(r1.staging_rows, r2.staging_rows):
            assert a.value == b.value
            assert a.reporting_period_bs == b.reporting_period_bs


# ── Expenditure ───────────────────────────────────────────────────────────────

class TestExpenditure:
    def test_status_success(self, expenditure_result):
        assert expenditure_result.status == "success", (
            f"errors: {[e.error_detail for e in expenditure_result.errors]}"
        )

    def test_row_count(self, expenditure_result):
        assert len(expenditure_result.staging_rows) >= 10

    def test_slug(self, expenditure_result):
        slugs = {r.indicator_slug_raw for r in expenditure_result.staging_rows}
        assert "nrb-fiscal-expenditure-cumulative-ytd" in slugs

    def test_required_fields_populated(self, expenditure_result):
        for row in expenditure_result.staging_rows:
            assert row.indicator_slug_raw
            assert row.value is not None
            assert row.unit == "npr_million"
            assert row.reporting_period_type == "year_to_date"
            assert row.reporting_period_bs
            assert row.reporting_period_ad_start
            assert row.reporting_period_ad_end
            assert row.fiscal_year_bs

    def test_known_value_aug(self, expenditure_result):
        # Aug (Bhadra) 2024/25 Total Expenditure = 37874.7
        aug_rows = [
            r for r in expenditure_result.staging_rows
            if "Bhadra" in r.reporting_period_bs
        ]
        assert len(aug_rows) >= 1
        assert abs(aug_rows[0].value - 37874.7) < 0.01

    def test_known_value_may(self, expenditure_result):
        # May (Jestha) Total Expenditure = 1133951.6
        may_rows = [
            r for r in expenditure_result.staging_rows
            if "Jestha" in r.reporting_period_bs
        ]
        assert len(may_rows) >= 1
        assert abs(may_rows[0].value - 1133951.6) < 0.01

    def test_fiscal_year_label(self, expenditure_result):
        # Sheet "GBO 2024-25" → AD 2024/25 → BS 2081/82
        for row in expenditure_result.staging_rows:
            assert row.fiscal_year_bs == "2081/82"


# ── Domestic Debt ─────────────────────────────────────────────────────────────

class TestDomesticDebt:
    def test_status_success(self, domestic_debt_result):
        assert domestic_debt_result.status == "success", (
            f"errors: {[e.error_detail for e in domestic_debt_result.errors]}"
        )

    def test_row_count(self, domestic_debt_result):
        assert len(domestic_debt_result.staging_rows) >= 10

    def test_slug(self, domestic_debt_result):
        slugs = {r.indicator_slug_raw for r in domestic_debt_result.staging_rows}
        assert "nrb-fiscal-debt-domestic-outstanding" in slugs

    def test_required_fields_populated(self, domestic_debt_result):
        for row in domestic_debt_result.staging_rows:
            assert row.indicator_slug_raw
            assert row.value is not None
            assert row.unit == "npr_million"
            assert row.reporting_period_bs
            assert row.fiscal_year_bs

    def test_known_value_aug(self, domestic_debt_result):
        # Aug (Bhadra) 2024/25 Total Domestic Debt = 1199986.4
        aug_rows = [
            r for r in domestic_debt_result.staging_rows
            if "Bhadra" in r.reporting_period_bs
        ]
        assert len(aug_rows) >= 1
        assert abs(aug_rows[0].value - 1199986.4) < 0.1

    def test_known_value_may(self, domestic_debt_result):
        # May (Jestha) 2024/25 Total Domestic Debt = 1262789.1
        may_rows = [
            r for r in domestic_debt_result.staging_rows
            if "Jestha" in r.reporting_period_bs
        ]
        assert len(may_rows) >= 1
        assert abs(may_rows[0].value - 1262789.1) < 0.1

    def test_fiscal_year_label(self, domestic_debt_result):
        # Sheet "ODD 2024-25" → AD 2024/25 → BS 2081/82
        for row in domestic_debt_result.staging_rows:
            assert row.fiscal_year_bs == "2081/82"


# ── Foreign Debt (annual) ─────────────────────────────────────────────────────

class TestForeignDebt:
    def test_status_success(self, foreign_debt_result):
        assert foreign_debt_result.status == "success", (
            f"errors: {[e.error_detail for e in foreign_debt_result.errors]}"
        )

    def test_row_count(self, foreign_debt_result):
        # File covers FY 2010/11–2022/23 (up to 13 years)
        assert len(foreign_debt_result.staging_rows) >= 10

    def test_slug(self, foreign_debt_result):
        slugs = {r.indicator_slug_raw for r in foreign_debt_result.staging_rows}
        assert "nrb-fiscal-debt-external-outstanding" in slugs

    def test_required_fields_populated(self, foreign_debt_result):
        for row in foreign_debt_result.staging_rows:
            assert row.indicator_slug_raw
            assert row.value is not None
            assert row.unit == "npr_million"
            assert row.reporting_period_type == "annual"
            assert row.reporting_period_bs
            assert row.reporting_period_ad_start
            assert row.reporting_period_ad_end
            assert row.fiscal_year_bs

    def test_unit_conversion_fy2021_22(self, foreign_debt_result):
        # FY 2021/22 Net Outstanding Foreign Debt = 102584.71 × 10 = 1025847.1 NPR million
        # Source value 102584.71 in Rs. in 10 million
        fy2021_rows = [
            r for r in foreign_debt_result.staging_rows
            if r.fiscal_year_bs == "2078/79"  # AD 2021/22 → BS 2078/79
        ]
        assert len(fy2021_rows) >= 1
        assert abs(fy2021_rows[0].value - 1025847.1) < 1.0

    def test_known_value_fy2012_13(self, foreign_debt_result):
        # FY 2012/13 Net Outstanding = 33344.15 Rs. in 10 million → 333441.5 NPR million
        fy_rows = [
            r for r in foreign_debt_result.staging_rows
            if r.fiscal_year_bs == "2069/70"
        ]
        assert len(fy_rows) >= 1
        assert abs(fy_rows[0].value - 333441.5) < 1.0

    def test_reporting_period_type_annual(self, foreign_debt_result):
        for row in foreign_debt_result.staging_rows:
            assert row.reporting_period_type == "annual"

    def test_confidence_grade(self, foreign_debt_result):
        for row in foreign_debt_result.staging_rows:
            assert row.confidence_grade_proposed == "B"


# ── Missing file → failure ────────────────────────────────────────────────────

def test_missing_revenue_file_returns_failure():
    result = parse(str(FIXTURES / "nonexistent-government-revenue.xlsx"), "test-id")
    assert result.status == "failure"
    assert len(result.errors) >= 1


def test_missing_expenditure_file_returns_failure():
    result = parse(str(FIXTURES / "nonexistent-government-budgetary.xlsx"), "test-id")
    assert result.status == "failure"
    assert len(result.errors) >= 1


def test_unknown_filename_returns_failure(tmp_path):
    # Copy a fixture with an unrecognised filename; the parser should
    # detect the file type as None and return failure.
    import shutil

    unknown = tmp_path / "unknown-fiscal-data.xlsx"
    shutil.copy(str(REVENUE_FIXTURE), str(unknown))
    result = parse(str(unknown), "test-id")
    assert result.status == "failure"
    assert len(result.errors) >= 1
    # The error should mention inability to detect file type
    assert any(
        "detect file type" in e.error_detail or "file type" in e.error_detail
        for e in result.errors
    )


# ── Idempotency ────────────────────────────────────────────────────────────────

def test_expenditure_idempotent():
    r1 = parse(str(EXPENDITURE_FIXTURE), "test-id")
    r2 = parse(str(EXPENDITURE_FIXTURE), "test-id")
    assert r1.status == r2.status
    assert len(r1.staging_rows) == len(r2.staging_rows)


def test_foreign_debt_idempotent():
    r1 = parse(str(FOREIGN_DEBT_FIXTURE), "test-id")
    r2 = parse(str(FOREIGN_DEBT_FIXTURE), "test-id")
    assert r1.status == r2.status
    assert len(r1.staging_rows) == len(r2.staging_rows)


# ── to_json_dict serialisation ────────────────────────────────────────────────

def test_staging_rows_serialisable(revenue_result):
    import json
    for row in revenue_result.staging_rows:
        d = row.to_json_dict()
        json.dumps(d)  # must not raise
        assert isinstance(d["reporting_period_ad_start"], str)
        assert "T" in d["reporting_period_ad_start"]  # ISO 8601


def test_foreign_debt_serialisable(foreign_debt_result):
    import json
    for row in foreign_debt_result.staging_rows:
        d = row.to_json_dict()
        json.dumps(d)
