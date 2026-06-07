"""Tests for the MoF White Book foreign-aid parser.

The real source is a multi-page PDF whose two clean English summary tables
(Ministrywise + Development-Partnerwise) are the deterministically parseable
target; older editions are Preeti-encoded and one file is a mislabelled
CID-broken intergovernmental-transfer book (see the parser module docstring). We
do NOT commit the binaries (ADR-0003 / source profile) and no PDF-writing library
is in the venv — so the deterministic core (``extract_dimensional_rows``) is
exercised against SYNTHESIZED tiny tables that reproduce the real 12-/13-column
geometry (code-led rows, a Total row, a preserved zero, a dropped dash, the
ministrywise GoN-Budget column offset).

Optional integration tests run the full ``parse_whitebook`` + CLI against the
real FY 2020/21 edition when it is on disk; they are skipped otherwise so CI stays
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
from mof_whitebook import PARSER_VERSION, WhitebookResult, parse_whitebook
from mof_whitebook.parser import (
    _DONOR_SPEC,
    _SECTOR_SPEC,
    DimensionalRowDraft,
    detect_ad_fiscal_year,
    detect_unit,
    extract_dimensional_rows,
)

PERIOD_TOLERANCE = timedelta(days=40)  # mid-month AD approximation slack
# AD 2020/21 → BS 2077/78 (+57, ADR-0013).
AD_FY_2020_LEAD = 2020
BS_FY_2077_START = 2077

# Real PDF, if Mother has the corpus in the worktree. Optional integration only.
REAL_PDF = (
    Path(__file__).resolve().parents[3]
    / "Financial Data"
    / "mof_documents"
    / "whitebook"
    / "Source Book White Book FY 2020-21_dkjqgrt.pdf"
)


# ---------------------------------------------------------------------------
# Synthesized DONOR table — 12 cols. Layout:
#   0 code | 1 name | 2 cash | 3 reimb | 4 direct | 5 commodity | 6 TOTAL GRANT
#   | 7 loan-direct | 8 loan-reimb | 9 loan-cash | 10 TOTAL LOAN | 11 Total
# ---------------------------------------------------------------------------

_DONOR_TABLE: list[list[object]] = [
    # Header row (no leading code) — skipped.
    ["Donor", "", "Cash", "Reimbursable", "Direct Payment", "Commodity",
     "Total Grant", "Direct Payment", "Reimbursable", "Cash", "Total Loan", "Total"],
    # ADB: grant 33,526 + loan 564,947.
    ["2101001", "ADB - General", "0", "5,165", "28,361", "0", "33,526",
     "292,328", "262,932", "9,687", "564,947", "598,473"],
    # ADB/PBL: grant 0 (preserved!) + loan 253,500.
    ["2101004", "ADB/PBL", "0", "0", "0", "0", "0",
     "0", "0", "253,500", "253,500", "253,500"],
    # UNDP: grant 460 + loan blank (dash) → no loan fact.
    ["2109002", "UNDP", "460", "0", "0", "0", "460",
     "-", "-", "-", "-", "460"],
    # Grand total — skipped.
    ["Total", "49,447", "300,520", "235,885", "19,425", "605,277",
     "854,284", "970,287", "1,170,422", "2,994,993", "3,600,270", ""],
]

# Expected donor (grant, loan); loan None when source is dash/blank.
_DONOR_EXPECTED: dict[str, tuple[float, float | None]] = {
    "ADB - General": (33526.0, 564947.0),
    "ADB/PBL": (0.0, 253500.0),  # zero grant preserved
    "UNDP": (460.0, None),  # dash loan → no loan fact
}


# ---------------------------------------------------------------------------
# Synthesized SECTOR (ministrywise) table — 13 cols (extra GoN-Budget at col 2):
#   0 code | 1 name | 2 GoN | 3 cash | 4 reimb | 5 direct | 6 commodity
#   | 7 TOTAL GRANT | 8 loan-direct | 9 loan-reimb | 10 loan-cash
#   | 11 TOTAL LOAN | 12 Total
# ---------------------------------------------------------------------------

_SECTOR_TABLE: list[list[object]] = [
    ["Ministry", "", "GoN", "Cash", "Reimbursable", "Direct Payment", "Commodity",
     "Total Grant", "Direct Payment", "Reimbursable", "Cash", "Total Loan", "Total"],
    # 305 MoF: grant 68,543 + loan 149,687.
    ["305", "Ministry of Finance", "127,340", "0", "11,271", "57,272", "0",
     "68,543", "0", "0", "149,687", "149,687", "345,570"],
    # 314 Home: grant 15,000 + loan 6,992.
    ["314", "Ministry of Home Affairs", "1,336,991", "0", "15,000", "0", "0",
     "15,000", "0", "6,992", "0", "6,992", "1,358,983"],
    ["Total", "8,500,626", "49,447", "300,520", "235,885", "19,425", "605,277",
     "854,284", "970,287", "1,170,422", "2,994,993", "12,100,896", ""],
]

_SECTOR_EXPECTED: dict[str, tuple[float, float]] = {
    "Ministry of Finance": (68543.0, 149687.0),
    "Ministry of Home Affairs": (15000.0, 6992.0),
}


@pytest.fixture(scope="module")
def donor_rows() -> list[DimensionalRowDraft]:
    out, errors = extract_dimensional_rows(
        _DONOR_TABLE, _DONOR_SPEC, "npr_lakh", BS_FY_2077_START
    )
    assert errors == [], f"unexpected errors: {errors}"
    return out


@pytest.fixture(scope="module")
def sector_rows() -> list[DimensionalRowDraft]:
    out, errors = extract_dimensional_rows(
        _SECTOR_TABLE, _SECTOR_SPEC, "npr_lakh", BS_FY_2077_START
    )
    assert errors == [], f"unexpected errors: {errors}"
    return out


def _facts_for(rows: list[DimensionalRowDraft], slug: str) -> dict[str, float]:
    return {r.dimension_label: r.value for r in rows if r.base_indicator_slug == slug}


# ---------------------------------------------------------------------------
# Donor-table extraction.
# ---------------------------------------------------------------------------


def test_donor_grant_facts(donor_rows: list[DimensionalRowDraft]) -> None:
    grants = _facts_for(donor_rows, "foreign-aid-grant")
    assert set(grants) == set(_DONOR_EXPECTED)
    for name, (grant, _loan) in _DONOR_EXPECTED.items():
        assert grants[name] == pytest.approx(grant)


def test_donor_loan_facts_skip_dash_keep_zero(donor_rows: list[DimensionalRowDraft]) -> None:
    loans = _facts_for(donor_rows, "foreign-aid-loan")
    expected = {n for n, (_g, loan) in _DONOR_EXPECTED.items() if loan is not None}
    assert set(loans) == expected
    # ADB/PBL has a real loan; UNDP's dash loan produced NO fact.
    assert "UNDP" not in loans
    assert loans["ADB/PBL"] == pytest.approx(253500.0)


def test_donor_zero_grant_preserved(donor_rows: list[DimensionalRowDraft]) -> None:
    """A genuine source 0 (ADB/PBL grant) is kept as a fact, never dropped."""
    grants = _facts_for(donor_rows, "foreign-aid-grant")
    assert grants["ADB/PBL"] == pytest.approx(0.0)


def test_donor_total_row_excluded(donor_rows: list[DimensionalRowDraft]) -> None:
    labels = {r.dimension_label for r in donor_rows}
    assert "Total" not in labels
    assert all(not lbl.lower().startswith("total") for lbl in labels)


def test_donor_dimension_kind_and_unit(donor_rows: list[DimensionalRowDraft]) -> None:
    for r in donor_rows:
        assert r.dimension_kind == "donor"
        assert r.unit == "npr_lakh"
        assert r.confidence_grade == "B"
        assert r.base_indicator_slug in {"foreign-aid-grant", "foreign-aid-loan"}


def test_donor_row_count(donor_rows: list[DimensionalRowDraft]) -> None:
    # 3 grant facts + 2 loan facts (UNDP loan is a dash) = 5.
    assert len(donor_rows) == 5


# ---------------------------------------------------------------------------
# Sector (ministrywise) extraction — the GoN-Budget column offset.
# ---------------------------------------------------------------------------


def test_sector_grant_facts_use_offset_columns(sector_rows: list[DimensionalRowDraft]) -> None:
    """Ministrywise has an extra GoN column → Total-Grant is col 7 (not 6)."""
    grants = _facts_for(sector_rows, "foreign-aid-grant")
    assert set(grants) == set(_SECTOR_EXPECTED)
    for name, (grant, _loan) in _SECTOR_EXPECTED.items():
        assert grants[name] == pytest.approx(grant)


def test_sector_loan_facts_use_offset_columns(sector_rows: list[DimensionalRowDraft]) -> None:
    loans = _facts_for(sector_rows, "foreign-aid-loan")
    for name, (_grant, loan) in _SECTOR_EXPECTED.items():
        assert loans[name] == pytest.approx(loan)


def test_sector_dimension_kind(sector_rows: list[DimensionalRowDraft]) -> None:
    for r in sector_rows:
        assert r.dimension_kind == "sector"


def test_sector_does_not_read_gon_budget_as_grant(sector_rows: list[DimensionalRowDraft]) -> None:
    """Regression: MoF GoN Budget is 127,340; the grant must be 68,543 (col 7),
    proving the offset is applied and the GoN column is not mistaken for grant."""
    grants = _facts_for(sector_rows, "foreign-aid-grant")
    assert grants["Ministry of Finance"] == pytest.approx(68543.0)
    assert grants["Ministry of Finance"] != pytest.approx(127340.0)


# ---------------------------------------------------------------------------
# Period dating (ADR-0013).
# ---------------------------------------------------------------------------


def test_period_is_annual_bs_fy(donor_rows: list[DimensionalRowDraft]) -> None:
    for r in donor_rows:
        assert r.reporting_period_type == "annual"
        assert r.reporting_period_bs == "2077/78"
        assert r.fiscal_year_bs == "2077/78"
        assert r.fiscal_year_ad_label == "2020/21"  # BS 2077 → AD 2020 (+57)


def test_annual_span_brackets_fiscal_year(donor_rows: list[DimensionalRowDraft]) -> None:
    expected_start = datetime(2020, 7, 15, tzinfo=UTC)
    for r in donor_rows:
        assert abs(r.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
        assert r.reporting_period_ad_end > r.reporting_period_ad_start


def test_magnitude_sanity_npr_lakh(donor_rows: list[DimensionalRowDraft]) -> None:
    """ADR-0011: ADB loan = 564,947 lakh = NPR 56.5 billion — the right order of
    magnitude for a top multilateral lender's annual portfolio."""
    loans = _facts_for(donor_rows, "foreign-aid-loan")
    npr = loans["ADB - General"] * 100_000  # lakh → rupees
    assert 1e10 < npr < 1e11


