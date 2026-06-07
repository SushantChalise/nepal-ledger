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
    assert PARSER_VERSION == "0.2.0"


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
    assert blob["parser_version"] == "0.2.0"
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


# ---------------------------------------------------------------------------
# Financial-inclusion + migration batch (Hhld11, Hhld12, Hhld17)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("stem", "expected_mode", "expected_value_cols", "expected_family"),
    [
        ("Hhld11_FemaleOwnershipOfFixedAsset", "B", 6, "household_economic"),
        ("Hhld12_SmallScaleBusiness", "B", 13, "household_economic"),
        ("Hhld17_AbsentHousehold", "B", 6, "household_demographic"),
    ],
)
def test_migration_batch_parses(
    stem: str,
    expected_mode: str,
    expected_value_cols: int,
    expected_family: str,
) -> None:
    """Happy-path for the three parseable migration/financial-inclusion tables."""
    result = parse(
        str(FIXTURES / f"{stem}.csv"),
        "doc-id-test",
        resolver_for_tests=_stub_resolver,
    )
    assert result.status == "success", f"errors: {result.errors}"
    assert result.mode == expected_mode
    # Each fixture has 2 palika rows (aggregate row with gapa==0 is skipped).
    assert len(result.facts) == 2 * expected_value_cols, (
        f"got {len(result.facts)} facts; expected 2*{expected_value_cols}"
    )
    families = {f.indicator_family for f in result.facts}
    assert families == {expected_family}


