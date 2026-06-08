"""Tests for the Department of Customs Foreign Trade Statistics (FTS) parser.

The real source is a set of multi-MB XLSX workbooks (one per cumulative month +
an annual file) compiled from ASYCUDA World. We do NOT commit the binaries
(ADR-0003 / source profile — they live in the gitignored ``Financial Data/``),
so the deterministic core (the per-sheet ``extract_*`` functions and the
period-descriptor parser) is exercised against SYNTHESIZED tiny tables that
reproduce the real geometry (row-2 header, HS-code commodity rows, country/
customs rows, a trailing blank-coded "Total" row, a preserved zero, a dropped
dash).

Two optional integration tests run the full ``parse_customs_fts`` against the
real files when present and are skipped otherwise so CI stays green.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from _common.types import ParserError
from customs_trade import PARSER_VERSION, parse_customs_fts
from customs_trade.parser import (
    DimensionalRowDraft,
    _Period,
    extract_commodity_partner_rows,
    extract_commodity_rows,
    extract_country_rows,
    extract_customs_rows,
    parse_period_descriptor,
)

# Real files, if Mother has the corpus in the worktree. Optional integration only.
_DATA_DIR = Path(__file__).resolve().parents[3] / "Financial Data" / "customs"
REAL_ANNUAL = _DATA_DIR / "FTS_Annual_2081_82.xlsx"
REAL_SHRAWAN = _DATA_DIR / "FTS_Shrawan_2081_82.xlsx"


_IMP = "customs-merchandise-imports"
_EXP = "customs-merchandise-exports"


def _by_dim(rows: list[DimensionalRowDraft], slug: str) -> dict[str, float]:
    """{dimension_value: value} for the facts of one base measure."""
    return {r.dimension_value: r.value for r in rows if r.base_indicator_slug == slug}


# A fixed annual period used across the core extraction tests.
_PERIOD_ANNUAL = _Period(
    reporting_period_type="annual",
    reporting_period_bs="2081/82",
    reporting_period_ad_start=datetime(2024, 7, 15, tzinfo=UTC),
    reporting_period_ad_end=datetime(2025, 7, 15, tzinfo=UTC),
    fiscal_year_bs="2081/82",
    fiscal_year_ad_label="2024/25",
    cumulative_note=None,
)


# ---------------------------------------------------------------------------
# Period descriptor parsing — the three real scope shapes.
# ---------------------------------------------------------------------------


def test_period_annual() -> None:
    desc = "Based on Annual data (Shrawan-Asar) of FY 2081/82 (Mid July 2024 to Mid July 2025)"
    period, err = parse_period_descriptor(desc)
    assert err is None
    assert period is not None
    assert period.reporting_period_type == "annual"
    assert period.reporting_period_bs == "2081/82"
    assert period.fiscal_year_bs == "2081/82"
    assert period.fiscal_year_ad_label == "2024/25"  # BS 2081 → AD 2024 (+57)
    assert period.reporting_period_ad_start == datetime(2024, 7, 15, tzinfo=UTC)
    assert period.reporting_period_ad_end == datetime(2025, 7, 15, tzinfo=UTC)
    assert period.cumulative_note is None


def test_period_first_month_is_monthly_shrawan() -> None:
    desc = "Based on First Month (Shrawan) of FY 2081/82 (Mid July 2024 to Mid August 2024)"
    period, err = parse_period_descriptor(desc)
    assert err is None
    assert period is not None
    assert period.reporting_period_type == "monthly"
    assert period.reporting_period_bs == "Shrawan 2081"  # month 1, lead BS year
    assert period.cumulative_note is None


def test_period_eleven_months_is_year_to_date_jestha() -> None:
    desc = (
        "Based on First Eleven Months (Shrawan-Jestha) of FY 2081/82 "
        "(Mid July 2024 to Mid June 2025)"
    )
    period, err = parse_period_descriptor(desc)
    assert err is None
    assert period is not None
    assert period.reporting_period_type == "year_to_date"
    # End month Jestha is fiscal position 11 → rolls into BS 2082 (lead+1).
    assert period.reporting_period_bs == "Jestha 2082"
    assert period.fiscal_year_bs == "2081/82"
    assert period.cumulative_note is not None
    assert "cumulative" in period.cumulative_note
    assert "11 months" in period.cumulative_note


def test_period_end_month_read_from_scope_not_ad_edge() -> None:
    """The BS end month comes from the scope parenthetical, never the AD edge.

    "to Mid June 2025" is the CLOSE of Jestha; naively mapping AD June → a BS
    month would yield Ashadh and mislabel the period. Guard against regression.
    """
    desc = (
        "Based on First Eleven Months (Shrawan-Jestha) of FY 2081/82 "
        "(Mid July 2024 to Mid June 2025)"
    )
    period, _ = parse_period_descriptor(desc)
    assert period is not None
    assert period.reporting_period_bs.startswith("Jestha")
    assert "Ashadh" not in period.reporting_period_bs


def test_period_asar_alias_maps_to_ashadh() -> None:
    desc = "Based on Annual data (Shrawan-Asar) of FY 2080/81 (Mid July 2023 to Mid July 2024)"
    period, err = parse_period_descriptor(desc)
    assert err is None and period is not None
    assert period.fiscal_year_bs == "2080/81"


def test_period_rejects_garbage_descriptor() -> None:
    period, err = parse_period_descriptor("totally unrelated text")
    assert period is None
    assert err is not None
    assert err.error_class == "RegexMismatch"


def test_period_rejects_inconsistent_fy_tail() -> None:
    desc = "Based on Annual data (Shrawan-Asar) of FY 2081/85 (Mid July 2024 to Mid July 2025)"
    period, err = parse_period_descriptor(desc)
    assert period is None
    assert err is not None and err.error_class == "RegexMismatch"


# ---------------------------------------------------------------------------
# Commodity sheet core (HS code → fact).
# ---------------------------------------------------------------------------

# Synthesized imports-by-commodity table: [HSCode, Description, Unit, Qty, Value, Revenue].
_IMPORTS_COMMODITY: list[tuple[object, ...]] = [
    ("Table 5:Imports by Commodities", None, None, None, None, None),  # title (r0)
    (None, None, None, None, "(figures are in Rs. Thousands)", None),  # unit note (r1)
    ("HSCode", "Description", "Unit", "Quantity", "Imports_Value", "Imports_Revenue"),  # r2
    ("01012900", "Other horses", "PCS", "22", "24441.6385", "0"),
    ("27101941", "Diesel (HSD)", "Ltr", "1000000", "150000000.5", "30000000.0"),
    ("87032391", "Motor cars 1500-2500cc", "PCS", "0", "0", "0"),  # genuine zero kept
    ("", "Total", "", None, "150024442.1385", "30000000.0"),  # aggregate → excluded
]


def test_commodity_imports_one_fact_per_hs_code() -> None:
    rows, errors = extract_commodity_rows(
        _IMPORTS_COMMODITY,
        "customs-merchandise-imports",
        "Merchandise imports (customs)",
        _PERIOD_ANNUAL,
        value_col=4,
    )
    assert errors == []
    by_code = {r.dimension_value: r.value for r in rows}
    assert by_code == {
        "01012900": pytest.approx(24441.6385),
        "27101941": pytest.approx(150000000.5),
        "87032391": pytest.approx(0.0),  # zero preserved
    }
    for r in rows:
        assert r.base_indicator_slug == "customs-merchandise-imports"
        assert r.dimension_kind == "commodity"
        assert r.unit == "npr_thousand"
        assert r.confidence_grade == "A"


def test_commodity_hs_code_is_dimension_value_label_is_description() -> None:
    rows, _ = extract_commodity_rows(
        _IMPORTS_COMMODITY, "customs-merchandise-imports", "x", _PERIOD_ANNUAL, value_col=4
    )
    diesel = next(r for r in rows if r.dimension_value == "27101941")
    assert diesel.dimension_label == "Diesel (HSD)"


def test_commodity_total_row_excluded() -> None:
    rows, _ = extract_commodity_rows(
        _IMPORTS_COMMODITY, "customs-merchandise-imports", "x", _PERIOD_ANNUAL, value_col=4
    )
    assert "Total" not in {r.dimension_label for r in rows}
    assert len(rows) == 3


def test_commodity_non_hs_code_row_surfaces_error_not_silent() -> None:
    table = [
        ("t", None, None, None, None, None),
        (None, None, None, None, None, None),
        ("HSCode", "Description", "Unit", "Quantity", "Imports_Value", "Imports_Revenue"),
        ("ABC123", "Bogus code", "PCS", "1", "100.0", "0"),  # not 6/8 digits
    ]
    rows, errors = extract_commodity_rows(
        table, "customs-merchandise-imports", "x", _PERIOD_ANNUAL, value_col=4
    )
    assert rows == []
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"
    assert isinstance(errors[0], ParserError)


def test_commodity_exports_value_column() -> None:
    # Exports sheet: [HSCode, Description, Unit, Quantity, Exports_Value].
    table = [
        ("Table 7", None, None, None, None),
        (None, None, None, "(Exports Value are in Rs. Thousand)", None),
        ("HSCode", "Description", "Unit", "Quantity", "Exports_Value"),
        ("09042110", "Dried ginger", "Kg", "5000", "987.65"),
        ("", "Total", "", None, "987.65"),
    ]
    rows, errors = extract_commodity_rows(
        table,
        "customs-merchandise-exports",
        "Merchandise exports (customs)",
        _PERIOD_ANNUAL,
        value_col=4,
    )
    assert errors == []
    assert len(rows) == 1
    assert rows[0].dimension_value == "09042110"
    assert rows[0].value == pytest.approx(987.65)
    assert rows[0].base_indicator_slug == "customs-merchandise-exports"


# ---------------------------------------------------------------------------
# Commodity×partner cross-tab core (long form: HS, Desc, Partner, Unit, Qty, Value)
# → composite "<hs>__<country-slug>" dimension (ADR-0018).
# ---------------------------------------------------------------------------

# Synthesized imports cross-tab: [HSCode, Description, Partner, Unit, Qty, Imports_Value, Revenue].
# Two commodities; the first spread across two partners — its partner-sum (24 + 76
# = 100) must equal a single-dimension commodity total of 100 (reconciliation).
_IMPORTS_XTAB: list[tuple[object, ...]] = [
    ("Table 4:Imports by Commodity and Partner", None, None, None, None, None, None),  # r0
    (None, None, None, None, "(Import Value ... Rs. Thousand)", None, None),  # r1
    (
        "HSCode",
        "Description",
        "Partner Countries",
        "Unit",
        "Quantity",
        "Imports_Value",
        "Rev",
    ),  # r2
    ("27101930", "Diesel", "India", "Ltr", "1000", "24.0", "2.4"),
    ("27101930", "Diesel", "United Arab Emirates", "Ltr", "3000", "76.0", "7.6"),
    ("85171300", "Smartphones", "China", "PCS", "0", "0", "0"),  # genuine zero kept
    ("", "Total", "", "", None, "100.0", "10.0"),  # grand total → excluded
]


def test_commodity_partner_composite_dimension_value_and_label() -> None:
    rows, errors = extract_commodity_partner_rows(
        _IMPORTS_XTAB,
        "customs-merchandise-imports",
        "Merchandise imports (customs)",
        "customs-import-source",
        _PERIOD_ANNUAL,
        value_col=5,
    )
    assert errors == []
    by_dim = {r.dimension_value: r for r in rows}
    # Composite value = "<hs>__<country-slug>"; label = "<description> → <country>".
    assert set(by_dim) == {
        "27101930__india",
        "27101930__united-arab-emirates",
        "85171300__china",
    }
    diesel_in = by_dim["27101930__india"]
    assert diesel_in.dimension_label == "Diesel → India"
    assert diesel_in.value == pytest.approx(24.0)
    assert by_dim["27101930__united-arab-emirates"].value == pytest.approx(76.0)
    assert by_dim["85171300__china"].value == pytest.approx(0.0)  # zero preserved
    for r in rows:
        assert r.dimension_kind == "customs-import-source"
        assert r.base_indicator_slug == "customs-merchandise-imports"
        assert r.unit == "npr_thousand"
        assert r.confidence_grade == "A"
        # Separator is unambiguous: country slug part contains no "__".
        assert r.dimension_value.count("__") == 1


def test_commodity_partner_reconciles_to_commodity_total() -> None:
    """ADR-0011: summing a commodity's partner cells == its commodity total."""
    rows, _ = extract_commodity_partner_rows(
        _IMPORTS_XTAB,
        "customs-merchandise-imports",
        "x",
        "customs-import-source",
        _PERIOD_ANNUAL,
        5,
    )
    diesel_partner_sum = sum(r.value for r in rows if r.dimension_value.startswith("27101930__"))
    assert diesel_partner_sum == pytest.approx(100.0)  # 24 + 76 == commodity total


