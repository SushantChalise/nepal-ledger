"""Tests for the NRB Financial Sector XLSX parser (v0.1.0).

Integration fixtures: four XLSX files from the NRB Financial Sector page.
All 8 target slugs must be present and the latest data values verified
against the scout findings.

Scout-verified values (December 2025 / end-of-Poush 2082):
  nrb-finsec-loans-realestate-monthly       → 195685.94  (Rs. in million)
  nrb-finsec-loans-agriculture-monthly      → 408716.73  (Rs. in million)
  nrb-finsec-loans-manufacturing-monthly    → 906361.15  (Rs. in million)
  nrb-finsec-m1-level-monthly               → 1129375.92 (Rs. in million)
  nrb-finsec-m2-level-monthly               → 8134381.26 (Rs. in million)
  nrb-finsec-deposit-rate-monthly           → 3.6612     (percent per annum)
  nrb-finsec-lending-rate-monthly           → 7.2617     (percent per annum)
  nrb-finsec-nepse-index-monthly (2025/26 Dec) → 2601.616 (index points)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nrb_db_financial_sector import PARSER_VERSION, parse

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

TARGET_SLUGS: frozenset[str] = frozenset({
    "nrb-finsec-loans-realestate-monthly",
    "nrb-finsec-loans-agriculture-monthly",
    "nrb-finsec-loans-manufacturing-monthly",
    "nrb-finsec-nepse-index-monthly",
    "nrb-finsec-m2-level-monthly",
    "nrb-finsec-m1-level-monthly",
    "nrb-finsec-lending-rate-monthly",
    "nrb-finsec-deposit-rate-monthly",
})


@pytest.fixture(scope="module")
def result() -> ParserResult:
    assert FIXTURE_DIR.exists(), f"fixture directory missing: {FIXTURE_DIR}"
    return parse(str(FIXTURE_DIR), "test-doc-id")


# ── Core status tests ─────────────────────────────────────────────────────────


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", (
        f"unexpected status={result.status!r}; errors={result.errors}"
    )


def test_row_count(result: ParserResult) -> None:
    # Each slug should have multiple historical rows.
    assert len(result.staging_rows) >= len(TARGET_SLUGS)


def test_all_target_slugs_present(result: ParserResult) -> None:
    found = {row.indicator_slug_raw for row in result.staging_rows}
    missing = TARGET_SLUGS - found
    assert not missing, f"missing target slugs: {missing}"


# ── Field completeness ────────────────────────────────────────────────────────


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw in TARGET_SLUGS, (
            f"unexpected slug: {row.indicator_slug_raw!r}"
        )
        assert row.unit, f"empty unit on {row.indicator_slug_raw}"
        assert row.reporting_period_type == "monthly"
        assert row.reporting_period_bs, f"empty reporting_period_bs on {row.indicator_slug_raw}"
        assert row.fiscal_year_bs, f"empty fiscal_year_bs on {row.indicator_slug_raw}"
        assert row.fiscal_year_ad_label, f"empty fiscal_year_ad_label on {row.indicator_slug_raw}"
        assert row.confidence_grade_proposed in ("A", "B", "C")
        assert isinstance(row.value, float)
        assert row.reporting_period_ad_start is not None
        assert row.reporting_period_ad_end is not None
        assert row.publication_date_ad is not None
        assert row.publication_date_bs
        # Point-in-time: start == end for monthly
        assert row.reporting_period_ad_start == row.reporting_period_ad_end


# ── Confidence grade ─────────────────────────────────────────────────────────


def test_confidence_grade_a(result: ParserResult) -> None:
    """NRB direct XLSX → confidence A for all rows."""
    for row in result.staging_rows:
        assert row.confidence_grade_proposed == "A", (
            f"{row.indicator_slug_raw} unexpectedly not A: {row.parser_notes!r}"
        )


# ── Latest-value spot checks ──────────────────────────────────────────────────


def _rows_for(result: ParserResult, slug: str) -> list[StagingRowDraft]:
    return [r for r in result.staging_rows if r.indicator_slug_raw == slug]


def _latest(result: ParserResult, slug: str) -> StagingRowDraft:
    rows = _rows_for(result, slug)
    assert rows, f"no rows for {slug!r}"
    return max(rows, key=lambda r: r.reporting_period_ad_end)


def test_loans_agriculture_latest_value(result: ParserResult) -> None:
    """Dec 2025 agriculture loans = 408716.73 Rs. million (scout verified)."""
    row = _latest(result, "nrb-finsec-loans-agriculture-monthly")
    assert row.value == pytest.approx(408716.73, rel=1e-3)
    assert row.unit == "npr_million"


def test_loans_manufacturing_latest_value(result: ParserResult) -> None:
    """Dec 2025 productions (manufacturing) loans = 906361.15 Rs. million."""
    row = _latest(result, "nrb-finsec-loans-manufacturing-monthly")
    assert row.value == pytest.approx(906361.15, rel=1e-3)
    assert row.unit == "npr_million"


def test_loans_realestate_latest_value(result: ParserResult) -> None:
    """Dec 2025 real estate loans = 195685.94 Rs. million."""
    row = _latest(result, "nrb-finsec-loans-realestate-monthly")
    assert row.value == pytest.approx(195685.94, rel=1e-3)
    assert row.unit == "npr_million"


def test_m1_latest_value(result: ParserResult) -> None:
    """Mid-Dec 2025 M1 = 1129375.92 Rs. million."""
    row = _latest(result, "nrb-finsec-m1-level-monthly")
    assert row.value == pytest.approx(1129375.92, rel=1e-3)
    assert row.unit == "npr_million"


def test_m2_latest_value(result: ParserResult) -> None:
    """Mid-Dec 2025 M2 = 8134381.26 Rs. million."""
    row = _latest(result, "nrb-finsec-m2-level-monthly")
    assert row.value == pytest.approx(8134381.26, rel=1e-3)
    assert row.unit == "npr_million"


def test_deposit_rate_latest_value(result: ParserResult) -> None:
    """Dec 2025 weighted avg deposit rate = 3.6612% p.a."""
    row = _latest(result, "nrb-finsec-deposit-rate-monthly")
    assert row.value == pytest.approx(3.6612, rel=1e-3)
    assert row.unit == "percent_per_annum"


def test_lending_rate_latest_value(result: ParserResult) -> None:
    """Dec 2025 weighted avg lending rate = 7.2617% p.a."""
    row = _latest(result, "nrb-finsec-lending-rate-monthly")
    assert row.value == pytest.approx(7.2617, rel=1e-3)
    assert row.unit == "percent_per_annum"


def test_nepse_dec_2025_26_value(result: ParserResult) -> None:
    """NEPSE Dec 2025/26 (Mangsir 2082) = 2601.616 index points (scout verified)."""
    nepse_rows = _rows_for(result, "nrb-finsec-nepse-index-monthly")
    # Dec column in FY 2025/26 → BS Mangsir 2082
    mangsir_rows = [r for r in nepse_rows if "Mangsir" in r.reporting_period_bs and "2082/83" in r.fiscal_year_bs]
    assert mangsir_rows, "expected Mangsir 2082 NEPSE row not found"
    row = mangsir_rows[0]
    assert row.value == pytest.approx(2601.616, rel=1e-3)
    assert row.unit == "index_points"


# ── Date sanity ───────────────────────────────────────────────────────────────


def test_loans_latest_period_bs(result: ParserResult) -> None:
    """Dec 2025 maps to BS Poush 2082 (FY 2082/83)."""
    row = _latest(result, "nrb-finsec-loans-agriculture-monthly")
    assert "Poush" in row.reporting_period_bs
    assert "2082" in row.reporting_period_bs
    assert row.fiscal_year_bs == "2082/83"
    assert row.fiscal_year_ad_label == "2025/26"


def test_monetary_latest_period_bs(result: ParserResult) -> None:
    """Mid-Dec 2025 maps to BS Poush 2082."""
    row = _latest(result, "nrb-finsec-m2-level-monthly")
    assert "Poush" in row.reporting_period_bs
    assert row.fiscal_year_bs == "2082/83"


def test_nepse_dec_period_bs(result: ParserResult) -> None:
    """NEPSE Dec col for FY 2025/26 → BS Mangsir 2082/83."""
    nepse_rows = _rows_for(result, "nrb-finsec-nepse-index-monthly")
    mangsir_rows = [r for r in nepse_rows if "Mangsir" in r.reporting_period_bs and "2082/83" in r.fiscal_year_bs]
    assert mangsir_rows, "expected Mangsir 2082 NEPSE row not found"
    row = mangsir_rows[0]
    assert "Mangsir" in row.reporting_period_bs
    assert row.fiscal_year_bs == "2082/83"
    assert row.fiscal_year_ad_label == "2025/26"


# ── Historical coverage ───────────────────────────────────────────────────────


def test_loans_multi_year_coverage(result: ParserResult) -> None:
    """Agriculture loans should span many years (data starts 2009)."""
    agri_rows = _rows_for(result, "nrb-finsec-loans-agriculture-monthly")
    fy_labels = {r.fiscal_year_bs for r in agri_rows}
    assert len(fy_labels) >= 10, f"expected ≥10 fiscal years, got {len(fy_labels)}"


def test_nepse_multi_year_coverage(result: ParserResult) -> None:
    """NEPSE should span many fiscal years."""
    nepse_rows = _rows_for(result, "nrb-finsec-nepse-index-monthly")
    fy_labels = {r.fiscal_year_bs for r in nepse_rows}
    assert len(fy_labels) >= 10, f"expected ≥10 fiscal years, got {len(fy_labels)}"


# ── Idempotency ───────────────────────────────────────────────────────────────


def test_idempotent() -> None:
    first = parse(str(FIXTURE_DIR), "x")
    second = parse(str(FIXTURE_DIR), "x")
    assert first.status == second.status
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


# ── Missing file ──────────────────────────────────────────────────────────────


def test_missing_path_returns_failure() -> None:
    res = parse("nonexistent/path/does/not/exist", "x")
    assert res.status == "failure"
    assert res.errors
    assert any("not found" in e.error_detail for e in res.errors)


# ── CLI JSON output ───────────────────────────────────────────────────────────


def test_cli_emits_valid_json() -> None:
    """The __main__ block must produce valid JSON parseable by the TS Zod schema."""
    repo_root = Path(__file__).resolve().parents[3]
    proc = subprocess.run(
        [sys.executable, "-m", "nrb_db_financial_sector.parser", str(FIXTURE_DIR), "test-doc-id"],
        cwd=repo_root / "scrapers",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] in ("success", "partial")
    assert payload["parser_version"] == PARSER_VERSION
    assert len(payload["staging_rows"]) >= len(TARGET_SLUGS)
    for row in payload["staging_rows"]:
        assert "T" in row["reporting_period_ad_start"]
        assert "T" in row["reporting_period_ad_end"]
        assert "T" in row["publication_date_ad"]
