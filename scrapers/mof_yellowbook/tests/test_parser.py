"""Tests for the MoF / DPM-Office Yellow Book public-enterprise parser.

The real source is a multi-MB Devanagari PDF whose only deterministically
parseable per-enterprise matrix is Annex-1 (loan-investment-by-enterprise) of
the FY2080/81 edition; most other tables are CID-broken or Preeti-encoded (see
the parser module docstring). We do NOT commit the binary (ADR-0003 / source
profile) and no PDF-writing library is in the venv — so the deterministic core
(``extract_dimensional_rows``) is exercised against a SYNTHESIZED tiny Annex-1
table that reproduces the real geometry (sector sub-headers, serial-led rows,
total rows, Devanagari numerals, blank/zero values).

A single optional integration test runs the full ``parse_yellowbook`` against
the real PDF when it is on disk; it is skipped otherwise so CI stays green.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserError
from mof_yellowbook import PARSER_VERSION, parse_yellowbook
from mof_yellowbook.parser import (
    DimensionalRowDraft,
    _detect_fiscal_year_bs,
    _slugify_enterprise,
    extract_dimensional_rows,
)

PERIOD_TOLERANCE = timedelta(days=40)  # mid-month AD approximation slack
FY_2080_81_START = 2080

# Real PDF, if Mother has the corpus in the worktree. Optional integration only.
REAL_PDF = (
    Path(__file__).resolve().parents[3]
    / "Financial Data"
    / "mof_documents"
    / "yellowbook"
    / "Webiste Uploaded Yellow_sdwyi9v.pdf"
)


# ---------------------------------------------------------------------------
# Synthesized Annex-1 table — mirrors the real 10-column geometry. Columns:
# [serial, name, share, loan, kista, byaj, ..., deposit, mukti] (cols ≥4 unused
# by the parser; included so widths match the real extract_tables() output).
# ---------------------------------------------------------------------------

_ANNEX1_TABLE: list[list[object]] = [
    ["अनसु ूची-1", None, None, None, None, None, None, None, None, None],
    ["आ.व.२०८०/८१ को अन्त्य ... ऋण लगानी", None, None, None, None, None, None, None, None, None],
    ["(रु. हजारमा)", None, None, None, None, None, None, None, None, None],
    # Header: cols are [serial, name, share(शेयर), loan(ऋण), kista, byaj, ...].
    ["�.सं.", "संस्थाको नाम", "शेयर", "ऋण", "�कस्ता", "ब्याज", "साँवा", "ब्याज", "�डपोिजट", "म�ु ती"],
    # Sector sub-header: name carries "क्षेत्र", value columns blank.
    ["", "औद्योगिक क्षेत्र", "", None, None, None, None, None, None, None],
    ["१", "दुग्ध विकास संस्थान", "366424", "649972", "0", "1021139", "0", "17500", "0", "0"],
    ["२", "हेटौंडा सिमेन्ट उद्योग लि.", "900685", "120000", "120000", "357856", "0", "0", "0", "0"],
    # An enterprise with a zero loan (real 0 must be preserved, not dropped).
    ["३", "जनकपुर चुरोट कारखाना लि.", "40837", "0", "0", "0", "0", "0", "0", "0"],
    # Sub-total row inside the sector — must be skipped.
    ["जम्मा", None, "1307946", "769972", None, None, None, None, None, None],
    ["", "वित्तीय क्षेत्र", "", None, None, None, None, None, None, None],
    ["४", "नेपाल बैंक लि.", "7493951", "-", "0", "0", "0", "0", "0", "0"],
    # Grand total — skipped.
    ["कूल जम्मा", None, "8801897", "769972", None, None, None, None, None, None],
    ["�ोतः-सावजर् �नक ऋण व्यवस्थापन कायार्लय", None, None, None, None, None, None, None, None, None],
]

# Expected enterprises and their (share, loan) — loan is None when source is "-".
_EXPECTED: dict[str, tuple[float, float | None]] = {
    "दुग्ध विकास संस्थान": (366424.0, 649972.0),
    "हेटौंडा सिमेन्ट उद्योग लि.": (900685.0, 120000.0),
    "जनकपुर चुरोट कारखाना लि.": (40837.0, 0.0),  # zero loan preserved
    "नेपाल बैंक लि.": (7493951.0, None),  # loan "-" → no loan fact
}


@pytest.fixture(scope="module")
def rows() -> list[DimensionalRowDraft]:
    out, errors = extract_dimensional_rows(_ANNEX1_TABLE, FY_2080_81_START)
    assert errors == [], f"unexpected errors: {errors}"
    return out


def _facts_for(rows: list[DimensionalRowDraft], slug: str) -> dict[str, float]:
    return {r.dimension_label: r.value for r in rows if r.base_indicator_slug == slug}


# ---------------------------------------------------------------------------
# Core extraction.
# ---------------------------------------------------------------------------


def test_share_facts_one_per_enterprise(rows: list[DimensionalRowDraft]) -> None:
    shares = _facts_for(rows, "soe-government-share")
    assert set(shares) == set(_EXPECTED)
    for name, (share, _loan) in _EXPECTED.items():
        assert shares[name] == pytest.approx(share)


def test_loan_facts_skip_dash_keep_zero(rows: list[DimensionalRowDraft]) -> None:
    loans = _facts_for(rows, "soe-loan-principal")
    expected_loan_names = {n for n, (_s, loan) in _EXPECTED.items() if loan is not None}
    assert set(loans) == expected_loan_names
    # Zero loan is preserved as a real fact (not fabricated, not dropped).
    assert loans["जनकपुर चुरोट कारखाना लि."] == pytest.approx(0.0)
    # Dash loan produced NO fact.
    assert "नेपाल बैंक लि." not in loans


def test_total_row_count(rows: list[DimensionalRowDraft]) -> None:
    # 4 share facts + 3 loan facts (Nepal Bank's loan is a dash) = 7.
    assert len(rows) == 7


def test_sector_and_total_rows_excluded(rows: list[DimensionalRowDraft]) -> None:
    labels = {r.dimension_label for r in rows}
    assert not any("क्षेत्र" in label for label in labels)
    assert "जम्मा" not in labels
    assert "कूल जम्मा" not in labels


def test_dimension_kind_and_unit(rows: list[DimensionalRowDraft]) -> None:
    for r in rows:
        assert r.dimension_kind == "public_enterprise"
        assert r.unit == "npr_thousand"  # ADR-0011: header "(रु. हजारमा)" = thousand
        assert r.confidence_grade == "B"
        assert r.base_indicator_slug in {"soe-government-share", "soe-loan-principal"}


def test_period_is_annual_bs_fy(rows: list[DimensionalRowDraft]) -> None:
    for r in rows:
        assert r.reporting_period_type == "annual"
        assert r.reporting_period_bs == "2080/81"
        assert r.fiscal_year_bs == "2080/81"
        assert r.fiscal_year_ad_label == "2023/24"  # BS 2080 → AD 2023 (+57, ADR-0013)


def test_annual_span_brackets_fiscal_year(rows: list[DimensionalRowDraft]) -> None:
    expected_start = datetime(2023, 7, 15, tzinfo=UTC)
    for r in rows:
        assert abs(r.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
        assert r.reporting_period_ad_end > r.reporting_period_ad_start


def test_magnitude_sanity_npr_thousand(rows: list[DimensionalRowDraft]) -> None:
    """ADR-0011 magnitude check: Nepal Bank share = 7,493,951 thousand =
    NPR 7.49 billion — the right order of magnitude for a large listed SOE."""
    shares = _facts_for(rows, "soe-government-share")
    npr = shares["नेपाल बैंक लि."] * 1_000  # thousand → rupees
    assert 5e9 < npr < 1e10


def test_dimension_value_is_kebab_and_distinct(rows: list[DimensionalRowDraft]) -> None:
    for r in rows:
        assert r.dimension_value
        assert " " not in r.dimension_value
        assert r.dimension_value == r.dimension_value.strip("-")
    # Distinct enterprises keep distinct slugs (Devanagari preserved).
    share_slugs = {
        r.dimension_value for r in rows if r.base_indicator_slug == "soe-government-share"
    }
    assert len(share_slugs) == len(_EXPECTED)


def test_value_unparseable_when_both_columns_blank() -> None:
    """A serial-led enterprise row whose share AND loan are both unparseable
    surfaces a typed ValueUnparseable — data loss is visible, never silent."""
    table = [
        ["�.सं.", "संस्थाको नाम", "शेयर", "ऋण", None, None],
        ["१", "रहस्यमय संस्थान लि.", "-", "", None, None],
    ]
    out, errors = extract_dimensional_rows(table, FY_2080_81_START)
    assert out == []
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"
    assert isinstance(errors[0], ParserError)


def test_devanagari_numeral_value_parses() -> None:
    """Values written in Devanagari numerals are normalised to ASCII floats."""
    table = [
        ["�.सं.", "संस्थाको नाम", "शेयर", "ऋण", None, None],
        ["१", "नमुना संस्थान", "१२३४५", "-", None, None],
    ]
    out, errors = extract_dimensional_rows(table, FY_2080_81_START)
    assert errors == []
    assert len(out) == 1
    assert out[0].value == pytest.approx(12345.0)


def test_empty_table_yields_nothing() -> None:
    out, errors = extract_dimensional_rows([], FY_2080_81_START)
    assert out == []
    assert errors == []


def test_idempotent() -> None:
    """Same input → identical output (parser contract / DATA_PIPELINE.md)."""
    first, _ = extract_dimensional_rows(_ANNEX1_TABLE, FY_2080_81_START)
    second, _ = extract_dimensional_rows(_ANNEX1_TABLE, FY_2080_81_START)
    assert [r.to_json_dict() for r in first] == [r.to_json_dict() for r in second]


# ---------------------------------------------------------------------------
# Header FY detection + slug helper.
# ---------------------------------------------------------------------------


def test_detect_fiscal_year_bs_from_header() -> None:
    assert _detect_fiscal_year_bs("आ.व.२०८०/८१ को अन्त्य सम्ममा ...") == 2080
    assert _detect_fiscal_year_bs("आ.व. 2079/80 को अन्त्य") == 2079


def test_detect_fiscal_year_rejects_inconsistent_tail() -> None:
    # Tail must equal (lead + 1) mod 100; a mismatch is not a fiscal year.
    assert _detect_fiscal_year_bs("आ.व.२०८०/८५ बेमेल") is None


def test_detect_fiscal_year_none_when_absent() -> None:
    assert _detect_fiscal_year_bs("रकम (रू. लाखमा)") is None


def test_slugify_preserves_devanagari_distinctness() -> None:
    a = _slugify_enterprise("नेपाल बैंक लि.")
    b = _slugify_enterprise("कृषि विकास बैंक लि.")
    assert a != b
    assert " " not in a and "." not in a


# ---------------------------------------------------------------------------
# Contract / robustness.
# ---------------------------------------------------------------------------


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


def test_missing_file_returns_failure() -> None:
    res = parse_yellowbook("nonexistent-yellowbook.pdf", "x")
    assert res.status == "failure"
    assert res.dimensional_rows == []
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_result_json_shape_matches_dne_cli_contract(rows: list[DimensionalRowDraft]) -> None:
    """The result JSON must carry the keys the cloned DNE ingest CLI reads."""
    from mof_yellowbook.parser import YellowbookResult

    result = YellowbookResult(
        status="success", parser_version=PARSER_VERSION, dimensional_rows=rows, errors=[]
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
# Optional integration against the real PDF (skipped if absent).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real Yellow Book PDF not on disk")
def test_real_pdf_extracts_enterprise_facts() -> None:
    result = parse_yellowbook(str(REAL_PDF), "real-doc")
    assert result.status in ("success", "partial"), f"errors={result.errors}"
    shares = [r for r in result.dimensional_rows if r.base_indicator_slug == "soe-government-share"]
    loans = [r for r in result.dimensional_rows if r.base_indicator_slug == "soe-loan-principal"]
    # FY2080/81 Annex-1 lists ~42 enterprises.
    assert len(shares) >= 35
    assert len(loans) >= 20
    for r in result.dimensional_rows:
        assert r.dimension_kind == "public_enterprise"
        assert r.unit == "npr_thousand"
        assert r.value >= 0


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real Yellow Book PDF not on disk")
def test_cli_emits_valid_json_on_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "mof_yellowbook.parser", str(REAL_PDF), "doc"],
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