def test_commodity_partner_grand_total_excluded() -> None:
    rows, _ = extract_commodity_partner_rows(
        _IMPORTS_XTAB,
        "customs-merchandise-imports",
        "x",
        "customs-import-source",
        _PERIOD_ANNUAL,
        5,
    )
    assert "Total" not in {r.dimension_label for r in rows}
    assert len(rows) == 3  # 2 diesel partners + 1 smartphone partner


def test_commodity_partner_exports_value_column_and_kind() -> None:
    # Exports cross-tab: [HSCode, Description, Partner, Unit, Qty, Exports_Value].
    table = [
        ("Table 6:Exports by Commodity and Partner", None, None, None, None, None),
        (None, None, None, None, "(Exports Value are in Rs. Thousand)", None),
        ("HSCode", "Description", "Partner Countries", "Unit", "Quantity", "Exports_Value"),
        ("09042110", "Dried ginger", "United States", "Kg", "5000", "987.65"),
        ("", "Total", "", "", None, "987.65"),
    ]
    rows, errors = extract_commodity_partner_rows(
        table,
        "customs-merchandise-exports",
        "Merchandise exports (customs)",
        "customs-export-destination",
        _PERIOD_ANNUAL,
        value_col=5,
    )
    assert errors == []
    assert len(rows) == 1
    assert rows[0].dimension_value == "09042110__united-states"
    assert rows[0].dimension_label == "Dried ginger → United States"
    assert rows[0].value == pytest.approx(987.65)
    assert rows[0].dimension_kind == "customs-export-destination"
    assert rows[0].base_indicator_slug == "customs-merchandise-exports"


