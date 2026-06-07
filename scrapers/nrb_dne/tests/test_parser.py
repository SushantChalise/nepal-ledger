"""Tests for the NRB DNE XLSX parser (nrb_dne.parser).

All tests run against programmatically-generated XLSX fixtures from conftest.py.
No network. No binary fixtures committed.

Test matrix:
    test_happy_path_*       — main parser logic on the external-reserves fixture
    test_empty_workbook_*   — empty sheet → partial status, NoDataExtracted error
    test_ambiguous_unit_*   — missing unit → UnitAmbiguous error, rows still parsed
    test_bad_period_*       — malformed period header → PeriodUnparseable error
    test_missing_file_*     — non-existent path → failure status
    test_idempotent         — same input → same output
    test_json_serialisable  — asdict output round-trips through json.dumps
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from _common.types import ParserResult, StagingRowDraft
from nrb_dne import (
    PARSER_VERSION,
    SOURCE_ID,
    DimensionalRowDraft,
    DneParserResult,
    parse,
    parse_dne,
)

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def happy_result(happy_path_xlsx: Path) -> ParserResult:
    return parse(str(happy_path_xlsx), source_document_id="test-doc-happy")


def test_happy_status_success(happy_result: ParserResult) -> None:
    assert happy_result.status == "success", f"errors={happy_result.errors}"


def test_happy_parser_version(happy_result: ParserResult) -> None:
    assert happy_result.parser_version == PARSER_VERSION == "0.5.0"


def test_happy_source_id() -> None:
    assert SOURCE_ID == "nrb-dne-xlsx"


def test_happy_row_count(happy_result: ParserResult) -> None:
    # 3 indicators × (3 annual + 2 monthly) = 15 rows.
    assert len(happy_result.staging_rows) == 15


def test_happy_no_errors(happy_result: ParserResult) -> None:
    assert happy_result.errors == [], f"unexpected errors: {happy_result.errors}"


def test_happy_slugs(happy_result: ParserResult) -> None:
    slugs = {r.indicator_slug_raw for r in happy_result.staging_rows}
    assert "dne-total-foreign-exchange-reserves" in slugs
    assert "dne-gold-reserves" in slugs
    assert "dne-foreign-currency-assets" in slugs


def test_happy_unit_all_usd_million(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert row.unit == "usd_million", f"slug={row.indicator_slug_raw} unit={row.unit}"


def test_happy_annual_periods(happy_result: ParserResult) -> None:
    annual = [r for r in happy_result.staging_rows if r.reporting_period_type == "annual"]
    # 3 indicators × 3 annual columns = 9 annual rows.
    assert len(annual) == 9
    fy_labels = {r.fiscal_year_bs for r in annual}
    assert "2080/81" in fy_labels
    assert "2081/82" in fy_labels
    assert "2082/83" in fy_labels


def test_happy_monthly_periods(happy_result: ParserResult) -> None:
    monthly = [r for r in happy_result.staging_rows if r.reporting_period_type == "monthly"]
    # 3 indicators × 2 monthly columns = 6 monthly rows.
    assert len(monthly) == 6
    bs_labels = {r.reporting_period_bs for r in monthly}
    assert "Shrawan 2082" in bs_labels
    assert "Bhadra 2082" in bs_labels


def test_happy_confidence_grade(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert row.confidence_grade_proposed == "B"


def test_happy_values_correct(happy_result: ParserResult) -> None:
    """Spot-check specific known values from the synthetic fixture."""
    total_rows = [
        r for r in happy_result.staging_rows
        if r.indicator_slug_raw == "dne-total-foreign-exchange-reserves"
    ]
    annual_vals = {
        r.fiscal_year_bs: r.value
        for r in total_rows
        if r.reporting_period_type == "annual"
    }
    assert annual_vals["2080/81"] == pytest.approx(1500.0)
    assert annual_vals["2081/82"] == pytest.approx(2100.0)
    assert annual_vals["2082/83"] == pytest.approx(2300.0)


def test_happy_all_rows_are_staging_drafts(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert isinstance(row, StagingRowDraft)


def test_happy_period_ad_start_before_end(happy_result: ParserResult) -> None:
    for row in happy_result.staging_rows:
        assert row.reporting_period_ad_start < row.reporting_period_ad_end, (
            f"slug={row.indicator_slug_raw} period_bs={row.reporting_period_bs}: "
            f"ad_start >= ad_end"
        )


def test_happy_ad_label_format(happy_result: ParserResult) -> None:
    """fiscal_year_ad_label should be YYYY/YY format for all annual rows."""
    annual = [r for r in happy_result.staging_rows if r.reporting_period_type == "annual"]
    for row in annual:
        parts = row.fiscal_year_ad_label.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit() and len(parts[0]) == 4
        assert parts[1].isdigit() and len(parts[1]) == 2


# ---------------------------------------------------------------------------
# Empty workbook → partial, NoDataExtracted
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def empty_result(empty_workbook_xlsx: Path) -> ParserResult:
    return parse(str(empty_workbook_xlsx), source_document_id="test-doc-empty")


def test_empty_status_partial(empty_result: ParserResult) -> None:
    assert empty_result.status == "partial"


def test_empty_no_rows(empty_result: ParserResult) -> None:
    assert empty_result.staging_rows == []


def test_empty_has_no_data_error(empty_result: ParserResult) -> None:
    detail_texts = " ".join(e.error_detail for e in empty_result.errors)
    assert "NoDataExtracted" in detail_texts, f"errors={empty_result.errors}"


# ---------------------------------------------------------------------------
# Ambiguous unit → UnitAmbiguous error, rows still parsed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ambiguous_result(ambiguous_unit_xlsx: Path) -> ParserResult:
    return parse(str(ambiguous_unit_xlsx), source_document_id="test-doc-ambiguous")


def test_ambiguous_has_rows(ambiguous_result: ParserResult) -> None:
    # Parser should still emit rows even when unit is ambiguous.
    assert len(ambiguous_result.staging_rows) > 0


def test_ambiguous_has_unit_error(ambiguous_result: ParserResult) -> None:
    error_classes = [e.error_class for e in ambiguous_result.errors]
    assert "UnitAmbiguous" in error_classes, f"errors={ambiguous_result.errors}"


def test_ambiguous_status_partial(ambiguous_result: ParserResult) -> None:
    # Errors present → partial.
    assert ambiguous_result.status == "partial"


def test_ambiguous_slug_prefix(ambiguous_result: ParserResult) -> None:
    for row in ambiguous_result.staging_rows:
        assert row.indicator_slug_raw.startswith("dne-")


# ---------------------------------------------------------------------------
# Bad period header → PeriodUnparseable error, valid column still parsed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bad_period_result(bad_period_xlsx: Path) -> ParserResult:
    return parse(str(bad_period_xlsx), source_document_id="test-doc-bad-period")


def test_bad_period_has_error(bad_period_result: ParserResult) -> None:
    error_classes = [e.error_class for e in bad_period_result.errors]
    assert "PeriodUnparseable" in error_classes, f"errors={bad_period_result.errors}"


def test_bad_period_still_parses_valid_column(bad_period_result: ParserResult) -> None:
    # The valid "2081/82" column should still produce a row for "Tax Revenue".
    slugs = {r.indicator_slug_raw for r in bad_period_result.staging_rows}
    assert "dne-tax-revenue" in slugs


def test_bad_period_status_partial(bad_period_result: ParserResult) -> None:
    assert bad_period_result.status == "partial"


# ---------------------------------------------------------------------------
# Missing file → failure
# ---------------------------------------------------------------------------


def test_missing_file_returns_failure() -> None:
    result = parse("nonexistent-dne.xlsx", source_document_id="x")
    assert result.status == "failure"
    assert result.errors
    assert result.staging_rows == []


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotent(happy_path_xlsx: Path) -> None:
    a = parse(str(happy_path_xlsx), source_document_id="x")
    b = parse(str(happy_path_xlsx), source_document_id="x")
    assert a.status == b.status
    assert len(a.staging_rows) == len(b.staging_rows)
    for ra, rb in zip(a.staging_rows, b.staging_rows, strict=True):
        assert ra == rb


# ---------------------------------------------------------------------------
# JSON serialisability (orchestrator contract)
# ---------------------------------------------------------------------------


def test_json_serialisable(happy_result: ParserResult) -> None:
    payload = asdict(happy_result)
    for row in payload.get("staging_rows", []):
        for key in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            val = row.get(key)
            from datetime import datetime

            if isinstance(val, datetime):
                row[key] = val.isoformat()

    dumped = json.dumps(payload)
    assert "staging_rows" in dumped
    assert "parser_version" in dumped
    assert "dne-" in dumped


# ---------------------------------------------------------------------------
# Sample row spot-check (aids debugging when the suite first runs)
# ---------------------------------------------------------------------------


def test_sample_row_shape(happy_result: ParserResult) -> None:
    """Verify one representative row has all required StagingRowDraft fields."""
    row = next(
        r for r in happy_result.staging_rows
        if r.indicator_slug_raw == "dne-total-foreign-exchange-reserves"
        and r.reporting_period_type == "annual"
        and r.fiscal_year_bs == "2082/83"
    )
    assert row.value == pytest.approx(2300.0)
    assert row.unit == "usd_million"
    assert row.confidence_grade_proposed == "B"
    assert row.fiscal_year_ad_label == "2025/26"
    assert row.reporting_period_bs == "2082/83"


# ---------------------------------------------------------------------------
# Real-file structure tests (v0.2.0 — derived from actual NRB DNE XLSX layouts)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bs_fy_suffix_result(bs_fy_suffix_xlsx: Path) -> ParserResult:
    """BS FY with NRB revision/provisional suffixes (e.g. "2079/80R", "2080/81P")."""
    return parse(str(bs_fy_suffix_xlsx), source_document_id="test-doc-bs-suffix")


def test_bs_fy_suffix_parses_successfully(bs_fy_suffix_result: ParserResult) -> None:
    """NRB revision suffix R/P/E should be stripped; BS FY should parse."""
    assert bs_fy_suffix_result.status == "success", (
        f"expected success, got {bs_fy_suffix_result.status}; "
        f"errors={bs_fy_suffix_result.errors}"
    )


def test_bs_fy_suffix_row_count(bs_fy_suffix_result: ParserResult) -> None:
    # 1 indicator × 3 FY columns (2079/80R, 2080/81P, 2081/82) = 3 rows.
    assert len(bs_fy_suffix_result.staging_rows) == 3


def test_bs_fy_suffix_stripped_to_plain_bs(bs_fy_suffix_result: ParserResult) -> None:
    """Suffixes must be stripped; fiscal_year_bs must be plain YYYY/YY."""
    fy_labels = {r.fiscal_year_bs for r in bs_fy_suffix_result.staging_rows}
    assert fy_labels == {"2079/80", "2080/81", "2081/82"}


def test_bs_fy_suffix_unit_npr_million(bs_fy_suffix_result: ParserResult) -> None:
    for row in bs_fy_suffix_result.staging_rows:
        assert row.unit == "npr_million", f"unit={row.unit!r}"


def test_bs_fy_suffix_values(bs_fy_suffix_result: ParserResult) -> None:
    vals = {r.fiscal_year_bs: r.value for r in bs_fy_suffix_result.staging_rows}
    assert vals["2079/80"] == pytest.approx(5000.0)
    assert vals["2080/81"] == pytest.approx(5500.0)
    assert vals["2081/82"] == pytest.approx(6000.0)


@pytest.fixture(scope="module")
def ad_year_result(ad_year_sheet_xlsx: Path) -> ParserResult:
    """AD-calendar-year FY headers (e.g. "2021/22") — converted to BS per ADR-0013."""
    return parse(str(ad_year_sheet_xlsx), source_document_id="test-doc-ad-year")


def test_ad_year_sheet_status_success(ad_year_result: ParserResult) -> None:
    """AD-year FY headers now parse (ADR-0013): converted to BS, status success."""
    assert ad_year_result.status == "success", f"errors: {ad_year_result.errors}"


def test_ad_year_sheet_emits_rows(ad_year_result: ParserResult) -> None:
    """The fixture's two AD-year columns (2021/22, 2022/23) yield two facts."""
    assert len(ad_year_result.staging_rows) == 2