# ---------------------------------------------------------------------------
# Unit detection (ADR-0011) — the per-edition annotation.
# ---------------------------------------------------------------------------


def test_detect_unit_lakh() -> None:
    assert detect_unit("Some caption (Rs. in '00000')") == "npr_lakh"


def test_detect_unit_thousand() -> None:
    assert detect_unit("Donor Summary (NRs'000s)") == "npr_thousand"
    assert detect_unit("Details ( Rs. 000 )") == "npr_thousand"


def test_detect_unit_none_when_absent() -> None:
    # Table-of-Contents lines carry the caption but no unit annotation.
    assert detect_unit("Summary of Ministrywise Development Partners i") is None


def test_detect_unit_lakh_not_confused_with_thousand() -> None:
    """Five zeros (lakh) must not be read as the three-zero thousand form."""
    assert detect_unit("(Rs. in '00000')") == "npr_lakh"


# ---------------------------------------------------------------------------
# Fiscal-year detection.
# ---------------------------------------------------------------------------


def test_detect_fiscal_year() -> None:
    assert detect_ad_fiscal_year("Fiscal Year 2020/21") == 2020
    assert detect_ad_fiscal_year("Fiscal Year 2015-16") == 2015


def test_detect_fiscal_year_rejects_inconsistent_tail() -> None:
    assert detect_ad_fiscal_year("Fiscal Year 2020/25") is None


