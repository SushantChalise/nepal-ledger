"""Tests for oag_audit_reports.parser — pure table-row logic (ADR-0027 model).

Fixtures are the REAL extracted tables from the 58th Annual Report (English,
FY 2076/77), pages 28 (audited entities), 33 + 34 (irregularity by
classification x tier, page-split) and 34 (settlement), captured via pdfplumber.
The pure functions are exercised without a PDF; figures are asserted against
docs/research/oag-audit-reports-audit.md.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from oag_audit_reports.parser import (
    ParserError,
    build_output,
    fiscal_year_from_title,
    parse_amount,
    parse_ch1_audited,
    parse_ch2_beruju,
    parse_ch2_total_row,
    parse_settlement_table,
    reconcile_beruju,
)

# --- Chapter 1, page 28: "Details of Audited Entities" (NRs. Billions) -------
CH1_ROWS: list[list[str | None]] = [
    ["Audited Entity and Sub-classification", None, "Number", "Amounts in NRs. Billions"],
    [None, None, None, None],
    ["(A) Financial Audit", None, None, None],
    ["1. Federal Ministry and Constitutional Bodies", None, "3079", "1555.81"],
    ["2. Provincial Ministry and Offices", None, "1019", "237.41"],
    ["3. Local Level (Including District Coordination Committees)", None, "699", "815.99"],
    ["4. Committee & Other Institutions", None, "584", "163.57"],
    ["5. Corporate Body", None, "81", "2555.13"],
    ["(B) Performance Audit", "11", "-", "-"],
]

# --- Chapter 2, page 33: "Status of Irregularity..." (NRs. Millions) ---------
# Columns: Classification | Federal | Provincial | Local | Committee | Total | %
CH2_ROWS: list[list[str | None]] = [
    ["Classification", "Federal", "Provincial", "Local Level", "Committee/", "Total", "Percent on"],
    [None, "Government", "Government", None, "Other", None, "Total"],
    [None, "Office", "Office", None, "Institution", None, "Irregularity"],
    ["1. Recoverable", "20,292.1", "636.4", "5,474.9", "746.1", "27,149.5", "26.01"],
    ["2. To be regularized", "18,270.2", "4,832.5", "28,179.9", "10,980.8", "62,263.4", "59.65"],
    [
        "Irregular (non- compliance)]",
        "5,679.9", "2,105.6", "10,751.8", "6,002.9", "24,540.2", "23.51",
    ],
    [
        "Evidences/documents not submitted (Unsubstantiated)",
        "12,584.7", "2,726.9", "17,166.5", "4,977.3", "37,455.4", "35.88",
    ],
    ["2.3 Balance not brought forward", "3.9", None, "244.9", "-", "248.8", "0.24"],
    ["Reimbursements not received", "1.7", None, "16.7", ".6", "19.0", "0.02"],
    ["3. Advance", "5,829.8", "1,030.8", "7,179.9", "930.9", "14,971.4", "14.34"],
    ["3.1 Staff Advance", "34.2", "93.3", "2,929.6", "68.6", "3,125.4", "2.99"],
]

# --- Chapter 2 continuation, page 34: 3.x advance leaves + printed total row ---
CH2_CONTINUATION_ROWS: list[list[str | None]] = [
    ["3.2 Mobilization Advance", "1,280.9", None, None, None, "1,280.9", "1.23"],
    ["3.3 Other Advance", "4,514.7", "937.5", "4,250.3", "862.3", "10,564.8", "10.12"],
    ["Total irregularity", "44,392.1", "6,499.7", "40,834.7", "12,657.8", "104,384.3", "100.00"],
]

# The parser concatenates the page-split Ch.2 table; mirror that here.
CH2_FULL: list[list[str | None]] = CH2_ROWS + CH2_CONTINUATION_ROWS

# Settlement / lifecycle table: opening | adjustment | settled | net | current | cumulative
SETTLEMENT_ROWS: list[list[str | None]] = [
    [None, None, "Adjustment", "Last Year's Cleared/", "Net", "Current Year's", "Cumulative"],
    [
        "Particulars", "Last Year's Irregularity", None, "Settled", "Balance",
        "Irregularity", "Outstanding",
    ],
    [
        "Federal Government Office",
        "273,579.1", "1.0", "85,435.0", "188,145.1", "44,392.0", "232,537.1",
    ],
    [
        "Provincial Government Office",
        "8,392.6", "0", "2,413.3", "5,979.3", "6,499.7", "12,479.0",
    ],
    ["Local Level", "69,810.9", "-94.2", "7,513.7", "62,203.0", "40,834.7", "103,037.7"],
    [
        "Other Committee/ Institution (Including Provincial)",
        "66,534.7", "0", "8,395.9", "58,138.8", "12,657.9", "70,796.7",
    ],
    ["Total", "418,317.3", "-93.2", "103,757.9", "314,466.2", "104,384.3", "418,850.5"],
]

_M = Decimal(10) ** 6  # million -> NPR
_B = Decimal(10) ** 9  # billion -> NPR
_DOC = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("20,292.1", Decimal("20292.1")),
        (".6", Decimal("0.6")),
        ("1,030.8", Decimal("1030.8")),
        ("-94.2", Decimal("-94.2")),
        ("-", None),
        ("", None),
        (None, None),
        ("  3.9 ", Decimal("3.9")),
    ],
)
def test_parse_amount(raw: str | None, expected: Decimal | None) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    ("title", "fy"),
    [
        ("58th Annual Report of the Auditor General 2078", "2076/77"),
        ("63rd Annual Report 2083", "2081/82"),
        # The English edition spells the ordinal out, with the title-year trap:
        # "2021 (2078)" is the publish year, NOT the audited FY (2076/77).
        ("The Auditor General's\nFifty-Eighth\nAnnual Report\n2021 (2078)", "2076/77"),
        ("Sixtieth Annual Report 2080", "2078/79"),
        ("Sixty-Third Annual Report", "2081/82"),
        ("Annual Report without ordinal", None),
    ],
)
def test_fiscal_year_from_title(title: str, fy: str | None) -> None:
    assert fiscal_year_from_title(title) == fy


def test_parse_ch1_audited_per_class() -> None:
    rows = parse_ch1_audited(CH1_ROWS)
    by_class = {r.subject_class: r for r in rows}
    assert set(by_class) == {
        "federal_government", "provincial_government", "local_government",
        "committee_board_authority", "public_corporation",
    }
    fed = by_class["federal_government"]
    assert fed.entity_count == 3079
    assert fed.audited_npr == Decimal("1555.81") * _B
    assert by_class["local_government"].audited_npr == Decimal("815.99") * _B
    assert by_class["public_corporation"].entity_count == 81


def test_parse_ch2_beruju_recoverable_row() -> None:
    cells = parse_ch2_beruju(CH2_FULL)
    rec = {c.subject_class: c for c in cells if c.category_code == "recoverable"}
    assert rec["federal_government"].amount_npr == Decimal("20292.1") * _M
    assert rec["provincial_government"].amount_npr == Decimal("636.4") * _M
    assert rec["local_government"].amount_npr == Decimal("5474.9") * _M
    assert rec["committee_board_authority"].amount_npr == Decimal("746.1") * _M
    assert rec["federal_government"].aggregation_role == "detail"
    assert rec["federal_government"].main_category == "recoverable"


def test_parse_ch2_stores_parents_as_subtotals_with_corrected_codes() -> None:
    cells = parse_ch2_beruju(CH2_FULL)
    by_role: dict[str, set[str]] = {}
    for c in cells:
        by_role.setdefault(c.aggregation_role, set()).add(c.category_code)
    # Parent rows are STORED as subtotals (not skipped).
    assert "to_be_regularized" in by_role["subtotal"]
    assert "advance" in by_role["subtotal"]
    # Leaves are detail, including the two corrected mappings + the advance leaves.
    assert {
        "recoverable",
        "tbr_irregular",
        "tbr_evidence_not_submitted",
        "tbr_balance_not_brought_forward",  # was wrongly responsibility_not_transferred
        "tbr_reimbursement_not_received",  # was wrongly revenue_arrears
        "adv_staff",
        "adv_mobilization",
        "adv_other_institutional",
    } <= by_role["detail"]
    # The two wrong legacy codes never appear.
    all_codes = by_role.get("detail", set()) | by_role.get("subtotal", set())
    assert "responsibility_not_transferred" not in all_codes
    assert "revenue_arrears" not in all_codes


def test_parse_ch2_normalizes_in_cell_newlines() -> None:
    # pdfplumber emits in-cell line breaks ("Mobilization\nAdvance"); the
    # multi-word needle must still match the leaf, not fall through to the
    # generic "advance" subtotal (regression: the real p34 continuation).
    rows = [
        ["Classification", "Federal", "Provincial", "Local Level", "Committee/", "Total", "%"],
        ["3. Advance", "5,829.8", "1,030.8", "7,179.9", "930.9", "14,971.4", "14.34"],
        ["3.1 Staff\nAdvance", "34.2", "93.3", "2,929.6", "68.6", "3,125.4", "2.99"],
        ["3.2 Mobilization\nAdvance", "1,280.9", None, None, None, "1,280.9", "1.23"],
    ]
    cells = parse_ch2_beruju(rows)
    fed = {c.category_code: c for c in cells if c.subject_class == "federal_government"}
    assert fed["advance"].aggregation_role == "subtotal"
    assert fed["advance"].amount_npr == Decimal("5829.8") * _M
    assert fed["adv_staff"].aggregation_role == "detail"
    assert fed["adv_mobilization"].aggregation_role == "detail"
    assert fed["adv_mobilization"].amount_npr == Decimal("1280.9") * _M
    # source_row_label is whitespace-collapsed (no stray newline).
    assert "\n" not in fed["adv_mobilization"].source_row_label


def test_parse_ch2_column_alignment_with_blank_cells() -> None:
    # "Balance not brought forward" has blank Provincial + dash Committee; the
    # 3.9 (Federal) and 244.9 (Local) must NOT slide into the wrong tiers.
    cells = parse_ch2_beruju(CH2_FULL)
    code = "tbr_balance_not_brought_forward"
    bal = {c.subject_class: c for c in cells if c.category_code == code}
    assert set(bal) == {"federal_government", "local_government"}
    assert bal["federal_government"].amount_npr == Decimal("3.9") * _M
    assert bal["local_government"].amount_npr == Decimal("244.9") * _M


def test_detail_leaves_reconcile_to_printed_total_per_tier() -> None:
    # Per tier, the DETAIL leaves (excluding subtotals) sum to the printed total.
    cells = parse_ch2_beruju(CH2_FULL)
    per_class: dict[str, Decimal] = {}
    for c in cells:
        if c.aggregation_role != "detail":
            continue
        per_class[c.subject_class] = per_class.get(c.subject_class, Decimal(0)) + c.amount_npr
    assert per_class["federal_government"] == Decimal("44392.1") * _M
    assert per_class["provincial_government"] == Decimal("6499.7") * _M
    assert per_class["local_government"] == Decimal("40834.7") * _M
    assert per_class["committee_board_authority"] == Decimal("12657.8") * _M


def test_parse_ch2_total_row() -> None:
    totals = parse_ch2_total_row(CH2_CONTINUATION_ROWS)
    assert totals["federal_government"].npr == Decimal("44392.1") * _M
    assert totals["federal_government"].raw == "44,392.1"
    assert set(totals) == {
        "federal_government", "provincial_government",
        "local_government", "committee_board_authority",
    }


def test_parse_settlement_table_maps_committee_not_provincial() -> None:
    settle = parse_settlement_table(SETTLEMENT_ROWS)
    # "Other Committee/Institution (Including Provincial)" -> committee, NOT provincial.
    assert settle["committee_board_authority"]["cumulative"].npr == Decimal("70796.7") * _M
    assert settle["provincial_government"]["cumulative"].npr == Decimal("12479.0") * _M
    assert settle["federal_government"]["settled"].npr == Decimal("85435.0") * _M
    assert settle["federal_government"]["settled"].raw == "85,435.0"
    assert settle["federal_government"]["cumulative"].npr == Decimal("232537.1") * _M
    # The current-year column is captured for the cross-check.
    assert settle["federal_government"]["current"].npr == Decimal("44392.0") * _M
    assert "Total" not in settle


def test_reconcile_clean_on_real_data() -> None:
    # The 58th data reconciles: detail->total + subtotal->leaves exact per tier,
    # settlement current-year within the cross-source rounding tolerance (0.1M).
    cells = parse_ch2_beruju(CH2_FULL)
    totals = parse_ch2_total_row(CH2_CONTINUATION_ROWS)
    settlement = parse_settlement_table(SETTLEMENT_ROWS)
    assert reconcile_beruju(cells, totals, settlement) == []


def test_reconcile_flags_settlement_cross_check_drift() -> None:
    # Push the settlement current-year far from the classification total -> drift
    # beyond tolerance -> a ReconciliationFailed entry.
    rows = [list(r) for r in SETTLEMENT_ROWS]
    rows[2][5] = "50,000.0"  # Federal current-year 44,392.0 -> 50,000.0
    errors = reconcile_beruju(
        parse_ch2_beruju(CH2_FULL),
        parse_ch2_total_row(CH2_CONTINUATION_ROWS),
        parse_settlement_table(rows),
    )
    assert any("settlement current-year" in e["error_detail"] for e in errors)


def test_build_output_contract_shape() -> None:
    out = build_output(
        fiscal_year_bs="2076/77",
        source_document_id=_DOC,
        ch1=parse_ch1_audited(CH1_ROWS),
        ch2=parse_ch2_beruju(CH2_FULL),
        totals=parse_ch2_total_row(CH2_CONTINUATION_ROWS),
        settlement=parse_settlement_table(SETTLEMENT_ROWS),
    )
    assert out["status"] == "success"
    assert out["errors"] == []
    assert out["source_id"] == "oag-audit-reports"
    assert out["fiscal_year_bs"] == "2076/77"
    assert len(out["summaries"]) == 5
    assert out["financial_stocks"] == []
    assert out["paragraph_metrics"] == []
    assert out["findings"] == []

    # Every promoted row carries required provenance + the new model fields.
    for row in out["summaries"] + out["beruju_lines"]:
        assert row["confidence_grade"] == "A"
        assert row["source_document_id"] == _DOC
        assert row["extraction_method"] == "text_layer"
    for line in out["beruju_lines"]:
        assert line["amount_raw"]
        assert line["source_unit"] == "NPR_million"
        assert line["amount_basis"] == "current_year_raised"
        assert line["source_table_code"] == "ch2_irregularity_classification"
        assert line["value_origin"] == "printed"
        assert line["aggregation_role"] in {"detail", "subtotal"}
        assert line["beruju_category"]  # lookup-code string, non-empty

    fed = next(s for s in out["summaries"] if s["audit_subject_class"] == "federal_government")
    assert fed["beruju_raised_npr"] == f"{Decimal('44392.1') * _M:.2f}"
    assert fed["beruju_raised_raw"] == "44,392.1"
    assert fed["settled_this_year_npr"] == f"{Decimal('85435.0') * _M:.2f}"
    assert fed["cumulative_outstanding_npr"] == f"{Decimal('232537.1') * _M:.2f}"

    # Raw-when-amount invariant on every non-null summary scalar.
    for s in out["summaries"]:
        for npr_key, raw_key in (
            ("audited_amount_npr", "audited_amount_raw"),
            ("beruju_raised_npr", "beruju_raised_raw"),
            ("settled_this_year_npr", "settled_this_year_raw"),
            ("cumulative_outstanding_npr", "cumulative_outstanding_raw"),
        ):
            if s[npr_key] is not None:
                assert s[raw_key], f"{raw_key} missing for {s['audit_subject_class']}"

    # Corporate bodies: audited only (absent from the Ch.2 irregularity table).
    corp = next(s for s in out["summaries"] if s["audit_subject_class"] == "public_corporation")
    assert corp["beruju_raised_npr"] is None
    assert corp["audited_amount_npr"] == f"{Decimal('2555.13') * _B:.2f}"


def test_build_output_flags_reconciliation_variance() -> None:
    # Corrupt one DETAIL cell so the federal column no longer sums to its printed
    # total -> a ReconciliationFailed error and status 'partial'.
    bad = [list(r) for r in CH2_FULL]
    bad[3][1] = "20,292.9"  # Recoverable / Federal: 20,292.1 -> 20,292.9
    out = build_output(
        fiscal_year_bs="2076/77",
        source_document_id=_DOC,
        ch1=parse_ch1_audited(CH1_ROWS),
        ch2=parse_ch2_beruju(bad),
        totals=parse_ch2_total_row(CH2_CONTINUATION_ROWS),
        settlement=parse_settlement_table(SETTLEMENT_ROWS),
    )
    assert out["status"] == "partial"
    assert any(e["error_class"] == "ReconciliationFailed" for e in out["errors"])


def test_parse_ch1_raises_when_no_class_rows() -> None:
    with pytest.raises(ParserError):
        parse_ch1_audited([["Header only", None, None], ["(A) Financial Audit", None, None]])


def test_parse_ch2_raises_when_empty() -> None:
    with pytest.raises(ParserError):
        parse_ch2_beruju([["Classification", "Federal", "Total"]])