def test_ad_year_sheet_converts_ad_fy_to_bs(ad_year_result: ParserResult) -> None:
    """AD fiscal year → BS via the +57 offset (ADR-0013): 2021/22→2078/79,
    2022/23→2079/80. The AD label is preserved in fiscal_year_ad_label."""
    by_bs = {r.reporting_period_bs: r for r in ad_year_result.staging_rows}
    assert set(by_bs) == {"2078/79", "2079/80"}
    assert by_bs["2078/79"].fiscal_year_ad_label == "2021/22"
    assert by_bs["2079/80"].fiscal_year_ad_label == "2022/23"
    assert by_bs["2078/79"].reporting_period_type == "annual"


def test_ad_year_sheet_no_period_error(ad_year_result: ParserResult) -> None:
    """No PeriodUnparseable now that AD fiscal years are accepted."""
    assert "PeriodUnparseable" not in [e.error_class for e in ad_year_result.errors]


# ---------------------------------------------------------------------------
# v0.4.0 — integer-year + monthly two-row header (Foreign-exchange-reserves)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ym_result(year_month_header_xlsx: Path) -> ParserResult:
    """Two-row header: integer AD years over AD month names (forward-filled)."""
    return parse(str(year_month_header_xlsx), source_document_id="test-doc-ym")


