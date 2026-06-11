"""Tests for the FCGO Consolidated Financial Statements parser.

The real source is a 3.9 MB / 325-page PDF whose detailed tables render
with reversed glyph order under pdfplumber; only the clean forward-text
Executive Summary / Treasury-Position prose is matched. We do NOT commit
the binary (ADR-0003 / source profile), and no PDF-writing library is in
the venv — so the deterministic core (``extract_indicators``) is exercised
against SYNTHESIZED TEXT fixtures that reproduce two phrasings plus a miss.

A single optional integration test runs the full ``parse`` against the real
PDF when it happens to be on disk (``Financial Data/fcgo_consolidated/...``);
it is skipped otherwise so CI without the binary stays green.
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

PERIOD_TOLERANCE = timedelta(days=40)  # mid-month AD approximation slack

EXPECTED_SLUGS: frozenset[str] = frozenset(
    {
        "fcgo-total-revenue-outturn-annual",
        "fcgo-total-expenditure-outturn-annual",
        "fcgo-recurrent-expenditure-outturn-annual",
        "fcgo-capital-expenditure-outturn-annual",
        "fcgo-provincial-expenditure-consolidated-annual",
        "fcgo-local-level-expenditure-consolidated-annual",
    }
)

# Expected REAL values from the FY 2022/23 publication (npr_million).
EXPECTED_VALUES: dict[str, float] = {
    "fcgo-total-revenue-outturn-annual": 1_506_321.46,
    "fcgo-total-expenditure-outturn-annual": 1_672_128.84,
    "fcgo-recurrent-expenditure-outturn-annual": 1_356_150.86,
    "fcgo-capital-expenditure-outturn-annual": 527_447.04,
    "fcgo-provincial-expenditure-consolidated-annual": 204_678.62,
    "fcgo-local-level-expenditure-consolidated-annual": 453_817.73,
}

# The real PDF, if Mother has downloaded it into the worktree. Optional.
REAL_PDF = (
    Path(__file__).resolve().parents[3]
    / "Financial Data"
    / "fcgo_consolidated"
    / "FCGO_CFS_2022-23.pdf"
)


# ---------------------------------------------------------------------------
# Synthesized text fixtures — reproduce the clean forward-text prose.
# ---------------------------------------------------------------------------

# Phrasing #1: the canonical FY 2022/23 wording (verbatim anchors).
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

# Phrasing #2: a plausible future-edition drift that exercises every
# alternation branch ("amounts to"→"is"/"stands at"→"is"; "totaling"→
# "amounting to"). Values are DELIBERATELY different so a test can prove
# the parser reads the drifted phrasing rather than echoing phrasing #1.
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
    "fcgo-provincial-expenditure-consolidated-annual": 210_000.00,
    "fcgo-local-level-expenditure-consolidated-annual": 460_000.00,
}

# A miss: prose with none of the headline anchors present.
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
    assert result_1.parser_version == PARSER_VERSION == "0.2.0"


def test_phrasing1_all_six_indicators(result_1: ParserResult) -> None:
    slugs = {row.indicator_slug_raw for row in result_1.staging_rows}
    assert slugs == EXPECTED_SLUGS, f"missing: {EXPECTED_SLUGS - slugs}"


def test_phrasing1_row_count(result_1: ParserResult) -> None:
    assert len(result_1.staging_rows) == len(EXPECTED_SLUGS)


def test_phrasing1_no_errors(result_1: ParserResult) -> None:
    assert result_1.errors == [], f"unexpected errors: {result_1.errors}"


def test_phrasing1_values(result_1: ParserResult) -> None:
    for slug, expected in EXPECTED_VALUES.items():
        assert _value_for(result_1, slug) == pytest.approx(expected, abs=1e-6)


def test_phrasing1_total_revenue_magnitude(result_1: ParserResult) -> None:
    """The magnitude check from the brief: total revenue ≈ 1,506,321
    npr_million (≈ NPR 1.5 trillion — correct for Nepal's 3-tier revenue)."""
    val = _value_for(result_1, "fcgo-total-revenue-outturn-annual")
    assert 1_400_000 < val < 1_600_000


def test_phrasing1_recurrent_capital_distinct(result_1: ParserResult) -> None:
    """Recurrent and capital come from groups 1 and 2 of the same shared
    sentence — they must not collide on one value."""
    recurrent = _value_for(result_1, "fcgo-recurrent-expenditure-outturn-annual")
    capital = _value_for(result_1, "fcgo-capital-expenditure-outturn-annual")
    assert recurrent == pytest.approx(1_356_150.86, abs=1e-6)
    assert capital == pytest.approx(527_447.04, abs=1e-6)
    assert recurrent != capital


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
        assert row.value > 0
        assert isinstance(row.reporting_period_ad_start, datetime)
        assert isinstance(row.reporting_period_ad_end, datetime)
        assert isinstance(row.publication_date_ad, datetime)
        assert row.publication_date_bs


def test_phrasing1_units_all_npr_million(result_1: ParserResult) -> None:
    for row in result_1.staging_rows:
        assert row.unit == "npr_million"


def test_phrasing1_basis_notes_present(result_1: ParserResult) -> None:
    """Every row carries a basis note; recurrent/capital flag the gross-vs-
    after-elimination caveat so downstream consumers don't mis-reconcile."""
    by_slug = {r.indicator_slug_raw: r.parser_notes for r in result_1.staging_rows}
    for note in by_slug.values():
        assert note  # non-empty
    assert "gross" in (by_slug["fcgo-recurrent-expenditure-outturn-annual"] or "")
    assert "gross" in (by_slug["fcgo-capital-expenditure-outturn-annual"] or "")
    assert "eliminating" in (
        by_slug["fcgo-total-expenditure-outturn-annual"] or ""
    )


def test_phrasing1_annual_period_spans_fiscal_year(result_1: ParserResult) -> None:
    """Annual span runs ~mid-July (FY open) to ~the following mid-year
    (FY close) under the mid-month AD approximation."""
    expected_start = datetime(2022, 7, 15, tzinfo=UTC)
    for row in result_1.staging_rows:
        assert (
            abs(row.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
        )
        assert row.reporting_period_ad_end > row.reporting_period_ad_start


# ---------------------------------------------------------------------------
# Phrasing #2 — alternation branches / drifted wording.
# ---------------------------------------------------------------------------


def test_phrasing2_reads_drifted_wording() -> None:
    result = extract_indicators(TEXT_PHRASING_2)
    assert result.status == "success", f"errors={result.errors}"
    assert {r.indicator_slug_raw for r in result.staging_rows} == EXPECTED_SLUGS
    for slug, expected in EXPECTED_VALUES_PHRASING_2.items():
        assert _value_for(result, slug) == pytest.approx(expected, abs=1e-6), slug


# ---------------------------------------------------------------------------
# Miss — anchors absent: typed PageLayoutChanged, never a crash.
# ---------------------------------------------------------------------------


def test_miss_yields_failure_and_typed_errors() -> None:
    result = extract_indicators(TEXT_MISS)
    assert result.status == "failure"
    assert len(result.errors) == len(EXPECTED_SLUGS)
    assert all(e.error_class == "PageLayoutChanged" for e in result.errors)
    assert result.staging_rows == []


def test_partial_when_some_anchors_missing() -> None:
    """If only some anchors are present, status is 'partial': the found
    rows are emitted and the missing ones surface as typed errors."""
    partial_text = (
        "Total expenditure of all seven provinces amounts to NPR 204,678.62 "
        "million.\nTotal expenditure of all local governments amounts to NPR "
        "453,817.73 million.\n"
    )
    result = extract_indicators(partial_text)
    assert result.status == "partial"
    assert len(result.staging_rows) == 2
    assert len(result.errors) == len(EXPECTED_SLUGS) - 2
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
    """Same input → identical output (parser contract / DATA_PIPELINE.md)."""
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
    """AD FY lead → BS FY lead (+57) must round-trip via the canonical
    BS→AD label helper (ADR-0013)."""
    from _common.periods import fiscal_year_ad_label
    from fcgo_consolidated.parser import _ad_fy_to_bs_start

    bs = _ad_fy_to_bs_start(2022)
    assert bs == 2079
    assert fiscal_year_ad_label(bs) == "2022/23"


# ---------------------------------------------------------------------------
# FY auto-detection (v0.2.0 — dynamic period metadata).
# ---------------------------------------------------------------------------


def test_fy_detected_from_phrasing1() -> None:
    """v0.2.0: FY 2022/23 is auto-detected; period metadata is BS 2079/80."""
    assert _detect_ad_fy_start(TEXT_PHRASING_1) == 2022
    result = extract_indicators(TEXT_PHRASING_1)
    assert result.status == "success"
    for row in result.staging_rows:
        assert row.reporting_period_bs == "FY 2079/80"
        assert row.fiscal_year_ad_label == "2022/23"


def test_fy_2324_variant_produces_correct_period() -> None:
    """FY 2023/24 prose produces BS 2080/81 period metadata without code change."""
    text_2324 = TEXT_PHRASING_1.replace("FY 2022/23", "FY 2023/24")
    assert _detect_ad_fy_start(text_2324) == 2023
    result = extract_indicators(text_2324)
    assert result.status == "success"
    assert len(result.staging_rows) == len(EXPECTED_SLUGS)
    for row in result.staging_rows:
        assert row.reporting_period_bs == "FY 2080/81"
        assert row.fiscal_year_bs == "2080/81"
        assert row.fiscal_year_ad_label == "2023/24"


def test_fy_detection_rejects_malformed_labels() -> None:
    assert _detect_ad_fy_start("FY 2022/24") is None  # suffix mismatch
    assert _detect_ad_fy_start("FY 2000/01") is None  # before 2018 cutoff
    assert _detect_ad_fy_start("no fy label here") is None


# ---------------------------------------------------------------------------
# Optional integration test against the real PDF (skipped if absent).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real FCGO CFS PDF not on disk")
def test_real_pdf_extracts_all_six_values() -> None:
    result = parse(str(REAL_PDF), source_document_id="real-doc")
    assert result.status == "success", f"errors={result.errors}"
    assert {r.indicator_slug_raw for r in result.staging_rows} == EXPECTED_SLUGS
    for slug, expected in EXPECTED_VALUES.items():
        assert _value_for(result, slug) == pytest.approx(expected, abs=1e-6), slug


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real FCGO CFS PDF not on disk")
def test_cli_emits_valid_json_on_real_pdf() -> None:
    """The ``__main__`` block must produce JSON the TS-side Zod schema can
    parse. Exercised against the real PDF when present."""
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
    assert payload["parser_version"] == PARSER_VERSION == "0.2.0"
    assert len(payload["staging_rows"]) == len(EXPECTED_SLUGS)
    for row in payload["staging_rows"]:
        assert "T" in row["reporting_period_ad_start"]
        assert "T" in row["reporting_period_ad_end"]
        assert "T" in row["publication_date_ad"]
        assert row["unit"] == "npr_million"
