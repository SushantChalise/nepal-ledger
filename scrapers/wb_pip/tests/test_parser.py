"""Tests for the WB PIP Nepal parser.

Runs against the saved fixture at
``scrapers/wb_pip/tests/fixtures/pip_npl_2026.json`` (values lifted from a live
PIP API response). No network access. Counts are computed from the fixture so
the suite cannot drift.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from wb_pip import PARSER_VERSION, parse
from wb_pip.parser import _ANCHOR_FIELDS

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "pip_npl_2026.json"
PERIOD_TOLERANCE = timedelta(days=2)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _expected_anchor_rows() -> int:
    doc = _fixture()
    fields = [f[0] for f in _ANCHOR_FIELDS]
    return sum(
        1 for a in doc["anchors"] for f in fields if a.get(f) is not None
    )


def _anchor_years() -> set[int]:
    return {a["reporting_year"] for a in _fixture()["anchors"]}


def _expected_series_rows() -> int:
    doc = _fixture()
    anchors = _anchor_years()
    return sum(
        1
        for p in doc["series_365"]
        if p.get("headcount") is not None and p["reporting_year"] not in anchors
    )


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
    assert len(result.staging_rows) == _expected_anchor_rows() + _expected_series_rows()


def test_all_rows_annual_with_pip_prefix(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.reporting_period_type == "annual"
        assert row.indicator_slug_raw.startswith("pip-"), row.indicator_slug_raw


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw
        assert isinstance(row.value, float)
        assert row.unit
        assert row.fiscal_year_bs == row.reporting_period_bs
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.publication_date_ad, datetime)


def test_all_10_slugs_present(result: ParserResult) -> None:
    expected = {f[1] for f in _ANCHOR_FIELDS}
    found = {r.indicator_slug_raw for r in result.staging_rows}
    assert expected == found, f"missing: {expected - found}"
    assert len(expected) == 10


# ─── Period mapping (PIP calendar year → Nepal FY, WDI convention) ──────────


def test_period_mapping_2022_survey(result: ParserResult) -> None:
    """PIP 2022 → BS FY 2079/80 → AD Jul 15 2022 – Jul 15 2023."""
    rows = [r for r in result.staging_rows if r.fiscal_year_bs == "2079/80"]
    assert rows
    for row in rows:
        assert row.fiscal_year_ad_label == "2022/23"
        assert abs(row.reporting_period_ad_start - datetime(2022, 7, 15, tzinfo=UTC)) <= PERIOD_TOLERANCE


# ─── observation_type (ADR-0025) ────────────────────────────────────────────


def test_anchor_rows_are_actual_confidence_a(result: ParserResult) -> None:
    anchors = _anchor_years()
    actual_rows = [r for r in result.staging_rows if r.observation_type == "actual"]
    assert len(actual_rows) == _expected_anchor_rows()
    for r in actual_rows:
        assert r.confidence_grade_proposed == "A"
        assert (r.reporting_period_ad_start.year) in anchors


def test_series_rows_are_confidence_b_non_actual(result: ParserResult) -> None:
    series_rows = [
        r
        for r in result.staging_rows
        if r.indicator_slug_raw == "pip-poverty-headcount-365" and r.observation_type != "actual"
    ]
    assert len(series_rows) == _expected_series_rows()
    for r in series_rows:
        assert r.confidence_grade_proposed == "B"


def test_interpolation_vs_extrapolation_mapping(result: ParserResult) -> None:
    """2007/2015 interpolation→interpolated; 2024/2026 fwd extrapolation→projection;
    1982 backward extrapolation→estimate."""
    by_year = {
        r.reporting_period_ad_start.year: r.observation_type
        for r in result.staging_rows
        if r.indicator_slug_raw == "pip-poverty-headcount-365" and r.observation_type != "actual"
    }
    assert by_year[2007] == "interpolated"
    assert by_year[2015] == "interpolated"
    assert by_year[2024] == "projection"
    assert by_year[2026] == "projection"
    assert by_year[1982] == "estimate"


def test_anchor_year_not_duplicated_by_series(result: ParserResult) -> None:
    """2022 appears in series_365 too, but the survey anchor is authoritative —
    exactly one pip-poverty-headcount-365 row for BS 2079/80, and it's 'actual'."""
    rows_2022 = [
        r
        for r in result.staging_rows
        if r.indicator_slug_raw == "pip-poverty-headcount-365" and r.fiscal_year_bs == "2079/80"
    ]
    assert len(rows_2022) == 1
    assert rows_2022[0].observation_type == "actual"
    assert abs(rows_2022[0].value - 5.38) < 1e-6  # 0.0538 × 100, NOT the series 0.054


# ─── Values + units ──────────────────────────────────────────────────────────


def test_headcount_ratio_scaled_to_percent(result: ParserResult) -> None:
    """LSS-IV (2022) extreme poverty: 0.0021 × 100 = 0.21 percent."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "pip-poverty-headcount-215" and r.fiscal_year_bs == "2079/80"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "percent"
    assert abs(rows[0].value - 0.21) < 1e-6


def test_gini_scaled_to_index_points(result: ParserResult) -> None:
    """LSS-IV Gini 0.3002 × 100 = 30.02 index_points (matches wdi-gini-index scale)."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "pip-gini" and r.fiscal_year_bs == "2079/80"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "index_points"
    assert abs(rows[0].value - 30.02) < 1e-6


def test_mean_consumption_unit_and_value(result: ParserResult) -> None:
    """Mean daily consumption is stored as-is in intl_dollar_per_day."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "pip-mean-consumption" and r.fiscal_year_bs == "2079/80"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "intl_dollar_per_day"
    assert abs(rows[0].value - 9.4669) < 1e-6


def test_gini_only_for_survey_anchors(result: ParserResult) -> None:
    """Gini exists only for the 5 survey years — never for modelled years."""
    gini_rows = [r for r in result.staging_rows if r.indicator_slug_raw == "pip-gini"]
    assert len(gini_rows) == 5
    assert all(r.observation_type == "actual" for r in gini_rows)


def test_publication_date_from_fetched_at(result: ParserResult) -> None:
    expected = datetime(2026, 6, 11, tzinfo=UTC)
    for row in result.staging_rows:
        assert abs((row.publication_date_ad - expected).total_seconds()) < 1.0


# ─── Robustness ──────────────────────────────────────────────────────────────


def test_null_series_value_skipped(result: ParserResult) -> None:
    """2011 has null headcount → BS 2068/69 must not appear in the series."""
    assert all(
        not (r.indicator_slug_raw == "pip-poverty-headcount-365" and r.fiscal_year_bs == "2068/69")
        for r in result.staging_rows
    )


def test_idempotent() -> None:
    first = parse(str(FIXTURE_PATH), source_document_id="x")
    second = parse(str(FIXTURE_PATH), source_document_id="x")
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


def test_no_anchors_returns_failure() -> None:
    doc = {"fetched_at": "2026-06-11T00:00:00Z", "country_code": "NPL", "anchors": [], "series_365": []}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"


def test_unparseable_anchor_value_is_error_others_survive() -> None:
    doc = _fixture()
    doc["anchors"][0]["gini"] = "not-a-number"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "partial"
    assert any("gini" in e.error_detail for e in res.errors)