def test_commodity_partner_blank_partner_surfaces_error_not_silent() -> None:
    table = [
        ("t", None, None, None, None, None),
        (None, None, None, None, None, None),
        ("HSCode", "Description", "Partner Countries", "Unit", "Quantity", "Imports_Value"),
        ("27101930", "Diesel", "", "Ltr", "1000", "24.0"),  # blank partner (not a total)
    ]
    rows, errors = extract_commodity_partner_rows(
        table, "customs-merchandise-imports", "x", "customs-import-source", _PERIOD_ANNUAL, 5
    )
    assert rows == []
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"
    assert isinstance(errors[0], ParserError)


def test_commodity_partner_bad_hs_surfaces_error() -> None:
    table = [
        ("t", None, None, None, None, None),
        (None, None, None, None, None, None),
        ("HSCode", "Description", "Partner Countries", "Unit", "Quantity", "Imports_Value"),
        ("ABC123", "Bogus", "India", "PCS", "1", "100.0"),  # not 6/8 digits
    ]
    rows, errors = extract_commodity_partner_rows(
        table, "customs-merchandise-imports", "x", "customs-import-source", _PERIOD_ANNUAL, 5
    )
    assert rows == []
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"


def test_commodity_partner_empty_sheet_yields_nothing() -> None:
    assert extract_commodity_partner_rows(
        [], "s", "n", "customs-import-source", _PERIOD_ANNUAL, 5
    ) == ([], [])


