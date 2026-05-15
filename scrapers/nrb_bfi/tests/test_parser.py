"""Tests for the NRB BFI canonical-month (Bhadau 2082) parser.

Runs against a trimmed fixture XLSX checked into the repo at
``scrapers/nrb_bfi/tests/fixtures/bhadau_2082.xlsx``. No network.
The fixture is schema-faithful to the real Bhadau_2082_Publish.xlsx C5
layout (4 bank-class sub-tables, label in col 2, Mid-Sept values at
cols 7/15/23/31).
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from nrb_bfi import PARSER_VERSION, parse
from nrb_bfi.parser import (
    _C5_INDICATORS,
    _LATEST_VALUE_COL_BY_CLASS,
    BankingSectorFactRow,
    ParserResult,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bhadau_2082.xlsx"


def _build_fixture(path: Path) -> None:
    """Build a trimmed XLSX that matches the real C5 layout structurally.

    Layout per real corpus:
      row 0..3: header rows (period labels, year labels)
      row 4..:  data rows; label in col 2, values at cols 7/15/23/31 for
                system_total / commercial / development / finance.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    # Default sheet -> rename to C5; add a couple of stub sheets for sheet
    # name fidelity.
    default = wb.active
    if default is None:
        raise RuntimeError("openpyxl returned no default sheet")
    default.title = "C5"
    wb.create_sheet("C1")
    wb.create_sheet("C6")

    ws = wb["C5"]

    # Header rows. openpyxl is 1-indexed.
    ws.cell(row=2, column=2, value="Liabilities")
    # period label row
    ws.cell(row=4, column=4, value="Mid-July ")
    ws.cell(row=4, column=7, value="Mid-Aug")
    ws.cell(row=4, column=8, value="Mid-Sept")
    ws.cell(row=4, column=16, value="Mid-Sept")
    ws.cell(row=4, column=24, value="Mid-Sept")
    ws.cell(row=4, column=32, value="Mid-Sept")
    # year row
    for c in (4, 5, 6, 7, 8):
        ws.cell(row=5, column=c, value=2022 + (c - 4))

    # Body rows. Use synthetic values that are recognisable per-class so we
    # can assert column wiring is correct: system_total = 1000.x,
    # commercial = 700.x, development = 200.x, finance = 100.x where .x
    # is a small offset per indicator.
    body_start = 7  # 1-indexed Excel row
    for offset, (label, _slug) in enumerate(_C5_INDICATORS):
        r = body_start + offset
        ws.cell(row=r, column=3, value=label)  # col index 2 in 0-based
        # Cell column = openpyxl 1-based; map 0-based col 7 -> col 8 etc.
        ws.cell(row=r, column=8, value=1000 + offset + 0.5)  # system_total
        ws.cell(row=r, column=16, value=700 + offset + 0.5)  # commercial
        ws.cell(row=r, column=24, value=200 + offset + 0.5)  # development
        ws.cell(row=r, column=32, value=100 + offset + 0.5)  # finance

    wb.save(str(path))


@pytest.fixture(scope="module", autouse=True)
def ensure_fixture() -> None:
    """Materialise the fixture on first run. Cheap (≤10 rows)."""
    if not FIXTURE.exists():
        _build_fixture(FIXTURE)


@pytest.fixture(scope="module")
def result() -> ParserResult:
    return parse(str(FIXTURE), source_document_id="test-doc-id")


def test_status_success(result: ParserResult) -> None:
    assert result.status == "success", f"errors={result.errors}"


def test_parser_version(result: ParserResult) -> None:
    assert result.parser_version == PARSER_VERSION == "0.1.0"


def test_row_count(result: ParserResult) -> None:
    expected = len(_C5_INDICATORS) * len(_LATEST_VALUE_COL_BY_CLASS)
    assert len(result.fact_rows) == expected


def test_bank_classes_balanced(result: ParserResult) -> None:
    per_class: dict[str, int] = dict.fromkeys(_LATEST_VALUE_COL_BY_CLASS.keys(), 0)
    for row in result.fact_rows:
        per_class[row.bank_class] += 1
    assert per_class == {k: len(_C5_INDICATORS) for k in _LATEST_VALUE_COL_BY_CLASS}


def test_required_fields_populated(result: ParserResult) -> None:
    for row in result.fact_rows:
        assert isinstance(row, BankingSectorFactRow)
        assert row.indicator_slug.startswith("bfi-c5-")
        assert row.unit == "npr_million"
        assert row.source_sheet == "C5"
        assert row.reporting_period_type == "monthly"
        assert row.reporting_period_bs == "Bhadra 2082"
        assert row.fiscal_year_bs == "2082/83"
        assert row.confidence_grade == "A"
        assert row.bank_entity_id is None
        assert isinstance(row.value, float)


def test_per_class_value_wiring(result: ParserResult) -> None:
    """The synthetic fixture uses class-specific value bases: system_total
    starts at 1000.5, commercial at 700.5, development at 200.5, finance at
    100.5. Confirms column wiring is correct for all 4 classes.
    """
    by_class: dict[str, list[float]] = {
        "system_total": [],
        "commercial": [],
        "development": [],
        "finance": [],
    }
    for row in result.fact_rows:
        by_class[row.bank_class].append(row.value)

    # Pick first indicator (CAPITAL FUND -> offset 0 -> values 1000.5, 700.5,
    # 200.5, 100.5). The slug suffix is 'capital-fund'.
    cf_rows = [r for r in result.fact_rows if r.indicator_slug.endswith("capital-fund")]
    cf_by_class = {r.bank_class: r.value for r in cf_rows}
    assert cf_by_class["system_total"] == pytest.approx(1000.5)
    assert cf_by_class["commercial"] == pytest.approx(700.5)
    assert cf_by_class["development"] == pytest.approx(200.5)
    assert cf_by_class["finance"] == pytest.approx(100.5)


def test_idempotent() -> None:
    a = parse(str(FIXTURE), source_document_id="x")
    b = parse(str(FIXTURE), source_document_id="x")
    assert a.status == b.status
    assert len(a.fact_rows) == len(b.fact_rows)
    for ra, rb in zip(a.fact_rows, b.fact_rows, strict=True):
        assert ra == rb


def test_missing_file_returns_failure() -> None:
    res = parse("nonexistent-bfi.xlsx", source_document_id="x")
    assert res.status == "failure"
    assert res.errors


def test_no_unexpected_errors(result: ParserResult) -> None:
    assert result.errors == [], f"unexpected errors: {result.errors}"


def test_json_serialisable(result: ParserResult) -> None:
    """Ingest CLI consumes the JSON dict; ensure it's JSON-clean."""
    import json

    payload = json.dumps(result.to_json_dict())
    assert "fact_rows" in payload
    assert "parser_version" in payload
