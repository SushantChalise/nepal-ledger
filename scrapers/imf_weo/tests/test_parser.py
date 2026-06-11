"""Tests for the IMF WEO Nepal parser.

All tests run against the saved fixture at
``scrapers/imf_weo/tests/fixtures/weo_npl_2026-04.json``.  No network access.

Row counts are computed *from the fixture* rather than hard-coded, so the
suite cannot drift if the fixture changes.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from imf_weo import PARSER_VERSION, parse
from imf_weo.parser import _INDICATOR_CONFIG

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "weo_npl_2026-04.json"
PERIOD_TOLERANCE = timedelta(days=2)
PROJECTION_FROM_YEAR = 2025


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _expected_nonnull_rows() -> int:
    """Count non-null datapoints for *known* codes in the fixture."""
    doc = _fixture()
    total = 0
    for code, points in doc["indicators"].items():
        if code not in _INDICATOR_CONFIG:
            continue
        total += sum(1 for p in points if p.get("value") is not None)
    return total


def _expected_projection_rows() -> int:
    doc = _fixture()
    total = 0
    for code, points in doc["indicators"].items():
        if code not in _INDICATOR_CONFIG:
            continue
        total += sum(
            1
            for p in points
            if p.get("value") is not None and int(p["date"]) >= PROJECTION_FROM_YEAR
        )
    return total


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
    assert len(result.staging_rows) == _expected_nonnull_rows()


def test_all_rows_are_annual(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.reporting_period_type == "annual", row.indicator_slug_raw


def test_all_rows_are_confidence_A(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.confidence_grade_proposed == "A"


def test_all_rows_have_weo_prefix(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.indicator_slug_raw.startswith("weo-"), row.indicator_slug_raw


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


def test_all_13_indicator_slugs_present(result: ParserResult) -> None:
    expected = {cfg[0] for cfg in _INDICATOR_CONFIG.values()}
    found = {r.indicator_slug_raw for r in result.staging_rows}
    assert expected == found, f"missing: {expected - found}"
    assert len(expected) == 13


# ─── Period mapping ─────────────────────────────────────────────────────


def test_period_mapping_weo2023(result: ParserResult) -> None:
    """WEO year 2023 → BS FY 2080/81 → AD Jul 15 2023 – Jul 15 2024."""
    rows = [r for r in result.staging_rows if r.fiscal_year_bs == "2080/81"]
    assert rows, "no rows for WEO year 2023 (BS 2080/81)"
    for row in rows:
        assert row.fiscal_year_ad_label == "2023/24"
        assert abs(row.reporting_period_ad_start - datetime(2023, 7, 15, tzinfo=UTC)) <= PERIOD_TOLERANCE
        assert abs(row.reporting_period_ad_end - datetime(2024, 7, 15, tzinfo=UTC)) <= PERIOD_TOLERANCE


def test_period_mapping_weo2025_projection_year(result: ParserResult) -> None:
    """WEO year 2025 → BS FY 2082/83; also the first projection year."""
    rows = [r for r in result.staging_rows if r.fiscal_year_bs == "2082/83"]
    assert rows
    for row in rows:
        assert row.fiscal_year_ad_label == "2025/26"


# ─── observation_type (ADR-0025) ────────────────────────────────────────


def test_projection_count_matches_fixture(result: ParserResult) -> None:
    projections = [r for r in result.staging_rows if r.observation_type == "projection"]
    assert len(projections) == _expected_projection_rows()


def test_actuals_are_pre_projection_years(result: ParserResult) -> None:
    """Every 'actual' maps to a BS FY whose AD start year < projection_from_year."""
    for row in result.staging_rows:
        ad_year = row.reporting_period_ad_start.year
        if row.observation_type == "actual":
            assert ad_year < PROJECTION_FROM_YEAR, f"{row.indicator_slug_raw} {ad_year}"
        elif row.observation_type == "projection":
            assert ad_year >= PROJECTION_FROM_YEAR, f"{row.indicator_slug_raw} {ad_year}"
        else:
            pytest.fail(f"unexpected observation_type {row.observation_type}")


def test_projections_are_still_confidence_A(result: ParserResult) -> None:
    """Projections are high-authority forecasts: confidence A AND projection."""
    projections = [r for r in result.staging_rows if r.observation_type == "projection"]
    assert projections
    assert all(r.confidence_grade_proposed == "A" for r in projections)


def test_no_projection_marking_without_boundary() -> None:
    """When projection_from_year is absent, every row is 'actual'."""
    doc = _fixture()
    doc.pop("projection_from_year", None)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "success"
    assert all(r.observation_type == "actual" for r in res.staging_rows)


# ─── Values + units ─────────────────────────────────────────────────────


def test_gdp_current_usd_scaled_billion_to_million(result: ParserResult) -> None:
    """NGDPD 2023: 40.8 billion ×1000 = 40800 usd_million."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "weo-gdp-current-usd" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "usd_million"
    assert abs(rows[0].value - 40800.0) < 1e-6
    assert rows[0].observation_type == "actual"


