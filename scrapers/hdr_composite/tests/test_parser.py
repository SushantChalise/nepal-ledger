"""Tests for the UNDP HDR Composite Indices (Nepal) parser.

Runs against a trimmed CSV fixture whose Nepal row holds real HDR 2025 values.
No network access. Expected counts are computed from the fixture.
"""

from __future__ import annotations

import csv
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from hdr_composite import PARSER_VERSION, parse
from hdr_composite.parser import _INDICATOR_CONFIG

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "hdr_composite_npl.csv"


def _nepal_record() -> dict[str, str]:
    rows = list(csv.DictReader(FIXTURE_PATH.read_text(encoding="latin-1").splitlines()))
    return next(r for r in rows if r["iso3"] == "NPL")


def _expected_rows() -> int:
    rec = _nepal_record()
    total = 0
    for col, value in rec.items():
        m = re.match(r"^([a-z_]+)_(\d{4})$", col)
        if m and m.group(1) in _INDICATOR_CONFIG and (value or "").strip() != "":
            total += 1
    return total


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


def test_all_rows_actual_confidence_a_hdr_prefix(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.observation_type == "actual"
        assert row.confidence_grade_proposed == "A"
        assert row.reporting_period_type == "annual"
        assert row.indicator_slug_raw.startswith("hdr-"), row.indicator_slug_raw


def test_only_nepal_extracted(result: ParserResult) -> None:
    """The USA distractor row must not contribute (HDI 2023 is Nepal's 0.622)."""
    hdi_2023 = [
        r for r in result.staging_rows if r.indicator_slug_raw == "hdr-hdi" and r.fiscal_year_bs == "2080/81"
    ]
    assert len(hdi_2023) == 1
    assert abs(hdi_2023[0].value - 0.622) < 1e-9


def test_hdi_anchor_value_and_unit(result: ParserResult) -> None:
    """Nepal HDI 2023 = 0.622 (index_0_1) — the published anchor."""
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "hdr-hdi"]
    by_fy = {r.fiscal_year_bs: r for r in rows}
    assert by_fy["2080/81"].unit == "index_0_1"
    assert abs(by_fy["2080/81"].value - 0.622) < 1e-9
    assert abs(by_fy["2047/48"].value - 0.404) < 1e-9  # hdi_1990 → BS 1990+57=2047 → 2047/48


def test_multi_year_hdi(result: ParserResult) -> None:
    """hdi has 1990, 2022, 2023 in the fixture → 3 rows."""
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "hdr-hdi"]
    assert len(rows) == 3


def test_exact_prefix_no_leakage(result: ParserResult) -> None:
    """`hdi` must not capture hdi_rank_2023; hdi_f / hdi_m are their own slugs."""
    slugs = {r.indicator_slug_raw for r in result.staging_rows}
    assert "hdr-hdi-female" in slugs
    assert "hdr-hdi-male" in slugs
    # hdi_rank_2023 is unconfigured → no row with a value of 145
    assert all(r.value != 145.0 for r in result.staging_rows if r.indicator_slug_raw == "hdr-hdi")


def test_unconfigured_columns_ignored(result: ParserResult) -> None:
    """abr_2023 (67.169) is not configured and must not appear."""
    assert all(abs(r.value - 67.169) > 1e-9 for r in result.staging_rows)


def test_empty_cell_skipped(result: ParserResult) -> None:
    """ihdi_2010 is blank for Nepal → only ihdi_2023 emitted."""
    ihdi = [r for r in result.staging_rows if r.indicator_slug_raw == "hdr-ihdi"]
    assert len(ihdi) == 1
    assert ihdi[0].fiscal_year_bs == "2080/81"


def test_units_by_family(result: ParserResult) -> None:
    units = {r.indicator_slug_raw: r.unit for r in result.staging_rows}
    assert units["hdr-life-expectancy"] == "years"
    assert units["hdr-mean-years-schooling"] == "years"
    assert units["hdr-gni-per-capita-ppp"] == "intl_dollar"
    assert units["hdr-ihdi-overall-loss"] == "percent"
    assert units["hdr-gii"] == "index_0_1"


def test_gni_per_capita_value(result: ParserResult) -> None:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == "hdr-gni-per-capita-ppp"]
    assert len(rows) == 1
    assert abs(rows[0].value - 4725.930613) < 1e-6


def test_period_mapping_2023(result: ParserResult) -> None:
    """HDR 2023 → BS 2080/81 → AD Jul 15 2023."""
    rows = [r for r in result.staging_rows if r.fiscal_year_bs == "2080/81"]
    assert rows
    for r in rows:
        assert r.fiscal_year_ad_label == "2023/24"
        assert r.reporting_period_ad_start == datetime(2023, 7, 15, tzinfo=UTC)


def test_publication_date_pinned(result: ParserResult) -> None:
    for r in result.staging_rows:
        assert r.publication_date_ad == datetime(2025, 5, 6, tzinfo=UTC)


def test_idempotent() -> None:
    a = parse(str(FIXTURE_PATH), source_document_id="x")
    b = parse(str(FIXTURE_PATH), source_document_id="x")
    assert [r.value for r in a.staging_rows] == [r.value for r in b.staging_rows]


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent.csv", source_document_id="x")
    assert res.status == "failure"
    assert res.errors


def test_no_nepal_row_returns_failure() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="latin-1") as f:
        f.write("iso3,country,hdi_2023\nUSA,United States,0.927\n")
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"


def test_missing_iso3_column_returns_failure() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="latin-1") as f:
        f.write("country,hdi_2023\nNepal,0.622\n")
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "failure"


def test_non_numeric_cell_is_error_others_survive() -> None:
    rec_cols = "iso3,country,hdi_2023,le_2023\nNPL,Nepal,not-a-num,70.354\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="latin-1") as f:
        f.write(rec_cols)
        tmp = f.name
    res = parse(tmp, source_document_id="x")
    assert res.status == "partial"
    assert any("hdi_2023" in e.error_detail for e in res.errors)
    assert any(r.indicator_slug_raw == "hdr-life-expectancy" for r in res.staging_rows)
