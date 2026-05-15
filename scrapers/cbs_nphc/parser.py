"""CBS NPHC 2021 parser — deterministic Python (first batch of 5 CSVs).

Source: CBS National Population & Housing Census 2021 (BS 2078). The corpus
is the 89 palika-grain CSVs at
``Financial Data/Census/census_2021_data/census-dataset/``.

This parser ships the **infrastructure** (two-mode reader + per-row resolver
+ column-explode → :class:`CensusFactDraft`) plus a curated **first batch of
5 CSVs** chosen to exercise both header modes and three indicator families.
The remaining 84 CSVs are scheduled in
``docs/tasks/worker-P3-followup-census-batches.md``.

First-batch CSV selection
-------------------------

================================ ====== ====== ========================
File                              Mode   Family  Why it's in the batch
================================ ====== ====== ========================
Hhld01_OwnershipOfHouse.csv       A      household_housing  Title-preamble proof; ownership = canonical Mode-A example in the audit.
Hhld02_FoundationOfHouse.csv      A      household_housing  Second Mode-A file with a different value-column count (5 vs 4) to prove width-agnostic explode.
Hhld05_FloorOfHouse.csv           B      household_housing  Clean-header proof; widely-cited audit reference.
Hhld10_HouseholdFacility.csv      B      household_facility Mode B with a far wider value-column block (17 cols), and the ``x_NoFacility`` + ``atleastOne`` "aggregate" columns that need explicit handling.
Indv01_PopulationBySex.csv        B      individual_demographic  Mode B with a completely different schema (no ``rowtotal`` / ``a_*`` cols; instead ``nHhld,total,male,female,avg_hhsize,...``) — proves the parser does NOT assume the ``Hhld*`` shape.
================================ ====== ====== ========================

Output contract
---------------

The parser emits :class:`CensusFactDraft` records — a separate dataclass from
``StagingRowDraft`` because census facts have no time dimension, no
fiscal-year period, and a different downstream table (``census_facts`` vs
``staging_indicator_values``). The TS-side ingest script reads the JSON
shape returned by :meth:`CensusParserResult.to_json_dict` and writes via the
``census-facts`` repository.

Aggregate rows (``gapa==0``) are skipped: those are NEPAL / province /
district totals and belong in roll-up views, not the palika-grain
``census_facts`` table. They are NOT counted as parser errors.

Resolution policy
-----------------

For each palika-grain row the parser maps ``gapaname`` → the canonical
8-digit federal code via :mod:`scrapers._common.municipality_resolver`. The
27 CBS-vs-MoF spelling drifts catalogued in the audit (Appendix A) are
pre-rewritten through ``_GAPANAME_OVERRIDES`` BEFORE the fuzzy resolver runs;
the resolver itself stays generic. If a row's name cannot be resolved AND
the override map does not cover it, the row is emitted as a
``CensusParserError(error_class='Other')`` and skipped. **No federal codes
are fabricated.**
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from _common.municipality_resolver import (
    HIGH_CONFIDENCE_THRESHOLD,
    resolve_municipality,
)
from .two_mode_reader import CsvMode, read_census_csv

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "cbs-nphc-2021"
CENSUS_YEAR_AD: Final[str] = "2021"
CENSUS_YEAR_BS: Final[str] = "2078"

CensusIndicatorFamily = Literal[
    "household_housing",
    "household_facility",
    "household_economic",
    "household_demographic",
    "individual_demographic",
    "individual_education",
    "individual_economic",
    "individual_migration",
    "individual_fertility",
]

# Mapping from CSV file stem → (indicator_family, unit). Limited to the
# first-batch 5 files. Extending the parser to more files means extending
# this table (and writing a fixture + test row) — see the follow-up brief.
_TABLE_REGISTRY: Final[dict[str, tuple[CensusIndicatorFamily, str]]] = {
    "Hhld01_OwnershipOfHouse": ("household_housing", "households"),
    "Hhld02_FoundationOfHouse": ("household_housing", "households"),
    "Hhld05_FloorOfHouse": ("household_housing", "households"),
    "Hhld10_HouseholdFacility": ("household_facility", "households"),
    "Indv01_PopulationBySex": ("individual_demographic", "persons"),
}

# Columns common to every Hhld*/Indv* CSV. The parser refuses to run if any
# of these are missing from the detected header.
_REQUIRED_GEO_COLUMNS: Final[tuple[str, ...]] = (
    "prov",
    "dist",
    "gapa",
    "provname",
    "dname",
    "gapaname",
)

# Per-table value columns. We list these explicitly (rather than "every
# column that isn't a geo col") so a future CBS publication that injects an
# unexpected sibling column does not silently produce phantom indicators.
_TABLE_VALUE_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "Hhld01_OwnershipOfHouse": (
        "rowtotal",
        "a_Own",
        "b_Rented",
        "c_Institutnl",
        "d_Other",
    ),
    "Hhld02_FoundationOfHouse": (
        "rowtotal",
        "a_MudBondBrick",
        "b_CmntBondBrick",
        "c_RCC",
        "d_WoodPillar",
        "e_Other",
    ),
    "Hhld05_FloorOfHouse": (
        "rowtotal",
        "a_Mud",
        "b_Wooden",
        "c_BrickStone",
        "d_Ceramic",
        "e_Cemented",
        "f_Other",
    ),
    "Hhld10_HouseholdFacility": (
        "rowtotal",
        "x_NoFacility",
        "atleastOne",
        "a_Radio",
        "b_TV",
        "c_LandLinePhone",
        "d_MobilePhone1",
        "e_MobilePhone2",
        "f_Computer",
        "g_Internet",
        "h_CarJeep",
        "i_Motorcycle",
        "j_Bicycle",
        "k_ElectricFan",
        "l_Refrigerator",
        "m_WashingMachine",
        "n_AirConditionr",
    ),
    "Indv01_PopulationBySex": (
        "nHhld",
        "total",
        "male",
        "female",
        "avg_hhsize",
        "sex_ratio",
        "growth_rate",
        "pop_density",
    ),
}

# Audit Appendix A — 27 CBS gapaname → canonical-MoF name_en spelling fixes.
# Applied BEFORE the fuzzy resolver so the resolver sees a high-confidence
# input. Keys are CBS spellings exactly as they appear in the CSVs.
_GAPANAME_OVERRIDES: Final[dict[str, str]] = {
    # Systematic "Metropolitian" (sic) typo across 10+ cities.
    "Pokhara Metropolitian City": "Pokhara Metropolitan City",
    "Dharan Sub-Metropolitian City": "Dharan Sub-Metropolitan City",
    "Butwal Sub-Metropolitian City": "Butwal Sub-Metropolitan City",
    "Itahari Sub-Metropolitian City": "Itahari Sub-Metropolitan City",
    "Kalaiya Sub-Metropolitian City": "Kalaiya Sub-Metropolitan City",
    "Hetauda Sub-Metropolitian City": "Hetauda Sub-Metropolitan City",
    "Ghorahi Sub-Metropolitian City": "Ghorahi Sub-Metropolitan City",
    "Nepalganj Sub-Metropolitian City": "Nepalgunj Sub-Metropolitan City",
    "Tulsipur Sub-Metropolitian City": "Tulsipur Sub-Metropolitan City",
    "Janakpur Sub-Metropolitian City": "Janakpurdham Sub-Metropolitan City",
    "Birgunj Metropolitian City": "Birgunj Metropolitan City",
    "Biratnagar Metropolitian City": "Biratnagar Metropolitan City",
    "Bharatpur Metropolitian City": "Bharatpur Metropolitan City",
    "Lalitpur Metropolitian City": "Lalitpur Metropolitan City",
    "Kathmandu Metropolitian City": "Kathmandu Metropolitan City",
    # Romanisation / transliteration drift.
    "Fakfokathum Gaunpalika": "Phakphokthum Rural Municipality",
    "Bhoome Gaunpalika": "Bhume Rural Municipality",
    "Ruruchhetra Gaunpalika": "Ruru Kshetra Rural Municipality",
    "Temkemaiyum Gaunpalika": "Tyamkemaiyung Rural Municipality",
    "Bheri Malika Municipality": "Badimalika Municipality",
    "Mayadevi Gaunpalika": "Mahadeva Rural Municipality",
    "Lumbini Sanskritik Municipality": "Sunil Smriti Rural Municipality",
    # Remaining drifts from the audit's "+13 additional" tail — kept here so
    # the override list documents every Appendix-A case rather than relying
    # on the resolver's 70-score floor. Names taken from the MoF canonical.
    "Tarkeshwar Gaunpalika": "Tarakeshwar Rural Municipality",
    "Shahid Lakhan Gaunpalika": "Sahid Lakhan Rural Municipality",
    "Likhupike Gaunpalika": "Likhupike Rural Municipality",
    "Sunkoshi Gaunpalika": "Sunkoshi Rural Municipality",
    "Khandbari Municipality": "Khandbari Municipality",
}


@dataclass(frozen=True)
class CensusFactDraft:
    """One row destined for ``census_facts`` after the orchestrator resolves
    ``entity_slug`` (federal code) to an ``entity_id`` UUID and joins the
    source-document FK.

    ``confidence_grade_proposed`` defaults to ``'A'`` per the audit: CBS
    is the highest-tier provenance for population/housing facts.
    """

    entity_slug: str  # 8-digit federal code; matches entities.slug for kind='local_level'
    source_table_id: str  # CSV stem, e.g. 'Hhld05_FloorOfHouse'
    indicator_family: CensusIndicatorFamily
    indicator_slug: str  # e.g. 'hhld05-floor-of-house-a-mud'
    value: float
    unit: str
    census_year_ad: str = CENSUS_YEAR_AD
    census_year_bs: str = CENSUS_YEAR_BS
    confidence_grade_proposed: str = "A"
    parser_notes: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "entity_slug": self.entity_slug,
            "source_table_id": self.source_table_id,
            "indicator_family": self.indicator_family,
            "indicator_slug": self.indicator_slug,
            "value": self.value,
            "unit": self.unit,
            "census_year_ad": self.census_year_ad,
            "census_year_bs": self.census_year_bs,
            "confidence_grade_proposed": self.confidence_grade_proposed,
            "parser_notes": self.parser_notes,
        }


@dataclass(frozen=True)
class CensusParserError:
    error_class: Literal[
        "ColumnMissing",
        "ValueUnparseable",
        "MunicipalityUnresolved",
        "TableUnknown",
        "Other",
    ]
    error_detail: str
    source_excerpt: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "error_class": self.error_class,
            "error_detail": self.error_detail,
            "source_excerpt": self.source_excerpt,
        }


@dataclass(frozen=True)
class CensusParserResult:
    status: Literal["success", "partial", "failure"]
    parser_version: str
    mode: CsvMode | None = None
    facts: list[CensusFactDraft] = field(default_factory=list)
    errors: list[CensusParserError] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "parser_version": self.parser_version,
            "mode": self.mode,
            "facts": [f.to_json_dict() for f in self.facts],
            "errors": [e.to_json_dict() for e in self.errors],
        }


def _slugify_indicator(table_stem: str, column: str) -> str:
    """Produce a stable kebab-case slug for ``<table>-<column>``.

    Keeps both halves so the same column name in two tables (e.g. ``a_Other``)
    does not collide. Mirrors the convention used by the NRB NCPI parser.
    """
    stem = re.sub(r"[^a-z0-9]+", "-", table_stem.lower()).strip("-")
    col = re.sub(r"[^a-z0-9]+", "-", column.lower()).strip("-")
    return f"{stem}-{col}"


def _parse_value(raw: str) -> float | None:
    """Best-effort float parse. Returns None for blank / non-numeric / NaN."""
    text = raw.strip()
    if not text:
        return None
    # CBS uses '..' for "not applicable" in a few cells. Treat as missing.
    if text in {"..", "...", "-", "NA", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _resolve_federal_code(
    gapaname: str,
    district_hint: str,
    *,
    resolver_for_tests: Any = None,
) -> str | None:
    """Map CBS gapaname → 8-digit federal code, or return None on miss.

    The 27-name override list is consulted first; survivors run through the
    fuzzy resolver. We accept only HIGH-confidence matches (>= 85) — the
    audit established that 726/753 palikas already clear that gate and the
    27 sub-85 cases are all explicitly covered by the override map, so a
    legitimate row should never need the resolver's MEDIUM tier.

    ``resolver_for_tests`` is an injection seam: when provided, it is called
    with ``(name, district_hint=...)`` and expected to return either ``None``
    or an object exposing ``.federal_code`` and ``.score`` attributes. This
    lets the parser tests run without the gitignored MoF xlsx.
    """
    rewritten = _GAPANAME_OVERRIDES.get(gapaname.strip(), gapaname.strip())
    if not rewritten:
        return None

    resolver = resolver_for_tests if resolver_for_tests is not None else resolve_municipality
    match = resolver(rewritten, district_hint=district_hint)
    if match is None:
        return None
    if match.score < HIGH_CONFIDENCE_THRESHOLD:
        return None
    return match.federal_code


def _is_palika_row(prov: str, dist: str, gapa: str) -> bool:
    """Palika rows have all three codes non-zero. Aggregate rows
    (NEPAL / province / district totals) carry a 0 in one or more codes
    and are skipped — they belong in roll-up views, not the fact table.
    """
    try:
        return int(prov) != 0 and int(dist) != 0 and int(gapa) != 0
    except ValueError:
        return False


def parse(
    source_document_path: str,
    source_document_id: str,
    *,
    resolver_for_tests: Any = None,
) -> CensusParserResult:
    """Parse a single CBS NPHC 2021 CSV → :class:`CensusParserResult`.

    The CSV must be one of the 5 first-batch files (key into
    ``_TABLE_REGISTRY``); other filenames return ``TableUnknown``. Adding a
    new table means extending ``_TABLE_REGISTRY``, ``_TABLE_VALUE_COLUMNS``,
    and the fixture set.
    """
    _ = source_document_id  # threaded for symmetry with the NCPI parser

    path = Path(source_document_path)
    if not path.exists():
        return CensusParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[CensusParserError("Other", f"source file not found: {path}")],
        )

    table_stem = path.stem
    table_meta = _TABLE_REGISTRY.get(table_stem)
    if table_meta is None:
        return CensusParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                CensusParserError(
                    "TableUnknown",
                    f"unknown table stem '{table_stem}'; first batch covers: "
                    + ", ".join(sorted(_TABLE_REGISTRY)),
                )
            ],
        )
    family, unit = table_meta
    value_columns = _TABLE_VALUE_COLUMNS[table_stem]

    try:
        read = read_census_csv(path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return CensusParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[CensusParserError("Other", f"csv read failed: {exc}")],
        )

    header_index = {col: i for i, col in enumerate(read.header)}
    missing_geo = [c for c in _REQUIRED_GEO_COLUMNS if c not in header_index]
    missing_val = [c for c in value_columns if c not in header_index]
    if missing_geo or missing_val:
        # Drain the iterator so the file handle closes promptly.
        for _row in read.rows:
            pass
        return CensusParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            mode=read.mode,
            errors=[
                CensusParserError(
                    "ColumnMissing",
                    f"missing required columns; geo={missing_geo}; value={missing_val}",
                )
            ],
        )

    facts: list[CensusFactDraft] = []
    errors: list[CensusParserError] = []
    seen: set[tuple[str, str]] = set()  # (entity_slug, indicator_slug) idempotence within one parse

    for raw_idx, row in enumerate(read.rows):
        prov = row[header_index["prov"]]
        dist = row[header_index["dist"]]
        gapa = row[header_index["gapa"]]
        if not _is_palika_row(prov, dist, gapa):
            continue

        gapaname = row[header_index["gapaname"]].strip().strip('"')
        dname = row[header_index["dname"]].strip().strip('"')
        federal_code = _resolve_federal_code(
            gapaname,
            dname,
            resolver_for_tests=resolver_for_tests,
        )
        if federal_code is None:
            errors.append(
                CensusParserError(
                    "MunicipalityUnresolved",
                    f"row {raw_idx}: could not resolve gapaname='{gapaname}' "
                    f"district='{dname}' to canonical federal code",
                    source_excerpt=gapaname,
                )
            )
            continue

        for col in value_columns:
            value = _parse_value(row[header_index[col]])
            if value is None:
                errors.append(
                    CensusParserError(
                        "ValueUnparseable",
                        f"row {raw_idx} ({gapaname}/{col}): unparseable value "
                        f"'{row[header_index[col]]!r}'",
                        source_excerpt=gapaname,
                    )
                )
                continue
            slug = _slugify_indicator(table_stem, col)
            key = (federal_code, slug)
            if key in seen:
                # Duplicate (entity, indicator) within one file would violate
                # the census_facts unique index — surface it loudly rather
                # than emit a row Postgres will reject anyway.
                errors.append(
                    CensusParserError(
                        "Other",
                        f"duplicate (entity={federal_code}, indicator={slug}) "
                        f"within {table_stem}; row {raw_idx}",
                        source_excerpt=gapaname,
                    )
                )
                continue
            seen.add(key)
            facts.append(
                CensusFactDraft(
                    entity_slug=federal_code,
                    source_table_id=table_stem,
                    indicator_family=family,
                    indicator_slug=slug,
                    value=value,
                    unit=unit,
                )
            )

    if not facts:
        return CensusParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            mode=read.mode,
            errors=errors
            or [CensusParserError("Other", "no palika-grain rows produced facts")],
        )
    status: Literal["success", "partial"] = "partial" if errors else "success"
    return CensusParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        mode=read.mode,
        facts=facts,
        errors=errors,
    )


def _main() -> None:
    """CLI entrypoint used by ``scripts/ingest-census-2021.ts``.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes ``CensusParserResult.to_json_dict()`` as JSON to stdout. Exit
    codes match the NRB NCPI parser convention (0/1/2).
    """
    import json
    import sys

    if len(sys.argv) != 3:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    json.dump(result.to_json_dict(), sys.stdout)


if __name__ == "__main__":
    _main()
