"""Tests for the NRB CMEFs English-edition PDF parser.

Fixture: ``cmefs_nine_months_excerpt.pdf`` — first 6 pages of NRB's
"Current Macroeconomic and Financial Situation of Nepal based on Nine
Months of 2025/26", trimmed from the in-repo original PDF
``Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf`` (Mother
copies the canonical source into Supabase Storage; the test fixture is
the trimmed excerpt that exercises every headline pattern). No network
access.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nrb_cmefs import PARSER_VERSION, parse

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cmefs_nine_months_excerpt.pdf"
PERIOD_TOLERANCE = timedelta(days=2)

EXPECTED_SLUGS: frozenset[str] = frozenset(
    {
        "cmefs-ncpi-yoy-overall",
        "cmefs-remittance-inflow-ytd",
        "cmefs-merchandise-imports-ytd",
        "cmefs-trade-deficit-ytd",
        "cmefs-bop-surplus-ytd",
        "cmefs-gross-forex-reserves",
        "cmefs-forex-reserves-months-of-import-cover",
    }
)


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    return parse(str(FIXTURE), source_document_id="test-doc-id")


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", (
        f"got status={result.status} errors={result.errors}"
    )


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_all_seven_indicators_present(result: ParserResult) -> None:
    slugs = {row.indicator_slug_raw for row in result.staging_rows}
    assert slugs == EXPECTED_SLUGS, f"missing: {EXPECTED_SLUGS - slugs}"


def test_row_count(result: ParserResult) -> None:
    assert len(result.staging_rows) == len(EXPECTED_SLUGS)


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw.startswith("cmefs-")
        assert row.unit
        assert row.reporting_period_type == "nine_months_cumulative"
        assert row.reporting_period_bs == "FY 2082/83 9M"
        assert row.fiscal_year_bs == "2082/83"
        assert row.fiscal_year_ad_label == "2025/26"
        assert row.confidence_grade_proposed in ("A", "B")
        assert isinstance(row.value, float)
        assert row.value > 0
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


def _value_for(result: ParserResult, slug: str) -> float:
    matches = [r for r in result.staging_rows if r.indicator_slug_raw == slug]
    assert len(matches) == 1, f"expected exactly one {slug}, got {len(matches)}"
    return matches[0].value


def test_ncpi_value_cross_validates_ncpi_parser(result: ParserResult) -> None:
    """NCPI overall YoY at end of nine months should equal the figure
    NRB highlights in the executive narrative (4.47% for FY2082/83 9M)."""
    assert _value_for(result, "cmefs-ncpi-yoy-overall") == pytest.approx(
        4.47, abs=1e-6
    )


def test_remittance_value(result: ParserResult) -> None:
    """NRB para 23: remittance inflows Rs.1659.41 billion (nine months)."""
    assert _value_for(result, "cmefs-remittance-inflow-ytd") == pytest.approx(
        1659.41, abs=1e-6
    )


def test_imports_value(result: ParserResult) -> None:
    """NRB para 14: merchandise imports Rs.1490.50 billion (nine months)."""
    assert _value_for(result, "cmefs-merchandise-imports-ytd") == pytest.approx(
        1490.50, abs=1e-6
    )


def test_trade_deficit_value(result: ParserResult) -> None:
    """NRB para 15: total trade deficit Rs.1267.56 billion (nine months)."""
    assert _value_for(result, "cmefs-trade-deficit-ytd") == pytest.approx(
        1267.56, abs=1e-6
    )


def test_bop_surplus_value(result: ParserResult) -> None:
    """NRB para 29: BoP surplus Rs.731.16 billion (nine months)."""
    assert _value_for(result, "cmefs-bop-surplus-ytd") == pytest.approx(
        731.16, abs=1e-6
    )


def test_gross_forex_reserves_value(result: ParserResult) -> None:
    """NRB para 30: gross forex reserves Rs.3494.73 billion (mid-Chait)."""
    assert _value_for(result, "cmefs-gross-forex-reserves") == pytest.approx(
        3494.73, abs=1e-6
    )


def test_months_of_import_cover_value(result: ParserResult) -> None:
    """NRB para 32: merchandise + services imports cover of 18.4 months."""
    assert _value_for(
        result, "cmefs-forex-reserves-months-of-import-cover"
    ) == pytest.approx(18.4, abs=1e-6)


def test_units_per_indicator(result: ParserResult) -> None:
    by_slug = {row.indicator_slug_raw: row.unit for row in result.staging_rows}
    assert by_slug["cmefs-ncpi-yoy-overall"] == "percent_yoy"
    assert by_slug["cmefs-remittance-inflow-ytd"] == "npr_billion"
    assert by_slug["cmefs-merchandise-imports-ytd"] == "npr_billion"
    assert by_slug["cmefs-trade-deficit-ytd"] == "npr_billion"
    assert by_slug["cmefs-bop-surplus-ytd"] == "npr_billion"
    assert by_slug["cmefs-gross-forex-reserves"] == "npr_billion"
    assert by_slug["cmefs-forex-reserves-months-of-import-cover"] == "months"


def test_end_of_period_indicators_anchored_to_chait_mid(
    result: ParserResult,
) -> None:
    """NCPI YoY, gross forex reserves and months-of-cover all describe
    the state at end of nine months — period_start == period_end == mid-Chait."""
    end_of_period_slugs = {
        "cmefs-ncpi-yoy-overall",
        "cmefs-gross-forex-reserves",
        "cmefs-forex-reserves-months-of-import-cover",
    }
    expected = datetime(2026, 3, 15, tzinfo=UTC)
    for row in result.staging_rows:
        if row.indicator_slug_raw in end_of_period_slugs:
            assert row.reporting_period_ad_start == row.reporting_period_ad_end
            assert abs(row.reporting_period_ad_end - expected) <= PERIOD_TOLERANCE


def test_cumulative_indicators_span_nine_months(result: ParserResult) -> None:
    """Cumulative indicators (remittance, imports, deficit, BoP) span
    mid-Shrawan..mid-Chait."""
    cumulative_slugs = {
        "cmefs-remittance-inflow-ytd",
        "cmefs-merchandise-imports-ytd",
        "cmefs-trade-deficit-ytd",
        "cmefs-bop-surplus-ytd",
    }
    expected_start = datetime(2025, 7, 15, tzinfo=UTC)
    expected_end = datetime(2026, 3, 15, tzinfo=UTC)
    for row in result.staging_rows:
        if row.indicator_slug_raw in cumulative_slugs:
            assert (
                abs(row.reporting_period_ad_start - expected_start)
                <= PERIOD_TOLERANCE
            )
            assert (
                abs(row.reporting_period_ad_end - expected_end)
                <= PERIOD_TOLERANCE
            )


def test_default_confidence_grade_a(result: ParserResult) -> None:
    """No inline 'P' provisional markers in the current bulletin —
    every row should land at confidence A."""
    for row in result.staging_rows:
        assert row.confidence_grade_proposed == "A", (
            f"{row.indicator_slug_raw} unexpectedly downgraded to "
            f"{row.confidence_grade_proposed} ({row.parser_notes})"
        )


def test_no_unexpected_errors(result: ParserResult) -> None:
    assert result.errors == [], f"unexpected parser errors: {result.errors}"


def test_idempotent() -> None:
    """Per docs/DATA_PIPELINE.md §"Parser Contract": running twice on
    identical input produces identical output."""
    first = parse(str(FIXTURE), source_document_id="x")
    second = parse(str(FIXTURE), source_document_id="x")
    assert first.status == second.status
    assert first.parser_version == second.parser_version
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-file.pdf", source_document_id="x")
    assert res.status == "failure"
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_cli_emits_valid_json() -> None:
    """The ``__main__`` block must produce JSON that the TS-side Zod
    schema (``ParserOutputSchema``) can parse. We exercise the contract
    by invoking ``python -m scrapers.nrb_cmefs.parser`` and validating
    the shape of stdout.
    """
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "nrb_cmefs.parser", str(FIXTURE), "test-doc-id"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] == "success"
    assert payload["parser_version"] == PARSER_VERSION
    assert len(payload["staging_rows"]) == len(EXPECTED_SLUGS)
    for row in payload["staging_rows"]:
        # ISO 8601 datetimes
        assert "T" in row["reporting_period_ad_start"]
        assert "T" in row["reporting_period_ad_end"]
        assert "T" in row["publication_date_ad"]