def test_gdp_projection_value_and_type(result: ParserResult) -> None:
    """NGDPD 2026 (projection): 49.1 billion ×1000 = 49100 usd_million."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "weo-gdp-current-usd" and r.fiscal_year_bs == "2083/84"
    ]
    assert len(rows) == 1
    assert abs(rows[0].value - 49100.0) < 1e-6
    assert rows[0].observation_type == "projection"


def test_ppp_gdp_scaled_and_unit(result: ParserResult) -> None:
    """PPPGDP 2023: 143.0 billion ×1000 = 143000 intl_dollar_million."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "weo-gdp-ppp-intl-dollar" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert rows[0].unit == "intl_dollar_million"
    assert abs(rows[0].value - 143000.0) < 1e-6


def test_current_account_surplus_projection(result: ParserResult) -> None:
    """BCA_NGDPD 2026: +6.7 % of GDP — the remittance-driven surplus, projected."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "weo-current-account-pct-gdp" and r.fiscal_year_bs == "2083/84"
    ]
    assert len(rows) == 1
    assert abs(rows[0].value - 6.7) < 1e-6
    assert rows[0].observation_type == "projection"


def test_negative_fiscal_balance_roundtrips(result: ParserResult) -> None:
    """GGXCNL_NGDP 2023: -5.8 (negatives must survive)."""
    rows = [
        r for r in result.staging_rows
        if r.indicator_slug_raw == "weo-fiscal-balance-pct-gdp" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(rows) == 1
    assert abs(rows[0].value - (-5.8)) < 1e-6


def test_population_unit_is_persons_million(result: ParserResult) -> None:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "weo-population"]
    assert rows
    assert all(r.unit == "persons_million" for r in rows)


def test_null_values_skipped(result: ParserResult) -> None:
    """LUR has null for 2021 & 2022; LP & GGXWDG have null for 2027."""
    lur = [r for r in result.staging_rows if r.indicator_slug_raw == "weo-unemployment-rate-pct"]
    assert {r.fiscal_year_bs for r in lur}.isdisjoint({"2078/79", "2079/80"})
    debt = [r for r in result.staging_rows if r.indicator_slug_raw == "weo-govt-gross-debt-pct-gdp"]
    assert all(r.fiscal_year_bs != "2084/85" for r in debt)  # 2027 → BS 2084/85


def test_publication_date_from_fetched_at(result: ParserResult) -> None:
    expected = datetime(2026, 6, 11, tzinfo=UTC)
    for row in result.staging_rows:
        assert abs((row.publication_date_ad - expected).total_seconds()) < 1.0


# ─── Robustness ─────────────────────────────────────────────────────────


def test_idempotent() -> None:
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


def test_unknown_code_is_error_known_codes_unaffected() -> None:
    doc = _fixture()
    doc["indicators"]["XX.UNKNOWN"] = [{"date": "2023", "value": 1.0}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "partial"
    assert any("XX.UNKNOWN" in e.error_detail for e in res.errors)
    assert len(res.staging_rows) == _expected_nonnull_rows()


def test_invalid_projection_from_year_type_fails() -> None:
    doc = _fixture()
    doc["projection_from_year"] = "2025"  # string, not int
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"


def test_empty_indicators_returns_failure() -> None:
    doc = {"fetched_at": "2026-06-11T00:00:00Z", "country_code": "NPL", "indicators": {}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"
