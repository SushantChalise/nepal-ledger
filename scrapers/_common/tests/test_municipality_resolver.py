"""Tests for _common.municipality_resolver.

Live canonical-table tests are skipped when ``Financial Data/`` is absent.
Resolution tests run against a 3-row in-memory fixture injected into the
module cache.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from _common import municipality_resolver
from _common._common_paths import financial_data_root
from _common.municipality_resolver import (
    MunicipalityMatch,
    load_canonical_municipalities,
    resolve_municipality,
)

# ---------------------------------------------------------------------------
# Live-data gate
# ---------------------------------------------------------------------------
CANONICAL_TABLE_PRESENT = (
    financial_data_root()
    / "mof_documents"
    / "Cleaned"
    / "Fiscal Transfer_2082_82.xlsx"
).exists()


# ---------------------------------------------------------------------------
# Fixture: 3-row canonical table
# ---------------------------------------------------------------------------
FIXTURE_ROWS: list[MunicipalityMatch] = [
    MunicipalityMatch(
        federal_code="27101001",
        name_en="Kathmandu Metropolitan City",
        name_ne="काठमाडौँ महानगरपालिका",
        local_level_type="metropolitan_city",
        district_en="Kathmandu",
        score=0.0,
    ),
    MunicipalityMatch(
        federal_code="40103001",
        name_en="Pokhara Metropolitan City",
        name_ne="पोखरा महानगरपालिका",
        local_level_type="metropolitan_city",
        district_en="Kaski",
        score=0.0,
    ),
    MunicipalityMatch(
        federal_code="80101101",
        name_en="Phungling Municipality",
        name_ne="फुङलिङ नगरपालिका",
        local_level_type="municipality",
        district_en="Taplejung",
        score=0.0,
    ),
]


@pytest.fixture(autouse=True)
def install_fixture_table() -> Iterator[None]:
    """Replace the module cache with the 3-row fixture for every test."""
    municipality_resolver._set_cache_for_tests(FIXTURE_ROWS)
    yield
    municipality_resolver._clear_cache_for_tests()


# ---------------------------------------------------------------------------
# Resolution tests
# ---------------------------------------------------------------------------


def test_resolve_clean_nepali_exact_match() -> None:
    match = resolve_municipality("काठमाडौँ महानगरपालिका")
    assert match is not None
    assert match.federal_code == "27101001"
    assert match.name_en == "Kathmandu Metropolitan City"
    assert match.local_level_type == "metropolitan_city"
    assert match.score == pytest.approx(100.0)


def test_resolve_clean_english_exact_match() -> None:
    match = resolve_municipality("Pokhara Metropolitan City")
    assert match is not None
    assert match.federal_code == "40103001"
    assert match.district_en == "Kaski"
    assert match.score == pytest.approx(100.0)


def test_resolve_with_ocr_typo_resolves_via_normalization() -> None:
    # The OCR typo "पाललका" should be normalized to "पालिका" before fuzzy
    # matching against the canonical Phungling row.
    match = resolve_municipality("फुङलिङ नगरपाललका")
    assert match is not None
    assert match.federal_code == "80101101"
    assert match.name_ne == "फुङलिङ नगरपालिका"
    # After normalization the strings are identical, so score should be 100.
    assert match.score == pytest.approx(100.0)


def test_resolve_english_fuzzy_under_threshold_returns_match() -> None:
    # A small English typo — should still land in High or Medium band.
    match = resolve_municipality("Phungling Municipalty")
    assert match is not None
    assert match.federal_code == "80101101"
    assert match.score >= municipality_resolver.MEDIUM_CONFIDENCE_THRESHOLD


def test_resolve_unmatchable_returns_none() -> None:
    # A non-existent fictitious municipality name.
    assert resolve_municipality("Atlantis Megalopolis") is None


def test_resolve_empty_input_returns_none() -> None:
    assert resolve_municipality("") is None
    assert resolve_municipality("   ") is None


def test_resolve_district_hint_narrows_search() -> None:
    match = resolve_municipality("Kathmandu Metropolitan City", district_hint="Kathmandu")
    assert match is not None
    assert match.district_en == "Kathmandu"


def test_resolve_unknown_district_hint_falls_back_to_full_table() -> None:
    # Hint a district that doesn't appear in the fixture — resolver falls
    # back to the full table rather than silently failing.
    match = resolve_municipality(
        "Kathmandu Metropolitan City",
        district_hint="Unknown District",
    )
    assert match is not None
    assert match.district_en == "Kathmandu"


# ---------------------------------------------------------------------------
# Live canonical-table loader (skipped without Financial Data/)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not CANONICAL_TABLE_PRESENT,
    reason="Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx not present",
)
def test_load_canonical_municipalities_live() -> None:
    # Drop the fixture so the real loader runs.
    municipality_resolver._clear_cache_for_tests()
    rows = load_canonical_municipalities()
    assert len(rows) == 753
    type_counts: dict[str, int] = {}
    for r in rows:
        type_counts[r.local_level_type] = type_counts.get(r.local_level_type, 0) + 1
    # Sanity-check the official Nepal split:
    assert type_counts["metropolitan_city"] == 6
    assert type_counts["sub_metropolitan_city"] == 11
    assert type_counts["municipality"] == 276
    assert type_counts["rural_municipality"] == 460
