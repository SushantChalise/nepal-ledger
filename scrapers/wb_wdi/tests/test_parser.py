"""Tests for scrapers/wb_wdi/parser.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wb_wdi.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    _CODE_TO_SLUG,
    parse,
)

# ---------------------------------------------------------------------------
# Synthesized snapshot — exercises all six indicator codes across several years
# ---------------------------------------------------------------------------

_SNAPSHOT: dict = {
    "schema_version": "1",
    "fetched_at": "2026-06-11",
    "country_code": "NPL",
    "indicators": {
        "NY.GDP.MKTP.KD.ZG": {
            "alias": "gdp_real_growth",
            "series": [
                {"year": 2019, "value": 6.7},
                {"year": 2020, "value": -2.4},
                {"year": 2021, "value": 4.2},
                {"year": 2022, "value": 5.6},
                {"year": 2023, "value": 3.9},
            ],
            "count": 5,
        },
        "FP.CPI.TOTL.ZG": {
            "alias": "cpi_inflation_avg",
            "series": [
                {"year": 2021, "value": 3.6},
                {"year": 2022, "value": 8.6},
                {"year": 2023, "value": 7.8},
            ],
            "count": 3,
        },
        "GC.BAL.CASH.GD.ZS": {
            "alias": "fiscal_balance_pct_gdp",
            "series": [
                {"year": 2022, "value": -3.8},
                {"year": 2023, "value": -2.5},
            ],
            "count": 2,
        },
        "BN.CAB.XOKA.GD.ZS": {
            "alias": "current_account_pct_gdp",
            "series": [
                {"year": 2022, "value": -11.2},
                {"year": 2023, "value": -0.3},
            ],
            "count": 2,
        },
        "GC.DOD.TOTL.GD.ZS": {
            "alias": "public_debt_pct_gdp",
            "series": [
                {"year": 2022, "value": 42.5},
                {"year": 2023, "value": 44.1},
            ],
            "count": 2,
        },
        "FI.RES.TOTL.MO": {
            "alias": "gross_reserves_months",
            "series": [
                {"year": 2022, "value": 9.0},
                {"year": 2023, "value": 13.1},
            ],
            "count": 2,
        },
    },
}

_DOC_ID = "test-doc-wdi-001"
# Total data points: 5 + 3 + 2 + 2 + 2 + 2 = 16
_TOTAL_POINTS = 16

FIXTURE_JSON = Path(__file__).parent / "fixtures" / "wb_wdi_sample.json"


@pytest.fixture
def snapshot_path(tmp_path: Path) -> Path:
    p = tmp_path / "wdi_snapshot.json"
    p.write_text(json.dumps(_SNAPSHOT), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Status and row count
# ---------------------------------------------------------------------------


def test_success_status_on_complete_snapshot(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    assert result.status == "success"
    assert result.errors == []


def test_row_count_matches_all_series_points(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    assert len(result.staging_rows) == _TOTAL_POINTS


def test_all_six_slugs_present(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    slugs = {r.indicator_slug_raw for r in result.staging_rows}
    expected = {slug for slug, _ in _CODE_TO_SLUG.values()}
    assert expected == slugs


# ---------------------------------------------------------------------------
# Calendar-year → Nepal FY mapping
# ---------------------------------------------------------------------------


def test_fy_mapping_cy2023_to_bs2080_81(snapshot_path: Path) -> None:
    """CY 2023 → FY 2080/81 (bs_start = 2023 + 57 = 2080)."""
    result = parse(str(snapshot_path), _DOC_ID)
    gdp_rows = [r for r in result.staging_rows if r.indicator_slug_raw == "wdi-gdp-real-growth"]
    row = next(r for r in gdp_rows if r.fiscal_year_bs == "2080/81")
    assert row.fiscal_year_ad_label == "2023/24"
    assert row.value == pytest.approx(3.9)


def test_fy_mapping_cy2020_to_bs2077_78(snapshot_path: Path) -> None:
    """CY 2020 → FY 2077/78 (bs_start = 2020 + 57 = 2077)."""
    result = parse(str(snapshot_path), _DOC_ID)
    gdp_rows = [r for r in result.staging_rows if r.indicator_slug_raw == "wdi-gdp-real-growth"]
    row = next(r for r in gdp_rows if r.fiscal_year_bs == "2077/78")
    assert row.fiscal_year_ad_label == "2020/21"
    assert row.value == pytest.approx(-2.4)


def test_period_start_is_mid_july(snapshot_path: Path) -> None:
    """period_start = mid_month_ad("Shrawan", bs_start) → 15 July of cal_year."""
    result = parse(str(snapshot_path), _DOC_ID)
    row = next(
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-gdp-real-growth" and r.fiscal_year_bs == "2080/81"
    )
    assert row.reporting_period_ad_start.month == 7
    assert row.reporting_period_ad_start.day == 15
    assert row.reporting_period_ad_start.year == 2023


def test_period_end_is_mid_june_following_year(snapshot_path: Path) -> None:
    """period_end = mid_month_ad("Ashadh", bs_start) → 15 June of cal_year+1."""
    result = parse(str(snapshot_path), _DOC_ID)
    row = next(
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-gdp-real-growth" and r.fiscal_year_bs == "2080/81"
    )
    # Ashadh 2080 → ad_month=6 < 7 → ad_year = 2080 - 56 = 2024
    assert row.reporting_period_ad_end.month == 6
    assert row.reporting_period_ad_end.year == 2024


# ---------------------------------------------------------------------------
# Values and units
# ---------------------------------------------------------------------------


def test_negative_values_preserved(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    ca_rows = [r for r in result.staging_rows if r.indicator_slug_raw == "wdi-current-account-pct-gdp"]
    assert any(r.value == pytest.approx(-11.2) for r in ca_rows)


def test_units_correct_for_all_slugs(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    slug_unit = {r.indicator_slug_raw: r.unit for r in result.staging_rows}
    assert slug_unit["wdi-gdp-real-growth"] == "percent"
    assert slug_unit["wdi-cpi-inflation-avg"] == "percent"
    assert slug_unit["wdi-fiscal-balance-pct-gdp"] == "percent_gdp"
    assert slug_unit["wdi-current-account-pct-gdp"] == "percent_gdp"
    assert slug_unit["wdi-public-debt-pct-gdp"] == "percent_gdp"
    assert slug_unit["wdi-gross-reserves-months"] == "months"


def test_confidence_grade_A_for_all_rows(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    assert all(r.confidence_grade_proposed == "A" for r in result.staging_rows)


def test_reporting_period_type_annual(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    assert all(r.reporting_period_type == "annual" for r in result.staging_rows)


# ---------------------------------------------------------------------------
# Publication date
# ---------------------------------------------------------------------------


def test_publication_date_from_fetched_at(snapshot_path: Path) -> None:
    """fetched_at "2026-06-11" → pub_date_ad = 2026-06-11T00:00:00Z."""
    result = parse(str(snapshot_path), _DOC_ID)
    row = result.staging_rows[0]
    assert row.publication_date_ad.year == 2026
    assert row.publication_date_ad.month == 6
    assert row.publication_date_ad.day == 11


# ---------------------------------------------------------------------------
# Parser notes
# ---------------------------------------------------------------------------


def test_parser_notes_include_calendar_year_and_code(snapshot_path: Path) -> None:
    result = parse(str(snapshot_path), _DOC_ID)
    row = next(
        r for r in result.staging_rows
        if r.indicator_slug_raw == "wdi-gdp-real-growth" and r.fiscal_year_bs == "2080/81"
    )
    assert "calendar year 2023" in (row.parser_notes or "")
    assert "NY.GDP.MKTP.KD.ZG" in (row.parser_notes or "")
    assert "2026-06-11" in (row.parser_notes or "")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_source_id_and_version() -> None:
    assert SOURCE_ID == "wb-wdi"
    assert PARSER_VERSION == "0.1.0"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_file_not_found_returns_failure() -> None:
    result = parse("/no/such/file.json", _DOC_ID)
    assert result.status == "failure"
    assert any(e.error_class == "Other" and "not found" in e.error_detail for e in result.errors)
    assert result.staging_rows == []


def test_invalid_json_returns_failure(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    result = parse(str(p), _DOC_ID)
    assert result.status == "failure"
    assert any(e.error_class == "Other" and "parse error" in e.error_detail for e in result.errors)


def test_wrong_schema_version_returns_failure(tmp_path: Path) -> None:
    bad = {**_SNAPSHOT, "schema_version": "99"}
    p = tmp_path / "bad_version.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    result = parse(str(p), _DOC_ID)
    assert result.status == "failure"
    assert any(
        e.error_class == "Other" and "schema_version" in e.error_detail
        for e in result.errors
    )


def test_missing_indicator_code_is_partial_with_column_missing(tmp_path: Path) -> None:
    """One missing code → status=partial, ColumnMissing error, remaining rows emitted."""
    partial = {
        **_SNAPSHOT,
        "indicators": {
            k: v for k, v in _SNAPSHOT["indicators"].items() if k != "FI.RES.TOTL.MO"
        },
    }
    p = tmp_path / "partial.json"
    p.write_text(json.dumps(partial), encoding="utf-8")
    result = parse(str(p), _DOC_ID)
    assert result.status == "partial"
    assert any(
        e.error_class == "ColumnMissing" and "FI.RES.TOTL.MO" in e.error_detail
        for e in result.errors
    )
    slugs = {r.indicator_slug_raw for r in result.staging_rows}
    assert "wdi-gross-reserves-months" not in slugs
    assert "wdi-gdp-real-growth" in slugs


def test_unknown_indicator_code_emits_other_warning(tmp_path: Path) -> None:
    extra = {
        **_SNAPSHOT,
        "indicators": {
            **_SNAPSHOT["indicators"],
            "XX.UNKNOWN.CODE": {
                "alias": "mystery",
                "series": [{"year": 2023, "value": 1.0}],
                "count": 1,
            },
        },
    }
    p = tmp_path / "extra_code.json"
    p.write_text(json.dumps(extra), encoding="utf-8")
    result = parse(str(p), _DOC_ID)
    assert any(
        e.error_class == "Other" and "XX.UNKNOWN.CODE" in e.error_detail
        for e in result.errors
    )


# ---------------------------------------------------------------------------
# Integration test — requires real snapshot from fetch.py
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not FIXTURE_JSON.exists(),
    reason=(
        "integration fixture absent — generate with: "
        "python -m scrapers.wb_wdi.fetch --output "
        "scrapers/wb_wdi/tests/fixtures/wb_wdi_sample.json"
    ),
)
def test_integration_real_snapshot() -> None:
    result = parse(str(FIXTURE_JSON), _DOC_ID)
    assert result.status in {"success", "partial"}
    assert len(result.staging_rows) >= 30, "expected at least 5 years × 6 indicators"
    slugs = {r.indicator_slug_raw for r in result.staging_rows}
    for slug, _ in _CODE_TO_SLUG.values():
        assert slug in slugs, f"missing slug from real snapshot: {slug}"
