"""Tests for the NRB NCPI Table 2(B) parser.

Runs against the real CSV checked into the repo at
``NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv``. No network access.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nrb_ncpi import PARSER_VERSION, parse

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "NRB Current" / "CMEFs_Table_Nine-Months_2082.83(2(B).csv"

EXPECTED_INDICATORS_PER_GEO = 26  # Overall + Food agg + 10 food + Non-food agg + 13 non-food
EXPECTED_GEOGRAPHIES = ("overall", "rural", "urban")
EXPECTED_TOTAL_ROWS = EXPECTED_INDICATORS_PER_GEO * len(EXPECTED_GEOGRAPHIES)
PERIOD_TOLERANCE = timedelta(days=2)


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert CSV_PATH.exists(), f"fixture missing: {CSV_PATH}"
    return parse(str(CSV_PATH), source_document_id="test-doc-id")


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", f"got status={result.status} errors={result.errors}"


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_total_row_count(result: ParserResult) -> None:
    assert len(result.staging_rows) == EXPECTED_TOTAL_ROWS


def test_geographies_balanced(result: ParserResult) -> None:
    per_geo: dict[str, int] = {g: 0 for g in EXPECTED_GEOGRAPHIES}
    for row in result.staging_rows:
        for geo in EXPECTED_GEOGRAPHIES:
            if row.indicator_slug_raw.endswith(f"-{geo}-yoy"):
                per_geo[geo] += 1
                break
    assert per_geo == {g: EXPECTED_INDICATORS_PER_GEO for g in EXPECTED_GEOGRAPHIES}


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw.startswith("ncpi-")
        assert row.indicator_slug_raw.endswith("-yoy")
        assert row.unit == "percent_yoy"
        assert row.reporting_period_type == "nine_months_cumulative"
        assert row.reporting_period_bs == "FY 2082/83 9M"
        assert row.fiscal_year_bs == "2082/83"
        assert row.fiscal_year_ad_label == "2025/26"
        assert row.confidence_grade_proposed == "A"
        assert isinstance(row.value, float)
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


def test_ad_span_brackets_nine_months(result: ParserResult) -> None:
    """Shrawan 2082 starts mid-July 2025; Chait 2082 ends mid-April 2026.

    Allow PERIOD_TOLERANCE either side because the parser uses naive
    mid-month placeholders that the TS validator refines.
    """
    expected_start = datetime(2025, 7, 15, tzinfo=UTC)
    expected_end = datetime(2026, 3, 15, tzinfo=UTC)
    for row in result.staging_rows:
        delta_start = abs(row.reporting_period_ad_start - expected_start)
        delta_end = abs(row.reporting_period_ad_end - expected_end)
        assert delta_start <= PERIOD_TOLERANCE, (
            f"start out of tolerance: {row.reporting_period_ad_start} vs {expected_start}"
        )
        assert delta_end <= PERIOD_TOLERANCE, (
            f"end out of tolerance: {row.reporting_period_ad_end} vs {expected_end}"
        )


def test_overall_index_yoy_matches_csv(result: ParserResult) -> None:
    """Spot-check: Overall Index overall-geo YoY column is 4.47% per the CSV
    row 13 (1.17 MoM / 4.47 YoY).
    """
    matches = [
        r for r in result.staging_rows if r.indicator_slug_raw == "ncpi-overall-index-overall-yoy"
    ]
    assert len(matches) == 1
    assert matches[0].value == pytest.approx(4.47, abs=1e-6)


def test_food_aggregate_rural_yoy(result: ParserResult) -> None:
    """Spot-check: A (Food and Beverages) rural YoY is 2.72%."""
    matches = [
        r
        for r in result.staging_rows
        if r.indicator_slug_raw == "ncpi-a-food-and-beverages-rural-yoy"
    ]
    assert len(matches) == 1
    assert matches[0].value == pytest.approx(2.72, abs=1e-6)


def test_transportation_urban_yoy(result: ParserResult) -> None:
    """Spot-check: B.7 Transportation urban YoY is 12.02%."""
    matches = [
        r
        for r in result.staging_rows
        if r.indicator_slug_raw == "ncpi-b-7-transportation-urban-yoy"
    ]
    assert len(matches) == 1
    assert matches[0].value == pytest.approx(12.02, abs=1e-6)


def test_idempotent() -> None:
    """Per docs/DATA_PIPELINE.md §"Parser Contract": running twice on the same
    input produces identical output.
    """
    first = parse(str(CSV_PATH), source_document_id="x")
    second = parse(str(CSV_PATH), source_document_id="x")
    assert first.status == second.status
    assert first.parser_version == second.parser_version
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-file.csv", source_document_id="x")
    assert res.status == "failure"
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_no_unexpected_errors(result: ParserResult) -> None:
    """Clean parse against the canonical fixture should not emit errors."""
    assert result.errors == [], f"unexpected parser errors: {result.errors}"