def test_hhld11_slug_format_and_unit() -> None:
    """Hhld11 slugs follow the kebab-case stem+col convention; unit is 'households'."""
    result = parse(
        str(FIXTURES / "Hhld11_FemaleOwnershipOfFixedAsset.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    slugs = {f.indicator_slug for f in result.facts}
    assert "hhld11-femaleownershipoffixedasset-rowtotal" in slugs
    assert "hhld11-femaleownershipoffixedasset-a-houseonly" in slugs
    assert "hhld11-femaleownershipoffixedasset-d-noownership" in slugs
    units = {f.unit for f in result.facts}
    assert units == {"households"}


def test_hhld11_female_ownership_values() -> None:
    """Hhld11 emits correct numeric values for a known palika row."""
    result = parse(
        str(FIXTURES / "Hhld11_FemaleOwnershipOfFixedAsset.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    # Phaktanlung fixture row: rowtotal=2832, a_HouseOnly=10, b_LandOnly=159,
    # c_HouseAndLand=83, d_NoOwnership=2547, e_notstd=33
    phaktanlung = [f for f in result.facts if f.entity_slug == "01010101"]
    assert len(phaktanlung) == 6
    by_slug = {f.indicator_slug: f.value for f in phaktanlung}
    assert by_slug["hhld11-femaleownershipoffixedasset-rowtotal"] == 2832.0
    assert by_slug["hhld11-femaleownershipoffixedasset-a-houseonly"] == 10.0
    assert by_slug["hhld11-femaleownershipoffixedasset-d-noownership"] == 2547.0


# ---------------------------------------------------------------------------
# Absent-population batch — multi-row-per-palika (Hhld18 / Hhld19 / Hhld20)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("stem", "expected_mode", "expected_sub_rows", "expected_value_cols", "expected_family"),
    [
        # Hhld18: 3 sex sub-rows × 2 palikas × 16 value cols
        ("Hhld18_AbsentPopnBySex", "B", 3, 16, "individual_migration"),
        # Hhld19: fixture has 5 sub-rows for Phaktanlung + 4 for Pokhara = 9 total.
        ("Hhld19_AbsentPopnByCountry", "B", None, 13, "individual_migration"),
        # Hhld20: fixture has 4 sub-rows for Phaktanlung + 4 for Pokhara = 8 total.
        ("Hhld20_AbsentPopnByReasonOfAbsence", "B", None, 8, "individual_migration"),
    ],
)
def test_absent_population_batch_parses(
    stem: str,
    expected_mode: str,
    expected_sub_rows: int | None,
    expected_value_cols: int,
    expected_family: str,
) -> None:
    """Happy-path for all three absent-population tables."""
    result = parse(
        str(FIXTURES / f"{stem}.csv"),
        "doc-id-test",
        resolver_for_tests=_stub_resolver,
    )
    assert result.status == "success", f"errors: {result.errors}"
    assert result.mode == expected_mode
    families = {f.indicator_family for f in result.facts}
    assert families == {expected_family}
    # Validate no duplicate (entity_slug, indicator_slug) pairs.
    pairs = [(f.entity_slug, f.indicator_slug) for f in result.facts]
    assert len(pairs) == len(set(pairs)), "duplicate (entity, slug) pairs emitted"
    # For tables where sub-row count is fixed across palikas, assert exact count.
    if expected_sub_rows is not None:
        assert len(result.facts) == 2 * expected_sub_rows * expected_value_cols, (
            f"got {len(result.facts)} facts; expected 2×{expected_sub_rows}×{expected_value_cols}"
        )


def test_hhld19_slug_encodes_sex_and_agegrp() -> None:
    """Indicator slugs for Hhld19 must include both sexname and agegrpname so
    slugs from different sub-rows of the same palika do not collide.
    """
    result = parse(
        str(FIXTURES / "Hhld19_AbsentPopnByCountry.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    slugs = {f.indicator_slug for f in result.facts}
    # Total × All Ages row.
    assert "hhld19-absentpopnbycountry-total-all-ages-a-india" in slugs
    # Male × All Ages row — must be distinct from Total × All Ages.
    assert "hhld19-absentpopnbycountry-male-all-ages-a-india" in slugs
    # Total × 15-24 row.
    assert "hhld19-absentpopnbycountry-total-15-24-a-india" in slugs
    # The three slugs above are distinct (no collision).
    slug_list = [
        "hhld19-absentpopnbycountry-total-all-ages-a-india",
        "hhld19-absentpopnbycountry-male-all-ages-a-india",
        "hhld19-absentpopnbycountry-total-15-24-a-india",
    ]
    assert len(set(slug_list)) == 3


def test_hhld19_no_duplicate_entity_slug_pairs() -> None:
    """Every (entity_slug, indicator_slug) pair must be unique within one parse."""
    result = parse(
        str(FIXTURES / "Hhld19_AbsentPopnByCountry.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    pairs = [(f.entity_slug, f.indicator_slug) for f in result.facts]
    assert len(pairs) == len(set(pairs)), "duplicate (entity, slug) pairs found"


def test_hhld19_spot_check_value() -> None:
    """Phaktanlung × Total × All Ages × a_india should be 83."""
    result = parse(
        str(FIXTURES / "Hhld19_AbsentPopnByCountry.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    target = [
        f for f in result.facts
        if f.entity_slug == "01010101"
        and f.indicator_slug == "hhld19-absentpopnbycountry-total-all-ages-a-india"
    ]
    assert len(target) == 1
    assert target[0].value == 83.0
    assert target[0].unit == "persons"


def test_same_gapaname_different_prov_dist_gapa_no_collision(
    tmp_path: Path,
) -> None:
    """Two palika rows with identical gapaname but different (prov, dist, gapa) triples
    must each produce facts — no collision errors — even when the stub resolver maps
    both names to the same federal code.

    This is the class of bug that caused ~378 dropped facts on Hhld19: two palikas
    named "Madi Municipality" (e.g. Sankhuwasabha and Chitwan) both resolved to the
    same federal code, so the second palika's facts were suppressed as "duplicates."
    The fix keys the seen-set on (prov, dist, gapa) not federal_code.
    """
    # Write a minimal Hhld05_FloorOfHouse CSV with two palika rows sharing the
    # same gapaname but different (prov, dist, gapa) triples.
    # The filename stem must match a registered table key.
    collision_csv = tmp_path / "Hhld05_FloorOfHouse.csv"
    collision_csv.write_text(
        "prov,dist,gapa,provname,dname,gapaname,rowtotal,a_Mud,b_Wooden,"
        "c_BrickStone,d_Ceramic,e_Cemented,f_Other\n"
        "0,0,0,NEPAL,NEPAL,NEPAL,6660841,3074510,135503,91236,180603,3151140,27849\n"
        "1,2,9,Province-1,Sankhuwasabha,Madi Municipality,2832,2409,280,12,6,101,24\n"
        "3,35,7,Bagmati,Chitwan,Madi Municipality,5000,4000,400,100,50,400,50\n",
        encoding="utf-8",
    )

    # Resolver that always maps "Madi Municipality" to the same code — simulating
    # the real resolver's failure to disambiguate by district.
    collision_codes: dict[str, str] = {
        "Madi Municipality": "09090909",
    }

    def _collision_stub(name: str, district_hint: str | None = None) -> _StubMatch | None:
        _ = district_hint  # intentionally ignored — simulates resolver collision
        code = collision_codes.get(name.strip())
        if code is None:
            return None
        return _StubMatch(federal_code=code, score=95.0)

    result = parse(
        str(collision_csv),
        "doc-id-collision",
        resolver_for_tests=_collision_stub,
    )
    # Both palikas must produce facts — no "Other" collision errors.
    other_errors = [e for e in result.errors if e.error_class == "Other"]
    assert other_errors == [], f"unexpected collision errors: {other_errors}"
    assert result.status == "success", f"errors: {result.errors}"
    # Two palika rows × 7 value cols = 14 facts.  Both rows share the same
    # entity_slug (the resolver returns the same code for both) but they come
    # from distinct (prov, dist, gapa) triples, so the seen-set does not
    # suppress either.
    assert len(result.facts) == 14, f"got {len(result.facts)} facts, expected 14"
    # Both facts use entity_slug="09090909" (the collision code).
    slugs_by_code = [f.entity_slug for f in result.facts]
    assert all(s == "09090909" for s in slugs_by_code)


def test_hhld18_slug_encodes_sex_only() -> None:
    """Hhld18 has one dimension (sexname); slug must encode it, not agegrpname."""
    result = parse(
        str(FIXTURES / "Hhld18_AbsentPopnBySex.csv"),
        "doc-id",
        resolver_for_tests=_stub_resolver,
    )
    slugs = {f.indicator_slug for f in result.facts}
    assert "hhld18-absentpopnbysex-total-rowtotal" in slugs
    assert "hhld18-absentpopnbysex-male-a-00to04" in slugs
    assert "hhld18-absentpopnbysex-female-n-65plus" in slugs