def test_ym_status_success(ym_result: ParserResult) -> None:
    assert ym_result.status == "success", f"errors={ym_result.errors}"


def test_ym_row_count(ym_result: ParserResult) -> None:
    # 2 indicators × 8 monthly columns = 16 rows.
    assert len(ym_result.staging_rows) == 16


def test_ym_all_monthly(ym_result: ParserResult) -> None:
    assert all(r.reporting_period_type == "monthly" for r in ym_result.staging_rows)


def test_ym_unit_npr_million(ym_result: ParserResult) -> None:
    assert all(r.unit == "npr_million" for r in ym_result.staging_rows)


def test_ym_year_forward_filled(ym_result: ParserResult) -> None:
    """The sparse year row must forward-fill: Aug-Dec → AD 2001, Jan-Mar → 2002."""
    by_label = {
        (r.indicator_slug_raw, r.reporting_period_bs): r
        for r in ym_result.staging_rows
    }
    # Slug "dne-nepal-rastra-bank": the "A." outline enumerator on the source
    # label "A. Nepal Rastra Bank" is stripped for slug derivation (v0.5.0).
    # Aug 2001 → Bhadra (AD month 8), BS year 2001+57 = 2058.
    aug = by_label[("dne-nepal-rastra-bank", "Bhadra 2058")]
    assert aug.value == pytest.approx(100.0)
    assert aug.fiscal_year_ad_label == "2001/02"
    # Jan 2002 → Magh (AD month 1, < July), BS year 2002+56 = 2058.
    jan = by_label[("dne-nepal-rastra-bank", "Magh 2058")]
    assert jan.value == pytest.approx(150.0)
    # Jan belongs to FY that began the prior July (AD 2001/02).
    assert jan.fiscal_year_ad_label == "2001/02"