# ---------------------------------------------------------------------------
# Country sheet core (SN, Partner, Imports_Value, Exports_Value, Trade_Balance).
# ---------------------------------------------------------------------------

_COUNTRY: list[tuple[object, ...]] = [
    ("Table 3 :Trade Balance by Partner", None, None, None, None),
    (None, None, None, None, "(figures are in Rs. Thousands)"),
    ("SN", "Partner Countries", "Imports_Value", "Exports_Value", "Trade_Balance"),
    ("1", "India", "1000000.0", "200000.0", "-800000.0"),
    ("2", "China", "500000.0", "0", "-500000.0"),  # zero export preserved
    ("3", "Angola", "0", "220.8", "220.8"),  # zero import preserved
    ("4", "Andorra", "2328.6", "-", "-2328.6"),  # dash export → no export fact
    ("", "Total", "1502328.6", "200220.8", "-1302107.8"),  # aggregate → excluded
]


def test_country_emits_both_directions() -> None:
    rows, errors = extract_country_rows(_COUNTRY, _PERIOD_ANNUAL)
    assert errors == []
    imports = _by_dim(rows, _IMP)
    exports = _by_dim(rows, _EXP)
    assert imports == {
        "india": pytest.approx(1000000.0),
        "china": pytest.approx(500000.0),
        "angola": pytest.approx(0.0),
        "andorra": pytest.approx(2328.6),
    }
    # Andorra export is a dash → no export fact; China export 0 IS a fact.
    assert exports == {
        "india": pytest.approx(200000.0),
        "china": pytest.approx(0.0),
        "angola": pytest.approx(220.8),
    }


