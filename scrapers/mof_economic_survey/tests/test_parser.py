"""Tests for the MoF Economic Survey statistical-annex parser.

The real sources are 5–18 MB PDFs with wildly mixed encoding (see the parser
module docstring + ADR-0016). The one cleanly, deterministically parseable
high-value table is **Annex 6.1: Number of Workers having Foreign Employment
Permit** in the English 2023/24 edition; the headline MACRO annex (GDP/prices/
fiscal) is RTL-mirrored and the two Nepali editions' annex is CID-broken — both
deferred. We do NOT commit the binaries (ADR-0003 / source profile) and no
PDF-writing library is in the venv, so the deterministic core
(``extract_foreign_employment_rows`` + helpers + ``classify_annex_text``) is
exercised against a SYNTHESIZED Annex-6.1 table that mirrors the real geometry.

Optional integration tests run the full ``parse`` (and the ``__main__`` CLI)
against the real PDFs when present (EN → ``partial`` with Annex-6.1 rows +
deferral errors; Nepali editions → documented ``failure``); skipped otherwise so
CI stays green.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _common.types import ParserError, ParserResult, StagingRowDraft
from mof_economic_survey import PARSER_VERSION, parse
from mof_economic_survey.parser import (
    SOURCE_ID,
    _ad_fy_to_bs_start,
    _full_year_lead,
    _parse_count,
    classify_annex_text,
    extract_foreign_employment_rows,
)

PERIOD_TOLERANCE = timedelta(days=40)  # mid-month AD approximation slack

TOTAL_SLUG = "economic-survey-foreign-employment-permits-total"
FEMALE_SLUG = "economic-survey-foreign-employment-permits-female"
MALE_SLUG = "economic-survey-foreign-employment-permits-male"
EXPECTED_SLUGS = frozenset({TOTAL_SLUG, FEMALE_SLUG, MALE_SLUG})


# ---------------------------------------------------------------------------
# Synthesized Annex-6.1 table — mirrors the real page-405 geometry exactly.
# Columns: [Fiscal Year, Female, Male, Total]. Includes the cumulative and
# partial/starred rows that MUST be skipped.
# ---------------------------------------------------------------------------

_ANNEX_6_1_TABLE: list[list[object]] = [
    ["Fiscal Year", "Female", "Male", "Total"],
    ["Upto July 2015", "135806", "3065462", "3201268"],  # cumulative → skip
    ["2015/16", "18377", "384797", "403174"],
    ["2016/17", "20189", "363304", "383493"],
    ["2021/22", "33062", "315806", "348867"],
    ["2022/23", "53500", "440724", "494224"],
    ["2023/24*", "38758", "246624", "285382"],  # partial/starred → skip
    ["Upto Mid March 2024", "368067", "5601169", "5969235"],  # cumulative → skip
]

# Full-year rows in the fixture (the starred + cumulative rows are excluded).
_FULL_YEARS: dict[str, tuple[float, float, float]] = {
    # fy_label: (female, male, total)
    "2015/16": (18377.0, 384797.0, 403174.0),
    "2016/17": (20189.0, 363304.0, 383493.0),
    "2021/22": (33062.0, 315806.0, 348867.0),
    "2022/23": (53500.0, 440724.0, 494224.0),
}


@pytest.fixture(scope="module")
def rows() -> list[StagingRowDraft]:
    out, errors = extract_foreign_employment_rows(_ANNEX_6_1_TABLE)
    assert errors == [], f"unexpected errors: {errors}"
    return out


def _by(rows: list[StagingRowDraft], slug: str) -> dict[str, float]:
    return {r.fiscal_year_ad_label: r.value for r in rows if r.indicator_slug_raw == slug}


# ---------------------------------------------------------------------------
# Core extraction — Annex 6.1.
# ---------------------------------------------------------------------------


def test_row_count_full_years_times_measures(rows: list[StagingRowDraft]) -> None:
    # 4 full years × 3 measures (Total/Female/Male) = 12; cumulative + starred
    # rows excluded.
    assert len(rows) == len(_FULL_YEARS) * 3


def test_all_three_measures_present(rows: list[StagingRowDraft]) -> None:
    assert {r.indicator_slug_raw for r in rows} == EXPECTED_SLUGS


def test_total_values(rows: list[StagingRowDraft]) -> None:
    totals = _by(rows, TOTAL_SLUG)
    for fy, (_f, _m, total) in _FULL_YEARS.items():
        ad_label = fy  # source labels are AD fiscal years
        assert totals[ad_label] == pytest.approx(total)


def test_female_male_values(rows: list[StagingRowDraft]) -> None:
    females = _by(rows, FEMALE_SLUG)
    males = _by(rows, MALE_SLUG)
    for fy, (female, male, _t) in _FULL_YEARS.items():
        assert females[fy] == pytest.approx(female)
        assert males[fy] == pytest.approx(male)


def test_cumulative_and_starred_rows_skipped(rows: list[StagingRowDraft]) -> None:
    # No row should correspond to the cumulative ("Upto …") or partial ("2023/24*")
    # rows. The 2023/24 AD label (the starred partial year) must be absent.
    ad_labels = {r.fiscal_year_ad_label for r in rows}
    assert "2023/24" not in ad_labels
    # Only the four full years appear.
    assert ad_labels == set(_FULL_YEARS)


def test_unit_is_count(rows: list[StagingRowDraft]) -> None:
    for r in rows:
        assert r.unit == "count"


def test_confidence_grade_b(rows: list[StagingRowDraft]) -> None:
    for r in rows:
        assert r.confidence_grade_proposed == "B"


def test_period_is_annual_with_bs_fy(rows: list[StagingRowDraft]) -> None:
    for r in rows:
        assert r.reporting_period_type == "annual"
        # AD 2022/23 → BS 2079/80 (+57); AD 2015/16 → BS 2072/73.
        assert r.reporting_period_bs == f"FY {r.fiscal_year_bs}"
        assert isinstance(r.value, float)
        assert r.value >= 0
    by_ad = {r.fiscal_year_ad_label: r.fiscal_year_bs for r in rows}
    assert by_ad["2022/23"] == "2079/80"
    assert by_ad["2015/16"] == "2072/73"


def test_annual_span_brackets_fiscal_year(rows: list[StagingRowDraft]) -> None:
    by_ad = {r.fiscal_year_ad_label: r for r in rows}
    r = by_ad["2022/23"]
    expected_start = datetime(2022, 7, 15, tzinfo=UTC)
    assert abs(r.reporting_period_ad_start - expected_start) <= PERIOD_TOLERANCE
    assert r.reporting_period_ad_end > r.reporting_period_ad_start


def test_parser_notes_present(rows: list[StagingRowDraft]) -> None:
    for r in rows:
        assert r.parser_notes
        assert "Annex 6.1" in r.parser_notes


def test_magnitude_sanity_permits(rows: list[StagingRowDraft]) -> None:
    """ADR-0011 magnitude check: ~400–500k labour permits/year is the right
    order for Nepal; the FY2022/23 total is 494,224."""
    totals = _by(rows, TOTAL_SLUG)
    assert 400_000 < totals["2022/23"] < 600_000
    # Female + Male reconcile to Total in the source.
    females = _by(rows, FEMALE_SLUG)
    males = _by(rows, MALE_SLUG)
    assert females["2022/23"] + males["2022/23"] == pytest.approx(totals["2022/23"])


def test_value_unparseable_surfaces_typed_error() -> None:
    """A full-year row with a non-empty but unparseable measure cell surfaces a
    typed ValueUnparseable — data loss is visible, never silent (Rule 6)."""
    table = [
        ["Fiscal Year", "Female", "Male", "Total"],
        ["2020/21", "7178", "n.a.", "72081"],  # male cell garbage but non-empty
    ]
    out, errors = extract_foreign_employment_rows(table)
    # Female + Total still emit; Male errors.
    male = [r for r in out if r.indicator_slug_raw == MALE_SLUG]
    assert male == []
    assert any(e.error_class == "ValueUnparseable" for e in errors)
    assert all(isinstance(e, ParserError) for e in errors)


def test_blank_cell_is_dropped_not_zero() -> None:
    """A blank measure cell yields NO fact (never fabricated as 0) and NO error
    (blank is an expected absence, not a parse failure)."""
    table = [
        ["Fiscal Year", "Female", "Male", "Total"],
        ["2019/20", "", "172251", "190453"],
    ]
    out, errors = extract_foreign_employment_rows(table)
    females = [r for r in out if r.indicator_slug_raw == FEMALE_SLUG]
    assert females == []  # blank dropped
    assert errors == []  # blank is not an error


def test_genuine_zero_preserved() -> None:
    table = [
        ["Fiscal Year", "Female", "Male", "Total"],
        ["2018/19", "0", "215633", "215633"],
    ]
    out, _ = extract_foreign_employment_rows(table)
    females = [r for r in out if r.indicator_slug_raw == FEMALE_SLUG]
    assert len(females) == 1
    assert females[0].value == pytest.approx(0.0)


def test_idempotent() -> None:
    first, _ = extract_foreign_employment_rows(_ANNEX_6_1_TABLE)
    second, _ = extract_foreign_employment_rows(_ANNEX_6_1_TABLE)
    assert [r.to_json_dict() for r in first] == [r.to_json_dict() for r in second]


def test_empty_table_yields_nothing() -> None:
    out, errors = extract_foreign_employment_rows([])
    assert out == []
    assert errors == []


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def test_full_year_lead_accepts_valid() -> None:
    assert _full_year_lead("2015/16") == 2015
    assert _full_year_lead("2022/23") == 2022


def test_full_year_lead_rejects_partial_and_cumulative() -> None:
    assert _full_year_lead("2023/24*") is None  # starred partial
    assert _full_year_lead("Upto July 2015") is None
    assert _full_year_lead("2020/99") is None  # inconsistent tail


def test_parse_count_handles_separators_and_blanks() -> None:
    assert _parse_count("1,234") == pytest.approx(1234.0)
    assert _parse_count("0") == pytest.approx(0.0)
    assert _parse_count("") is None
    assert _parse_count("-") is None
    assert _parse_count("n/a") is None


def test_ad_fy_to_bs_roundtrip() -> None:
    from _common.periods import fiscal_year_ad_label

    bs = _ad_fy_to_bs_start(2023)
    assert bs == 2080
    assert fiscal_year_ad_label(bs) == "2023/24"


# ---------------------------------------------------------------------------
# Diagnostic classifier (documents the deferred macro annex / CID pages).
# ---------------------------------------------------------------------------

CLEAN_MACRO = (
    "Annex 1.1: Annual Growth Rate of GDP by Economic Activities\n"
    "Macroeconomic Indicators Gross Domestic Product Price Inflation\n"
)
CID_BROKEN = "(cid:20)(cid:21)(cid:17) " * 20  # > 30 cid markers
# Reversed single-word macro vocabulary (the RTL mirror; multi-word phrases do
# not survive line-wrapping, single words do): GDP→PDG, Product→tcudorP,
# Price→ecirP, Inflation→noitalfnI, Indicators→srotacidnI.
RTL_MIRRORED = "srotacidnI PDG tcudorP ecirP noitalfnI raeY lacsiF\n8.4075 5.8435\n"


def test_classify_clean_macro() -> None:
    assert classify_annex_text(CLEAN_MACRO) == "clean"


def test_classify_cid_broken() -> None:
    assert classify_annex_text(CID_BROKEN) == "cid_broken"


def test_classify_rtl_mirrored() -> None:
    assert classify_annex_text(RTL_MIRRORED) == "rtl_mirrored"


def test_classify_empty() -> None:
    assert classify_annex_text("   \n ") == "empty"


def test_single_reversed_token_not_enough_to_flag_mirror() -> None:
    # One stray reversed token (no forward macro vocab) is NOT a mirror — needs ≥2.
    assert classify_annex_text("PDG figures for the year\nsome prose here") != "rtl_mirrored"


def test_rtl_number_decodes_to_gdp_magnitude() -> None:
    """The mirrored macro GDP cell '8.4075' reverses to '5704.8' ⇒ NPR 5,704.8
    billion ≈ NPR 5.7 trillion (ADR-0011 NPR 5–6 trillion band). Recorded to
    prove the deferred macro numbers are real (a geometry problem, not a parse
    bug); we never emit them."""
    gdp_billion = float("8.4075"[::-1])
    assert gdp_billion == pytest.approx(5704.8)
    assert 5_000 < gdp_billion < 6_000


# ---------------------------------------------------------------------------
# Contract / robustness.
# ---------------------------------------------------------------------------


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


def test_source_id_matches_registry() -> None:
    assert SOURCE_ID == "mof-economic-survey-annual"


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-economic-survey.pdf", source_document_id="x")
    assert res.status == "failure"
    assert res.staging_rows == []
    assert res.errors
    assert all(e.error_class for e in res.errors)


def test_extract_output_json_serialisable(rows: list[StagingRowDraft]) -> None:
    result = ParserResult(status="partial", parser_version=PARSER_VERSION, staging_rows=rows)
    payload = result.to_json_dict()
    assert set(payload) == {"status", "parser_version", "staging_rows", "errors"}
    sample = payload["staging_rows"][0]
    assert "T" in sample["reporting_period_ad_start"]
    assert sample["unit"] == "count"
    json.dumps(payload)  # must round-trip


# ---------------------------------------------------------------------------
# Optional integration against the real PDFs (skipped if absent).
# ---------------------------------------------------------------------------

_ES_DIR = (
    Path(__file__).resolve().parents[3]
    / "Financial Data"
    / "mof_documents"
    / "economic_survey"
)
_EN_PDF = _ES_DIR / "Economic_Survey_2023-24_EN.pdf"
_NP_2080_PDF = _ES_DIR / "Economic_Survey_2080-81_NP.pdf"
_PDF_2081 = _ES_DIR / "Economic_Survey_2081-82.pdf"


@pytest.mark.skipif(not _EN_PDF.exists(), reason="real EN Economic Survey PDF not on disk")
def test_real_en_pdf_extracts_annex_6_1_partial() -> None:
    result = parse(str(_EN_PDF), source_document_id="real-en")
    # Some clean Annex-6.1 rows extracted; macro annex + CID pages deferred → partial.
    assert result.status == "partial", f"status={result.status} errors={result.errors}"
    assert {r.indicator_slug_raw for r in result.staging_rows} == EXPECTED_SLUGS
    totals = [r for r in result.staging_rows if r.indicator_slug_raw == TOTAL_SLUG]
    # At least the full years 2015/16..2022/23 (8 of them).
    assert len(totals) >= 7
    for r in result.staging_rows:
        assert r.unit == "count"
        assert r.reporting_period_type == "annual"
        assert r.value >= 0
    # The FY2022/23 total is the published 494,224.
    by_ad = {r.fiscal_year_ad_label: r.value for r in totals}
    assert by_ad.get("2022/23") == pytest.approx(494224.0)
    # Deferral diagnostics name the mirrored macro annex + CID chapters.
    classes = {e.error_class for e in result.errors}
    assert "PageLayoutChanged" in classes  # RTL-mirrored macro annex
    assert "EncodingError" in classes  # CID-broken chapters


@pytest.mark.skipif(
    not _NP_2080_PDF.exists(), reason="real NP 2080-81 Economic Survey PDF not on disk"
)
def test_real_np_2080_pdf_is_documented_failure() -> None:
    # The Nepali edition's annex is CID-broken; no clean Annex 6.1 → documented failure.
    result = parse(str(_NP_2080_PDF), source_document_id="real-np2080")
    assert result.status == "failure"
    assert result.staging_rows == []
    assert any("NoCleanAnnexTable" in e.error_detail for e in result.errors)


@pytest.mark.skipif(not _PDF_2081.exists(), reason="real 2081-82 Economic Survey PDF not on disk")
def test_real_2081_pdf_is_documented_failure() -> None:
    result = parse(str(_PDF_2081), source_document_id="real-2081")
    assert result.status == "failure"
    assert result.staging_rows == []
    assert any("NoCleanAnnexTable" in e.error_detail for e in result.errors)


@pytest.mark.skipif(not _EN_PDF.exists(), reason="real EN Economic Survey PDF not on disk")
def test_cli_emits_valid_json_on_real_pdf() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "mof_economic_survey.parser", str(_EN_PDF), "doc"],
        cwd=scrapers_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] == "partial"
    assert payload["parser_version"] == PARSER_VERSION
    assert len(payload["staging_rows"]) > 0
    for row in payload["staging_rows"]:
        assert "T" in row["reporting_period_ad_start"]
        assert row["unit"] == "count"