def test_ym_ad_month_span_is_exact_gregorian(ym_result: ParserResult) -> None:
    """AD monthly span is the real Gregorian month, not a BS-derived guess."""
    aug = next(
        r for r in ym_result.staging_rows
        if r.indicator_slug_raw == "dne-nepal-rastra-bank"
        and r.reporting_period_bs == "Bhadra 2058"
    )
    assert aug.reporting_period_ad_start.year == 2001
    assert aug.reporting_period_ad_start.month == 8
    assert aug.reporting_period_ad_end.month == 8


def test_ym_approximation_flagged(ym_result: ParserResult) -> None:
    """Every AD-monthly row records the mid-month BS approximation in notes."""
    assert all(
        r.parser_notes and "mid-month" in r.parser_notes
        for r in ym_result.staging_rows
    )


# ---------------------------------------------------------------------------
# v0.4.0 — repeated (year, month) column → both values kept, flagged
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ym_dup_result(year_month_dup_xlsx: Path) -> ParserResult:
    return parse(str(year_month_dup_xlsx), source_document_id="test-doc-ym-dup")


def test_ym_dup_both_values_kept(ym_dup_result: ParserResult) -> None:
    """A repeated Oct column must NOT drop data — both Kartik 2082 values emitted."""
    kartik = [
        r for r in ym_dup_result.staging_rows if r.reporting_period_bs == "Kartik 2082"
    ]
    assert len(kartik) == 2
    assert sorted(r.value for r in kartik) == pytest.approx([300.0, 999.0])


