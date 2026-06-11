"""Tests for scrapers/nrb_concessional_loan/parser.py

Fixture: tests/fixtures/Interest-subsidized-loan-Chaitra-2082-Publish.xlsx
         (Chaitra BS 2082 = end of Chait 2082, within FY 2082/83)

Known values from the fixture (cross-checked from the XLSX directly):
    nrb-concession-total-outstanding       = 48462678.54783105  Rs. Hajar
    nrb-concession-agriculture-outstanding = 38306762.81149012  Rs. Hajar
    nrb-concession-sme-outstanding         = 9579170.90091093   Rs. Hajar (Women Entrepreneur proxy)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nrb_concessional_loan.parser import PARSER_VERSION, SOURCE_ID, parse
from _common.types import StagingRowDraft

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "Interest-subsidized-loan-Chaitra-2082-Publish.xlsx"
)

TARGET_SLUGS: frozenset[str] = frozenset({
    "nrb-concession-total-outstanding",
    "nrb-concession-agriculture-outstanding",
    "nrb-concession-sme-outstanding",
})


@pytest.fixture(scope="module")
def result():
    return parse(str(FIXTURE), "test-source-doc-id")


# ── Constants ─────────────────────────────────────────────────────────────────


def test_parser_version():
    assert PARSER_VERSION == "0.1.0"


def test_source_id():
    assert SOURCE_ID == "nrb-concessional-loan"


# ── Status and row count ──────────────────────────────────────────────────────


def test_status_success(result):
    assert result.status == "success", (
        f"expected 'success', got {result.status!r}; errors: {result.errors}"
    )


def test_row_count(result):
    assert len(result.staging_rows) >= len(TARGET_SLUGS), (
        f"expected at least {len(TARGET_SLUGS)} rows, got {len(result.staging_rows)}"
    )


def test_all_target_slugs_present(result):
    emitted = {row.indicator_slug_raw for row in result.staging_rows}
    missing = TARGET_SLUGS - emitted
    assert not missing, f"slugs missing from output: {missing}"


# ── Required fields populated ─────────────────────────────────────────────────


def test_required_fields_populated(result):
    for row in result.staging_rows:
        assert row.indicator_slug_raw, "indicator_slug_raw is empty"
        assert row.value is not None, "value is None"
        assert row.unit, "unit is empty"
        assert row.reporting_period_type, "reporting_period_type is empty"
        assert row.reporting_period_bs, "reporting_period_bs is empty"
        assert row.reporting_period_ad_start is not None
        assert row.reporting_period_ad_end is not None
        assert row.publication_date_ad is not None
        assert row.publication_date_bs, "publication_date_bs is empty"
        assert row.fiscal_year_bs, "fiscal_year_bs is empty"
        assert row.fiscal_year_ad_label, "fiscal_year_ad_label is empty"
        assert row.confidence_grade_proposed in ("A", "B", "C")


# ── Period metadata ───────────────────────────────────────────────────────────


def test_period_bs(result):
    """All rows should report Chaitra 2082 as their period (Chait 2082/83)."""
    for row in result.staging_rows:
        # Fixture is Chaitra 2082 → canonical BsMonth = "Chait"
        assert "Chait" in row.reporting_period_bs, (
            f"expected 'Chait' in reporting_period_bs, got {row.reporting_period_bs!r}"
        )


def test_fiscal_year_bs(result):
    for row in result.staging_rows:
        assert row.fiscal_year_bs == "2082/83", (
            f"expected fiscal_year_bs='2082/83', got {row.fiscal_year_bs!r}"
        )


def test_fiscal_year_ad_label(result):
    for row in result.staging_rows:
        assert row.fiscal_year_ad_label == "2025/26", (
            f"expected fiscal_year_ad_label='2025/26', got {row.fiscal_year_ad_label!r}"
        )


def test_reporting_period_type(result):
    for row in result.staging_rows:
        assert row.reporting_period_type == "monthly"


def test_unit(result):
    for row in result.staging_rows:
        assert row.unit == "npr_thousand"


# ── Specific known values from fixture ────────────────────────────────────────


def _get_row(result, slug: str) -> StagingRowDraft:
    rows = [r for r in result.staging_rows if r.indicator_slug_raw == slug]
    assert rows, f"no row for slug {slug!r}"
    return rows[0]


def test_total_outstanding_value(result):
    row = _get_row(result, "nrb-concession-total-outstanding")
    # Grand total from fixture row 23, col 17 = 48462678.54783105
    assert abs(row.value - 48462678.547) < 1.0, (
        f"total outstanding: expected ~48462678.547, got {row.value}"
    )


def test_agriculture_outstanding_value(result):
    row = _get_row(result, "nrb-concession-agriculture-outstanding")
    # Agriculture row (SN=1) from fixture row 11, col 17 = 38306762.81149012
    assert abs(row.value - 38306762.811) < 1.0, (
        f"agriculture outstanding: expected ~38306762.811, got {row.value}"
    )


def test_sme_outstanding_value(result):
    row = _get_row(result, "nrb-concession-sme-outstanding")
    # Women Entrepreneur (SN=4) from fixture row 16, col 17 = 9579170.90091093
    assert abs(row.value - 9579170.900) < 1.0, (
        f"SME/women-entrepreneur outstanding: expected ~9579170.900, got {row.value}"
    )


def test_sme_confidence_grade(result):
    """SME is a proxy → confidence should be B."""
    row = _get_row(result, "nrb-concession-sme-outstanding")
    assert row.confidence_grade_proposed == "B", (
        f"SME slug should have confidence B (proxy), got {row.confidence_grade_proposed!r}"
    )


def test_sme_proxy_note(result):
    """SME proxy row must carry a parser_notes documenting the limitation."""
    row = _get_row(result, "nrb-concession-sme-outstanding")
    assert row.parser_notes is not None and "PROXY" in row.parser_notes, (
        f"SME row should have PROXY in parser_notes, got {row.parser_notes!r}"
    )


def test_total_and_agriculture_confidence_a(result):
    for slug in ("nrb-concession-total-outstanding", "nrb-concession-agriculture-outstanding"):
        row = _get_row(result, slug)
        assert row.confidence_grade_proposed == "A", (
            f"{slug}: expected confidence A, got {row.confidence_grade_proposed!r}"
        )


# ── Error handling ────────────────────────────────────────────────────────────


def test_missing_file_returns_failure():
    result = parse("/nonexistent/path/no-file.xlsx", "test-id")
    assert result.status == "failure"
    assert result.staging_rows == []
    assert any(e.error_class == "Other" for e in result.errors)


def test_bad_filename_returns_failure(tmp_path):
    """A valid XLSX with an unrecognised filename pattern returns failure."""
    import shutil
    bad = tmp_path / "no-date-here.xlsx"
    shutil.copy(str(FIXTURE), str(bad))
    result = parse(str(bad), "test-id")
    assert result.status == "failure"
    assert any(e.error_class == "PeriodAmbiguous" for e in result.errors)


# ── Idempotency ───────────────────────────────────────────────────────────────


def test_idempotent():
    r1 = parse(str(FIXTURE), "test-id-1")
    r2 = parse(str(FIXTURE), "test-id-2")
    assert r1.status == r2.status
    assert len(r1.staging_rows) == len(r2.staging_rows)
    for a, b in zip(r1.staging_rows, r2.staging_rows, strict=True):
        assert a.indicator_slug_raw == b.indicator_slug_raw
        assert a.value == b.value


# ── JSON serialisation ────────────────────────────────────────────────────────


def test_to_json_dict_is_serialisable(result):
    """to_json_dict() must produce a JSON-serialisable structure."""
    import json
    payload = result.to_json_dict()
    dumped = json.dumps(payload)
    assert len(dumped) > 100
