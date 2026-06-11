"""Tests for the MoALD Agricultural Statistics parser.

Fixture: tests/fixtures/agri_stats_2080_81_excerpt.pdf
  4-page excerpt containing (in order):
    page 0 = orig p9  — §1.3 Cereal, §1.4 Cash, §1.5 Pulses start
    page 1 = orig p10 — §1.5 Pulses cont., §2.2 Livestock start
    page 2 = orig p11 — §2.2 Livestock cont., §3 Fertilizer
    page 3 = orig p14 — Table 1.1 ten-year cereal
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


def _val(rows: list, slug: str, dim_val: str, fy_bs: str) -> float | None:
    for r in rows:
        if r.base_indicator_slug == slug and r.dimension_value == dim_val and r.reporting_period_bs == fy_bs:
            return r.value
    return None


def _rows_for(rows: list, slug: str) -> list:
    return [r for r in rows if r.base_indicator_slug == slug]


# ---------------------------------------------------------------------------
# Status + structure
# ---------------------------------------------------------------------------


def test_status_success(result: AgriResult) -> None:
    assert result.status == "success"


def test_parser_version(result: AgriResult) -> None:
    assert result.parser_version == PARSER_VERSION


def test_no_errors(result: AgriResult) -> None:
    assert result.errors == []


def test_total_row_count(rows: list) -> None:
    # 6 crops × 3 metrics × 11 years = 198 cereal (Table 1.1: 2013/14–2023/24 = 11 rows)
    # 5 cash crops × 2 metrics × 3 years = 30
    # 8 pulses × 2 metrics × 3 years = 48
    # 13 livestock products × 3 years = 39
    # 4 fertilizer types × 3 years = 12
    assert len(rows) == 327


def test_slug_categories(rows: list) -> None:
    slugs = {r.base_indicator_slug for r in rows}
    expected = {
        "agri-cereal-area",
        "agri-cereal-production",
        "agri-cereal-yield",
        "agri-cashcrop-area",
        "agri-cashcrop-production",
        "agri-pulse-area",
        "agri-pulse-production",
        "agri-livestock-production",
        "agri-fertilizer-sales",
    }
    assert slugs == expected


# ---------------------------------------------------------------------------
# Table 1.1 — 10-year cereal series
# ---------------------------------------------------------------------------


def test_cereal_area_row_count(rows: list) -> None:
    # 6 crops × 11 years (2013/14–2023/24) = 66
    assert len(_rows_for(rows, "agri-cereal-area")) == 66


def test_cereal_production_row_count(rows: list) -> None:
    assert len(_rows_for(rows, "agri-cereal-production")) == 66


def test_cereal_yield_row_count(rows: list) -> None:
    assert len(_rows_for(rows, "agri-cereal-yield")) == 66


def test_cereal_crops_set(rows: list) -> None:
    crops = {r.dimension_value for r in _rows_for(rows, "agri-cereal-area")}
    assert crops == {"paddy", "maize", "millet", "buckwheat", "wheat", "barley"}


def test_cereal_fy_range(rows: list) -> None:
    fys = {r.reporting_period_bs for r in _rows_for(rows, "agri-cereal-area")}
    assert "2070/71" in fys
    assert "2080/81" in fys
    assert len(fys) == 11  # 2013/14–2023/24 = 11 years despite "Last Ten Years" heading


def test_paddy_production_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-cereal-production", "paddy", "2080/81")
    assert v == pytest.approx(5_724_234.0)


def test_paddy_production_fy2070_71(rows: list) -> None:
    # First year in the 10-year series: AD 2013/14 → BS 2070/71
    v = _val(rows, "agri-cereal-production", "paddy", "2070/71")
    assert v == pytest.approx(5_047_047.0)


def test_wheat_yield_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-cereal-yield", "wheat", "2080/81")
    assert v == pytest.approx(2.99)


def test_buckwheat_area_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-cereal-area", "buckwheat", "2080/81")
    assert v == pytest.approx(11_253.0)


def test_cereal_units(rows: list) -> None:
    assert all(r.unit == "hectare" for r in _rows_for(rows, "agri-cereal-area"))
    assert all(r.unit == "metric_tonne" for r in _rows_for(rows, "agri-cereal-production"))
    assert all(r.unit == "metric_tonne_per_hectare" for r in _rows_for(rows, "agri-cereal-yield"))


def test_cereal_period_type(rows: list) -> None:
    assert all(r.reporting_period_type == "annual" for r in _rows_for(rows, "agri-cereal-area"))


def test_cereal_confidence_grade(rows: list) -> None:
    assert all(r.confidence_grade == "B" for r in _rows_for(rows, "agri-cereal-area"))


def test_cereal_ad_span_fy2070_71(rows: list) -> None:
    r = next(
        r for r in _rows_for(rows, "agri-cereal-area")
        if r.reporting_period_bs == "2070/71" and r.dimension_value == "paddy"
    )
    assert r.reporting_period_ad_start.year == 2013
    assert r.reporting_period_ad_end.year == 2014


# ---------------------------------------------------------------------------
# Summary §1.4 — Cash crops (3-year)
# ---------------------------------------------------------------------------


def test_cashcrop_row_count(rows: list) -> None:
    # 5 crops × 2 metrics × 3 years = 30
    area = len(_rows_for(rows, "agri-cashcrop-area"))
    prod = len(_rows_for(rows, "agri-cashcrop-production"))
    assert area == 15 and prod == 15


def test_potato_production_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-cashcrop-production", "potato", "2080/81")
    assert v == pytest.approx(3_521_794.0)


def test_cashcrop_crops(rows: list) -> None:
    crops = {r.dimension_value for r in _rows_for(rows, "agri-cashcrop-area")}
    assert crops == {"oilseeds", "potato", "sugarcane", "jute", "cotton"}


# ---------------------------------------------------------------------------
# Summary §1.5 — Pulses (3-year)
# ---------------------------------------------------------------------------


def test_pulse_row_count(rows: list) -> None:
    # 8 crops × 2 metrics × 3 years = 48
    area = len(_rows_for(rows, "agri-pulse-area"))
    prod = len(_rows_for(rows, "agri-pulse-production"))
    assert area == 24 and prod == 24


def test_lentil_production_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-pulse-production", "lentil", "2080/81")
    assert v == pytest.approx(152_936.0)


def test_soyabean_area_fy2078_79(rows: list) -> None:
    v = _val(rows, "agri-pulse-area", "soyabean", "2078/79")
    assert v == pytest.approx(24_921.0)


def test_pulse_crops(rows: list) -> None:
    crops = {r.dimension_value for r in _rows_for(rows, "agri-pulse-area")}
    assert "lentil" in crops
    assert "black-gram" in crops
    assert "pigeon-pea" in crops
    assert len(crops) == 8


# ---------------------------------------------------------------------------
# Summary §2.2 — Livestock production (3-year)
# ---------------------------------------------------------------------------


def test_livestock_row_count(rows: list) -> None:
    # 13 products × 3 years = 39
    assert len(_rows_for(rows, "agri-livestock-production")) == 39


def test_milk_total_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-livestock-production", "milk-total", "2080/81")
    assert v == pytest.approx(2_683_874.0)


def test_wool_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-livestock-production", "wool", "2080/81")
    assert v == pytest.approx(389_742.0)


def test_eggs_total_fy2078_79(rows: list) -> None:
    v = _val(rows, "agri-livestock-production", "eggs-total", "2078/79")
    assert v == pytest.approx(1_330_602.0)


def test_livestock_units(rows: list) -> None:
    livestock = _rows_for(rows, "agri-livestock-production")
    milk_rows = [r for r in livestock if r.dimension_value.startswith("milk")]
    assert all(r.unit == "metric_tonne" for r in milk_rows)
    wool_rows = [r for r in livestock if r.dimension_value == "wool"]
    assert all(r.unit == "kg" for r in wool_rows)
    egg_rows = [r for r in livestock if r.dimension_value.startswith("eggs")]
    assert all(r.unit == "thousand_units" for r in egg_rows)


# ---------------------------------------------------------------------------
# Summary §3 — Fertilizer (3-year)
# ---------------------------------------------------------------------------


def test_fertilizer_row_count(rows: list) -> None:
    # 4 types × 3 years = 12
    assert len(_rows_for(rows, "agri-fertilizer-sales")) == 12


def test_urea_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-fertilizer-sales", "urea", "2080/81")
    assert v == pytest.approx(259_542.0)


def test_dap_fy2078_79(rows: list) -> None:
    v = _val(rows, "agri-fertilizer-sales", "dap", "2078/79")
    assert v == pytest.approx(77_720.0)


def test_fertilizer_total_fy2080_81(rows: list) -> None:
    v = _val(rows, "agri-fertilizer-sales", "total", "2080/81")
    assert v == pytest.approx(458_318.0)


def test_fertilizer_unit(rows: list) -> None:
    assert all(r.unit == "metric_tonne" for r in _rows_for(rows, "agri-fertilizer-sales"))


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------


def test_missing_file() -> None:
    r = parse("/nonexistent/path/agri.pdf")
    assert r.status == "failure"
    assert any("not found" in e.error_detail.lower() for e in r.errors)