def test_ym_dup_emits_period_ambiguous(ym_dup_result: ParserResult) -> None:
    assert "PeriodAmbiguous" in [e.error_class for e in ym_dup_result.errors]


def test_ym_dup_flagged_in_notes(ym_dup_result: ParserResult) -> None:
    flagged = [
        r for r in ym_dup_result.staging_rows
        if r.parser_notes and "repeated column" in r.parser_notes
    ]
    assert len(flagged) == 1  # only the second occurrence is flagged


# ---------------------------------------------------------------------------
# v0.4.0 — long panel (Exchange-rate): FY col + month col + value cols
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def long_panel_result(long_panel_xlsx: Path) -> ParserResult:
    return parse(str(long_panel_xlsx), source_document_id="test-doc-long-panel")


def test_long_panel_has_rows(long_panel_result: ParserResult) -> None:
    # 3 real month rows (Annual Average skipped) × 3 value columns = 9 rows.
    assert len(long_panel_result.staging_rows) == 9


def test_long_panel_all_monthly(long_panel_result: ParserResult) -> None:
    assert all(
        r.reporting_period_type == "monthly" for r in long_panel_result.staging_rows
    )


def test_long_panel_fy_forward_filled(long_panel_result: ParserResult) -> None:
    """The sparse FY label fills across its months. July 2022 → Shrawan 2079."""
    july = [r for r in long_panel_result.staging_rows if r.reporting_period_bs == "Shrawan 2079"]
    assert len(july) == 3  # three value columns
    assert all(r.fiscal_year_ad_label == "2022/23" for r in july)


def test_long_panel_jan_uses_trailing_calendar_year(long_panel_result: ParserResult) -> None:
    """FY 2023/24 January is AD 2024 (Jan), BS Magh 2080, but FY stays 2023/24."""
    jan = [r for r in long_panel_result.staging_rows if r.reporting_period_bs == "Magh 2080"]
    assert len(jan) == 3
    assert all(r.fiscal_year_ad_label == "2023/24" for r in jan)
    assert all(r.reporting_period_ad_start.year == 2024 for r in jan)


def test_long_panel_skips_aggregate_rows(long_panel_result: ParserResult) -> None:
    """The 'Annual Average' row must not produce any monthly fact."""
    # If it leaked, we'd have 4 month rows × 3 cols = 12, not 9.
    assert len(long_panel_result.staging_rows) == 9


def test_long_panel_unit_ambiguous(long_panel_result: ParserResult) -> None:
    """No controlled-vocab unit exists for FX rates → honest UnitAmbiguous."""
    assert "UnitAmbiguous" in [e.error_class for e in long_panel_result.errors]
    # Raw column sub-label carried as the unit (validator flags it).
    assert all(r.unit for r in long_panel_result.staging_rows)


# ---------------------------------------------------------------------------
# v0.4.0 — transposed layout (Tourist-arrivals): years-as-rows, months-as-cols
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def transposed_result(transposed_xlsx: Path) -> ParserResult:
    return parse(str(transposed_xlsx), source_document_id="test-doc-transposed")


def test_transposed_status_success(transposed_result: ParserResult) -> None:
    assert transposed_result.status == "success", f"errors={transposed_result.errors}"


def test_transposed_row_count(transposed_result: ParserResult) -> None:
    # 2 year rows × 12 months = 24 (the annual Total column is ignored).
    assert len(transposed_result.staging_rows) == 24


def test_transposed_all_monthly(transposed_result: ParserResult) -> None:
    assert all(
        r.reporting_period_type == "monthly" for r in transposed_result.staging_rows
    )


def test_transposed_total_column_ignored(transposed_result: ParserResult) -> None:
    """The 'Total' column is not a month → no value equals an annual total (1860)."""
    assert all(r.value not in (1860.0, 1872.0) for r in transposed_result.staging_rows)


