"""Tests for the MoF Red Book (annual budget) parser.

The real source is the 652-page "Red Book Central 2074-75" PDF whose clean
Devanagari-Unicode appropriation (विनियोजन) summary is the deterministically
parseable target; every other edition is CID-broken, Preeti-encoded, or
glyph-mangled (see the parser module docstring STEP-0 assessment). We do NOT
commit the binary (ADR-0003 / source profile) and no PDF-writing library is in
the venv — so the deterministic core (``extract_dimensional_rows``) is exercised
against SYNTHESIZED text-line fixtures that reproduce the real summary geometry
(a 3-4 digit code, a Devanagari name, then exactly eight money tokens; with
चालु/पूँजीगत sub-rows and a जम्मा total row interleaved exactly as the real PDF
emits them).

Optional integration tests run the full ``parse_redbook`` + CLI against the real
FY 2074/75 edition when it is on disk; they are skipped otherwise so CI stays
green.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserError
from mof_redbook import PARSER_VERSION, RedbookResult, parse_redbook
from mof_redbook.parser import (
    DimensionalRowDraft,
    detect_bs_fiscal_year,
    detect_unit,
    extract_dimensional_rows,
)

PERIOD_TOLERANCE = timedelta(days=40)  # mid-month AD approximation slack
BS_FY_2074_START = 2074  # AD 2017/18 (-57)
_UNIT = "npr_thousand"

# Real PDF, if Mother has the corpus in the worktree. Optional integration only.
REAL_PDF = (
    Path(__file__).resolve().parents[3]
    / "Financial Data"
    / "mof_documents"
    / "redbook"
    / "Red Book Central 2074-75_20170530083940_00lqgwe.pdf"
)


# ---------------------------------------------------------------------------
# Synthesized appropriation-summary text. Each budget-head line is:
#   <code> <name> <FY-2 actual> <FY-1 revised> <FY0 total> <recurrent>
#          <capital> <GoN> <grant> <loan>
# and is followed by चालु / पूँजीगत खर्च sub-rows (different token counts) plus a
# जम्मा total row — exactly the shapes the real PDF's extract_text() produces.
# Token indices we emit: [2]=total, [3]=recurrent, [4]=capital.
# ---------------------------------------------------------------------------

_SUMMARY_TEXT = "\n".join(
    [
        "संघीय संिचत कोषबाट विनियोजन हुने व्यय अनुमानको सारांश",
        "(रू.हजारमा)",
        "अनुदान संख्या ... 2074/75 को विनियोजन ... जम्मा रकम",
        # 101 President: total 150,775 = recurrent 119,113 + capital 31,662.
        "101 रा�प�त 32,22,02 29,10,54 15,07,75 11,91,13 3,16,62 15,07,75 0 0",
        "चाल ु 9,12,45 11,23,58 11,91,13 11,91,13 0 11,91,13 0 0",
        "पंूजीगत खच र् 23,09,57 17,86,96 3,16,62 0 3,16,62 3,16,62 0 0",
        # 301 PMO: total 1,49,62,20,73 = recurrent 77,27,93,19 + capital 72,34,27,54.
        # (The चालु/पूँजीगत sub-rows are skipped by leader regardless of their
        # numeric content, so they are abbreviated here to stay under 100 cols.)
        "301 �धानमन्�ी तथा मिन्�प�रषद्को कायार्लय 10,57,44,18 95,98,23,74 "
        "1,49,62,20,73 77,27,93,19 72,34,27,54 48,77,59,52 23,98,86,32 76,85,74,89",
        "चाल ु 10,14,54,22 53,34,89,26 77,27,93,19 77,27,93,19 0 22,63,37,80",
        "पंूजीगत खच र् 42,89,96 42,63,34,48 72,34,27,54 0 72,34,27,54 26,14,21,72",
        # 801 Local level: total = recurrent (capital 0). Tests a real 0 capital.
        "801 स्थानीय तह 0 0 2,25,05,45,91 2,25,05,45,91 0 2,20,63,34,26 2,08,12,85 2,33,98,80",
        "चाल ु 0 0 2,25,05,45,91 2,25,05,45,91 0 2,20,63,34,26 2,08,12,85 2,33,98,80",
        # Grand-total row — MUST be excluded as a dimension (no leading code).
        "जम्मा 524,138,931 8,69,75,96,15 11,95,37,81,31 7,72,51,51,47 4,22,86,29,84 "
        "9,09,17,50,74 72,16,76,28 2,14,03,54,29",
    ]
)

# Expected per-head (total, recurrent, capital) in thousand NPR.
_EXPECTED: dict[str, tuple[float, float, float]] = {
    "101": (150_775.0, 119_113.0, 31_662.0),
    "301": (1_496_220_73 / 1, 772_793_19 / 1, 723_427_54 / 1),
    "801": (2_250_545_91 / 1, 2_250_545_91 / 1, 0.0),
}


@pytest.fixture(scope="module")
def rows() -> list[DimensionalRowDraft]:
    out, errors = extract_dimensional_rows(_SUMMARY_TEXT, _UNIT, BS_FY_2074_START)
    assert errors == [], f"unexpected errors: {errors}"
    return out


def _facts_for(rows: list[DimensionalRowDraft], slug: str) -> dict[str, float]:
    """Map code-prefixed dimension_value → value for one base measure."""
    return {r.dimension_value: r.value for r in rows if r.base_indicator_slug == slug}


def _value_for(rows: list[DimensionalRowDraft], slug: str, code: str) -> float:
    for r in rows:
        if r.base_indicator_slug == slug and r.dimension_value.startswith(f"{code}-"):
            return r.value
    raise AssertionError(f"no {slug} fact for code {code}")


# ---------------------------------------------------------------------------
# Core extraction.
# ---------------------------------------------------------------------------


def test_three_measures_per_head(rows: list[DimensionalRowDraft]) -> None:
    """Each of the 3 heads emits total + recurrent + capital = 9 facts."""
    slugs = {
        "budget-allocation-total",
        "budget-allocation-recurrent",
        "budget-allocation-capital",
    }
    assert {r.base_indicator_slug for r in rows} == slugs
    assert len(rows) == 9  # 3 heads × 3 measures


def test_total_values(rows: list[DimensionalRowDraft]) -> None:
    for code, (total, _r, _c) in _EXPECTED.items():
        assert _value_for(rows, "budget-allocation-total", code) == pytest.approx(total)


def test_recurrent_and_capital_values(rows: list[DimensionalRowDraft]) -> None:
    for code, (_t, recurrent, capital) in _EXPECTED.items():
        assert _value_for(rows, "budget-allocation-recurrent", code) == pytest.approx(
            recurrent
        )
        assert _value_for(rows, "budget-allocation-capital", code) == pytest.approx(
            capital
        )


def test_total_equals_recurrent_plus_capital(rows: list[DimensionalRowDraft]) -> None:
    """Structural invariant (ADR-0011 correctness anchor): per head, the source's
    total column equals its recurrent + capital columns."""
    for code in _EXPECTED:
        total = _value_for(rows, "budget-allocation-total", code)
        recurrent = _value_for(rows, "budget-allocation-recurrent", code)
        capital = _value_for(rows, "budget-allocation-capital", code)
        assert total == pytest.approx(recurrent + capital)


def test_real_zero_capital_preserved(rows: list[DimensionalRowDraft]) -> None:
    """801 local-level has a genuine 0 capital — kept as a fact, not dropped."""
    assert _value_for(rows, "budget-allocation-capital", "801") == pytest.approx(0.0)


def test_grand_total_row_excluded(rows: list[DimensionalRowDraft]) -> None:
    """The जम्मा total row carries no leading code → never a dimension member."""
    for r in rows:
        assert "जम्मा" not in r.dimension_label
        # Every emitted head's slug starts with one of the synthesized codes.
        assert any(r.dimension_value.startswith(f"{c}-") for c in _EXPECTED)


def test_subrows_not_emitted(rows: list[DimensionalRowDraft]) -> None:
    """चालु / पूँजीगत खर्च sub-rows must not produce their own facts."""
    for r in rows:
        assert not r.dimension_label.startswith("चाल")
        assert not r.dimension_label.startswith("पंूज")


def test_dimension_kind_and_unit_and_confidence(rows: list[DimensionalRowDraft]) -> None:
    for r in rows:
        assert r.dimension_kind == "budget-head"
        assert r.unit == "npr_thousand"
        assert r.confidence_grade == "B"


def test_dimension_value_is_code_prefixed_kebab(rows: list[DimensionalRowDraft]) -> None:
    """Slug = kebab of '<code> <name>'; the code prefix guarantees distinct
    identity even when a glyph-mangled name would otherwise collide (ADR-0011)."""
    for r in rows:
        assert " " not in r.dimension_value
        assert r.dimension_value == r.dimension_value.strip("-")
        assert r.dimension_value[:3].isdigit()
    # Distinct heads → distinct slugs for each measure.
    totals = _facts_for(rows, "budget-allocation-total")
    assert len(totals) == len(_EXPECTED)


# ---------------------------------------------------------------------------
# Period dating (ADR-0013).
# ---------------------------------------------------------------------------


def test_period_is_annual_bs_fy(rows: list[DimensionalRowDraft]) -> None:
    for r in rows:
        assert r.reporting_period_type == "annual"
        assert r.reporting_period_bs == "2074/75"
        assert r.fiscal_year_bs == "2074/75"
        assert r.fiscal_year_ad_label == "2017/18"  # BS 2074 → AD 2017 (-57)


def test_annual_span_brackets_fiscal_year(rows: list[DimensionalRowDraft]) -> None:
    expected_start = datetime(2017, 7, 15, tzinfo=UTC)
    for r in rows:
        assert abs(r.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
        assert r.reporting_period_ad_end > r.reporting_period_ad_start


def test_magnitude_sanity_npr_thousand(rows: list[DimensionalRowDraft]) -> None:
    """ADR-0011: local-level (801) appropriation = 225,054,591 thousand =
    NPR 225.1 billion — the right order of magnitude for all-753 local transfers."""
    npr = _value_for(rows, "budget-allocation-total", "801") * 1_000  # thousand → rupees
    assert 1e11 < npr < 1e12


# ---------------------------------------------------------------------------
# Unit detection (ADR-0011).
# ---------------------------------------------------------------------------


def test_detect_unit_thousand() -> None:
    assert detect_unit("कुनै शीर्षक (रू.हजारमा)") == "npr_thousand"
    assert detect_unit("Details (रू. हजारमा)") == "npr_thousand"
    assert detect_unit("Details (रु. हजारमा)") == "npr_thousand"


def test_detect_unit_none_when_absent() -> None:
    assert detect_unit("संघीय संचित कोषबाट विनियोजन हुने अनुमानको सारांश") is None


# ---------------------------------------------------------------------------
# Fiscal-year detection.
# ---------------------------------------------------------------------------


def test_detect_fiscal_year() -> None:
    assert detect_bs_fiscal_year("आर्थिक वर्ष 2074/75 को व्यय अनुमान") == 2074
    assert detect_bs_fiscal_year("Budget 2074-75") == 2074


def test_detect_fiscal_year_rejects_inconsistent_tail() -> None:
    assert detect_bs_fiscal_year("2074/79") is None


def test_detect_fiscal_year_none_when_absent() -> None:
    assert detect_bs_fiscal_year("संघीय संचित कोष") is None


# ---------------------------------------------------------------------------
# Robustness / contract.
# ---------------------------------------------------------------------------


def test_invariant_violation_surfaces_error_and_skips_row() -> None:
    """A matched row where total != recurrent + capital (columns mis-segmented)
    surfaces a typed ValueUnparseable AND is skipped — no wrong number persisted
    (Rule 6). Here total=100 but recurrent 60 + capital 30 = 90."""
    # 8 numeric tokens: actual, revised, TOTAL=100, RECUR=60, CAP=30, src×3.
    table = "999 खराब शीर्षक 50 80 1,00 60 30 90 0 0"
    out, errors = extract_dimensional_rows(table, _UNIT, BS_FY_2074_START)
    assert out == []  # row skipped — no fact reaches the table
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"
    assert isinstance(errors[0], ParserError)
    assert "999" in (errors[0].source_excerpt or "")


def test_invariant_satisfied_emits_no_error() -> None:
    """A row that satisfies total == recurrent + capital emits 3 facts, 0 errors."""
    table = "999 कुनै निकाय 50 80 90 60 30 90 0 0"  # total 90 == 60 + 30
    out, errors = extract_dimensional_rows(table, _UNIT, BS_FY_2074_START)
    assert errors == []
    assert len(out) == 3


def test_dash_measures_not_matched_as_head() -> None:
    """A row whose value cells are dashes is NOT the numeric budget-head shape —
    it never matches the row regex, so it is ignored (no fact, no error)."""
    table = "777 कुनै निकाय 1,00 2,00 - - - - - -"
    out, errors = extract_dimensional_rows(table, _UNIT, BS_FY_2074_START)
    assert out == []
    assert errors == []


def test_non_head_lines_ignored() -> None:
    """Lines without the <code><name><8 numbers> shape are layout noise."""
    table = "\n".join(
        [
            "संघीय संचित कोषबाट विनियोजन हुने व्यय अनुमानको सारांश",
            "(रू.हजारमा)",
            "अनुदान संख्या शीर्षक नाम",  # header, no numbers
            "101 राष्ट्रपति 1,00 2,00",  # too few numbers
        ]
    )
    out, errors = extract_dimensional_rows(table, _UNIT, BS_FY_2074_START)
    assert out == []
    assert errors == []


def test_ten_column_annex_row_rejected() -> None:
    """A 10-number-column functional-annex row (extra growth-percent cols) must
    NOT be parsed as a budget head (the exact-8-column guard)."""
    # 10 numbers: the real अनुसूची-१ shape (adds तुलनामा वृद्धि growth columns).
    # The wrong column count rejects the row outright, before any invariant check.
    table = (
        "357 सिंचाइ मन्त्रालय 48,04 17,80,22 79,50,36 34,27 79,16,09 23,68,07 0 55,82,29 0 3,47"
    )
    out, errors = extract_dimensional_rows(table, _UNIT, BS_FY_2074_START)
    assert out == []
    assert errors == []


def test_empty_text_yields_nothing() -> None:
    out, errors = extract_dimensional_rows("", _UNIT, BS_FY_2074_START)
    assert out == []
    assert errors == []


def test_idempotent() -> None:
    """Same input → identical output (parser contract / DATA_PIPELINE.md)."""
    first, _ = extract_dimensional_rows(_SUMMARY_TEXT, _UNIT, BS_FY_2074_START)
    second, _ = extract_dimensional_rows(_SUMMARY_TEXT, _UNIT, BS_FY_2074_START)
    assert [r.to_json_dict() for r in first] == [r.to_json_dict() for r in second]


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.2.0"


def test_missing_file_returns_failure() -> None:
    res = parse_redbook("nonexistent-redbook.pdf", "x")
    assert res.status == "failure"
    assert res.dimensional_rows == []
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_result_json_shape_matches_cli_contract(rows: list[DimensionalRowDraft]) -> None:
    """The result JSON must carry the keys the ingest CLI reads (mirrors DNE)."""
    result = RedbookResult(
        status="success",
        parser_version=PARSER_VERSION,
        dimensional_rows=rows,
        errors=[],
    )
    payload = result.to_json_dict()
    assert set(payload) == {"status", "parser_version", "dimensional_rows", "errors"}
    sample = payload["dimensional_rows"][0]
    assert set(sample) == {
        "base_indicator_slug", "base_indicator_name", "dimension_kind",
        "dimension_value", "dimension_label", "value", "unit",
        "reporting_period_type", "reporting_period_bs", "reporting_period_ad_start",
        "reporting_period_ad_end", "fiscal_year_bs", "fiscal_year_ad_label",
        "confidence_grade",
    }
    assert "T" in sample["reporting_period_ad_start"]  # ISO-8601 datetime


# ---------------------------------------------------------------------------
# Optional integration against the real FY 2074/75 PDF (skipped if absent).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real Red Book PDF not on disk")
def test_real_pdf_extracts_budget_allocation_facts() -> None:
    result = parse_redbook(str(REAL_PDF), "real-doc")
    assert result.status in ("success", "partial"), f"errors={result.errors}"
    totals = [
        r for r in result.dimensional_rows
        if r.base_indicator_slug == "budget-allocation-total"
    ]
    # FY2074/75 appropriation summary lists ~37 budget heads.
    assert len(totals) >= 30
    for r in result.dimensional_rows:
        assert r.unit == "npr_thousand"
        assert r.fiscal_year_bs == "2074/75"
        assert r.dimension_kind == "budget-head"
        assert r.value >= 0


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real Red Book PDF not on disk")
def test_real_pdf_grand_total_magnitude() -> None:
    """ADR-0011 verification: summed per-head total appropriation ≈ NPR 1,195 bn
    (the FY2074/75 appropriation-from-Consolidated-Fund grand total जम्मा row =
    1,195,378,131 thousand). Allow ±2% for any head the layout drops."""
    result = parse_redbook(str(REAL_PDF), "real-doc")
    grand = sum(
        r.value for r in result.dimensional_rows
        if r.base_indicator_slug == "budget-allocation-total"
    )
    expected = 1_195_378_131.0  # thousand NPR (published जम्मा)
    assert grand == pytest.approx(expected, rel=0.02)


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real Red Book PDF not on disk")
def test_real_pdf_total_equals_recurrent_plus_capital() -> None:
    """Every parsed head's total must equal recurrent + capital (structural
    correctness anchor) on the real PDF."""
    result = parse_redbook(str(REAL_PDF), "real-doc")
    by_head: dict[str, dict[str, float]] = {}
    for r in result.dimensional_rows:
        by_head.setdefault(r.dimension_value, {})[r.base_indicator_slug] = r.value
    checked = 0
    for measures in by_head.values():
        if {"budget-allocation-total", "budget-allocation-recurrent",
            "budget-allocation-capital"} <= set(measures):
            assert measures["budget-allocation-total"] == pytest.approx(
                measures["budget-allocation-recurrent"]
                + measures["budget-allocation-capital"]
            )
            checked += 1
    assert checked >= 30


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real Red Book PDF not on disk")
def test_cli_emits_valid_json_on_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "mof_redbook.parser", str(REAL_PDF), "doc"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] in ("success", "partial")
    assert payload["parser_version"] == PARSER_VERSION
    assert len(payload["dimensional_rows"]) > 0
