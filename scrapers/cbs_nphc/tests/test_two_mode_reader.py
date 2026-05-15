"""Unit tests for the two-mode CBS NPHC 2021 CSV reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from cbs_nphc.two_mode_reader import detect_mode, read_census_csv

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_mode_a_title_preamble() -> None:
    line = ',,,"Table 01: Number of households ..., NPHC 2021",,,,,,,'
    assert detect_mode(line) == "A"


def test_detect_mode_b_clean_header() -> None:
    line = "prov,dist,gapa,provname,dname,gapaname,rowtotal,a_Mud"
    assert detect_mode(line) == "B"


def test_detect_mode_empty_falls_back_to_b() -> None:
    # Empty / unexpected files default to B so the parser fails on a
    # column-mismatch rather than silently misaligning a Mode-A file.
    assert detect_mode("") == "B"


def test_detect_mode_three_commas_without_table_is_b() -> None:
    # ",,,foo" without a literal '"Table ' is NOT Mode A.
    assert detect_mode(',,,foo,bar,baz') == "B"


def test_read_mode_a_hhld01() -> None:
    result = read_census_csv(FIXTURES / "Hhld01_OwnershipOfHouse.csv")
    assert result.mode == "A"
    assert result.header[:6] == ["prov", "dist", "gapa", "provname", "dname", "gapaname"]
    assert "a_Own" in result.header
    rows = list(result.rows)
    # Fixture: NEPAL + Phaktanlung + Pokhara = 3 data rows.
    assert len(rows) == 3
    # First data row is NEPAL aggregate.
    assert rows[0][3] == "NEPAL"
    # Last is Pokhara at (4,40,4).
    assert rows[-1][:3] == ["4", "40", "4"]


def test_read_mode_a_hhld02_wider_value_block() -> None:
    result = read_census_csv(FIXTURES / "Hhld02_FoundationOfHouse.csv")
    assert result.mode == "A"
    # Hhld02 has 5 value columns vs Hhld01's 4 — proves the reader doesn't
    # hard-code width.
    assert "e_Other" in result.header
    rows = list(result.rows)
    assert len(rows) == 3
    assert all(len(r) == len(result.header) for r in rows)


def test_read_mode_b_hhld05() -> None:
    result = read_census_csv(FIXTURES / "Hhld05_FloorOfHouse.csv")
    assert result.mode == "B"
    assert result.header[0] == "prov"
    rows = list(result.rows)
    assert len(rows) == 3


def test_read_mode_b_indv01_different_schema() -> None:
    result = read_census_csv(FIXTURES / "Indv01_PopulationBySex.csv")
    assert result.mode == "B"
    # Indv01 has 'nHhld,total,male,female' — no 'rowtotal' / 'a_*' cols.
    assert "rowtotal" not in result.header
    assert "total" in result.header
    assert "sex_ratio" in result.header


def test_read_nonexistent_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        read_census_csv(FIXTURES / "does_not_exist.csv")