def test_transposed_jan_1992_maps_to_magh_2048(transposed_result: ParserResult) -> None:
    """Jan 1992 → Magh (AD month 1, < July) BS year 1992+56 = 2048."""
    jan = next(
        r for r in transposed_result.staging_rows
        if r.reporting_period_bs == "Magh 2048"
    )
    assert jan.value == pytest.approx(100.0)
    assert jan.fiscal_year_ad_label == "1991/92"
    assert jan.reporting_period_ad_start.year == 1992
    assert jan.reporting_period_ad_start.month == 1


def test_transposed_unit_count(transposed_result: ParserResult) -> None:
    """The sheet title carries 'Number' → count."""
    assert all(r.unit == "count" for r in transposed_result.staging_rows)


def test_transposed_single_indicator_slug(transposed_result: ParserResult) -> None:
    """A transposed sheet is a single indicator surface; slug from the sheet name."""
    assert {r.indicator_slug_raw for r in transposed_result.staging_rows} == {
        "dne-tourist-arrival"
    }


# ---------------------------------------------------------------------------
# v0.5.0 — Foreign Trade → dimensional_rows (ADR-0015)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ft_result(foreign_trade_commodities_xlsx: Path) -> DneParserResult:
    """Foreign-Trade commodity matrix → dimensional rows via parse_dne dispatch."""
    return parse_dne(str(foreign_trade_commodities_xlsx), source_document_id="test-ft")


def test_ft_status_success(ft_result: DneParserResult) -> None:
    assert ft_result.status == "success", f"errors={ft_result.errors}"


def test_ft_no_staging_rows(ft_result: DneParserResult) -> None:
    """A dimensional file emits NO single-series staging rows (ADR-0015)."""
    assert ft_result.staging_rows == []


def test_ft_dimensional_row_count(ft_result: DneParserResult) -> None:
    # 2 sections: export-india has 3 commodities, import-china has 1 = 4 rows;
    # × 24 month columns (2 FY blocks × 12) = 96 dimensional rows. TOTAL skipped.
    assert len(ft_result.dimensional_rows) == 96


def test_ft_all_rows_are_dimensional_drafts(ft_result: DneParserResult) -> None:
    for row in ft_result.dimensional_rows:
        assert isinstance(row, DimensionalRowDraft)


def test_ft_row_shape_has_all_adr0015_fields(ft_result: DneParserResult) -> None:
    """Each dimensional row carries exactly the ADR-0015 contract fields."""
    expected = {
        "base_indicator_slug", "base_indicator_name", "dimension_kind",
        "dimension_value", "dimension_label", "value", "unit",
        "reporting_period_type", "reporting_period_bs",
        "reporting_period_ad_start", "reporting_period_ad_end",
        "fiscal_year_bs", "fiscal_year_ad_label", "confidence_grade",
    }
    assert set(ft_result.dimensional_rows[0].to_json_dict().keys()) == expected


def test_ft_base_slugs_partner_qualified(ft_result: DneParserResult) -> None:
    """Export/import direction + trade partner determine the base measure slug."""
    bases = {r.base_indicator_slug for r in ft_result.dimensional_rows}
    assert bases == {
        "dne-merchandise-exports-india",
        "dne-merchandise-imports-china",
    }


def test_ft_dimension_kind_is_commodity(ft_result: DneParserResult) -> None:
    assert {r.dimension_kind for r in ft_result.dimensional_rows} == {"commodity"}


def test_ft_unit_npr_million(ft_result: DneParserResult) -> None:
    assert {r.unit for r in ft_result.dimensional_rows} == {"npr_million"}


def test_ft_all_monthly_grade_b(ft_result: DneParserResult) -> None:
    assert all(r.reporting_period_type == "monthly" for r in ft_result.dimensional_rows)
    assert all(r.confidence_grade == "B" for r in ft_result.dimensional_rows)


def test_ft_known_commodity_present(ft_result: DneParserResult) -> None:
    """Cardamom (export to India) is present with the raw label preserved."""
    card = [
        r for r in ft_result.dimensional_rows
        if r.dimension_value == "cardamom"
        and r.base_indicator_slug == "dne-merchandise-exports-india"
    ]
    assert len(card) == 24  # 2 FY blocks × 12 months
    assert {r.dimension_label for r in card} == {"Cardamom"}
    aug12 = next(
        r for r in card
        if r.reporting_period_ad_start.year == 2012
        and r.reporting_period_ad_start.month == 8
    )
    assert aug12.value == pytest.approx(100.0)  # base_val + 0 for the Aug column
    assert aug12.fiscal_year_ad_label == "2012/13"
    assert aug12.base_indicator_name == "Merchandise Exports to India"


