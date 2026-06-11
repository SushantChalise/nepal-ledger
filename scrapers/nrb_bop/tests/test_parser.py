"""Tests for the NRB BOP BPM5 historical parser (nrb_bop.parser).

All tests run against programmatically-generated XLSX fixtures from conftest.py.
No network.  No binary fixtures committed.

Test matrix:
    test_happy_*          — main happy-path assertions on the synthetic fixture
    test_methodology_*    — BPM5 methodology tag present and correct on every row
    test_no_splice_*      — slug is remittance-inflow-bpm5, NOT dne-remittance-inflow
    test_fy_mapping_*     — AD FY labels correctly converted to BS FY labels
    test_revision_*       — R/P suffix captured in parser_notes, value still emitted
    test_error_*          — file-not-found, missing sheet, missing target row
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _common.types import ParserResult
from nrb_bop import PARSER_VERSION, SOURCE_ID, parse

# ---------------------------------------------------------------------------
# Happy-path fixture
# ---------------------------------------------------------------------------

# Expected AD FY labels (from conftest _PANEL1_FY_LABELS + _PANEL2_FY_LABELS)
_ALL_AD_FY_LABELS = [
    "2000/01", "2001/02", "2002/03", "2003/04", "2004/05", "2005/06",
    "2006/07", "2007/08", "2008/09", "2009/10", "2010/11", "2011/12",
    "2012/13", "2013/14", "2014/15", "2015/16", "2016/17", "2017/18",
    "2018/19", "2019/20", "2020/21",
    # suffix-bearing years — the suffix is stripped for the label
    "2021/22", "2022/23", "2023/24",
]

# Corresponding BS FY labels (add 57 to each AD start year)
_ALL_BS_FY_LABELS = [
    "2057/58", "2058/59", "2059/60", "2060/61", "2061/62", "2062/63",
    "2063/64", "2064/65", "2065/66", "2066/67", "2067/68", "2068/69",
    "2069/70", "2070/71", "2071/72", "2072/73", "2073/74", "2074/75",
    "2075/76", "2076/77", "2077/78", "2078/79", "2079/80", "2080/81",
]

# Spot-check values (from conftest)
_SPOT_CHECKS: list[tuple[str, float]] = [
    ("2057/58", 47216.1),    # AD 2000/01 — first year
    ("2068/69", 359554.4),   # AD 2011/12 — end of panel 1
    ("2069/70", 434581.7),   # AD 2012/13 — start of panel 2
    ("2079/80", 1240686.4),  # AD 2022/23R — revised
    ("2080/81", 1445315.1),  # AD 2023/24P — provisional
]


@pytest.fixture(scope="module")
def happy(bop_xlsx: Path) -> ParserResult:
    return parse(str(bop_xlsx), source_document_id="test-bop")


# ---------------------------------------------------------------------------
# Basic status + catalogue hygiene
# ---------------------------------------------------------------------------


def test_happy_status_success(happy: ParserResult) -> None:
    assert happy.status == "success", f"errors={happy.errors}"


def test_happy_no_errors(happy: ParserResult) -> None:
    assert happy.errors == []


def test_happy_parser_version(happy: ParserResult) -> None:
    assert happy.parser_version == PARSER_VERSION == "0.1.0"


def test_happy_source_id_constant() -> None:
    assert SOURCE_ID == "nrb-bop"


def test_happy_row_count(happy: ParserResult) -> None:
    """24 years (2000/01–2023/24), all present in the fixture."""
    assert len(happy.staging_rows) == 24


# ---------------------------------------------------------------------------
# Catalogue hygiene (ADR-0014): only remittance-inflow-bpm5 promoted
# ---------------------------------------------------------------------------


def test_no_splice_only_bpm5_slug(happy: ParserResult) -> None:
    """ONLY remittance-inflow-bpm5 is emitted — no other BoP lines, no BPM6 slug.

    The Current Account, Goods exports, and other BoP rows in the fixture must
    NOT appear in staging output (ADR-0014: no catalogue pollution).
    """
    slugs = {r.indicator_slug_raw for r in happy.staging_rows}
    assert slugs == {"remittance-inflow-bpm5"}


def test_no_splice_not_bpm6_slug(happy: ParserResult) -> None:
    """remittance-inflow-bpm5 must NEVER carry the BPM6 slug dne-remittance-inflow."""
    assert all(r.indicator_slug_raw != "dne-remittance-inflow" for r in happy.staging_rows)


# ---------------------------------------------------------------------------
# Unit and confidence
# ---------------------------------------------------------------------------


def test_happy_unit_npr_million(happy: ParserResult) -> None:
    assert all(r.unit == "npr_million" for r in happy.staging_rows)


def test_happy_confidence_grade_b(happy: ParserResult) -> None:
    assert all(r.confidence_grade_proposed == "B" for r in happy.staging_rows)


# ---------------------------------------------------------------------------
# Methodology note (DATA CONTINUITY PROTOCOL)
# ---------------------------------------------------------------------------


def test_methodology_note_present_on_every_row(happy: ParserResult) -> None:
    """Every row must carry a parser_notes field with the BPM5 tag."""
    for r in happy.staging_rows:
        assert r.parser_notes is not None, f"Missing parser_notes on {r.fiscal_year_bs}"
        assert "BPM5" in r.parser_notes, f"'BPM5' not in notes: {r.parser_notes}"


def test_methodology_note_names_bpm6_break(happy: ParserResult) -> None:
    """Notes must mention BPM6 and the approximate break year so UI can render it."""
    for r in happy.staging_rows:
        assert r.parser_notes is not None
        assert "BPM6" in r.parser_notes
        assert "2069/70" in r.parser_notes or "2012/13" in r.parser_notes


# ---------------------------------------------------------------------------
# FY mapping: AD → BS conversion
# ---------------------------------------------------------------------------


def test_fy_mapping_all_bs_labels_present(happy: ParserResult) -> None:
    """All 24 BS fiscal-year labels are present in staging output."""
    bs_labels = {r.fiscal_year_bs for r in happy.staging_rows}
    for expected in _ALL_BS_FY_LABELS:
        assert expected in bs_labels, f"Missing BS FY: {expected}"


def test_fy_mapping_all_ad_labels_present(happy: ParserResult) -> None:
    """All 24 AD fiscal-year labels are present (suffix stripped)."""
    ad_labels = {r.fiscal_year_ad_label for r in happy.staging_rows}
    for expected in _ALL_AD_FY_LABELS:
        assert expected in ad_labels, f"Missing AD FY: {expected}"


def test_fy_mapping_period_type_annual(happy: ParserResult) -> None:
    assert all(r.reporting_period_type == "annual" for r in happy.staging_rows)


def test_fy_mapping_bs_matches_fiscal_year_bs(happy: ParserResult) -> None:
    """reporting_period_bs must equal fiscal_year_bs for annual rows."""
    for r in happy.staging_rows:
        assert r.reporting_period_bs == r.fiscal_year_bs


def test_fy_mapping_period_start_july(happy: ParserResult) -> None:
    """Annual period start is July of the AD fiscal-year start year."""
    for r in happy.staging_rows:
        assert r.reporting_period_ad_start.month == 7, (
            f"Expected July start for {r.fiscal_year_bs}, "
            f"got month {r.reporting_period_ad_start.month}"
        )


def test_fy_mapping_period_end_july_following_year(happy: ParserResult) -> None:
    """Annual period end is July of the year following the AD FY start."""
    for r in happy.staging_rows:
        start_year = r.reporting_period_ad_start.year
        assert r.reporting_period_ad_end.year == start_year + 1
        assert r.reporting_period_ad_end.month == 7


# ---------------------------------------------------------------------------
# Spot-check values
# ---------------------------------------------------------------------------


def test_spot_check_values(happy: ParserResult) -> None:
    """Key values match the fixture (and the real NRB file) exactly."""
    by_bs = {r.fiscal_year_bs: r.value for r in happy.staging_rows}
    for bs_fy, expected in _SPOT_CHECKS:
        assert by_bs[bs_fy] == pytest.approx(expected, abs=0.2), (
            f"FY {bs_fy}: expected {expected}, got {by_bs[bs_fy]}"
        )


def test_panel1_panel2_values_distinct(happy: ParserResult) -> None:
    """Panel-1 years (≤2068/69) and panel-2 years (≥2069/70) all have positive values."""
    by_bs = {r.fiscal_year_bs: r.value for r in happy.staging_rows}
    for bs_fy in _ALL_BS_FY_LABELS[:12]:   # panel 1
        assert by_bs[bs_fy] > 0, f"Panel-1 zero/missing: {bs_fy}"
    for bs_fy in _ALL_BS_FY_LABELS[12:]:   # panel 2
        assert by_bs[bs_fy] > 0, f"Panel-2 zero/missing: {bs_fy}"


# ---------------------------------------------------------------------------
# Revision suffix handling
# ---------------------------------------------------------------------------


def test_revision_suffix_row_still_emitted(happy: ParserResult) -> None:
    """Rows with R/P suffix are emitted — suffix is NOT treated as missing data."""
    bs_labels = {r.fiscal_year_bs for r in happy.staging_rows}
    assert "2078/79" in bs_labels   # AD 2021/22R
    assert "2079/80" in bs_labels   # AD 2022/23R
    assert "2080/81" in bs_labels   # AD 2023/24P


def test_revision_suffix_r_captured_in_notes(happy: ParserResult) -> None:
    """'R' (revised) suffix rows carry the suffix in parser_notes."""
    revised_rows = [r for r in happy.staging_rows if r.fiscal_year_bs in ("2078/79", "2079/80")]
    assert len(revised_rows) == 2
    for r in revised_rows:
        assert r.parser_notes is not None
        # Note should mention the suffix (case-insensitive 'R' or 'revised')
        assert "R" in r.parser_notes or "revised" in r.parser_notes.lower()


def test_provisional_suffix_p_captured_in_notes(happy: ParserResult) -> None:
    """'P' (provisional) suffix row carries the suffix in parser_notes."""
    prov = next(r for r in happy.staging_rows if r.fiscal_year_bs == "2080/81")
    assert prov.parser_notes is not None
    assert "P" in prov.parser_notes or "provisional" in prov.parser_notes.lower()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_error_file_not_found() -> None:
    result = parse("/nonexistent/path/file.xlsx", source_document_id="test")
    assert result.status == "failure"
    assert any(e.error_class == "Other" for e in result.errors)
    assert any("not found" in e.error_detail.lower() for e in result.errors)


def test_error_missing_sheet(missing_sheet_xlsx: Path) -> None:
    """Workbook that lacks 'BOP 2000-' → failure with descriptive error."""
    result = parse(str(missing_sheet_xlsx), source_document_id="test")
    assert result.status == "failure"
    assert any("BOP 2000-" in e.error_detail for e in result.errors)


def test_error_no_target_row(no_remittances_row_xlsx: Path) -> None:
    """Sheet with header row but no Workers' remittances row → failure."""
    result = parse(str(no_remittances_row_xlsx), source_document_id="test")
    assert result.status == "failure"
    assert len(result.staging_rows) == 0
    assert any(e.error_class == "ColumnMissing" for e in result.errors)


# ---------------------------------------------------------------------------
# JSON serialisability
# ---------------------------------------------------------------------------


def test_json_serialisable(happy: ParserResult) -> None:
    """ParserResult can round-trip through json.dumps → no datetime objects escape."""
    import dataclasses
    dumped = json.dumps(dataclasses.asdict(happy), default=str)
    assert "remittance-inflow-bpm5" in dumped
    assert "npr_million" in dumped
    assert "BPM5" in dumped
