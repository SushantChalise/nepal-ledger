"""Tests for the IMF Article IV Selected Economic Indicators parser.

The real PDFs are not committed to the repo (large, proprietary).
Core extraction logic (``extract_rows_from_table`` + helpers) is
exercised against a synthesized table that mirrors the real appendix
geometry. Full-PDF integration tests are skipped unless a fixture PDF
is placed at ``tests/fixtures/imf_article_iv_sample.pdf``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from imf_article_iv import PARSER_VERSION, parse
from imf_article_iv.parser import (
    SOURCE_ID,
    _classify_row,
    _parse_fy_columns,
    _parse_value,
    extract_rows_from_table,
)

FIXTURE_PDF = Path(__file__).resolve().parent / "fixtures" / "imf_article_iv_sample.pdf"
PERIOD_TOLERANCE = timedelta(days=40)

# Synthesized "Selected Economic Indicators" table — mirrors the expected
# pdfplumber extract_tables() output for a typical Article IV appendix.
# Columns: label | 2020/21 | 2021/22 | 2022/23 | 2023/24E | 2024/25P | 2025/26P
_HDR = [
    "",
    "2020/21",
    "2021/22",
    "2022/23",
    "2023/24E",
    "2024/25P",
    "2025/26P",
]
_DATA_ROWS: list[list[str]] = [
    ["Output and prices", "", "", "", "", "", ""],  # section header — ignored
    ["Real GDP growth (%)", "4.8", "-1.7", "5.8", "3.5", "5.0", "5.5"],
    ["CPI inflation (avg., %)", "3.6", "6.3", "7.7", "5.4", "5.5", "5.5"],
    ["Fiscal balance (% of GDP)", "-6.9", "-4.5", "-7.0", "-6.2", "-5.4", "-4.5"],
    ["Current account balance (% of GDP)", "0.3", "-3.3", "-0.2", "-1.5", "-2.0", "-2.0"],
    ["Public sector debt (% of GDP)", "43.5", "47.9", "49.0", "48.5", "48.0", "47.5"],
    ["Gross official reserves (months of imports)", "9.5", "10.0", "11.5", "12.5", "13.0", "13.5"],
]

_PUB_DATE_AD = datetime(2024, 3, 15, tzinfo=UTC)
_PUB_DATE_BS = "2080 Chait 2"
_CONTEXT = "IMF Article IV 2024"

# Pre-compute expected actual/forecast slug sets.
_ACTUAL_PREFIXES = frozenset(
    {
        "imf-gdp-real-growth",
        "imf-cpi-inflation-avg",
        "imf-fiscal-balance-pct-gdp",
        "imf-current-account-pct-gdp",
        "imf-public-debt-pct-gdp",
        "imf-gross-reserves-months",
    }
)
_ACTUAL_SLUGS = frozenset(f"{p}-actual" for p in _ACTUAL_PREFIXES)
_FORECAST_SLUGS = frozenset(f"{p}-forecast" for p in _ACTUAL_PREFIXES)


@pytest.fixture(scope="module")
def table_result() -> list[StagingRowDraft]:
    rows, errors = extract_rows_from_table(
        header_row=_HDR,
        data_rows=_DATA_ROWS,
        report_context=_CONTEXT,
        publication_date_ad=_PUB_DATE_AD,
        publication_date_bs=_PUB_DATE_BS,
    )
    assert errors == [], f"unexpected errors: {errors}"
    return rows


# ── Column parser ──────────────────────────────────────────────────────────────


def test_parse_fy_columns_counts() -> None:
    cols = _parse_fy_columns(_HDR)
    assert len(cols) == 6


def test_parse_fy_columns_actuals_vs_forecasts() -> None:
    cols = _parse_fy_columns(_HDR)
    actuals = [c for c in cols if not c.is_forecast]
    forecasts = [c for c in cols if c.is_forecast]
    assert len(actuals) == 3  # 2020/21, 2021/22, 2022/23
    assert len(forecasts) == 3  # 2023/24E, 2024/25P, 2025/26P


def test_parse_fy_columns_fy_prefix_handling() -> None:
    # Some editions use "FY2023/24P" notation.
    hdr = ["", "FY2021/22", "FY2022/23", "FY2023/24E"]
    cols = _parse_fy_columns(hdr)
    assert len(cols) == 3
    assert cols[0].ad_lead_year == 2021
    assert not cols[0].is_forecast
    assert cols[2].is_forecast


# ── Row classifier ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("label", "expected_kind"),
    [
        ("Real GDP growth (%)", "gdp_real_growth"),
        ("  GDP growth  ", "gdp_real_growth"),
        ("CPI inflation (avg., %)", "cpi_inflation_avg"),
        ("Consumer price inflation, average", "cpi_inflation_avg"),
        ("Headline inflation (average)", "cpi_inflation_avg"),
        ("Fiscal balance (% of GDP)", "fiscal_balance"),
        ("Overall fiscal balance, incl. grants (% of GDP)", "fiscal_balance"),
        ("Current account balance (% of GDP)", "current_account"),
        ("Public sector debt (% of GDP)", "public_debt"),
        ("Central government debt (% of GDP)", "public_debt"),
        ("Gross official reserves (months of imports)", "gross_reserves_months"),
        ("In months of imports", "gross_reserves_months"),
        ("GDP at market prices", None),  # not a target row
        ("Total revenues (% of GDP)", None),
    ],
)
def test_classify_row(label: str, expected_kind: str | None) -> None:
    assert _classify_row(label) == expected_kind


# ── Value parser ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.8", 4.8),
        ("-1.7", -1.7),
        ("-6.2", -6.2),
        ("(6.2)", -6.2),  # bracketed negative convention
        ("", None),
        ("-", None),
        ("N/A", None),
        ("...", None),
    ],
)
def test_parse_value(raw: str, expected: float | None) -> None:
    result = _parse_value(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected, abs=1e-6)


# ── Core table extraction ──────────────────────────────────────────────────────


def test_row_count(table_result: list[StagingRowDraft]) -> None:
    # 6 kinds × (3 actual cols + 3 forecast cols) = 36 rows.
    assert len(table_result) == 36


def test_actual_slugs_present(table_result: list[StagingRowDraft]) -> None:
    slugs = {r.indicator_slug_raw for r in table_result}
    assert _ACTUAL_SLUGS.issubset(slugs)


def test_forecast_slugs_present(table_result: list[StagingRowDraft]) -> None:
    slugs = {r.indicator_slug_raw for r in table_result}
    assert _FORECAST_SLUGS.issubset(slugs)


def test_units_correct(table_result: list[StagingRowDraft]) -> None:
    by_slug = {r.indicator_slug_raw: r.unit for r in table_result}
    assert by_slug["imf-gdp-real-growth-actual"] == "percent"
    assert by_slug["imf-cpi-inflation-avg-actual"] == "percent"
    assert by_slug["imf-fiscal-balance-pct-gdp-actual"] == "percent_gdp"
    assert by_slug["imf-current-account-pct-gdp-actual"] == "percent_gdp"
    assert by_slug["imf-public-debt-pct-gdp-actual"] == "percent_gdp"
    assert by_slug["imf-gross-reserves-months-actual"] == "months"


def test_negative_values_preserved(table_result: list[StagingRowDraft]) -> None:
    fiscal = [r for r in table_result if r.indicator_slug_raw == "imf-fiscal-balance-pct-gdp-actual"]
    # All three actual fiscal balance values are negative in the fixture.
    assert all(r.value < 0 for r in fiscal)


def test_period_dates_for_actual_fy_2022_23(table_result: list[StagingRowDraft]) -> None:
    """BS 2079/80 actual: mid-Shrawan 2079 ≈ 15 Jul 2022, mid-Ashadh 2079 ≈ 15 Jun 2023."""
    # 2022/23 AD → BS 2079/80 (2022 + 57 = 2079)
    rows_2022_23 = [
        r for r in table_result
        if r.fiscal_year_bs == "2079/80" and r.indicator_slug_raw.endswith("-actual")
    ]
    assert rows_2022_23, "no actual rows for FY 2079/80"
    for row in rows_2022_23:
        assert row.reporting_period_type == "annual"
        assert row.fiscal_year_ad_label == "2022/23"
        expected_start = datetime(2022, 7, 15, tzinfo=UTC)
        expected_end = datetime(2023, 6, 15, tzinfo=UTC)
        assert abs(row.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
        assert abs(row.reporting_period_ad_end - expected_end) <= PERIOD_TOLERANCE


def test_forecast_marker_in_notes(table_result: list[StagingRowDraft]) -> None:
    forecast_rows = [r for r in table_result if r.indicator_slug_raw.endswith("-forecast")]
    for row in forecast_rows:
        assert row.parser_notes
        # Marker "E" or "P" should be referenced.
        assert any(tok in (row.parser_notes or "") for tok in ("E", "P", "marker"))


def test_confidence_grade_a(table_result: list[StagingRowDraft]) -> None:
    for row in table_result:
        assert row.confidence_grade_proposed == "A"


def test_source_id_constant() -> None:
    assert SOURCE_ID == "imf-article-iv"


def test_parser_version_constant() -> None:
    assert PARSER_VERSION == "0.1.0"


# ── Missing-file guard ─────────────────────────────────────────────────────────


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-imf.pdf", "test-id")
    assert res.status == "failure"
    assert res.errors


# ── Integration test (requires real PDF fixture) ───────────────────────────────


@pytest.mark.skipif(not FIXTURE_PDF.exists(), reason="fixture PDF not present")
def test_integration_against_real_pdf() -> None:
    res = parse(str(FIXTURE_PDF), "test-doc-id")
    assert res.status in ("success", "partial")
    assert len(res.staging_rows) > 0
    slugs = {r.indicator_slug_raw for r in res.staging_rows}
    # At minimum, GDP growth and inflation should be present in any edition.
    assert "imf-gdp-real-growth-actual" in slugs or "imf-gdp-real-growth-forecast" in slugs


@pytest.mark.skipif(not FIXTURE_PDF.exists(), reason="fixture PDF not present")
def test_cli_json_against_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "imf_article_iv.parser", str(FIXTURE_PDF), "test-doc-id"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] in ("success", "partial")
    assert payload["parser_version"] == PARSER_VERSION
