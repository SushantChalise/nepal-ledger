"""Tests for the ADB ADO Nepal Selected Economic Indicators parser.

Core extraction logic is tested with synthesized tables (no PDF required).
Two fixture tables exercise:
  1. Nepal FY notation ("2022/23", "2023/24e", "2024/25f")
  2. Calendar-year notation ("2022", "2023", "2024e", "2025f")

Full-PDF integration tests are skipped unless a fixture PDF is placed at
``tests/fixtures/adb_ado_nepal_sample.pdf``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from adb_ado import PARSER_VERSION, parse
from adb_ado.parser import (
    SOURCE_ID,
    _classify_row,
    _parse_value,
    _parse_year_columns,
    extract_rows_from_table,
)

FIXTURE_PDF = Path(__file__).resolve().parent / "fixtures" / "adb_ado_nepal_sample.pdf"
PERIOD_TOLERANCE = timedelta(days=40)

_PUB_DATE_AD = datetime(2024, 4, 1, tzinfo=UTC)
_PUB_DATE_BS = "2080 Chait 19"
_CONTEXT = "ADB ADO 2024"

# ── Fixture 1: Nepal FY notation ───────────────────────────────────────────────
_FY_HDR = ["", "2021/22", "2022/23", "2023/24e", "2024/25f", "2025/26f"]
_FY_DATA: list[list[str]] = [
    ["GDP growth (%)", "5.8", "1.9", "4.0", "5.5", "5.5"],
    ["Inflation (% change)", "7.7", "7.8", "5.0", "5.5", "5.0"],
    ["Fiscal balance (% of GDP)", "-7.0", "-5.0", "-4.0", "-3.5", "-3.0"],
    ["Current account balance (% of GDP)", "-0.2", "-0.8", "-1.5", "-1.5", "-1.5"],
    ["Gross official reserves (months of imports)", "11.5", "13.5", "12.5", "13.0", "13.0"],
]

# ── Fixture 2: Calendar-year notation ─────────────────────────────────────────
_CAL_HDR = ["", "2022", "2023", "2024e", "2025f"]
_CAL_DATA: list[list[str]] = [
    ["GDP growth", "5.8", "1.9", "4.0", "5.5"],
    ["Inflation", "7.7", "7.8", "5.0", "5.5"],
    ["Fiscal balance (% of GDP)", "-7.0", "-5.0", "-4.0", "-3.5"],
    ["Current account (% of GDP)", "-0.2", "-0.8", "-1.5", "-1.5"],
    ["Reserves (months)", "11.5", "13.5", "12.5", "13.0"],
]

_ACTUAL_PREFIXES = frozenset(
    {
        "adb-ado-gdp-real-growth",
        "adb-ado-cpi-inflation-avg",
        "adb-ado-fiscal-balance-pct-gdp",
        "adb-ado-current-account-pct-gdp",
        "adb-ado-gross-reserves-months",
    }
)
_ACTUAL_SLUGS = frozenset(f"{p}-actual" for p in _ACTUAL_PREFIXES)
_FORECAST_SLUGS = frozenset(f"{p}-forecast" for p in _ACTUAL_PREFIXES)


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def fy_result() -> list[StagingRowDraft]:
    rows, errors = extract_rows_from_table(_FY_HDR, _FY_DATA, _CONTEXT, _PUB_DATE_AD, _PUB_DATE_BS)
    assert errors == [], f"unexpected errors: {errors}"
    return rows


@pytest.fixture(scope="module")
def cal_result() -> list[StagingRowDraft]:
    rows, errors = extract_rows_from_table(
        _CAL_HDR, _CAL_DATA, _CONTEXT, _PUB_DATE_AD, _PUB_DATE_BS
    )
    assert errors == [], f"unexpected errors: {errors}"
    return rows


# ── Column parser ──────────────────────────────────────────────────────────────


def test_parse_fy_year_columns() -> None:
    cols = _parse_year_columns(_FY_HDR)
    assert len(cols) == 5
    actuals = [c for c in cols if not c.is_forecast]
    forecasts = [c for c in cols if c.is_forecast]
    assert len(actuals) == 2  # 2021/22, 2022/23
    assert len(forecasts) == 3  # 2023/24e, 2024/25f, 2025/26f


def test_parse_calendar_year_columns() -> None:
    cols = _parse_year_columns(_CAL_HDR)
    assert len(cols) == 4
    actuals = [c for c in cols if not c.is_forecast]
    forecasts = [c for c in cols if c.is_forecast]
    assert len(actuals) == 2  # 2022, 2023
    assert len(forecasts) == 2  # 2024e, 2025f


# ── Row classifier ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("label", "expected_kind"),
    [
        ("GDP growth (%)", "gdp_real_growth"),
        ("GDP growth", "gdp_real_growth"),
        ("Inflation (% change)", "cpi_inflation_avg"),
        ("Inflation", "cpi_inflation_avg"),
        ("CPI inflation, annual average", "cpi_inflation_avg"),
        ("Fiscal balance (% of GDP)", "fiscal_balance"),
        ("Overall government balance (% of GDP)", "fiscal_balance"),
        ("Current account balance (% of GDP)", "current_account"),
        ("Current account (% of GDP)", "current_account"),
        ("Gross official reserves (months of imports)", "gross_reserves_months"),
        ("Reserves (months)", "gross_reserves_months"),
        ("GDP at current prices (NPR billion)", None),
        ("Total revenue (% of GDP)", None),
    ],
)
def test_classify_row(label: str, expected_kind: str | None) -> None:
    assert _classify_row(label) == expected_kind


# ── Value parser ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5.5", 5.5),
        ("-4.0", -4.0),
        ("(4.0)", -4.0),
        ("", None),
        ("...", None),
    ],
)
def test_parse_value(raw: str, expected: float | None) -> None:
    result = _parse_value(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected, abs=1e-6)


# ── FY-notation table extraction ───────────────────────────────────────────────


def test_fy_row_count(fy_result: list[StagingRowDraft]) -> None:
    # 5 kinds × (2 actual cols + 3 forecast cols) = 25
    assert len(fy_result) == 25


def test_fy_actual_slugs(fy_result: list[StagingRowDraft]) -> None:
    slugs = {r.indicator_slug_raw for r in fy_result}
    assert _ACTUAL_SLUGS.issubset(slugs)


def test_fy_forecast_slugs(fy_result: list[StagingRowDraft]) -> None:
    slugs = {r.indicator_slug_raw for r in fy_result}
    assert _FORECAST_SLUGS.issubset(slugs)


def test_fy_units(fy_result: list[StagingRowDraft]) -> None:
    by_slug = {r.indicator_slug_raw: r.unit for r in fy_result}
    assert by_slug["adb-ado-gdp-real-growth-actual"] == "percent"
    assert by_slug["adb-ado-cpi-inflation-avg-actual"] == "percent"
    assert by_slug["adb-ado-fiscal-balance-pct-gdp-actual"] == "percent_gdp"
    assert by_slug["adb-ado-current-account-pct-gdp-actual"] == "percent_gdp"
    assert by_slug["adb-ado-gross-reserves-months-actual"] == "months"


def test_fy_period_bs_2022_23(fy_result: list[StagingRowDraft]) -> None:
    """2022/23 AD → BS 2079/80. period type = annual."""
    rows = [r for r in fy_result if r.fiscal_year_bs == "2079/80"]
    assert rows
    for row in rows:
        assert row.reporting_period_type == "annual"
        assert row.fiscal_year_ad_label == "2022/23"


def test_fy_negative_fiscal_preserved(fy_result: list[StagingRowDraft]) -> None:
    fiscal = [r for r in fy_result if "fiscal" in r.indicator_slug_raw]
    assert all(r.value < 0 for r in fiscal)


def test_fy_confidence_a(fy_result: list[StagingRowDraft]) -> None:
    for row in fy_result:
        assert row.confidence_grade_proposed == "A"


# ── Calendar-year table extraction ────────────────────────────────────────────


def test_cal_row_count(cal_result: list[StagingRowDraft]) -> None:
    # 5 kinds × (2 actual cols + 2 forecast cols) = 20
    assert len(cal_result) == 20


def test_cal_actual_slugs(cal_result: list[StagingRowDraft]) -> None:
    slugs = {r.indicator_slug_raw for r in cal_result}
    assert _ACTUAL_SLUGS.issubset(slugs)


def test_cal_period_bs_2023(cal_result: list[StagingRowDraft]) -> None:
    """Calendar 2023 → ad_lead_year 2023 → BS 2080/80."""
    rows = [r for r in cal_result if r.fiscal_year_bs == "2080/81"]
    assert rows
    for row in rows:
        assert row.fiscal_year_ad_label == "2023/24"


# ── Source constants ───────────────────────────────────────────────────────────


def test_source_id() -> None:
    assert SOURCE_ID == "adb-ado-nepal"


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


# ── Missing-file guard ─────────────────────────────────────────────────────────


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-adb.pdf", "test-id")
    assert res.status == "failure"
    assert res.errors


# ── Integration test (requires real PDF) ──────────────────────────────────────


@pytest.mark.skipif(not FIXTURE_PDF.exists(), reason="fixture PDF not present")
def test_integration_against_real_pdf() -> None:
    res = parse(str(FIXTURE_PDF), "test-doc-id")
    assert res.status in ("success", "partial")
    assert len(res.staging_rows) > 0
    slugs = {r.indicator_slug_raw for r in res.staging_rows}
    assert "adb-ado-gdp-real-growth-actual" in slugs or "adb-ado-gdp-real-growth-forecast" in slugs


@pytest.mark.skipif(not FIXTURE_PDF.exists(), reason="fixture PDF not present")
def test_cli_json_against_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "adb_ado.parser", str(FIXTURE_PDF), "test-doc-id"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] in ("success", "partial")
    assert payload["parser_version"] == PARSER_VERSION