def test_detect_fiscal_year_none_when_absent() -> None:
    assert detect_ad_fiscal_year("Summary of Ministrywise Donor Source") is None


# ---------------------------------------------------------------------------
# Robustness / contract.
# ---------------------------------------------------------------------------


def test_value_unparseable_when_both_totals_garbage() -> None:
    """A code-led row whose BOTH total cells are non-empty but unparseable
    surfaces a typed ValueUnparseable — data loss is visible, never silent."""
    table = [
        ["2199999", "Bad Donor", "0", "0", "0", "0", "n/m",
         "0", "0", "0", "n/m", "0"],
    ]
    out, errors = extract_dimensional_rows(table, _DONOR_SPEC, "npr_lakh", BS_FY_2077_START)
    assert out == []
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"
    assert isinstance(errors[0], ParserError)


def test_dimension_value_is_kebab_and_distinct(donor_rows: list[DimensionalRowDraft]) -> None:
    for r in donor_rows:
        assert r.dimension_value
        assert " " not in r.dimension_value
        assert r.dimension_value == r.dimension_value.strip("-")
    grant_slugs = {
        r.dimension_value for r in donor_rows if r.base_indicator_slug == "foreign-aid-grant"
    }
    assert len(grant_slugs) == len(_DONOR_EXPECTED)


