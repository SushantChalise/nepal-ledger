"""Tests for the WB International Debt Statistics (Nepal) parser.

Runs against a fixture whose values are lifted from a live IDS API response
(Nepal, 2023). No network access.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from wb_ids import PARSER_VERSION, parse
from wb_ids.parser import _INDICATOR_CONFIG

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "ids_npl_2026.json"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _expected_rows() -> int:
    doc = _fixture()
    return sum(
        1
        for slug, pts in doc["series"].items()
        if slug in _INDICATOR_CONFIG
        for p in pts
        if p.get("value") is not None
    )


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE_PATH.exists(), f"fixture missing: {FIXTURE_PATH}"
    return parse(str(FIXTURE_PATH), source_document_id="test-doc-id")


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", f"status={result.status} errors={result.errors}"


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_no_errors(result: ParserResult) -> None:
    assert result.errors == [], result.errors


def test_total_row_count(result: ParserResult) -> None:
    assert len(result.staging_rows) == _expected_rows()


def test_all_rows_actual_confidence_a_ids_prefix(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.observation_type == "actual"
        assert row.confidence_grade_proposed == "A"
        assert row.reporting_period_type == "annual"
        assert row.indicator_slug_raw.startswith("ids-"), row.indicator_slug_raw


def test_all_12_slugs_present(result: ParserResult) -> None:
    found = {r.indicator_slug_raw for r in result.staging_rows}
    assert found == set(_INDICATOR_CONFIG), set(_INDICATOR_CONFIG) - found
    assert len(found) == 12


def test_total_debt_scaled_to_million(result: ParserResult) -> None:
    """DT.DOD.DECT.CD 2023: 9,982,808,324 ÷ 1e6 = 9982.808324 usd_million."""
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "ids-external-debt-total-usd"]
    assert len(rows) == 1
    assert rows[0].unit == "usd_million"
    assert abs(rows[0].value - 9982.808324) < 1e-6


def test_debt_to_gni_is_percent_no_scaling(result: ParserResult) -> None:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "ids-external-debt-pct-gni"]
    assert len(rows) == 1
    assert rows[0].unit == "percent"
    assert abs(rows[0].value - 24.0384374799175) < 1e-9


def test_top_creditors_ordering(result: ParserResult) -> None:
    """Japan > India > China among bilateral creditors (the headline story)."""
    by_slug = {r.indicator_slug_raw: r.value for r in result.staging_rows}
    assert by_slug["ids-debt-bilateral-japan-usd"] > by_slug["ids-debt-bilateral-india-usd"]
    assert by_slug["ids-debt-bilateral-india-usd"] > by_slug["ids-debt-bilateral-china-usd"]
    # IDA + ADB dominate multilateral
    assert by_slug["ids-debt-multilateral-worldbank-ida-usd"] > by_slug["ids-debt-multilateral-adb-usd"]
    assert abs(by_slug["ids-debt-bilateral-china-usd"] - 262.099082) < 1e-6


def test_multi_year_short_term(result: ParserResult) -> None:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "ids-short-term-debt-usd"]
    assert len(rows) == 2
    assert {r.fiscal_year_bs for r in rows} == {"2080/81", "2079/80"}


def test_period_mapping_2023(result: ParserResult) -> None:
    """IDS 2023 → BS 2080/81 → AD Jul 15 2023 (shared nepal_wb_year_period)."""
    rows = [r for r in result.staging_rows if r.fiscal_year_bs == "2080/81"]
    assert rows
    for r in rows:
        assert r.fiscal_year_ad_label == "2023/24"
        assert r.reporting_period_ad_start == datetime(2023, 7, 15, tzinfo=UTC)
        assert r.reporting_period_ad_end == datetime(2024, 7, 15, tzinfo=UTC)


def test_publication_date_from_fetched_at(result: ParserResult) -> None:
    expected = datetime(2026, 6, 11, tzinfo=UTC)
    for row in result.staging_rows:
        assert abs((row.publication_date_ad - expected).total_seconds()) < 1.0


def test_idempotent() -> None:
    a = parse(str(FIXTURE_PATH), source_document_id="x")
    b = parse(str(FIXTURE_PATH), source_document_id="x")
    assert [r.value for r in a.staging_rows] == [r.value for r in b.staging_rows]


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent.json", source_document_id="x")
    assert res.status == "failure"
    assert res.errors


def test_invalid_json_returns_failure() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"
    assert any(e.error_class == "EncodingError" for e in res.errors)


def test_null_value_skipped() -> None:
    doc = _fixture()
    doc["series"]["ids-short-term-debt-usd"].append({"date": "2021", "value": None})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "success"
    st = [r for r in res.staging_rows if r.indicator_slug_raw == "ids-short-term-debt-usd"]
    assert len(st) == 2  # 2021 null skipped


def test_unknown_slug_is_error_known_unaffected() -> None:
    doc = _fixture()
    doc["series"]["ids-made-up"] = [{"date": "2023", "value": 1.0}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "partial"
    assert any("ids-made-up" in e.error_detail for e in res.errors)
    assert len(res.staging_rows) == _expected_rows()


def test_empty_series_returns_failure() -> None:
    doc = {"fetched_at": "2026-06-11T00:00:00Z", "country_code": "NPL", "series": {}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"
