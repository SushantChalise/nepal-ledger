"""Tests for the FCGO Consolidated Financial Statements parser.

v1.0.0: pymupdf backend (pdfplumber reversed 165/325 landscape pages).
9 indicators: 7 extracted from Executive Summary prose + 2 derived.
Exercised against synthesized text fixtures; optional real-PDF integration.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from fcgo_consolidated import PARSER_VERSION, parse
from fcgo_consolidated.parser import _detect_ad_fy_start, extract_indicators

PERIOD_TOLERANCE = timedelta(days=40)

# 7 extracted from prose.
EXTRACTED_SLUGS: frozenset[str] = frozenset(
    {
        "fcgo-total-revenue-outturn-annual",
        "fcgo-total-expenditure-outturn-annual",
        "fcgo-recurrent-expenditure-outturn-annual",
        "fcgo-capital-expenditure-outturn-annual",
        "fcgo-financing-disbursements-outturn-annual",
        "fcgo-provincial-expenditure-consolidated-annual",
        "fcgo-local-level-expenditure-consolidated-annual",
    }
)

# 2 derived from extracted values.
DERIVED_SLUGS: frozenset[str] = frozenset(
    {
        "fcgo-federal-expenditure-outturn-annual",
        "fcgo-fiscal-balance-outturn-annual",
    }
)

ALL_SLUGS: frozenset[str] = EXTRACTED_SLUGS | DERIVED_SLUGS

EXPECTED_VALUES: dict[str, float] = {
    "fcgo-total-revenue-outturn-annual": 1_506_321.46,
    "fcgo-total-expenditure-outturn-annual": 1_672_128.84,
    "fcgo-recurrent-expenditure-outturn-annual": 1_356_150.86,
    "fcgo-capital-expenditure-outturn-annual": 527_447.04,
    "fcgo-financing-disbursements-outturn-annual": 196_225.41,
    "fcgo-provincial-expenditure-consolidated-annual": 204_678.62,
    "fcgo-local-level-expenditure-consolidated-annual": 453_817.73,
    # derived
    "fcgo-federal-expenditure-outturn-annual": round(
        1_672_128.84 - 204_678.62 - 453_817.73, 2
    ),
    "fcgo-fiscal-balance-outturn-annual": round(
        1_506_321.46 - 1_672_128.84, 2
    ),
}

REAL_PDF = (
    Path(__file__).resolve().parents[3]
    / "Financial Data"
    / "fcgo_consolidated"
    / "FCGO_CFS_2022-23.pdf"
)


# ---------------------------------------------------------------------------
# Synthesized text fixtures.
# ---------------------------------------------------------------------------

TEXT_PHRASING_1 = (
    "EXECUTIVE SUMMARY\n"
    "The total revenue utilization (excluding fiscal transfer) of the three "
    "tiers of government for FY 2022/23 amounts to NPR 1,506,321.46 million "
    "after revenue sharing settlements. Total expenditure stands at NPR "
    "1,672,128.84 million after eliminating all types of intergovernmental "
    "fiscal transfers (excluding EBUs).\n"
    "In FY 2022/23, the total revenue collection of all seven provinces "
    "amounts to NPR 112,369.43 million, including revenue from internal "
    "source. Total expenditure of all seven provinces amounts to NPR "
    "204,678.62 million, including fiscal transfers to local governments.\n"
    "In FY 2022/23, the total receipts of all 753 local governments amount "
    "to NPR 532,462.13 million. Total expenditure of all local governments "
    "amounts to NPR 453,817.73 million.\n"
    "Total disbursements from the consolidated fund for the same fiscal year "
    "amounted to NPR 2,079,823.31 million. These disbursements included "
    "recurrent expenditures, capital expenditures, and financing "
    "disbursements totaling NPR 1,356,150.86 million, NPR 527,447.04 "
    "million, and NPR 196,225.41 million, respectively.\n"
)

TEXT_PHRASING_2 = (
    "EXECUTIVE SUMMARY\n"
    "The total revenue utilization of the three tiers of government for FY "
    "2022/23 is NPR 1,600,000.00 million after revenue sharing settlements. "
    "Total expenditure is NPR 1,700,000.00 million after eliminating all "
    "types of intergovernmental fiscal transfers.\n"
    "Total expenditure of all seven provinces stands at NPR 210,000.00 "
    "million, including fiscal transfers. Total expenditure of all local "
    "governments stands at NPR 460,000.00 million.\n"
    "These disbursements included recurrent expenditures, capital "
    "expenditures, and financing disbursements amounting to NPR 1,400,000.00 "
    "million, NPR 530,000.00 million, and NPR 200,000.00 million, "
    "respectively.\n"
)

EXPECTED_VALUES_PHRASING_2: dict[str, float] = {
    "fcgo-total-revenue-outturn-annual": 1_600_000.00,
    "fcgo-total-expenditure-outturn-annual": 1_700_000.00,
    "fcgo-recurrent-expenditure-outturn-annual": 1_400_000.00,
    "fcgo-capital-expenditure-outturn-annual": 530_000.00,
    "fcgo-financing-disbursements-outturn-annual": 200_000.00,
    "fcgo-provincial-expenditure-consolidated-annual": 210_000.00,
    "fcgo-local-level-expenditure-consolidated-annual": 460_000.00,
    # derived
    "fcgo-federal-expenditure-outturn-annual": round(
        1_700_000.00 - 210_000.00 - 460_000.00, 2
    ),
    "fcgo-fiscal-balance-outturn-annual": round(
        1_600_000.00 - 1_700_000.00, 2
    ),
}

TEXT_MISS = (
    "ACCOUNTING POLICY AND EXPLANATORY NOTES\n"
    "The Constitution of Nepal outlines financial procedures for the "
    "federal, provincial, and local governments. This section contains no "
    "headline fiscal aggregates and no NPR figures the parser anchors on.\n"
)


def _value_for(result: ParserResult, slug: str) -> float:
    matches = [r for r in result.staging_rows if r.indicator_slug_raw == slug]
    assert len(matches) == 1, f"expected exactly one {slug}, got {len(matches)}"
    return matches[0].value


# ---------------------------------------------------------------------------
# Phrasing #1 — verbatim canonical wording.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def result_1() -> ParserResult:
    return extract_indicators(TEXT_PHRASING_1)


def test_phrasing1_status_success(result_1: ParserResult) -> None:
    assert result_1.status == "success", (
        f"status={result_1.status} errors={result_1.errors}"
    )


def test_phrasing1_parser_version(result_1: ParserResult) -> None:
    assert result_1.parser_version == PARSER_VERSION == "1.0.0"


def test_phrasing1_all_nine_indicators(result_1: ParserResult) -> None:
    slugs = {row.indicator_slug_raw for row in result_1.staging_rows}
    assert slugs == ALL_SLUGS, f"missing: {ALL_SLUGS - slugs}"


def test_phrasing1_row_count(result_1: ParserResult) -> None:
    assert len(result_1.staging_rows) == len(ALL_SLUGS)


def test_phrasing1_no_errors(result_1: ParserResult) -> None:
    assert result_1.errors == [], f"unexpected errors: {result_1.errors}"


def test_phrasing1_values(result_1: ParserResult) -> None:
    for slug, expected in EXPECTED_VALUES.items():
        assert _value_for(result_1, slug) == pytest.approx(expected, abs=1e-2), slug


def test_phrasing1_total_revenue_magnitude(result_1: ParserResult) -> None:
    val = _value_for(result_1, "fcgo-total-revenue-outturn-annual")
    assert 1_400_000 < val < 1_600_000


def test_phrasing1_recurrent_capital_financing_distinct(
    result_1: ParserResult,
) -> None:
    recurrent = _value_for(result_1, "fcgo-recurrent-expenditure-outturn-annual")
    capital = _value_for(result_1, "fcgo-capital-expenditure-outturn-annual")
    financing = _value_for(result_1, "fcgo-financing-disbursements-outturn-annual")
    assert recurrent == pytest.approx(1_356_150.86, abs=1e-6)
    assert capital == pytest.approx(527_447.04, abs=1e-6)
    assert financing == pytest.approx(196_225.41, abs=1e-6)
    assert len({recurrent, capital, financing}) == 3


def test_phrasing1_required_fields(result_1: ParserResult) -> None:
    for row in result_1.staging_rows:
        assert isinstance(row, StagingRowDraft)
        assert row.indicator_slug_raw.startswith("fcgo-")
        assert row.unit == "npr_million"
        assert row.reporting_period_type == "annual"
        assert row.reporting_period_bs == "FY 2079/80"
        assert row.fiscal_year_bs == "2079/80"
        assert row.fiscal_year_ad_label == "2022/23"
        assert row.confidence_grade_proposed == "A"
        assert isinstance(row.value, float)
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


def test_phrasing1_units_all_npr_million(result_1: ParserResult) -> None:
    for row in result_1.staging_rows:
        assert row.unit == "npr_million"


def test_phrasing1_basis_notes_present(result_1: ParserResult) -> None:
    by_slug = {r.indicator_slug_raw: r.parser_notes for r in result_1.staging_rows}
    for note in by_slug.values():
        assert note
    assert "gross" in (by_slug["fcgo-recurrent-expenditure-outturn-annual"] or "")
    assert "gross" in (by_slug["fcgo-capital-expenditure-outturn-annual"] or "")
    assert "gross" in (by_slug["fcgo-financing-disbursements-outturn-annual"] or "")
    assert "eliminating" in (
        by_slug["fcgo-total-expenditure-outturn-annual"] or ""
    )
    assert "derived" in (by_slug["fcgo-federal-expenditure-outturn-annual"] or "")
    assert "derived" in (by_slug["fcgo-fiscal-balance-outturn-annual"] or "")


def test_phrasing1_annual_period_spans_fiscal_year(result_1: ParserResult) -> None:
    expected_start = datetime(2022, 7, 15, tzinfo=UTC)
    for row in result_1.staging_rows:
        assert (
            abs(row.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
        )
        assert row.reporting_period_ad_end > row.reporting_period_ad_start


# ---------------------------------------------------------------------------
# Derived indicator arithmetic.
# ---------------------------------------------------------------------------


def test_federal_expenditure_is_total_minus_provincial_minus_local(
    result_1: ParserResult,
) -> None:
    total = _value_for(result_1, "fcgo-total-expenditure-outturn-annual")
    prov = _value_for(result_1, "fcgo-provincial-expenditure-consolidated-annual")
    local = _value_for(result_1, "fcgo-local-level-expenditure-consolidated-annual")
    federal = _value_for(result_1, "fcgo-federal-expenditure-outturn-annual")
    assert federal == pytest.approx(total - prov - local, abs=1e-2)


def test_fiscal_balance_is_revenue_minus_expenditure(
    result_1: ParserResult,
) -> None:
    rev = _value_for(result_1, "fcgo-total-revenue-outturn-annual")
    exp = _value_for(result_1, "fcgo-total-expenditure-outturn-annual")
    balance = _value_for(result_1, "fcgo-fiscal-balance-outturn-annual")
    assert balance == pytest.approx(rev - exp, abs=1e-2)
    assert balance < 0, "FY 2022/23 ran a deficit"


# ---------------------------------------------------------------------------
# Phrasing #2 — alternation branches / drifted wording.
# ---------------------------------------------------------------------------


def test_phrasing2_reads_drifted_wording() -> None:
    result = extract_indicators(TEXT_PHRASING_2)
    assert result.status == "success", f"errors={result.errors}"
    assert {r.indicator_slug_raw for r in result.staging_rows} == ALL_SLUGS
    for slug, expected in EXPECTED_VALUES_PHRASING_2.items():
        assert _value_for(result, slug) == pytest.approx(expected, abs=1e-2), slug


# ---------------------------------------------------------------------------
# Miss — anchors absent: typed PageLayoutChanged, never a crash.
# ---------------------------------------------------------------------------


def test_miss_yields_failure_and_typed_errors() -> None:
    result = extract_indicators(TEXT_MISS)
    assert result.status == "failure"
    assert len(result.errors) == len(EXTRACTED_SLUGS)
    assert all(e.error_class == "PageLayoutChanged" for e in result.errors)
    assert result.staging_rows == []


def test_partial_when_some_anchors_missing() -> None:
    partial_text = (
        "Total expenditure of all seven provinces amounts to NPR 204,678.62 "
        "million.\nTotal expenditure of all local governments amounts to NPR "
        "453,817.73 million.\n"
    )
    result = extract_indicators(partial_text)
    assert result.status == "partial"
    # 2 extracted + 0 derived (no total-exp for federal/balance derivation)
    assert len(result.staging_rows) == 2
    assert len(result.errors) == len(EXTRACTED_SLUGS) - 2
    assert all(e.error_class == "PageLayoutChanged" for e in result.errors)


def test_empty_text_fails_cleanly() -> None:
    result = extract_indicators("   \n  ")
    assert result.status == "failure"
    assert len(result.errors) == 1
    assert result.errors[0].error_class == "PageLayoutChanged"


# ---------------------------------------------------------------------------
# Contract / robustness.
# ---------------------------------------------------------------------------


def test_idempotent() -> None:
    first = extract_indicators(TEXT_PHRASING_1)
    second = extract_indicators(TEXT_PHRASING_1)
    assert first.status == second.status
    assert len(first.staging_rows) == len(second.staging_rows)
    for a, b in zip(first.staging_rows, second.staging_rows, strict=True):
        assert a == b


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-file.pdf", source_document_id="x")
    assert res.status == "failure"
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_ad_fy_to_bs_roundtrip() -> None:
    from _common.periods import fiscal_year_ad_label
    from fcgo_consolidated.parser import _ad_fy_to_bs_start

    bs = _ad_fy_to_bs_start(2022)
    assert bs == 2079
    assert fiscal_year_ad_label(bs) == "2022/23"


# ---------------------------------------------------------------------------
# FY auto-detection (v0.2.0+).
# ---------------------------------------------------------------------------


def test_fy_detected_from_phrasing1() -> None:
    assert _detect_ad_fy_start(TEXT_PHRASING_1) == 2022
    result = extract_indicators(TEXT_PHRASING_1)
    assert result.status == "success"
    for row in result.staging_rows:
        assert row.reporting_period_bs == "FY 2079/80"
        assert row.fiscal_year_ad_label == "2022/23"


def test_fy_2324_variant_produces_correct_period() -> None:
    text_2324 = TEXT_PHRASING_1.replace("FY 2022/23", "FY 2023/24")
    assert _detect_ad_fy_start(text_2324) == 2023
    result = extract_indicators(text_2324)
    assert result.status == "success"
    assert len(result.staging_rows) == len(ALL_SLUGS)
    for row in result.staging_rows:
        assert row.reporting_period_bs == "FY 2080/81"
        assert row.fiscal_year_bs == "2080/81"
        assert row.fiscal_year_ad_label == "2023/24"


def test_fy_detection_rejects_malformed_labels() -> None:
    assert _detect_ad_fy_start("FY 2022/24") is None
    assert _detect_ad_fy_start("FY 2000/01") is None
    assert _detect_ad_fy_start("no fy label here") is None


# ---------------------------------------------------------------------------
# Optional integration test against the real PDF (skipped if absent).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real FCGO CFS PDF not on disk")
def test_real_pdf_extracts_all_nine_values() -> None:
    result = parse(str(REAL_PDF), source_document_id="real-doc")
    assert result.status == "success", f"errors={result.errors}"
    slugs = {r.indicator_slug_raw for r in result.staging_rows}
    assert slugs == ALL_SLUGS, f"missing: {ALL_SLUGS - slugs}"
    for slug, expected in EXPECTED_VALUES.items():
        assert _value_for(result, slug) == pytest.approx(expected, abs=1e-2), slug


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real FCGO CFS PDF not on disk")
def test_cli_emits_valid_json_on_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "fcgo_consolidated.parser", str(REAL_PDF), "doc"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] == "success"
    assert payload["parser_version"] == PARSER_VERSION == "1.0.0"
    assert len(payload["staging_rows"]) == len(ALL_SLUGS)
    for row in payload["staging_rows"]:
        assert "T" in row["reporting_period_ad_start"]
        assert "T" in row["reporting_period_ad_end"]
        assert "T" in row["publication_date_ad"]
        assert row["unit"] == "npr_million"