def test_country_total_row_and_dimension_kind() -> None:
    rows, _ = extract_country_rows(_COUNTRY, _PERIOD_ANNUAL)
    assert all(r.dimension_kind == "country" for r in rows)
    assert "total" not in {r.dimension_value for r in rows}


def test_country_both_values_blank_surfaces_error() -> None:
    table = [
        ("t", None, None, None, None),
        (None, None, None, None, None),
        ("SN", "Partner Countries", "Imports_Value", "Exports_Value", "Trade_Balance"),
        ("1", "Nowhereland", "-", "", "0"),
    ]
    rows, errors = extract_country_rows(table, _PERIOD_ANNUAL)
    assert rows == []
    assert len(errors) == 1
    assert errors[0].error_class == "ValueUnparseable"


# ---------------------------------------------------------------------------
# Customs-office sheet core (SN, Customs, Imports_Value, Import_Share, Exports_Value, Export_Share).
# ---------------------------------------------------------------------------

_CUSTOMS: list[tuple[object, ...]] = [
    ("Table 9:Imports and Exports by Customs", None, None, None, None, None),
    (None, None, None, None, "(... in Rs. Thousand)", None),
    ("SN", "Customs", "Imports_Value", "Import_Share", "Exports_Value", "Export_Share"),
    ("1", "BHAIRAHAWA", "263815066.66", "14.62", "20922355.87", "7.55"),
    ("2", "BIRGUNJ", "500000.0", "27.7", "30000.0", "10.8"),
    ("", "Total", "763815066.66", "100.0", "20952355.87", "100.0"),
]


def test_customs_office_dimension_uses_exports_col_4() -> None:
    rows, errors = extract_customs_rows(_CUSTOMS, _PERIOD_ANNUAL)
    assert errors == []
    assert all(r.dimension_kind == "customs_office" for r in rows)
    exports = _by_dim(rows, _EXP)
    # Export value must come from col 4 (Exports_Value), NOT col 3 (Import_Share).
    assert exports["bhairahawa"] == pytest.approx(20922355.87)
    assert exports["birgunj"] == pytest.approx(30000.0)
    imports = _by_dim(rows, _IMP)
    assert imports["bhairahawa"] == pytest.approx(263815066.66)


def test_customs_total_excluded() -> None:
    rows, _ = extract_customs_rows(_CUSTOMS, _PERIOD_ANNUAL)
    assert "total" not in {r.dimension_value for r in rows}
    assert len(rows) == 4  # 2 offices × 2 directions


