"""Tests for the DoFE migrant-worker permit-counts parser (ADR-0026).

Runs against a committed copy of the real NRB ``Migrant-Workers-Remittance.xlsx``
(small, ~270 KB) in ``fixtures/`` — the same real-file-fixture convention the
nrb_dne suite uses. No network.

Coverage:
    - known cell values (district 'Achham' FY2021/22 Mid-Aug Total = 24)
    - AD→BS fiscal-year conversion (+57) and Aug-anchored month numbering
    - the parser-output contract (MigrationPermitFactInput shape): sex required,
      permits an integer-string, month 1–12, marginal dimensions are null
    - the Migrant Worker sheet → new_individual + reentry total rows
    - the RECONCILIATION GATE: district-total == country-total ==
      migrant-worker-total for the first 3 months of FY2078/79 (zero tolerance)
    - determinism (same input → identical output)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dofe_migrant_workers import PARSER_VERSION, parse, reconcile

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "Migrant-Workers-Remittance.xlsx"

_VALID_SEX = {"male", "female", "total"}
_VALID_CATEGORY = {"new_individual", "reentry", "recruitment_agency", "g2g"}
_INT_STR = re.compile(r"^\d+$")


@pytest.fixture(scope="module")
def records() -> list[dict]:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    return parse(FIXTURE)


# ---------------------------------------------------------------------------
# Smoke / version
# ---------------------------------------------------------------------------


def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


def test_extracts_many_rows(records: list[dict]) -> None:
    # district (11.8k) + Country (32.7k) + Migrant Worker (319) ≈ 45k rows.
    assert len(records) > 40_000


def test_all_three_sheets_present(records: list[dict]) -> None:
    sheets = {r["sourceSheet"] for r in records}
    assert sheets == {"district", "Country", "Migrant Worker"}


# ---------------------------------------------------------------------------
# Output-contract discipline (MigrationPermitFactInput shape)
# ---------------------------------------------------------------------------


def test_contract_invariants_hold_for_every_row(records: list[dict]) -> None:
    for r in records:
        # sex REQUIRED and from the enum.
        assert r["sex"] in _VALID_SEX
        # permits is a non-negative integer string.
        assert isinstance(r["permits"], str) and _INT_STR.match(r["permits"])
        # month 1–12 (this corpus is fully monthly — never an annual aggregate).
        assert isinstance(r["monthNum"], int) and 1 <= r["monthNum"] <= 12
        # fiscal year present.
        assert isinstance(r["fiscalYearBs"], str) and "/" in r["fiscalYearBs"]
        assert r["unit"] == "permits"
        if r["permitCategory"] is not None:
            assert r["permitCategory"] in _VALID_CATEGORY


def test_district_rows_are_origin_marginal(records: list[dict]) -> None:
    drow = next(r for r in records if r["sourceSheet"] == "district")
    assert drow["originDistrict"] is not None
    # Every other dimension is marginal (null).
    assert drow["destinationCountry"] is None
    assert drow["destinationRegion"] is None
    assert drow["skillClass"] is None
    assert drow["permitCategory"] is None


def test_country_rows_are_destination_marginal(records: list[dict]) -> None:
    crow = next(r for r in records if r["sourceSheet"] == "Country")
    assert crow["destinationCountry"] is not None
    assert crow["originDistrict"] is None
    assert crow["skillClass"] is None
    assert crow["permitCategory"] is None


# ---------------------------------------------------------------------------
# Known values + calendar conversion
# ---------------------------------------------------------------------------


def test_known_value_achham_fy2021_midaug_total(records: list[dict]) -> None:
    """district 'Achham', FY2021/22 (AD) → BS 2078/79, Mid-Aug → month 1, Total = 24."""
    hit = [
        r
        for r in records
        if r["sourceSheet"] == "district"
        and r["originDistrict"] == "Achham"
        and r["fiscalYearBs"] == "2078/79"
        and r["monthNum"] == 1
        and r["sex"] == "total"
    ]
    assert len(hit) == 1
    assert hit[0]["permits"] == "24"


def test_known_value_achham_fy2021_midaug_sexes(records: list[dict]) -> None:
    """Male=24, Female=0, Total=24 are READ (total is not a computed sum)."""
    by_sex = {
        r["sex"]: r["permits"]
        for r in records
        if r["sourceSheet"] == "district"
        and r["originDistrict"] == "Achham"
        and r["fiscalYearBs"] == "2078/79"
        and r["monthNum"] == 1
    }
    assert by_sex == {"male": "24", "female": "0", "total": "24"}


def test_aggregate_district_row_excluded(records: list[dict]) -> None:
    # The 'Total' national-aggregate row is NOT emitted as an origin district.
    assert not any(
        r["sourceSheet"] == "district" and r["originDistrict"] == "Total" for r in records
    )


def test_aggregate_country_row_excluded(records: list[dict]) -> None:
    assert not any(
        r["sourceSheet"] == "Country" and r["destinationCountry"] == "Total"
        for r in records
    )


def test_migrant_worker_new_and_reentry(records: list[dict]) -> None:
    """The Migrant Worker sheet yields a new_individual + a reentry total row per month.

    AD 2021-08 → FY2078/79 month 1: New Entry = 13800, Renew Entry = 11628.
    """
    rows = [
        r
        for r in records
        if r["sourceSheet"] == "Migrant Worker"
        and r["fiscalYearBs"] == "2078/79"
        and r["monthNum"] == 1
    ]
    by_cat = {r["permitCategory"]: r["permits"] for r in rows}
    assert by_cat == {"new_individual": "13800", "reentry": "11628"}
    # Both are sex='total', all spatial dims marginal.
    for r in rows:
        assert r["sex"] == "total"
        assert r["originDistrict"] is None and r["destinationCountry"] is None


# ---------------------------------------------------------------------------
# RECONCILIATION GATE — the correctness proof
# ---------------------------------------------------------------------------


def test_reconciliation_district_country_migrant(records: list[dict]) -> None:
    """For FY2078/79 months 1–3 the three sheets' national monthly totals agree.

    district 'total' sum == country 'total' sum == Migrant Worker (New+Renew).
    These early, fully-populated months reconcile to the EXACT permit (zero
    tolerance); see the README for the latest-FY partial-block caveat.
    """
    agg = reconcile(records)
    expected = {1: 25428, 2: 36040, 3: 39671}
    for month, want in expected.items():
        v = agg[("2078/79", month)]
        assert v["district"] == want, f"district M{month}: {v['district']} != {want}"
        assert v["country"] == want, f"country M{month}: {v['country']} != {want}"
        assert v["migrant"] == want, f"migrant M{month}: {v['migrant']} != {want}"


def test_reconciliation_holds_broadly_within_tolerance(records: list[dict]) -> None:
    """Across all fully-populated months, district==country (exact for the bulk)
    and the migrant-worker series tracks within a small tolerance.

    The single latest-FY month where the two wide sheets are misaligned in the
    source (different trailing months populated) is excluded — that is a source
    artifact, faithfully reproduced, not a parse error.
    """
    agg = reconcile(records)
    months = [
        k
        for k, v in agg.items()
        if v["district"] and v["country"] and v["migrant"]
    ]
    assert len(months) >= 40
    # district vs country: agree exactly for the bulk; a handful of months differ
    # by only a few permits (source rounding), and exactly one latest-FY month is
    # materially off (the two sheets populate different trailing months there).
    dc_exact = sum(1 for k in months if agg[k]["district"] == agg[k]["country"])
    assert dc_exact >= len(months) - 6
    dc_close = sum(
        1 for k in months if abs(agg[k]["district"] - agg[k]["country"]) <= 50
    )
    assert dc_close >= len(months) - 1  # at most one materially-off month
    # district vs migrant: within 5% for every month except the known source-
    # misaligned latest-FY month.
    big = [
        k
        for k in months
        if abs(agg[k]["district"] - agg[k]["migrant"]) / max(agg[k]["district"], 1) > 0.05
    ]
    assert len(big) <= 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_deterministic() -> None:
    assert parse(FIXTURE) == parse(FIXTURE)