def test_ft_commodity_slug_not_over_stripped(ft_result: DneParserResult) -> None:
    """"G.I. pipe"/"M.S. Pipe" stay DISTINCT slugs (leading G.I./M.S. not stripped)."""
    slugs = {r.dimension_value for r in ft_result.dimensional_rows}
    assert "g-i-pipe" in slugs
    assert "m-s-pipe" in slugs
    assert "pipe" not in slugs  # would mean both collapsed → data loss


def test_ft_no_unique_key_collisions(ft_result: DneParserResult) -> None:
    """No two rows share the dne_facts unique key (else ON CONFLICT drops data).

    Exercises the structural FY-advance: the second 12-month block has a BLANK
    FY-label cell; without the advance it would reuse 2012/13 and collide with
    block 1 on (base, dimension, period_bs, period_type).
    """
    keys = [
        (r.base_indicator_slug, r.dimension_kind, r.dimension_value,
         r.reporting_period_bs, r.reporting_period_type)
        for r in ft_result.dimensional_rows
    ]
    assert len(keys) == len(set(keys))
    # And both fiscal years are represented (block 2 was not collapsed onto block 1).
    fys = {r.fiscal_year_ad_label for r in ft_result.dimensional_rows}
    assert {"2012/13", "2013/14"} <= fys


def test_ft_json_serialisable(ft_result: DneParserResult) -> None:
    """The DNE result dict (with dimensional_rows) round-trips through json."""
    dumped = json.dumps(ft_result.to_json_dict())
    assert "dimensional_rows" in dumped
    assert "base_indicator_slug" in dumped
    assert "staging_rows" in dumped  # present (empty) for the contract


# ---------------------------------------------------------------------------
# v0.5.0 — single-series slug cleanup (FX-reserves / BoP enumerators + collisions)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fx_slug_result(fx_reserve_slug_xlsx: Path) -> ParserResult:
    return parse(str(fx_reserve_slug_xlsx), source_document_id="test-fx-slug")


def test_fx_slug_no_enumerator_prefix(fx_slug_result: ParserResult) -> None:
    """No emitted slug retains a leading single-letter/numeric outline enumerator."""
    import re as _re

    slugs = {r.indicator_slug_raw for r in fx_slug_result.staging_rows}
    offenders = [s for s in slugs if _re.match(r"dne-(?:[a-z]|\d+)-", s)]
    assert not offenders, f"enumerator-prefixed slugs remain: {offenders}"


def test_fx_slug_no_row_index_suffix(fx_slug_result: ParserResult) -> None:
    """No emitted slug uses the artifact "-rNN" collision suffix anymore."""
    import re as _re

    slugs = {r.indicator_slug_raw for r in fx_slug_result.staging_rows}
    offenders = [s for s in slugs if _re.search(r"-r\d+$", s)]
    assert not offenders, f"-rNN slugs remain: {offenders}"


def test_fx_slug_enumerator_and_agg_hint_stripped(fx_slug_result: ParserResult) -> None:
    """"A. Nepal Rastra Bank (1+2)" → clean "dne-nepal-rastra-bank"."""
    slugs = {r.indicator_slug_raw for r in fx_slug_result.staging_rows}
    assert "dne-nepal-rastra-bank" in slugs
    assert "dne-gross-foreign-exchange-reserve" in slugs


def test_fx_slug_collision_qualified_by_parent(fx_slug_result: ParserResult) -> None:
    """The repeated "Convertible" sub-row is qualified by its section parent.

    First "Convertible" (under "A. Nepal Rastra Bank") → "dne-convertible";
    second (under "C. Gross Foreign Exchange Reserve") →
    "dne-convertible-gross-foreign-exchange-reserve" — both present, neither lost.
    """
    slugs = {r.indicator_slug_raw for r in fx_slug_result.staging_rows}
    assert "dne-convertible" in slugs
    assert "dne-convertible-gross-foreign-exchange-reserve" in slugs