# ---------------------------------------------------------------------------
# Cross-cutting invariants.
# ---------------------------------------------------------------------------


def test_cumulative_note_appended_to_base_name() -> None:
    ytd = _Period(
        reporting_period_type="year_to_date",
        reporting_period_bs="Jestha 2082",
        reporting_period_ad_start=datetime(2024, 7, 15, tzinfo=UTC),
        reporting_period_ad_end=datetime(2025, 6, 15, tzinfo=UTC),
        fiscal_year_bs="2081/82",
        fiscal_year_ad_label="2024/25",
        cumulative_note="cumulative Shrawan–Jestha (11 months) of FY 2081/82",
    )
    rows, _ = extract_country_rows(_COUNTRY, ytd)
    assert all("[cumulative" in r.base_indicator_name for r in rows)


def test_idempotent() -> None:
    a, _ = extract_country_rows(_COUNTRY, _PERIOD_ANNUAL)
    b, _ = extract_country_rows(_COUNTRY, _PERIOD_ANNUAL)
    assert [r.to_json_dict() for r in a] == [r.to_json_dict() for r in b]


def test_dimension_values_are_kebab_and_non_empty() -> None:
    rows, _ = extract_country_rows(_COUNTRY, _PERIOD_ANNUAL)
    for r in rows:
        assert r.dimension_value
        assert " " not in r.dimension_value
        assert r.dimension_value == r.dimension_value.strip("-")


def test_empty_sheets_yield_nothing() -> None:
    assert extract_commodity_rows([], "s", "n", _PERIOD_ANNUAL, 4) == ([], [])
    assert extract_country_rows([], _PERIOD_ANNUAL) == ([], [])
    assert extract_customs_rows([], _PERIOD_ANNUAL) == ([], [])


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.3.0"


def test_missing_file_returns_failure() -> None:
    res = parse_customs_fts("nonexistent-customs.xlsx", "x")
    assert res.status == "failure"
    assert res.dimensional_rows == []
    assert res.errors and all(e.error_class for e in res.errors)


def test_result_json_shape_matches_dne_cli_contract() -> None:
    from customs_trade.parser import CustomsResult

    row = DimensionalRowDraft(
        base_indicator_slug="customs-merchandise-imports",
        base_indicator_name="Merchandise imports (customs)",
        dimension_kind="commodity",
        dimension_value="27101941",
        dimension_label="Diesel (HSD)",
        value=1.0,
        unit="npr_thousand",
        reporting_period_type="annual",
        reporting_period_bs="2081/82",
        reporting_period_ad_start=datetime(2024, 7, 15, tzinfo=UTC),
        reporting_period_ad_end=datetime(2025, 7, 15, tzinfo=UTC),
        fiscal_year_bs="2081/82",
        fiscal_year_ad_label="2024/25",
        confidence_grade="A",
    )
    payload = CustomsResult(
        status="success", parser_version=PARSER_VERSION, dimensional_rows=[row], errors=[]
    ).to_json_dict()
    assert set(payload) == {"status", "parser_version", "dimensional_rows", "errors"}
    sample = payload["dimensional_rows"][0]
    assert set(sample) == {
        "base_indicator_slug",
        "base_indicator_name",
        "dimension_kind",
        "dimension_value",
        "dimension_label",
        "value",
        "unit",
        "reporting_period_type",
        "reporting_period_bs",
        "reporting_period_ad_start",
        "reporting_period_ad_end",
        "fiscal_year_bs",
        "fiscal_year_ad_label",
        "confidence_grade",
    }
    assert "T" in sample["reporting_period_ad_start"]  # ISO-8601 datetime