def test_short_rows_ignored() -> None:
    """Rows narrower than the table's column count are layout noise — skipped."""
    table = [["2101001", "ADB", "0", "1"]]  # far fewer than 12 cols
    out, errors = extract_dimensional_rows(table, _DONOR_SPEC, "npr_lakh", BS_FY_2077_START)
    assert out == []
    assert errors == []


def test_empty_table_yields_nothing() -> None:
    out, errors = extract_dimensional_rows([], _DONOR_SPEC, "npr_lakh", BS_FY_2077_START)
    assert out == []
    assert errors == []


def test_idempotent() -> None:
    """Same input → identical output (parser contract / DATA_PIPELINE.md)."""
    first, _ = extract_dimensional_rows(_DONOR_TABLE, _DONOR_SPEC, "npr_lakh", BS_FY_2077_START)
    second, _ = extract_dimensional_rows(_DONOR_TABLE, _DONOR_SPEC, "npr_lakh", BS_FY_2077_START)
    assert [r.to_json_dict() for r in first] == [r.to_json_dict() for r in second]


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


def test_missing_file_returns_failure() -> None:
    res = parse_whitebook("nonexistent-whitebook.pdf", "x")
    assert res.status == "failure"
    assert res.dimensional_rows == []
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_result_json_shape_matches_cli_contract(donor_rows: list[DimensionalRowDraft]) -> None:
    """The result JSON must carry the keys the ingest CLI reads (mirrors DNE)."""
    result = WhitebookResult(
        status="success",
        parser_version=PARSER_VERSION,
        dimensional_rows=donor_rows,
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
# Optional integration against the real FY 2020/21 PDF (skipped if absent).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real White Book PDF not on disk")
def test_real_pdf_extracts_foreign_aid_facts() -> None:
    result = parse_whitebook(str(REAL_PDF), "real-doc")
    assert result.status in ("success", "partial"), f"errors={result.errors}"
    donor_grants = [
        r for r in result.dimensional_rows
        if r.dimension_kind == "donor" and r.base_indicator_slug == "foreign-aid-grant"
    ]
    sector_grants = [
        r for r in result.dimensional_rows
        if r.dimension_kind == "sector" and r.base_indicator_slug == "foreign-aid-grant"
    ]
    # FY2020/21 lists ~44 donors and ~23 ministries.
    assert len(donor_grants) >= 30
    assert len(sector_grants) >= 15
    for r in result.dimensional_rows:
        assert r.unit == "npr_lakh"  # FY2020/21 annotation = "(Rs. in '00000')"
        assert r.fiscal_year_bs == "2077/78"
        assert r.value >= 0


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real White Book PDF not on disk")
def test_real_pdf_donor_total_reconciles() -> None:
    """The summed per-donor grant + loan must equal the published Total row
    (grants 605,277 + loans 2,994,993 lakh = NPR 360.0 billion for FY2020/21)."""
    result = parse_whitebook(str(REAL_PDF), "real-doc")
    g = sum(
        r.value for r in result.dimensional_rows
        if r.dimension_kind == "donor" and r.base_indicator_slug == "foreign-aid-grant"
    )
    loan = sum(
        r.value for r in result.dimensional_rows
        if r.dimension_kind == "donor" and r.base_indicator_slug == "foreign-aid-loan"
    )
    assert g == pytest.approx(605_277.0)
    assert loan == pytest.approx(2_994_993.0)


@pytest.mark.skipif(not REAL_PDF.exists(), reason="real White Book PDF not on disk")
def test_cli_emits_valid_json_on_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "mof_whitebook.parser", str(REAL_PDF), "doc"],
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
