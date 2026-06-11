"""Tests for the NRB Financial Stability Report PDF parser (v0.1.0).

Integration fixture: ``financial-stability-report-fy2023-24.pdf`` — Issue 16,
FY 2023/24. Contains Table 2.3 "Financial Soundness Indicators of BFIs" with
Overall column values at mid-July 2023 and mid-July 2024.

Known values (FY2023/24, mid-July 2024, Overall column):
    NPL / Total loan ratio     : 3.86 %
    Tier 1 & Tier 2 Capital /RWE: 12.92 %
    CD Ratio                    : 79.09 %
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nrb_financial_stability_report import PARSER_VERSION, parse

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "financial-stability-report-fy2023-24.pdf"
)

TARGET_SLUGS: frozenset[str] = frozenset({
    "nrb-fsr-npl-ratio-annual",
    "nrb-fsr-capital-adequacy-annual",
    "nrb-fsr-credit-deposit-ratio-annual",
})

# Tolerance for date comparisons (mid-month approximations).
PERIOD_TOLERANCE = timedelta(days=2)


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    return parse(str(FIXTURE), source_document_id="test-doc-id")


# ── Version + status ─────────────────────────────────────────────────────────


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", (
        f"unexpected status={result.status!r} errors={result.errors}"
    )


# ── Row count + slugs ─────────────────────────────────────────────────────────


def test_row_count(result: ParserResult) -> None:
    assert len(result.staging_rows) >= len(TARGET_SLUGS)


def test_all_target_slugs_present(result: ParserResult) -> None:
    found = {row.indicator_slug_raw for row in result.staging_rows}
    missing = TARGET_SLUGS - found
    assert not missing, f"missing indicator slugs: {missing}"


# ── Required fields ───────────────────────────────────────────────────────────


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw in TARGET_SLUGS
        assert row.unit == "percent"
        assert row.reporting_period_type == "annual"
        assert row.reporting_period_bs
        assert row.fiscal_year_bs == "2080/81"
        assert row.fiscal_year_ad_label == "2023/24"
        assert row.confidence_grade_proposed == "A"
        assert isinstance(row.value, float) and row.value > 0
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


# ── Specific known values ─────────────────────────────────────────────────────


def _value_for(result: ParserResult, slug: str) -> float:
    matches = [r for r in result.staging_rows if r.indicator_slug_raw == slug]
    assert len(matches) == 1, f"expected exactly one {slug!r}, got {len(matches)}"
    return matches[0].value


def test_npl_ratio_value(result: ParserResult) -> None:
    """Table 2.3 Overall NPL/Total loan mid-July 2024 = 3.86%."""
    assert _value_for(result, "nrb-fsr-npl-ratio-annual") == pytest.approx(3.86, abs=1e-6)


def test_capital_adequacy_value(result: ParserResult) -> None:
    """Table 2.3 Overall Tier 1 & Tier 2 Capital/RWE mid-July 2024 = 12.92%."""
    assert _value_for(result, "nrb-fsr-capital-adequacy-annual") == pytest.approx(
        12.92, abs=1e-6
    )


def test_cd_ratio_value(result: ParserResult) -> None:
    """Table 2.3 Overall CD Ratio mid-July 2024 = 79.09%."""
    assert _value_for(result, "nrb-fsr-credit-deposit-ratio-annual") == pytest.approx(
        79.09, abs=1e-6
    )


# ── Reporting period ──────────────────────────────────────────────────────────


def test_reporting_period_ad_annual_span(result: ParserResult) -> None:
    """FY 2023/24 → Shrawan 2080 (mid-July 2023) to Ashadh 2080 (mid-June 2024)."""
    # BS FY 2080/81: Shrawan 2080 starts ~mid-July 2023 (AD).
    expected_start = datetime(2023, 7, 15, tzinfo=UTC)
    # Ashadh 2080 ends ~mid-June 2024 (AD).
    expected_end = datetime(2024, 6, 15, tzinfo=UTC)
    for row in result.staging_rows:
        assert abs(row.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE, (
            f"{row.indicator_slug_raw}: start {row.reporting_period_ad_start} "
            f"not within {PERIOD_TOLERANCE} of {expected_start}"
        )
        assert abs(row.reporting_period_ad_end - expected_end) <= PERIOD_TOLERANCE, (
            f"{row.indicator_slug_raw}: end {row.reporting_period_ad_end} "
            f"not within {PERIOD_TOLERANCE} of {expected_end}"
        )


# ── Error handling ────────────────────────────────────────────────────────────


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-file.pdf", source_document_id="x")
    assert res.status == "failure"
    assert res.errors
    assert res.errors[0].error_class == "Other"


# ── Idempotency ───────────────────────────────────────────────────────────────


def test_idempotent() -> None:
    first = parse(str(FIXTURE), source_document_id="x")
    second = parse(str(FIXTURE), source_document_id="x")
    assert first.status == second.status
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


# ── CLI JSON output ───────────────────────────────────────────────────────────


def test_cli_emits_valid_json() -> None:
    """The __main__ block must produce valid JSON with ISO 8601 datetimes."""
    repo_root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "nrb_financial_stability_report.parser",
            str(FIXTURE),
            "test-doc-id",
        ],
        cwd=repo_root / "scrapers",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] == "success"
    assert payload["parser_version"] == PARSER_VERSION
    assert len(payload["staging_rows"]) >= len(TARGET_SLUGS)
    for row in payload["staging_rows"]:
        assert "T" in row["reporting_period_ad_start"]
        assert "T" in row["reporting_period_ad_end"]
        assert "T" in row["publication_date_ad"]


# ── Pattern unit tests (no PDF required) ─────────────────────────────────────


def test_npl_row_pattern_matches_table_text() -> None:
    """NPL row pattern extracts correct value from raw table text."""
    from nrb_financial_stability_report.parser import (
        _NPL_ROW_RE,
        _extract_last_two_floats,
    )
    sample = "NPL/ Total loan 2.98 3.76 2.49 3.62 7.60 9.87 3.02 3.86\n"
    m = _NPL_ROW_RE.search(sample)
    assert m is not None
    pair = _extract_last_two_floats(m.group(1))
    assert pair is not None
    prev, current = pair
    assert prev == pytest.approx(3.02, abs=1e-6)
    assert current == pytest.approx(3.86, abs=1e-6)


def test_capital_row_pattern_matches_table_text() -> None:
    """Capital adequacy row pattern extracts correct value."""
    from nrb_financial_stability_report.parser import (
        _CAPITAL_ROW_RE,
        _extract_last_two_floats,
    )
    sample = "Tier 1 & Tier 2 Capital /RWE 13.37 12.84 13.21 13.38 17.01 14.89 13.42 12.92\n"
    m = _CAPITAL_ROW_RE.search(sample)
    assert m is not None
    pair = _extract_last_two_floats(m.group(1))
    assert pair is not None
    prev, current = pair
    assert prev == pytest.approx(13.42, abs=1e-6)
    assert current == pytest.approx(12.92, abs=1e-6)


def test_cd_ratio_row_pattern_matches_table_text() -> None:
    """CD Ratio row pattern extracts correct value."""
    from nrb_financial_stability_report.parser import (
        _CD_RATIO_ROW_RE,
        _extract_last_two_floats,
    )
    sample = "CD Ratio 81.62 78.79 81.80 82.64 81.02 76.42 81.63 79.09\n"
    m = _CD_RATIO_ROW_RE.search(sample)
    assert m is not None
    pair = _extract_last_two_floats(m.group(1))
    assert pair is not None
    prev, current = pair
    assert prev == pytest.approx(81.63, abs=1e-6)
    assert current == pytest.approx(79.09, abs=1e-6)


def test_fy_title_detection_four_digit_end() -> None:
    """Parser handles 4-digit year end: 'Fiscal year 2023/2024'."""
    from nrb_financial_stability_report.parser import _FY_TITLE_RE

    m = _FY_TITLE_RE.search("Financial Stability Report\nFiscal year 2023/2024\nIssue 16")
    assert m is not None
    assert int(m.group(1)) == 2023
    assert m.group(2) in ("2024", "24")


def test_fy_title_detection_two_digit_end() -> None:
    """Parser handles 2-digit year end: 'Fiscal Year 2023/24'."""
    from nrb_financial_stability_report.parser import _FY_TITLE_RE

    m = _FY_TITLE_RE.search("Fiscal Year 2023/24")
    assert m is not None
    assert int(m.group(1)) == 2023