# ---------------------------------------------------------------------------
# Optional integration against the real workbooks (skipped if absent).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_ANNUAL.exists(), reason="real annual FTS workbook not on disk")
def test_real_annual_magnitude_and_unit() -> None:
    res = parse_customs_fts(str(REAL_ANNUAL), "real-annual")
    assert res.status in ("success", "partial"), f"errors={res.errors[:3]}"
    # ADR-0011 magnitude: sum imports across the country dimension ≈ NPR 1.8tn.
    imp = sum(
        r.value
        for r in res.dimensional_rows
        if r.base_indicator_slug == "customs-merchandise-imports" and r.dimension_kind == "country"
    )
    npr = imp * 1_000  # thousand → rupees
    assert 1.5e12 < npr < 2.2e12, f"annual imports NPR {npr:,.0f} outside expected ~1.8tn"
    for r in res.dimensional_rows:
        assert r.unit == "npr_thousand"
        assert r.confidence_grade == "A"
    kinds = {r.dimension_kind for r in res.dimensional_rows}
    assert kinds == {
        "commodity",
        "country",
        "customs_office",
        "customs-import-source",
        "customs-export-destination",
    }
    assert res.dimensional_rows[0].reporting_period_type == "annual"


@pytest.mark.skipif(not REAL_ANNUAL.exists(), reason="real annual FTS workbook not on disk")
def test_real_annual_crosstab_reconciles_to_commodity_totals() -> None:
    """ADR-0011: a commodity's cross-tab partner cells sum to its commodity total.

    The composite-dimension cross-tab (sheets 4 & 6) is a strict disaggregation of
    the single-dimension commodity facts (sheets 5 & 7) under the SAME base measure
    slug, so for every commodity HS code the partner-sum must equal the commodity
    total. Verified across every commodity (worst relative diff must be ~0).
    """
    res = parse_customs_fts(str(REAL_ANNUAL), "real-annual")
    assert res.status in ("success", "partial")

    for base_slug, xtab_kind in (
        (_IMP, "customs-import-source"),
        (_EXP, "customs-export-destination"),
    ):
        # Single-dimension commodity totals: {hs_code: value}.
        commodity_total: dict[str, float] = {
            r.dimension_value: r.value
            for r in res.dimensional_rows
            if r.base_indicator_slug == base_slug and r.dimension_kind == "commodity"
        }
        # Cross-tab partner-sum per commodity: split "<hs>__<country>" on "__".
        partner_sum: dict[str, float] = {}
        for r in res.dimensional_rows:
            if r.base_indicator_slug != base_slug or r.dimension_kind != xtab_kind:
                continue
            hs_code = r.dimension_value.split("__", 1)[0]
            partner_sum[hs_code] = partner_sum.get(hs_code, 0.0) + r.value

        assert partner_sum, f"no cross-tab facts for {xtab_kind}"
        # Same commodity set on both sides (no commodity gained/lost in the cross-tab).
        assert set(partner_sum) == set(commodity_total)
        worst = max(
            abs(partner_sum[hs] - commodity_total[hs]) / abs(commodity_total[hs])
            for hs in commodity_total
            if commodity_total[hs] != 0
        )
        assert worst < 1e-6, f"{base_slug}: cross-tab partner-sum diverges from commodity total"


@pytest.mark.skipif(not REAL_SHRAWAN.exists(), reason="real Shrawan FTS workbook not on disk")
def test_real_shrawan_is_single_month() -> None:
    res = parse_customs_fts(str(REAL_SHRAWAN), "real-shrawan")
    assert res.status in ("success", "partial")
    s = res.dimensional_rows[0]
    assert s.reporting_period_type == "monthly"
    assert s.reporting_period_bs == "Shrawan 2081"
    # Monthly imports ~NPR 128bn — in the ADR-0011 100-150bn/month band.
    imp = sum(
        r.value
        for r in res.dimensional_rows
        if r.base_indicator_slug == "customs-merchandise-imports" and r.dimension_kind == "country"
    )
    assert 1.0e11 < imp * 1_000 < 1.6e11


@pytest.mark.skipif(not REAL_ANNUAL.exists(), reason="real annual FTS workbook not on disk")
def test_cli_emits_valid_json_on_real_file() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scrapers_dir = repo_root / "scrapers"
    proc = subprocess.run(
        [sys.executable, "-m", "customs_trade.parser", str(REAL_ANNUAL), "doc"],
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
