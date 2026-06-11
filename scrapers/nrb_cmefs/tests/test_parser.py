"""Tests for the NRB CMEFs English-edition PDF parser (v0.2.0).

Integration fixture: ``cmefs_nine_months_excerpt.pdf`` — first 6 pages of
NRB's "Current Macroeconomic and Financial Situation of Nepal based on Nine
Months of 2025/26". Exercises every headline pattern and the period-detection
path. Extended v0.2.0 indicators are tested against embedded prose strings
(no PDF required — their narrative paragraphs are outside the 6-page excerpt).
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
from nrb_cmefs.parser import _detect_period, _INDICATORS

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cmefs_nine_months_excerpt.pdf"
PERIOD_TOLERANCE = timedelta(days=2)

# The 7 headline indicators are expected in every NRB CMEFs edition.
HEADLINE_SLUGS: frozenset[str] = frozenset({
    "cmefs-ncpi-yoy-overall",
    "cmefs-remittance-inflow-ytd",
    "cmefs-merchandise-imports-ytd",
    "cmefs-trade-deficit-ytd",
    "cmefs-bop-surplus-ytd",
    "cmefs-gross-forex-reserves",
    "cmefs-forex-reserves-months-of-import-cover",
})

# Backward-compat alias used in some assertions below.
EXPECTED_SLUGS = HEADLINE_SLUGS


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    return parse(str(FIXTURE), source_document_id="test-doc-id")


# ── Integration tests against the 6-page excerpt ────────────────────────────


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.2.0"


def test_status_success_or_partial(result: ParserResult) -> None:
    """Headline indicators must be extracted; extended patterns are best-effort.

    The 6-page excerpt covers the executive summary only. Extended v0.2.0
    patterns (government finance, monetary) are in the body beyond page 6
    and may miss — producing partial status. That is not a failure.
    """
    assert result.status in ("success", "partial"), (
        f"unexpected status={result.status!r} errors={result.errors}"
    )


def test_all_headline_indicators_present(result: ParserResult) -> None:
    found = {row.indicator_slug_raw for row in result.staging_rows}
    missing = HEADLINE_SLUGS - found
    assert not missing, f"missing headline indicators: {missing}"


def test_row_count_at_least_headlines(result: ParserResult) -> None:
    assert len(result.staging_rows) >= len(HEADLINE_SLUGS)


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw.startswith("cmefs-")
        assert row.unit
        assert row.reporting_period_type in (
            "monthly", "nine_months_cumulative", "year_to_date"
        )
        assert row.reporting_period_bs
        assert row.fiscal_year_bs == "2082/83"
        assert row.fiscal_year_ad_label == "2025/26"
        assert row.confidence_grade_proposed in ("A", "B")
        assert isinstance(row.value, float) and row.value > 0
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


def test_missed_patterns_emit_page_layout_changed(result: ParserResult) -> None:
    """Any missed pattern must emit PageLayoutChanged — never a phantom value."""
    for err in result.errors:
        assert err.error_class == "PageLayoutChanged", (
            f"unexpected error class {err.error_class!r}: {err.error_detail}"
        )


def _value_for(result: ParserResult, slug: str) -> float:
    matches = [r for r in result.staging_rows if r.indicator_slug_raw == slug]
    assert len(matches) == 1, f"expected exactly one {slug!r}, got {len(matches)}"
    return matches[0].value


def test_ncpi_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-ncpi-yoy-overall") == pytest.approx(4.47, abs=1e-6)


def test_remittance_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-remittance-inflow-ytd") == pytest.approx(1659.41, abs=1e-6)


def test_imports_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-merchandise-imports-ytd") == pytest.approx(1490.50, abs=1e-6)


def test_trade_deficit_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-trade-deficit-ytd") == pytest.approx(1267.56, abs=1e-6)


def test_bop_surplus_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-bop-surplus-ytd") == pytest.approx(731.16, abs=1e-6)


def test_gross_forex_reserves_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-gross-forex-reserves") == pytest.approx(3494.73, abs=1e-6)


def test_months_of_import_cover_value(result: ParserResult) -> None:
    assert _value_for(result, "cmefs-forex-reserves-months-of-import-cover") == pytest.approx(
        18.4, abs=1e-6
    )


def test_units_per_headline_indicator(result: ParserResult) -> None:
    by_slug = {row.indicator_slug_raw: row.unit for row in result.staging_rows}
    assert by_slug["cmefs-ncpi-yoy-overall"] == "percent_yoy"
    assert by_slug["cmefs-remittance-inflow-ytd"] == "npr_billion"
    assert by_slug["cmefs-merchandise-imports-ytd"] == "npr_billion"
    assert by_slug["cmefs-trade-deficit-ytd"] == "npr_billion"
    assert by_slug["cmefs-bop-surplus-ytd"] == "npr_billion"
    assert by_slug["cmefs-gross-forex-reserves"] == "npr_billion"
    assert by_slug["cmefs-forex-reserves-months-of-import-cover"] == "months"


def test_end_of_period_indicators_anchored_to_chait_mid(result: ParserResult) -> None:
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
            assert abs(row.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
            assert abs(row.reporting_period_ad_end - expected_end) <= PERIOD_TOLERANCE


def test_default_confidence_grade_a(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert row.confidence_grade_proposed == "A", (
            f"{row.indicator_slug_raw} unexpectedly downgraded: {row.parser_notes}"
        )


def test_idempotent() -> None:
    first = parse(str(FIXTURE), source_document_id="x")
    second = parse(str(FIXTURE), source_document_id="x")
    assert first.status == second.status
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-file.pdf", source_document_id="x")
    assert res.status == "failure"
    assert res.errors


def test_cli_emits_valid_json() -> None:
    """The ``__main__`` block must produce JSON the TS-side Zod schema can parse."""
    repo_root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [sys.executable, "-m", "nrb_cmefs.parser", str(FIXTURE), "test-doc-id"],
        cwd=repo_root / "scrapers",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] in ("success", "partial")
    assert payload["parser_version"] == PARSER_VERSION
    assert len(payload["staging_rows"]) >= len(HEADLINE_SLUGS)
    for row in payload["staging_rows"]:
        assert "T" in row["reporting_period_ad_start"]
        assert "T" in row["reporting_period_ad_end"]
        assert "T" in row["publication_date_ad"]


# ── Period detection unit tests (no PDF required) ────────────────────────────


def test_detect_period_nine_months() -> None:
    """N-months title → nine_months_cumulative for BS 2082 (AD 2025/26)."""
    errors: list = []
    text = (
        "Current Macroeconomic and Financial Situation of Nepal "
        "based on Nine Months of 2025/26"
    )
    info = _detect_period(text, errors)
    assert errors == []
    assert info is not None
    assert info.bs_fy_start == 2082
    assert info.num_months == 9
    assert info.end_bs_month == "Chait"
    assert info.end_bs_year == 2082
    assert info.reporting_period_type == "nine_months_cumulative"
    assert info.reporting_period_bs == "FY 2082/83 9M"
    assert info.fiscal_year_bs == "2082/83"
    assert info.fiscal_year_ad_label == "2025/26"


def test_detect_period_monthly_magh() -> None:
    """Monthly title → monthly period for Magh 2082 (FY 2082/83, month 7)."""
    errors: list = []
    text = "based on Magh 2082"
    info = _detect_period(text, errors)
    assert errors == []
    assert info is not None
    assert info.bs_fy_start == 2082
    assert info.num_months == 7
    assert info.end_bs_month == "Magh"
    assert info.end_bs_year == 2082
    assert info.reporting_period_type == "monthly"
    assert info.reporting_period_bs == "2082/83 Magh"


def test_detect_period_baisakh_crosses_fy_year() -> None:
    """Months 10–12 (Baisakh–Ashadh) belong to FY start year - 1."""
    errors: list = []
    text = "based on Baisakh 2083"
    info = _detect_period(text, errors)
    assert errors == []
    assert info is not None
    assert info.bs_fy_start == 2082  # FY 2082/83, Baisakh falls in year 2083
    assert info.end_bs_year == 2083
    assert info.reporting_period_type == "monthly"


def test_detect_period_ten_months_ytd() -> None:
    """10-month cumulative → year_to_date."""
    errors: list = []
    text = "based on Ten Months of 2025/26"
    info = _detect_period(text, errors)
    assert errors == []
    assert info is not None
    assert info.num_months == 10
    assert info.end_bs_month == "Baisakh"
    assert info.end_bs_year == 2083
    assert info.reporting_period_type == "year_to_date"
    assert info.reporting_period_bs == "FY 2082/83 10M"


def test_detect_period_unknown_title_appends_error() -> None:
    errors: list = []
    info = _detect_period("Nepal Rastra Bank Annual Report 2082", errors)
    assert info is None
    assert len(errors) == 1
    assert errors[0].error_class == "PeriodAmbiguous"


# ── Extended indicator pattern unit tests (no PDF) ───────────────────────────
# Verify each v0.2.0 pattern compiles and matches representative NRB prose.


def _pattern_for(slug: str) -> "re.Pattern[str]":
    import re
    spec = next((s for s in _INDICATORS if s.slug == slug), None)
    assert spec is not None, f"no spec for {slug!r}"
    return spec.pattern


def test_exports_pattern_matches() -> None:
    p = _pattern_for("cmefs-merchandise-exports-ytd")
    m = p.search("Merchandise exports increased 15.3 percent to Rs.222.94 billion")
    assert m is not None
    assert float(m.group(1)) == pytest.approx(222.94, abs=1e-6)


def test_govt_revenue_pattern_matches() -> None:
    p = _pattern_for("cmefs-govt-revenue-total-ytd")
    m = p.search("Total government revenue increased 12.5 percent to Rs.987.65 billion")
    assert m is not None
    assert float(m.group(1)) == pytest.approx(987.65, abs=1e-6)


def test_govt_revenue_pattern_matches_without_government() -> None:
    p = _pattern_for("cmefs-govt-revenue-total-ytd")
    m = p.search("Total revenue decreased 3.2 percent to Rs.845.10 billion")
    assert m is not None


def test_govt_expenditure_pattern_matches() -> None:
    p = _pattern_for("cmefs-govt-expenditure-total-ytd")
    m = p.search("Total government expenditure increased 8.7 percent to Rs.1123.45 billion")
    assert m is not None
    assert float(m.group(1)) == pytest.approx(1123.45, abs=1e-6)


def test_fiscal_balance_deficit_pattern_matches() -> None:
    p = _pattern_for("cmefs-govt-fiscal-balance-ytd")
    m = p.search("Fiscal deficit remained at Rs.135.72 billion in nine months")
    assert m is not None
    assert "deficit" in m.group(0).lower()
    assert float(m.group(1)) == pytest.approx(135.72, abs=1e-6)


def test_fiscal_balance_surplus_pattern_matches() -> None:
    p = _pattern_for("cmefs-govt-fiscal-balance-ytd")
    m = p.search("Fiscal surplus of Rs.24.80 billion was recorded")
    assert m is not None
    assert "surplus" in m.group(0).lower()


def test_m2_yoy_pattern_matches() -> None:
    p = _pattern_for("cmefs-m2-yoy")
    m = p.search("Broad money (M2) increased 13.2 percent")
    assert m is not None
    assert float(m.group(1)) == pytest.approx(13.2, abs=1e-6)


def test_m2_yoy_pattern_without_parentheses() -> None:
    p = _pattern_for("cmefs-m2-yoy")
    m = p.search("Broad money M2 decreased 2.1 percent on a year-on-year basis")
    assert m is not None


def test_private_sector_credit_pattern_matches() -> None:
    p = _pattern_for("cmefs-private-sector-credit-yoy")
    m = p.search("Private sector credit increased 9.8 percent")
    assert m is not None
    assert float(m.group(1)) == pytest.approx(9.8, abs=1e-6)


def test_bfi_deposits_pattern_matches() -> None:
    p = _pattern_for("cmefs-bfi-deposits-yoy")
    m = p.search("Deposits of BFIs increased 11.4 percent on year-on-year basis")
    assert m is not None
    assert float(m.group(1)) == pytest.approx(11.4, abs=1e-6)


def test_bfi_deposits_pattern_matches_singular() -> None:
    p = _pattern_for("cmefs-bfi-deposits-yoy")
    m = p.search("Deposit of BFI increased 8.5 percent")
    assert m is not None


def test_exports_pattern_accepts_nrb_typo() -> None:
    """Accept both spellings — NRB's own typo 'mercandise' is documented."""
    p = _pattern_for("cmefs-merchandise-exports-ytd")
    m = p.search("mercandise exports increased 10.0 percent to Rs.100.00 billion")
    assert m is not None
