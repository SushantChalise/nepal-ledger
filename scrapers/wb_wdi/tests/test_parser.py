"""Tests for the WB WDI Nepal parser.

All tests run against the saved fixture at
``scrapers/wb_wdi/tests/fixtures/wdi_npl_2024.json``.  No network access.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from wb_wdi import PARSER_VERSION, parse

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "wdi_npl_2024.json"

# 15 codes × 3 years each, minus nulls:
# SI.POV.NAHC: 2 nulls (2021, 2023) → 1 non-null
# SI.POV.GINI: 2 nulls (2021, 2023) → 1 non-null
# GC.DOD.TOTL.GD.ZS: 1 null (2023) → 2 non-null
# All other 12 codes: 3 non-null each
# Total = 12×3 + 1 + 1 + 2 = 36 + 4 = 40
EXPECTED_TOTAL_ROWS = 40

PERIOD_TOLERANCE = timedelta(days=2)


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE_PATH.exists(), f"fixture missing: {FIXTURE_PATH}"
    return parse(str(FIXTURE_PATH), source_document_id="test-doc-id")


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", f"status={result.status} errors={result.errors}"


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_no_errors_on_clean_fixture(result: ParserResult) -> None:
    assert result.errors == [], f"unexpected parser errors: {result.errors}"


def test_total_row_count(result: ParserResult) -> None:
    assert len(result.staging_rows) == EXPECTED_TOTAL_ROWS


def test_all_rows_are_annual(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.reporting_period_type == "annual", f"non-annual row: {row.indicator_slug_raw}"


def test_all_rows_are_confidence_A(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.confidence_grade_proposed == "A"


def test_all_rows_have_wdi_prefix(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.indicator_slug_raw.startswith("wdi-"), row.indicator_slug_raw


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw
        assert isinstance(row.value, float)
        assert row.unit
        assert row.reporting_period_bs
        assert row.fiscal_year_bs == row.reporting_period_bs
        assert row.fiscal_year_ad_label
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


def test_period_mapping_wb2023(result: ParserResult) -> None:
    """WB year 2023 → BS FY 2080/81 → AD Jul 15 2023 – Jul 15 2024."""
    rows_2023 = [r for r in result.staging_rows if r.fiscal_year_bs == "2080/81"]
    assert len(rows_2023) > 0, "no rows for WB year 2023 (BS 2080/81)"
    for row in rows_2023:
        assert row.fiscal_year_ad_label == "2023/24"
        delta_start = abs(row.reporting_period_ad_start - datetime(2023, 7, 15, tzinfo=UTC))
        delta_end = abs(row.reporting_period_ad_end - datetime(2024, 7, 15, tzinfo=UTC))
        assert delta_start <= PERIOD_TOLERANCE, f"start out of tolerance: {row.reporting_period_ad_start}"
        assert delta_end <= PERIOD_TOLERANCE, f"end out of tolerance: {row.reporting_period_ad_end}"


def test_period_mapping_wb2022(result: ParserResult) -> None:
    """WB year 2022 → BS FY 2079/80 → AD Jul 15 2022 – Jul 15 2023."""
    rows_2022 = [r for r in result.staging_rows if r.fiscal_year_bs == "2079/80"]
    assert len(rows_2022) > 0
    for row in rows_2022:
        assert row.fiscal_year_ad_label == "2022/23"
        delta_start = abs(row.reporting_period_ad_start - datetime(2022, 7, 15, tzinfo=UTC))
        delta_end = abs(row.reporting_period_ad_end - datetime(2023, 7, 15, tzinfo=UTC))
        assert delta_start <= PERIOD_TOLERANCE
        assert delta_end <= PERIOD_TOLERANCE


def test_gdp_current_usd_value_and_unit(result: ParserResult) -> None:
    """NY.GDP.MKTP.CD 2023: raw 40835000000 ÷ 1e6 = 40835.0 usd_million."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-gdp-current-usd" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "usd_million"
    assert abs(rows[0].value - 40835.0) < 1.0


