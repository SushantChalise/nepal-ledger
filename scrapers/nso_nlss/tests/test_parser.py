"""Tests for the NSO NLSS-IV Summary Report parser.

Fixture: ``nlss_iv_summary_excerpt.pdf`` — a 5-page excerpt drawn from the
full 57-page NLSS-IV Summary Report (NSO, February 2024).  It contains pages
13, 16, 21, 22, and 27 of the original, covering every indicator-producing
section:

    Page 0 (orig 13): Figure 1 — per-capita consumption
    Page 1 (orig 16): Figure 2 — food/non-food shares
    Page 2 (orig 21): Table 9  — national/urban/rural headcount + Gini
    Page 3 (orig 22): Table 11 — provincial poverty headcounts
    Page 4 (orig 27): Annex A1 (headcount history) + A4 (Gini history)

Expected output: 14 NLSS-IV rows + 6 NLSS-III comparison rows = 20 rows total.

All tests run against the fixture only — no network access.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nso_nlss.parser import PARSER_VERSION, parse

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "nlss_iv_summary_excerpt.pdf"
PERIOD_TOLERANCE = timedelta(days=3)

# ── Expected indicator slugs ──────────────────────────────────────────────────

# 14 NLSS-IV indicators
_NLSS4_SLUGS: frozenset[str] = frozenset(
    {
        "nlss-poverty-headcount-national",
        "nlss-poverty-headcount-urban",
        "nlss-poverty-headcount-rural",
        "nlss-poverty-headcount-koshi",
        "nlss-poverty-headcount-madhesh",
        "nlss-poverty-headcount-bagmati",
        "nlss-poverty-headcount-gandaki",
        "nlss-poverty-headcount-lumbini",
        "nlss-poverty-headcount-karnali",
        "nlss-poverty-headcount-sudurpaschim",
        "nlss-per-capita-consumption-annual",
        "nlss-gini-consumption",
        "nlss-food-share-consumption",
        "nlss-non-food-share-consumption",
    }
)

# 6 NLSS-III comparison indicators (subset of above slugs, different fiscal year)
_NLSS3_SLUGS: frozenset[str] = frozenset(
    {
        "nlss-poverty-headcount-national",
        "nlss-poverty-headcount-urban",
        "nlss-poverty-headcount-rural",
        "nlss-gini-consumption",
        "nlss-food-share-consumption",
        "nlss-non-food-share-consumption",
    }
)

_NLSS4_FY = "2079/80"  # BS
_NLSS3_FY = "2067/68"  # BS


# ── Shared fixture ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE.exists(), (
        f"Fixture PDF missing: {FIXTURE}\n"
        "Run the fixture-extraction script to regenerate it:\n"
        "  cd scrapers && python nso_nlss/tests/build_fixture.py"
    )
    return parse(str(FIXTURE), source_document_id="test-doc-id")


@pytest.fixture(scope="module")
def nlss4_rows(result: ParserResult) -> list[StagingRowDraft]:
    return [r for r in result.staging_rows if r.fiscal_year_bs == _NLSS4_FY]


@pytest.fixture(scope="module")
def nlss3_rows(result: ParserResult) -> list[StagingRowDraft]:
    return [r for r in result.staging_rows if r.fiscal_year_bs == _NLSS3_FY]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _value_for(rows: list[StagingRowDraft], slug: str) -> float:
    matches = [r for r in rows if r.indicator_slug_raw == slug]
    assert len(matches) == 1, (
        f"expected exactly one row with slug={slug!r}, got {len(matches)}"
    )
    return matches[0].value


def _unit_for(rows: list[StagingRowDraft], slug: str) -> str:
    matches = [r for r in rows if r.indicator_slug_raw == slug]
    assert matches, f"no row with slug={slug!r}"
    return matches[0].unit


# ── Status and metadata ───────────────────────────────────────────────────────


def test_status(result: ParserResult) -> None:
    # Partial is acceptable if a section has a layout warning; failure is not.
    assert result.status in ("success", "partial"), (
        f"parser status={result.status!r}; errors={result.errors}"
    )


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_total_row_count(result: ParserResult) -> None:
    assert len(result.staging_rows) == 20, (
        f"expected 20 rows (14 NLSS-IV + 6 NLSS-III), "
        f"got {len(result.staging_rows)}"
    )


def test_nlss4_row_count(nlss4_rows: list[StagingRowDraft]) -> None:
    assert len(nlss4_rows) == 14, (
        f"expected 14 NLSS-IV rows, got {len(nlss4_rows)}: "
        f"{[r.indicator_slug_raw for r in nlss4_rows]}"
    )


def test_nlss3_row_count(nlss3_rows: list[StagingRowDraft]) -> None:
    assert len(nlss3_rows) == 6, (
        f"expected 6 NLSS-III rows, got {len(nlss3_rows)}: "
        f"{[r.indicator_slug_raw for r in nlss3_rows]}"
    )


def test_nlss4_slugs_complete(nlss4_rows: list[StagingRowDraft]) -> None:
    emitted = {r.indicator_slug_raw for r in nlss4_rows}
    assert emitted == _NLSS4_SLUGS, f"missing: {_NLSS4_SLUGS - emitted}"


def test_nlss3_slugs_complete(nlss3_rows: list[StagingRowDraft]) -> None:
    emitted = {r.indicator_slug_raw for r in nlss3_rows}
    assert emitted == _NLSS3_SLUGS, f"missing: {_NLSS3_SLUGS - emitted}"


# ── Required fields (all rows) ────────────────────────────────────────────────


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw.startswith("nlss-")
        assert row.unit in ("percent", "ratio", "npr")
        assert row.reporting_period_type == "annual"
        assert row.confidence_grade_proposed == "A"
        assert isinstance(row.value, float)
        assert row.value > 0
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs
        assert row.parser_notes


def test_publication_date(result: ParserResult) -> None:
    expected = datetime(2024, 2, 15, tzinfo=UTC)
    for row in result.staging_rows:
        assert row.publication_date_ad == expected, (
            f"slug={row.indicator_slug_raw} pub_date={row.publication_date_ad}"
        )


# ── Period anchoring: NLSS-IV (FY 2079/80 BS ≈ 2022/23 AD) ──────────────────


def test_nlss4_period_fields(nlss4_rows: list[StagingRowDraft]) -> None:
    for row in nlss4_rows:
        assert row.fiscal_year_bs == "2079/80", row.indicator_slug_raw
        assert row.fiscal_year_ad_label == "2022/23", row.indicator_slug_raw
        assert row.reporting_period_bs == "FY 2079/80", row.indicator_slug_raw


def test_nlss4_period_start_mid_shrawan_2079(nlss4_rows: list[StagingRowDraft]) -> None:
    # Shrawan 2079 ≈ mid-July 2022
    expected = datetime(2022, 7, 15, tzinfo=UTC)
    for row in nlss4_rows:
        assert abs(row.reporting_period_ad_start - expected) <= PERIOD_TOLERANCE, (
            f"slug={row.indicator_slug_raw} start={row.reporting_period_ad_start}"
        )


def test_nlss4_period_end_mid_ashadh_2079(nlss4_rows: list[StagingRowDraft]) -> None:
    # Ashadh 2079 ends mid-June 2023
    expected = datetime(2023, 6, 15, tzinfo=UTC)
    for row in nlss4_rows:
        assert abs(row.reporting_period_ad_end - expected) <= PERIOD_TOLERANCE, (
            f"slug={row.indicator_slug_raw} end={row.reporting_period_ad_end}"
        )


# ── Period anchoring: NLSS-III (FY 2067/68 BS ≈ 2010/11 AD) ─────────────────


def test_nlss3_period_fields(nlss3_rows: list[StagingRowDraft]) -> None:
    for row in nlss3_rows:
        assert row.fiscal_year_bs == "2067/68", row.indicator_slug_raw
        assert row.fiscal_year_ad_label == "2010/11", row.indicator_slug_raw
        assert row.reporting_period_bs == "FY 2067/68", row.indicator_slug_raw


def test_nlss3_period_start_mid_shrawan_2067(nlss3_rows: list[StagingRowDraft]) -> None:
    # Shrawan 2067 ≈ mid-July 2010
    expected = datetime(2010, 7, 15, tzinfo=UTC)
    for row in nlss3_rows:
        assert abs(row.reporting_period_ad_start - expected) <= PERIOD_TOLERANCE, (
            f"slug={row.indicator_slug_raw} start={row.reporting_period_ad_start}"
        )


def test_nlss3_period_end_mid_ashadh_2067(nlss3_rows: list[StagingRowDraft]) -> None:
    # Ashadh 2067 ends mid-June 2011
    expected = datetime(2011, 6, 15, tzinfo=UTC)
    for row in nlss3_rows:
        assert abs(row.reporting_period_ad_end - expected) <= PERIOD_TOLERANCE, (
            f"slug={row.indicator_slug_raw} end={row.reporting_period_ad_end}"
        )


# ── NLSS-IV indicator values ──────────────────────────────────────────────────


def test_national_headcount_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    """Table 9: Nepal poverty headcount 20.27% (NLSS-IV 2022/23)."""
    assert _value_for(nlss4_rows, "nlss-poverty-headcount-national") == pytest.approx(
        20.27, abs=1e-4
    )


def test_urban_headcount_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    """Table 9: Urban poverty headcount 18.34% (NLSS-IV)."""
    assert _value_for(nlss4_rows, "nlss-poverty-headcount-urban") == pytest.approx(
        18.34, abs=1e-4
    )


def test_rural_headcount_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    """Table 9: Rural poverty headcount 24.66% (NLSS-IV)."""
    assert _value_for(nlss4_rows, "nlss-poverty-headcount-rural") == pytest.approx(
        24.66, abs=1e-4
    )


@pytest.mark.parametrize(
    "slug, expected",
    [
        ("nlss-poverty-headcount-koshi", 17.19),
        ("nlss-poverty-headcount-madhesh", 22.53),
        ("nlss-poverty-headcount-bagmati", 12.59),
        ("nlss-poverty-headcount-gandaki", 11.88),
        ("nlss-poverty-headcount-lumbini", 24.35),
        ("nlss-poverty-headcount-karnali", 26.69),
        ("nlss-poverty-headcount-sudurpaschim", 34.16),
    ],
)
def test_provincial_headcount_nlss4(
    nlss4_rows: list[StagingRowDraft], slug: str, expected: float
) -> None:
    """Table 11: all 7 province poverty headcount rates (NLSS-IV)."""
    assert _value_for(nlss4_rows, slug) == pytest.approx(expected, abs=1e-4)


def test_gini_nlss4_is_ratio_scale(nlss4_rows: list[StagingRowDraft]) -> None:
    """Table 9: Gini 0.300 on 0–1 scale (NOT the Table A4 0–100 value of 30.0)."""
    val = _value_for(nlss4_rows, "nlss-gini-consumption")
    assert val == pytest.approx(0.300, abs=1e-4)
    # Guard against accidentally storing the 0–100 value (30.0)
    assert val < 1.0, f"Gini stored on wrong scale: {val}"


def test_percapita_consumption_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    """Figure 1: NEPAL annual per-capita consumption NPR 130,853 (NLSS-IV)."""
    assert _value_for(nlss4_rows, "nlss-per-capita-consumption-annual") == pytest.approx(
        130853.0, abs=1.0
    )


def test_food_share_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    """Figure 2: food share 53% (NLSS-IV)."""
    assert _value_for(nlss4_rows, "nlss-food-share-consumption") == pytest.approx(
        53.0, abs=1e-4
    )


def test_nonfood_share_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    """Figure 2: non-food share 47% (NLSS-IV). Pair must sum to 100."""
    food = _value_for(nlss4_rows, "nlss-food-share-consumption")
    nonfood = _value_for(nlss4_rows, "nlss-non-food-share-consumption")
    assert nonfood == pytest.approx(47.0, abs=1e-4)
    assert food + nonfood == pytest.approx(100.0, abs=1e-3)


# ── NLSS-III comparison values ────────────────────────────────────────────────


def test_national_headcount_nlss3(nlss3_rows: list[StagingRowDraft]) -> None:
    """Table A1: Nepal headcount 25.16% (NLSS-III 2010/11)."""
    assert _value_for(nlss3_rows, "nlss-poverty-headcount-national") == pytest.approx(
        25.16, abs=1e-4
    )


def test_urban_headcount_nlss3(nlss3_rows: list[StagingRowDraft]) -> None:
    """Table A1: Urban headcount 15.46% (NLSS-III)."""
    assert _value_for(nlss3_rows, "nlss-poverty-headcount-urban") == pytest.approx(
        15.46, abs=1e-4
    )


def test_rural_headcount_nlss3(nlss3_rows: list[StagingRowDraft]) -> None:
    """Table A1: Rural headcount 27.43% (NLSS-III)."""
    assert _value_for(nlss3_rows, "nlss-poverty-headcount-rural") == pytest.approx(
        27.43, abs=1e-4
    )


def test_gini_nlss3_divided_by_100(nlss3_rows: list[StagingRowDraft]) -> None:
    """Table A4: Gini 32.8 on 0–100 scale → stored as 0.328 on 0–1 scale."""
    val = _value_for(nlss3_rows, "nlss-gini-consumption")
    assert val == pytest.approx(0.328, abs=1e-4)
    assert val < 1.0, f"NLSS-III Gini stored on wrong scale: {val}"


def test_food_share_nlss3(nlss3_rows: list[StagingRowDraft]) -> None:
    """Figure 2: food share 62% (NLSS-III comparable)."""
    assert _value_for(nlss3_rows, "nlss-food-share-consumption") == pytest.approx(
        62.0, abs=1e-4
    )


def test_nonfood_share_nlss3(nlss3_rows: list[StagingRowDraft]) -> None:
    """Figure 2: non-food share 38% (NLSS-III comparable). Pair sums to 100."""
    food = _value_for(nlss3_rows, "nlss-food-share-consumption")
    nonfood = _value_for(nlss3_rows, "nlss-non-food-share-consumption")
    assert nonfood == pytest.approx(38.0, abs=1e-4)
    assert food + nonfood == pytest.approx(100.0, abs=1e-3)


# ── Unit checks ───────────────────────────────────────────────────────────────


def test_units_nlss4(nlss4_rows: list[StagingRowDraft]) -> None:
    assert _unit_for(nlss4_rows, "nlss-per-capita-consumption-annual") == "npr"
    assert _unit_for(nlss4_rows, "nlss-gini-consumption") == "ratio"
    for slug in (
        "nlss-poverty-headcount-national",
        "nlss-poverty-headcount-urban",
        "nlss-poverty-headcount-rural",
        "nlss-poverty-headcount-koshi",
        "nlss-poverty-headcount-madhesh",
        "nlss-poverty-headcount-bagmati",
        "nlss-poverty-headcount-gandaki",
        "nlss-poverty-headcount-lumbini",
        "nlss-poverty-headcount-karnali",
        "nlss-poverty-headcount-sudurpaschim",
        "nlss-food-share-consumption",
        "nlss-non-food-share-consumption",
    ):
        assert _unit_for(nlss4_rows, slug) == "percent", slug


def test_units_nlss3(nlss3_rows: list[StagingRowDraft]) -> None:
    assert _unit_for(nlss3_rows, "nlss-gini-consumption") == "ratio"
    for slug in (
        "nlss-poverty-headcount-national",
        "nlss-poverty-headcount-urban",
        "nlss-poverty-headcount-rural",
        "nlss-food-share-consumption",
        "nlss-non-food-share-consumption",
    ):
        assert _unit_for(nlss3_rows, slug) == "percent", slug


# ── Error path: missing file ──────────────────────────────────────────────────


def test_missing_file_returns_failure() -> None:
    r = parse("/nonexistent/path/report.pdf", "test-id")
    assert r.status == "failure"
    assert r.staging_rows == []
    assert any("not found" in (e.error_detail or "") for e in r.errors)


# ── CLI entrypoint (_main) ────────────────────────────────────────────────────


def test_cli_emits_valid_json() -> None:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    proc = subprocess.run(
        [sys.executable, "-m", "nso_nlss.parser", str(FIXTURE), "test-cli-doc"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,  # scrapers/ root
    )
    assert proc.returncode == 0, f"CLI exited {proc.returncode}: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] in ("success", "partial")
    assert payload["parser_version"] == "0.1.0"
    assert len(payload["staging_rows"]) == 20
    # Datetime fields must be ISO strings, not raw datetime objects.
    row = payload["staging_rows"][0]
    assert isinstance(row["reporting_period_ad_start"], str), (
        "datetime fields must be ISO strings in CLI output"
    )


def test_cli_usage_error() -> None:
    """CLI exits 2 on wrong number of arguments."""
    proc = subprocess.run(
        [sys.executable, "-m", "nso_nlss.parser"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    assert proc.returncode == 2
