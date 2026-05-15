"""Pytest fixtures for the MoF fiscal transfers parser.

The canonical 753-row municipality table lives in a gitignored XLSX
(``Financial Data/...``). Tests inject a 3-row fixture table directly into
the resolver's cache so the parser can run against a fully checked-in
sample XLSX without touching the real corpus.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from openpyxl import Workbook

from _common.municipality_resolver import (
    MunicipalityMatch,
    _clear_cache_for_tests,
    _set_cache_for_tests,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_XLSX = FIXTURE_DIR / "sample.xlsx"


def _fixture_canonical_table() -> list[MunicipalityMatch]:
    """Minimal canonical table — 3 real local levels from FY 2082/83."""
    return [
        MunicipalityMatch(
            federal_code="80101101",
            name_en="Kathmandu",
            name_ne="काठमाडौँ",
            local_level_type="metropolitan_city",
            district_en="Kathmandu",
            score=0.0,
        ),
        MunicipalityMatch(
            federal_code="80201101",
            name_en="Pokhara",
            name_ne="पोखरा",
            local_level_type="metropolitan_city",
            district_en="Kaski",
            score=0.0,
        ),
        MunicipalityMatch(
            federal_code="80103101",
            name_en="Budhanilkantha",
            name_ne="बुढानीलकण्ठ",
            local_level_type="municipality",
            district_en="Kathmandu",
            score=0.0,
        ),
    ]


def _build_sample_xlsx(path: Path) -> None:
    """Write a 5-row sample workbook mimicking the real Cleaned/ XLSX shape.

    Layout:
      Row 1: title-ish junk (mimics MoF cosmetic header)
      Row 2: header row with grant-type columns
      Rows 3-5: data rows (Kathmandu, Pokhara, Budhanilkantha)
      Row 6: 'Total' aggregator (parser must skip)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Sheet1"

    ws.append(["Annex 1: Fiscal Transfer FY 2082/83 (in NPR thousand)"])
    ws.append(
        [
            "S.N.",
            "District",
            "Local Level Name",
            "Equalization Grant (Minimum)",
            "Equalization Grant (Formula-Based)",
            "Equalization Grant (Performance-Based)",
            "Conditional Grant (Current)",
            "Conditional Grant (Capital)",
            "Special Grant (Current)",
            "Special Grant (Capital)",
            "Complementary Grant (Capital)",
        ],
    )
    ws.append([1, "Kathmandu", "Kathmandu", 100000, 250000, 50000, 800000, 600000, 0, 30000, 20000])
    ws.append([2, "Kaski", "Pokhara", 80000, 200000, 40000, 600000, 500000, 0, 25000, 15000])
    ws.append(
        [3, "Kathmandu", "Budhanilkantha", 60000, 150000, 30000, 400000, 300000, 0, 10000, 5000],
    )
    ws.append([4, "Total", "Total", 240000, 600000, 120000, 1800000, 1400000, 0, 65000, 40000])

    wb.save(path)


@pytest.fixture(scope="session", autouse=True)
def _ensure_sample_xlsx_and_canonical_table() -> Iterator[None]:
    """Generate the sample XLSX on first collection AND inject the canonical
    municipality table cache. Both must outlive ``module``-scoped result
    fixtures, so this is session-scoped.
    """
    if not SAMPLE_XLSX.exists():
        _build_sample_xlsx(SAMPLE_XLSX)
    _set_cache_for_tests(_fixture_canonical_table())
    try:
        yield
    finally:
        _clear_cache_for_tests()