def test_gdp_growth_value_and_unit(result: ParserResult) -> None:
    """NY.GDP.MKTP.KD.ZG 2023: 3.86 percent (no scaling)."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-gdp-growth-annual-pct" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "percent"
    assert abs(rows[0].value - 3.86) < 1e-6


def test_gdp_per_capita_unit_is_usd(result: ParserResult) -> None:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "wdi-gdp-per-capita-current-usd"]
    assert all(r.unit == "usd" for r in rows)


def test_gini_unit_is_index_points(result: ParserResult) -> None:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "wdi-gini-index"]
    assert len(rows) == 1, "only 1 non-null Gini in fixture (2022)"
    assert rows[0].unit == "index_points"
    assert abs(rows[0].value - 32.8) < 1e-6


def test_null_values_skipped(result: ParserResult) -> None:
    """SI.POV.NAHC has null for 2021 and 2023; only 2022 should appear."""
    poverty_rows = [r for r in result.staging_rows if r.indicator_slug_raw == "wdi-poverty-headcount-national-pct"]
    assert len(poverty_rows) == 1
    assert poverty_rows[0].fiscal_year_bs == "2079/80"  # WB 2022 → BS 2079/80
    assert abs(poverty_rows[0].value - 20.27) < 1e-6


def test_remittances_usd_scaling(result: ParserResult) -> None:
    """BX.TRF.PWKR.CD.DT 2023: raw 9340000000 ÷ 1e6 = 9340.0 usd_million."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-remittances-received-usd" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "usd_million"
    assert abs(rows[0].value - 9340.0) < 1.0


def test_current_account_negative_value(result: ParserResult) -> None:
    """BN.CAB.XOKA.GD.ZS 2023: -1.4 percent (negative values must round-trip)."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-current-account-balance-pct-gdp" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert abs(rows[0].value - (-1.4)) < 1e-6


def test_publication_date_from_fetched_at(result: ParserResult) -> None:
    """publication_date_ad comes from the fixture's fetched_at."""
    expected = datetime(2024, 12, 27, tzinfo=UTC)
    for row in result.staging_rows:
        assert abs((row.publication_date_ad - expected).total_seconds()) < 1.0


def test_idempotent() -> None:
    """Running twice on the same input produces identical output."""
    first = parse(str(FIXTURE_PATH), source_document_id="x")
    second = parse(str(FIXTURE_PATH), source_document_id="x")
    assert first.status == second.status
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-file.json", source_document_id="x")
    assert res.status == "failure"
    assert res.errors


def test_invalid_json_returns_failure() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"
    assert any(e.error_class == "EncodingError" for e in res.errors)


def test_unknown_indicator_code_is_error() -> None:
    """An unrecognised code emits an error but known codes still parse."""
    fixture = json.loads(FIXTURE_PATH.read_text())
    fixture["indicators"]["XX.UNKNOWN.ZZ"] = [{"date": "2023", "value": 1.0}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fixture, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "partial"
    assert any("XX.UNKNOWN.ZZ" in e.error_detail for e in res.errors)
    assert len(res.staging_rows) == EXPECTED_TOTAL_ROWS  # known codes unaffected


def test_empty_indicators_returns_failure() -> None:
    doc = {"fetched_at": "2024-12-27T00:00:00Z", "country_code": "NPL", "indicators": {}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"


def test_all_15_indicator_slugs_present(result: ParserResult) -> None:
    """Every configured indicator must appear at least once in the output."""
    expected_slugs = {
        "wdi-gdp-current-usd",
        "wdi-gdp-constant-2015-usd",
        "wdi-gdp-growth-annual-pct",
        "wdi-gdp-per-capita-current-usd",
        "wdi-gdp-per-capita-growth-pct",
        "wdi-cpi-inflation-annual-pct",
        "wdi-remittances-received-usd",
        "wdi-remittances-pct-gdp",
        "wdi-gni-current-usd",
        "wdi-gni-per-capita-current-usd",
        "wdi-poverty-headcount-national-pct",
        "wdi-gini-index",
        "wdi-gross-capital-formation-pct-gdp",
        "wdi-central-govt-debt-pct-gdp",
        "wdi-current-account-balance-pct-gdp",
    }
    found_slugs = {r.indicator_slug_raw for r in result.staging_rows}
    assert expected_slugs == found_slugs, f"missing: {expected_slugs - found_slugs}"
