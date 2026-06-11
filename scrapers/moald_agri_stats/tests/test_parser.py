"""Tests for the MoALD Agricultural Statistics parser (v0.2.0).

Fixture: tests/fixtures/agri_stats_2080_81_excerpt.pdf — an 11-page excerpt of
the 224-page FY 2080/81 report, carrying every table the parser targets:

  orig p9, p10  — Summary §1.6 (spices)
  orig p14      — Table 1.1 cereal 11-yr series + Table 1.2 cereal-by-province
  orig p15, p16 — Table 1.3 aggregate cereal by district (all 77 districts)
  orig p28      — Table 2.1 cash-crop 10-yr series + Table 2.2 cash-by-province
  orig p48      — Table 3.1 pulses 12-yr series (both sub-tables)
  orig p58      — Table 4.1 livestock population + Table 4.2 livestock products
  orig p81      — Table 6.1 fruit 10-yr series (4 types)
  orig p103     — Table 7.1 vegetable series + Table 7.2 vegetable-by-province
  orig p152     — Table 9.1 fertilizer 14-yr series

The parser is anchor-driven, so it produces identical output against this
fixture and the full PDF (verified: both 1546 rows, 0 errors).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from moald_agri_stats.parser import PARSER_VERSION, AgriResult, parse

FIXTURE = Path(__file__).parent / "fixtures" / "agri_stats_2080_81_excerpt.pdf"


@pytest.fixture(scope="module")
def result() -> AgriResult:
    return parse(str(FIXTURE))


@pytest.fixture(scope="module")
def rows(result: AgriResult) -> list:
    return result.dimensional_rows


def _val(
    rows: list, slug: str, dim_kind: str, dim_val: str, fy_bs: str = "2080/81",
) -> float | None:
    for r in rows:
        if (r.base_indicator_slug == slug and r.dimension_kind == dim_kind
                and r.dimension_value == dim_val and r.reporting_period_bs == fy_bs):
            return r.value
    return None


def _for(rows: list, slug: str, dim_kind: str | None = None) -> list:
    return [r for r in rows
            if r.base_indicator_slug == slug and (dim_kind is None or r.dimension_kind == dim_kind)]


# ---------------------------------------------------------------------------
# Status + overall shape
# ---------------------------------------------------------------------------


def test_status_success(result: AgriResult) -> None:
    assert result.status == "success"


def test_no_errors(result: AgriResult) -> None:
    assert result.errors == []


def test_parser_version(result: AgriResult) -> None:
    assert result.parser_version == "0.2.0"
    assert PARSER_VERSION == "0.2.0"


def test_total_row_count(rows: list) -> None:
    # Locked to the reconciled full-PDF == fixture count.
    assert len(rows) == 1546


def test_all_periods_annual(rows: list) -> None:
    assert all(r.reporting_period_type == "annual" for r in rows)


def test_all_confidence_b(rows: list) -> None:
    assert all(r.confidence_grade == "B" for r in rows)


def test_slug_catalogue(rows: list) -> None:
    assert {r.base_indicator_slug for r in rows} == {
        "agri-cereal-area", "agri-cereal-production", "agri-cereal-yield",
        "agri-cashcrop-area", "agri-cashcrop-production", "agri-cashcrop-yield",
        "agri-pulse-area", "agri-pulse-production", "agri-pulse-yield",
        "agri-livestock-population", "agri-livestock-production",
        "agri-fruit-total-area", "agri-fruit-productive-area",
        "agri-fruit-production", "agri-fruit-yield",
        "agri-vegetable-area", "agri-vegetable-production", "agri-vegetable-yield",
        "agri-fertilizer-sales", "agri-spice-area", "agri-spice-production",
    }


def test_dimension_kinds(rows: list) -> None:
    assert {r.dimension_kind for r in rows} == {
        "crop_type", "livestock_category", "livestock_product",
        "fertilizer_type", "province-crop", "province", "district",
    }


# ---------------------------------------------------------------------------
# Table 1.1 — cereal 11-yr series
# ---------------------------------------------------------------------------


def test_cereal_series_counts(rows: list) -> None:
    # 6 crops × 11 years
    assert len(_for(rows, "agri-cereal-area", "crop_type")) == 66
    assert len(_for(rows, "agri-cereal-production", "crop_type")) == 66
    assert len(_for(rows, "agri-cereal-yield", "crop_type")) == 66


def test_cereal_paddy_recent(rows: list) -> None:
    assert _val(rows, "agri-cereal-production", "crop_type", "paddy") == pytest.approx(5_724_234)


def test_cereal_paddy_oldest(rows: list) -> None:
    # AD 2013/14 → BS 2070/71 (the first year of the 11-row table)
    assert _val(
        rows, "agri-cereal-production", "crop_type", "paddy", "2070/71"
    ) == pytest.approx(5_047_047)


def test_cereal_wheat_yield(rows: list) -> None:
    assert _val(rows, "agri-cereal-yield", "crop_type", "wheat") == pytest.approx(2.99)


# ---------------------------------------------------------------------------
# Table 2.1 — cash crop 10-yr series
# ---------------------------------------------------------------------------


def test_cashcrop_series_counts(rows: list) -> None:
    # 5 crops × 10 years
    assert len(_for(rows, "agri-cashcrop-area", "crop_type")) == 50
    assert len(_for(rows, "agri-cashcrop-production", "crop_type")) == 50


def test_cashcrop_potato_recent(rows: list) -> None:
    assert _val(rows, "agri-cashcrop-production", "crop_type", "potato") == pytest.approx(3_521_794)


def test_cashcrop_sugarcane_oldest(rows: list) -> None:
    # AD 2014/15 → BS 2071/72 (first year of the 10-row table)
    assert _val(
        rows, "agri-cashcrop-area", "crop_type", "sugarcane", "2071/72"
    ) == pytest.approx(66_600)


# ---------------------------------------------------------------------------
# Table 3.1 — pulses 12-yr series (incl. variable Himili-Bean column)
# ---------------------------------------------------------------------------


def test_pulse_lentil_recent(rows: list) -> None:
    assert _val(rows, "agri-pulse-production", "crop_type", "lentil") == pytest.approx(152_936)


def test_pulse_lentil_oldest(rows: list) -> None:
    # AD 2012/13 → BS 2069/70 (first pulse year)
    assert _val(
        rows, "agri-pulse-production", "crop_type", "lentil", "2069/70"
    ) == pytest.approx(226_923)


def test_pulse_himili_present_recent_years_only(rows: list) -> None:
    # Himili Bean only appears in the last two source years (2022/23, 2023/24).
    himili = [
        r for r in rows
        if r.dimension_value == "himili-bean" and r.base_indicator_slug == "agri-pulse-production"
    ]
    assert {r.reporting_period_bs for r in himili} == {"2079/80", "2080/81"}
    assert _val(
        rows, "agri-pulse-production", "crop_type", "himili-bean", "2079/80"
    ) == pytest.approx(8_336)


def test_pulse_no_total_pseudo_crop(rows: list) -> None:
    # The 'Total' aggregate column must not be stored as a crop.
    assert _val(rows, "agri-pulse-production", "crop_type", "total") is None


# ---------------------------------------------------------------------------
# Table 4.1 / 4.2 — livestock population + products (transposed, right-aligned)
# ---------------------------------------------------------------------------


def test_livestock_population_count(rows: list) -> None:
    # 11 categories × 10 years
    assert len(_for(rows, "agri-livestock-population")) == 110


def test_livestock_cattle_recent(rows: list) -> None:
    assert _val(
        rows, "agri-livestock-population", "livestock_category", "cattle"
    ) == pytest.approx(5_198_388)


def test_livestock_goat_oldest(rows: list) -> None:
    # AD 2014/15 → BS 2071/72
    assert _val(
        rows, "agri-livestock-population", "livestock_category", "goat", "2071/72"
    ) == pytest.approx(10_251_569)


def test_livestock_milk_total(rows: list) -> None:
    assert _val(
        rows, "agri-livestock-production", "livestock_product", "milk-total"
    ) == pytest.approx(2_683_874)


def test_livestock_fish_right_aligned(rows: list) -> None:
    # Fish has only 8 of the 11 year-columns; values right-align to recent years.
    fish = [r for r in rows if r.dimension_value == "fish"]
    assert len(fish) == 8
    assert _val(
        rows, "agri-livestock-production", "livestock_product", "fish"
    ) == pytest.approx(123_403)
    # Earliest fish year present = AD 2016/17 → BS 2073/74
    assert _val(
        rows, "agri-livestock-production", "livestock_product", "fish", "2073/74"
    ) == pytest.approx(83_898)
    # No fish before that
    assert _val(rows, "agri-livestock-production", "livestock_product", "fish", "2070/71") is None


def test_livestock_units(rows: list) -> None:
    prod = _for(rows, "agri-livestock-production")
    assert next(r.unit for r in prod if r.dimension_value == "wool") == "kg"
    assert next(r.unit for r in prod if r.dimension_value == "eggs-total") == "thousand_units"
    assert next(r.unit for r in prod if r.dimension_value == "milk-total") == "metric_tonne"
    assert all(r.unit == "number" for r in _for(rows, "agri-livestock-population"))


# ---------------------------------------------------------------------------
# Table 6.1 — fruit series (4 types × 4 metrics × 10 years)
# ---------------------------------------------------------------------------


def test_fruit_counts(rows: list) -> None:
    assert len(_for(rows, "agri-fruit-production", "crop_type")) == 40  # 4 types × 10 yr


def test_fruit_types(rows: list) -> None:
    assert {r.dimension_value for r in _for(rows, "agri-fruit-production")} == {
        "citrus", "winter", "summer", "total-fruit",
    }


def test_fruit_citrus_recent(rows: list) -> None:
    assert _val(rows, "agri-fruit-production", "crop_type", "citrus") == pytest.approx(318_939)


def test_fruit_total_recent(rows: list) -> None:
    assert _val(
        rows, "agri-fruit-production", "crop_type", "total-fruit"
    ) == pytest.approx(1_508_701)


# ---------------------------------------------------------------------------
# Table 7.1 — vegetable series
# ---------------------------------------------------------------------------


def test_vegetable_series_count(rows: list) -> None:
    assert len(_for(rows, "agri-vegetable-production", "crop_type")) == 10


def test_vegetable_recent(rows: list) -> None:
    assert _val(
        rows, "agri-vegetable-production", "crop_type", "fresh-vegetable"
    ) == pytest.approx(4_440_116)


# ---------------------------------------------------------------------------
# Table 9.1 — fertilizer 14-yr series
# ---------------------------------------------------------------------------


def test_fertilizer_count(rows: list) -> None:
    # 4 types × 14 years
    assert len(_for(rows, "agri-fertilizer-sales")) == 56


def test_fertilizer_urea_recent(rows: list) -> None:
    assert _val(rows, "agri-fertilizer-sales", "fertilizer_type", "urea") == pytest.approx(259_542)


def test_fertilizer_urea_oldest(rows: list) -> None:
    # AD 2010/11 → BS 2067/68 (first fertilizer year)
    assert _val(
        rows, "agri-fertilizer-sales", "fertilizer_type", "urea", "2067/68"
    ) == pytest.approx(85_191)


# ---------------------------------------------------------------------------
# §1.6 — spices
# ---------------------------------------------------------------------------


def test_spice_ginger(rows: list) -> None:
    assert _val(rows, "agri-spice-production", "crop_type", "ginger") == pytest.approx(289_330)


def test_spice_crops(rows: list) -> None:
    assert {r.dimension_value for r in _for(rows, "agri-spice-production")} == {
        "large-cardamom", "ginger", "garlic", "turmeric", "dry-chili",
    }


# ---------------------------------------------------------------------------
# Provincial cross-sections (composite dimension)
# ---------------------------------------------------------------------------


def test_cereal_by_province_reconciles(rows: list) -> None:
    # Sum of province paddy production == national paddy production (FY 2080/81).
    national = _val(rows, "agri-cereal-production", "crop_type", "paddy")
    prov_sum = sum(
        r.value for r in rows
        if r.base_indicator_slug == "agri-cereal-production"
        and r.dimension_kind == "province-crop"
        and r.dimension_value.endswith("__paddy")
    )
    assert prov_sum == pytest.approx(national, abs=1)


def test_cereal_province_koshi_paddy(rows: list) -> None:
    assert _val(
        rows, "agri-cereal-production", "province-crop", "koshi__paddy"
    ) == pytest.approx(1_435_578)


def test_province_count_seven(rows: list) -> None:
    # Exactly 7 provinces, no district bleed-through.
    prov_rows = _for(rows, "agri-cereal-production", "province-crop")
    provs = {r.dimension_value.split("__")[0] for r in prov_rows}
    assert provs == {"koshi", "madhesh", "bagmati", "gandaki", "lumbini", "karnali", "sudurpaschim"}


def test_cashcrop_province_madhesh_sugarcane(rows: list) -> None:
    assert _val(
        rows, "agri-cashcrop-production", "province-crop", "madhesh__sugarcane"
    ) == pytest.approx(1_674_584)


def test_vegetable_by_province(rows: list) -> None:
    assert _val(rows, "agri-vegetable-production", "province", "bagmati") == pytest.approx(887_801)
    assert _val(
        rows, "agri-vegetable-production", "province", "sudurpaschim"
    ) == pytest.approx(328_085)


# ---------------------------------------------------------------------------
# District cross-section (Table 1.3) + reconciliation
# ---------------------------------------------------------------------------


def test_district_count_77(rows: list) -> None:
    districts = {r.dimension_value for r in _for(rows, "agri-cereal-production", "district")}
    assert len(districts) == 77


def test_district_jhapa(rows: list) -> None:
    assert _val(rows, "agri-cereal-production", "district", "jhapa") == pytest.approx(750_526)


def test_district_production_reconciles_to_national(rows: list) -> None:
    # Sum of all 77 districts' cereal production == national total (within rounding).
    dist_sum = sum(r.value for r in _for(rows, "agri-cereal-production", "district"))
    assert dist_sum == pytest.approx(11_293_841, abs=5)


def test_no_province_subtotal_in_districts(rows: list) -> None:
    # Province subtotal rows ('Koshi 772,510 …') and the 'N E P A L' grand total
    # must never be stored as districts.
    districts = {r.dimension_value for r in _for(rows, "agri-cereal-production", "district")}
    aggregates = {
        "koshi", "madhesh", "bagmati", "gandaki", "lumbini",
        "karnali", "sudurpaschim", "nepal",
    }
    assert not districts & aggregates


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


def test_missing_file() -> None:
    r = parse("/nonexistent/agri.pdf")
    assert r.status == "failure"
    assert any("not found" in e.error_detail.lower() for e in r.errors)
