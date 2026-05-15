"""End-to-end parser tests for the 5 first-batch CBS NPHC 2021 CSVs.

The real fuzzy resolver lives in :mod:`scrapers._common.municipality_resolver`
and depends on a gitignored MoF xlsx that may not be present in CI. These
tests inject a stub resolver via the parser's ``resolver_for_tests`` seam
so the parser logic is exercised without touching the gitignored data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from cbs_nphc import PARSER_VERSION, parse

FIXTURES = Path(__file__).parent / "fixtures"

# Canonical fixture mapping. Federal codes are arbitrary 8-digit strings —
# the parser does not validate the codes themselves, only that the resolver
# returns a HIGH-confidence match.
_FIXTURE_CODES: dict[str, str] = {
    "Phaktanlung Gaunpalika": "01010101",
    "Pokhara Metropolitan City": "04040040",  # canonical (post-override) name
}


@dataclass(frozen=True)
class _StubMatch:
    federal_code: str
    score: float


def _stub_resolver(name: str, district_hint: str | None = None) -> _StubMatch | None:
    """Test stub: looks up ``name`` in the fixture map. Returns None if absent.

    Mirrors the public shape of :func:`resolve_municipality` closely enough
    that the parser cannot tell the difference.
    """
    _ = district_hint
    code = _FIXTURE_CODES.get(name.strip())
    if code is None:
        return None
    return _StubMatch(federal_code=code, score=95.0)


# ---------------------------------------------------------------------------
# Sanity
# ---------------------------------------------------------------------------
def test_parser_version() -> None:
    assert PARSER_VERSION == "0.1.0"


def test_unknown_table_returns_failure() -> None:
    # Pass any path with an unrecognised stem.
    result = parse(
        str(FIXTURES / "Hhld01_OwnershipOfHouse.csv"),  # path exists
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    assert result.status == "success"  # smoke; real cases below

    # And an actually-unknown stem (a path that won't exist either):
    bogus = parse(str(FIXTURES.parent / "tests" / "nope_NotARealTable.csv"), "doc-id")
    assert bogus.status == "failure"


# ---------------------------------------------------------------------------
# Per-fixture happy paths
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("stem", "expected_mode", "expected_value_cols"),
    [
        ("Hhld01_OwnershipOfHouse", "A", 5),
        ("Hhld02_FoundationOfHouse", "A", 6),
        ("Hhld05_FloorOfHouse", "B", 7),
        ("Hhld10_HouseholdFacility", "B", 17),
        ("Indv01_PopulationBySex", "B", 8),
    ],
)
def test_first_batch_parses(stem: str, expected_mode: str, expected_value_cols: int) -> None:
    result = parse(
        str(FIXTURES / f"{stem}.csv"),
        "doc-id-test",
        resolver_for_tests=_stub_resolver,
    )
    assert result.status == "success", f"errors: {result.errors}"
    assert result.mode == expected_mode
    # Each palika row × value-column count. Fixtures have 2 palika rows
    # (NEPAL aggregate row is skipped because gapa==0).
    assert len(result.facts) == 2 * expected_value_cols, (
        f"got {len(result.facts)} facts; expected 2*{expected_value_cols}"
    )


def test_aggregate_rows_skipped() -> None:
    result = parse(
        str(FIXTURES / "Hhld05_FloorOfHouse.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    # NEPAL row has prov=dist=gapa=0 → skipped. Both kept rows must have
    # palika-level federal codes from the stub map.
    codes = {f.entity_slug for f in result.facts}
    assert codes == {"01010101", "04040040"}


def test_pokhara_override_applied() -> None:
    """Pokhara's CSV name is 'Pokhara Metropolitian City' (sic). The override
    must rewrite that to 'Pokhara Metropolitan City' before the resolver
    sees it; the stub resolver only knows the canonical spelling.
    """
    result = parse(
        str(FIXTURES / "Hhld01_OwnershipOfHouse.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    pokhara_facts = [f for f in result.facts if f.entity_slug == "04040040"]
    assert len(pokhara_facts) == 5  # 5 value cols in Hhld01


def test_indicator_slug_format() -> None:
    result = parse(
        str(FIXTURES / "Hhld05_FloorOfHouse.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    slugs = {f.indicator_slug for f in result.facts}
    # Slugs preserve the CSV stem verbatim (lowercased) so dev can grep
    # against the source filename. CamelCase boundaries are NOT split.
    assert "hhld05-floorofhouse-a-mud" in slugs
    assert "hhld05-floorofhouse-rowtotal" in slugs


def test_unresolved_municipality_becomes_error_not_fabricated_code() -> None:
    """If the resolver returns None, the parser must NOT fabricate a code —
    it emits a MunicipalityUnresolved error and skips the row.
    """

    def _always_none(name: str, district_hint: str | None = None) -> None:
        _ = name, district_hint
        return None

    result = parse(
        str(FIXTURES / "Hhld05_FloorOfHouse.csv"),
        "doc-id",
        resolver_for_tests=_always_none,
    )
    # Status must be failure because every palika row failed and zero facts emitted.
    assert result.status == "failure"
    # Two palika rows × one resolver miss each.
    assert len([e for e in result.errors if e.error_class == "MunicipalityUnresolved"]) == 2


def test_indv01_emits_population_indicators() -> None:
    """Indv01 has a different schema (no rowtotal / a_* cols) — proves the
    parser doesn't assume the Hhld* shape.
    """
    result = parse(
        str(FIXTURES / "Indv01_PopulationBySex.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    slugs = {f.indicator_slug for f in result.facts}
    assert "indv01-populationbysex-male" in slugs
    assert "indv01-populationbysex-female" in slugs
    assert "indv01-populationbysex-total" in slugs
    families = {f.indicator_family for f in result.facts}
    assert families == {"individual_demographic"}


def test_json_round_trip() -> None:
    """The parser's JSON dict shape is what the TS ingest script consumes."""
    result = parse(
        str(FIXTURES / "Hhld01_OwnershipOfHouse.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    blob = result.to_json_dict()
    assert blob["status"] == "success"
    assert blob["parser_version"] == "0.1.0"
    assert blob["mode"] == "A"
    assert len(blob["facts"]) == 10
    sample = blob["facts"][0]
    for key in (
        "entity_slug",
        "source_table_id",
        "indicator_family",
        "indicator_slug",
        "value",
        "unit",
        "census_year_ad",
        "census_year_bs",
        "confidence_grade_proposed",
    ):
        assert key in sample
