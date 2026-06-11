"""Deterministic parser for the OAG Annual Report (English edition), Tier 0.

Extracts the report's aggregate tables into the audit fact-domain parser-output
contract (ADR-0027; mirrors src/lib/ingestion/audit-types.ts):

  - Chapter 1 "Details of Audited Entities" -> audited amount + entity count
    per subject class (Federal / Provincial / Local / Committee / Corporate),
    in NRs. BILLIONS. -> AuditEntitySummary rows (NULL entity, aggregate_scope).
  - Chapter 2 "Status of Irregularity Witnessed From Audit" -> beruju by
    classification x tier, in NRs. MILLIONS. -> AuditBerujuLine rows keyed by a
    `beruju_categories` lookup code, tagged with an `aggregation_role`
    (detail / subtotal): parent rows ("To be regularized", "Advance") are STORED
    as subtotals (not skipped), and the detail leaves reconcile to the printed
    per-tier totals.
  - Chapter 2 settlement table -> per-class settled + cumulative summary scalars.

The English edition carries class AGGREGATES only (per-entity detail is in the
Nepali edition and the per-ministry table — a later PR). Born-digital ->
pdfplumber; no OCR. Production parsing is deterministic Python (ADR-0003). The
pure functions below are table-row-driven and unit-tested without a PDF;
`parse()` is the thin pdfplumber wrapper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, Literal

from oag_audit_reports.discover import audited_fy_for_edition

PARSER_VERSION: Final[str] = "0.2.0"
SOURCE_ID: Final[str] = "oag-audit-reports"
CH2_SOURCE_TABLE: Final[str] = "ch2_irregularity_classification"

SubjectClass = Literal[
    "federal_government",
    "provincial_government",
    "local_government",
    "public_corporation",
    "committee_board_authority",
    "other_institution",
]
MainCategory = Literal["recoverable", "to_be_regularized", "advance", "other"]
AggregationRole = Literal["detail", "subtotal", "grand_total"]

_NPR_BILLION: Final[Decimal] = Decimal(10) ** 9
_NPR_MILLION: Final[Decimal] = Decimal(10) ** 6
# Independent printed tables (classification vs settlement) round differently;
# tolerate up to NRs 0.1M of drift on the cross-source check (ADR-0027).
_CROSS_CHECK_TOLERANCE_NPR: Final[Decimal] = Decimal(100_000)

# Chapter-1 row label -> subject class (matched as a lowercase substring).
_CH1_CLASS: Final[tuple[tuple[str, SubjectClass], ...]] = (
    ("federal", "federal_government"),
    ("provincial", "provincial_government"),
    ("local level", "local_government"),
    ("committee", "committee_board_authority"),
    ("corporate", "public_corporation"),
)

# Chapter-2 tier column header -> subject class (column order in the table).
_CH2_TIER_COLUMNS: Final[tuple[SubjectClass, ...]] = (
    "federal_government",
    "provincial_government",
    "local_government",
    "committee_board_authority",
)

# Chapter-2 classification label -> (main_category, lookup code, aggregation_role).
# ORDER MATTERS: specific advance sub-types precede the bare "advance" parent, so
# "3.1 Staff Advance" maps to the leaf and "3. Advance" to the subtotal. The two
# parent rows ("to be regularized", "advance") are STORED as subtotals; the rest
# are detail leaves whose per-tier sum equals the printed total (ADR-0027).
_CH2_CLASSIFICATION: Final[tuple[tuple[str, MainCategory, str, AggregationRole], ...]] = (
    ("recoverable", "recoverable", "recoverable", "detail"),
    ("to be regularized", "to_be_regularized", "to_be_regularized", "subtotal"),
    ("irregular", "to_be_regularized", "tbr_irregular", "detail"),
    ("evidence", "to_be_regularized", "tbr_evidence_not_submitted", "detail"),
    ("document", "to_be_regularized", "tbr_evidence_not_submitted", "detail"),
    ("unsubstantiated", "to_be_regularized", "tbr_evidence_not_submitted", "detail"),
    ("balance not brought", "to_be_regularized", "tbr_balance_not_brought_forward", "detail"),
    ("reimbursement", "to_be_regularized", "tbr_reimbursement_not_received", "detail"),
    ("staff advance", "advance", "adv_staff", "detail"),
    ("mobilization advance", "advance", "adv_mobilization", "detail"),
    ("other advance", "advance", "adv_other_institutional", "detail"),
    ("advance", "advance", "advance", "subtotal"),
)
# Header + grand-total rows are not classification leaves. "total irregularity"
# also contains the substring "irregular" — skip it before classifying.
_CH2_SKIP_NEEDLES: Final[tuple[str, ...]] = ("classification", "total irregularity")

# Edition ordinal in the report title drives the audited FY via the recon-
# anchored mapping in discover.audited_fy_for_edition (58th -> 2076/77). This
# avoids the title-year trap: the cover/publish year is NOT the audited FY
# (docs/research/oag-audit-reports-audit.md). The English edition spells the
# ordinal out ("Fifty-Eighth"); the digit form ("58th") is also accepted.
_EDITION_RE: Final[re.Pattern[str]] = re.compile(r"\b(\d{1,3})(?:st|nd|rd|th)\b", re.IGNORECASE)
_ONES_ORDINAL: Final[dict[str, int]] = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
}
_TENS_CARDINAL: Final[dict[str, int]] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_TENS_ORDINAL: Final[dict[str, int]] = {
    "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
    "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90,
}


def _word_ordinal_to_int(text: str) -> int | None:
    """Parse a spelled-out English ordinal ("Fifty-Eighth", "Sixtieth") -> int.

    Covers the OAG edition range (compound tens+ones, plus exact tens ordinals).
    """
    low = text.lower()
    for tens_word, tens_val in _TENS_CARDINAL.items():
        for ones_word, ones_val in _ONES_ORDINAL.items():
            if re.search(rf"\b{tens_word}[\s-]+{ones_word}\b", low):
                return tens_val + ones_val
    for word, val in _TENS_ORDINAL.items():
        if re.search(rf"\b{word}\b", low):
            return val
    return None


class ParserError(RuntimeError):
    """Raised when a required table/figure cannot be located."""


@dataclass(frozen=True)
class AuditedEntityRow:
    subject_class: SubjectClass
    entity_count: int | None
    audited_npr: Decimal
    audited_raw: str


@dataclass(frozen=True)
class BerujuCell:
    subject_class: SubjectClass
    category_code: str  # FK code into beruju_categories
    main_category: MainCategory
    aggregation_role: AggregationRole
    source_row_label: str
    amount_npr: Decimal
    amount_raw: str


@dataclass(frozen=True)
class ClassScalar:
    """One printed per-class headline figure + its raw expression (NRs millions)."""

    npr: Decimal
    raw: str


def _norm(text: str) -> str:
    """Collapse all whitespace (incl. pdfplumber's in-cell newlines, e.g.
    "Mobilization\\nAdvance") to single spaces and lowercase — so multi-word
    needles like "mobilization advance" still substring-match."""
    return " ".join(text.split()).lower()


def parse_amount(raw: str | None) -> Decimal | None:
    """Parse "20,292.1" / ".6" / "-" -> Decimal (None for blank/dash)."""
    if raw is None:
        return None
    s = raw.strip().replace(",", "")
    if s in ("", "-", "–", "—"):
        return None
    if s.startswith("."):
        s = "0" + s
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def fiscal_year_from_title(title: str) -> str | None:
    """Audited FY ("2076/77") from the report title's edition ordinal.

    Accepts the digit form ("58th") or the spelled-out English form
    ("Fifty-Eighth", as the English edition prints it). Reuses
    ``discover.audited_fy_for_edition`` so the parser and the acquisition
    discovery share one anchor mapping. Returns None if no ordinal is present.
    """
    m = _EDITION_RE.search(title)
    edition = int(m.group(1)) if m else _word_ordinal_to_int(title)
    if edition is None:
        return None
    return audited_fy_for_edition(edition)


def _class_for_ch1_label(label: str) -> SubjectClass | None:
    low = _norm(label)
    for needle, cls in _CH1_CLASS:
        if needle in low:
            return cls
    return None


def _classify_ch2_label(label: str) -> tuple[MainCategory, str, AggregationRole] | None:
    """Classification label -> (main_category, lookup code, aggregation_role)."""
    low = _norm(label)
    if not low or any(skip in low for skip in _CH2_SKIP_NEEDLES):
        return None
    for needle, main, code, role in _CH2_CLASSIFICATION:
        if needle in low:
            return (main, code, role)
    return None


def _numeric_cells(row: list[str | None]) -> list[tuple[int, Decimal]]:
    """Return (col_index, value) for cells that parse to a number."""
    out: list[tuple[int, Decimal]] = []
    for idx, cell in enumerate(row):
        val = parse_amount(cell)
        if val is not None:
            out.append((idx, val))
    return out


def _entity_count(nums: list[tuple[int, Decimal]]) -> int | None:
    """The leading numeric cell is the entity count when it is a whole number
    distinct from the trailing amount cell (i.e. at least a count + an amount)."""
    count_plus_amount = 2
    if len(nums) < count_plus_amount:
        return None
    leading = nums[0][1]
    return int(leading) if leading == leading.to_integral() else None


def parse_ch1_audited(rows: list[list[str | None]]) -> list[AuditedEntityRow]:
    """Chapter-1 table -> audited amount (NRs billions) + count per class."""
    out: list[AuditedEntityRow] = []
    seen: set[SubjectClass] = set()
    for row in rows:
        label = " ".join((c or "") for c in row).strip()
        cls = _class_for_ch1_label(label)
        if cls is None or cls in seen:
            continue
        nums = _numeric_cells(row)
        if not nums:
            continue
        # Last numeric cell = audited amount (billions); a leading whole-number
        # cell (if present) is the entity count.
        amount = nums[-1][1]
        count = _entity_count(nums)
        seen.add(cls)
        out.append(
            AuditedEntityRow(
                subject_class=cls,
                entity_count=count,
                audited_npr=amount * _NPR_BILLION,
                audited_raw=str(amount),
            )
        )
    if not out:
        raise ParserError("Chapter-1 audited-entities table not found / unparsable")
    return out


def parse_ch2_beruju(rows: list[list[str | None]]) -> list[BerujuCell]:
    """Chapter-2 table -> beruju cells (NRs millions) per class x classification.

    Emits both `detail` leaves and the printed `subtotal` parents ("To be
    regularized", "Advance"). The 4 tier columns are at FIXED positions
    (``row[1..4]``) so rows with blank/dash tier cells stay aligned.
    """
    out: list[BerujuCell] = []
    for row in rows:
        # Collapse in-cell whitespace so multi-word labels (and source_row_label)
        # are clean; matching also normalizes.
        label = " ".join((row[0] or "").split())
        classified = _classify_ch2_label(label)
        if classified is None:
            continue
        main, code, role = classified
        if len(row) < 1 + len(_CH2_TIER_COLUMNS):
            continue
        for col, cls in enumerate(_CH2_TIER_COLUMNS, start=1):
            raw = (row[col] or "").strip()
            v = parse_amount(raw)
            if v is None or v == 0:
                continue
            out.append(
                BerujuCell(
                    subject_class=cls,
                    category_code=code,
                    main_category=main,
                    aggregation_role=role,
                    source_row_label=label,
                    amount_npr=v * _NPR_MILLION,
                    amount_raw=raw,
                )
            )
    if not out:
        raise ParserError("Chapter-2 irregularity table not found / unparsable")
    return out


def parse_ch2_total_row(rows: list[list[str | None]]) -> dict[SubjectClass, ClassScalar]:
    """The printed "Total irregularity" row -> per-class current-year beruju.

    This is the report's own column total (NRs millions); the detail leaves are
    reconciled against it per tier.
    """
    out: dict[SubjectClass, ClassScalar] = {}
    for row in rows:
        if "total irregularity" not in _norm(row[0] or ""):
            continue
        if len(row) < 1 + len(_CH2_TIER_COLUMNS):
            continue
        for col, cls in enumerate(_CH2_TIER_COLUMNS, start=1):
            raw = (row[col] or "").strip()
            v = parse_amount(raw)
            if v is not None:
                out[cls] = ClassScalar(v * _NPR_MILLION, raw)
        break
    return out


# Settlement-table (Ch.2 lifecycle) row label -> subject class. "committee" is
# checked before "provincial" because the committee row reads "Other Committee/
# Institution (Including Provincial)".
_SETTLEMENT_CLASS: Final[tuple[tuple[str, SubjectClass], ...]] = (
    ("federal", "federal_government"),
    ("committee", "committee_board_authority"),
    ("provincial", "provincial_government"),
    ("local", "local_government"),
)
# Columns: 0 Particulars | 1 opening | 2 adjustment | 3 settled | 4 net |
#          5 current-year | 6 cumulative-outstanding.
_SETTLE_SETTLED_COL: Final[int] = 3
_SETTLE_CURRENT_COL: Final[int] = 5
_SETTLE_CUMULATIVE_COL: Final[int] = 6


def _settlement_class_for_label(label: str) -> SubjectClass | None:
    low = _norm(label)
    if "total" in low or "particular" in low:
        return None
    for needle, cls in _SETTLEMENT_CLASS:
        if needle in low:
            return cls
    return None


def parse_settlement_table(
    rows: list[list[str | None]],
) -> dict[SubjectClass, dict[str, ClassScalar]]:
    """Ch.2 settlement/lifecycle table -> per-class scalars (NRs millions).

    Extracts "Last Year's Cleared/Settled" (settled), "Current Year's
    Irregularity" (current — an independent cross-check on the classification
    total), and "Cumulative Outstanding Irregularity" (cumulative).
    """
    out: dict[SubjectClass, dict[str, ClassScalar]] = {}
    columns = (
        ("settled", _SETTLE_SETTLED_COL),
        ("current", _SETTLE_CURRENT_COL),
        ("cumulative", _SETTLE_CUMULATIVE_COL),
    )
    for row in rows:
        cls = _settlement_class_for_label(row[0] or "")
        if cls is None or len(row) <= _SETTLE_CUMULATIVE_COL:
            continue
        scalars: dict[str, ClassScalar] = {}
        for key, col in columns:
            raw = (row[col] or "").strip()
            v = parse_amount(raw)
            if v is not None:
                scalars[key] = ClassScalar(v * _NPR_MILLION, raw)
        if scalars:
            out[cls] = scalars
    return out


def _provenance(source_document_id: str) -> dict[str, Any]:
    return {
        "source_document_id": source_document_id,
        "source_precedence": 1,  # annual report
        "extraction_method": "text_layer",
        "confidence_grade": "A",
        "promoted_by": f"{SOURCE_ID}.parser@{PARSER_VERSION}",
    }


def _scalar_pair(scalar: ClassScalar | None) -> tuple[str | None, str | None]:
    """(npr_string, raw) for a printed scalar, or (None, None) when absent."""
    return (f"{scalar.npr:.2f}", scalar.raw) if scalar is not None else (None, None)


def _summary_drafts(
    fy: str,
    ch1: list[AuditedEntityRow],
    totals: dict[SubjectClass, ClassScalar],
    settlement: dict[SubjectClass, dict[str, ClassScalar]],
    prov: dict[str, Any],
) -> list[dict[str, Any]]:
    """One aggregate summary row per subject class. Each headline scalar is a
    *printed* figure with its raw expression preserved (raw-when-amount
    invariant). source_unit is null: the row mixes the audited table (billions)
    with the irregularity/settlement tables (millions); each *_npr is canonical
    full NPR and each *_raw is the printed figure, so per-amount scale is
    implicit (npr/raw) rather than a single row-level unit.
    """
    out: list[dict[str, Any]] = []
    for r in ch1:
        cls = r.subject_class
        settle = settlement.get(cls, {})
        raised_npr, raised_raw = _scalar_pair(totals.get(cls))
        settled_npr, settled_raw = _scalar_pair(settle.get("settled"))
        cumulative_npr, cumulative_raw = _scalar_pair(settle.get("cumulative"))
        out.append(
            {
                "audited_entity_id": None,
                "audit_subject_class": cls,
                "aggregate_scope": f"all_{cls}",
                "fiscal_year_bs": fy,
                "audited_amount_npr": f"{r.audited_npr:.2f}",
                "audited_amount_raw": r.audited_raw,
                "beruju_raised_npr": raised_npr,
                "beruju_raised_raw": raised_raw,
                "settled_this_year_npr": settled_npr,
                "settled_this_year_raw": settled_raw,
                "cumulative_outstanding_npr": cumulative_npr,
                "cumulative_outstanding_raw": cumulative_raw,
                "source_unit": None,
                "source_scale": None,
                **prov,
            }
        )
    return out


def _beruju_line_drafts(
    fy: str, ch2: list[BerujuCell], prov: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "audited_entity_id": None,
            "audit_subject_class": cell.subject_class,
            "aggregate_scope": f"all_{cell.subject_class}",
            "fiscal_year_bs": fy,
            "amount_basis": "current_year_raised",
            "beruju_category": cell.category_code,
            "beruju_category_label_raw": cell.source_row_label,
            "source_row_label": cell.source_row_label,
            "aggregation_role": cell.aggregation_role,
            "value_origin": "printed",
            "source_table_code": CH2_SOURCE_TABLE,
            "amount_npr": f"{cell.amount_npr:.2f}",
            "amount_raw": cell.amount_raw,
            "source_unit": "NPR_million",
            "source_scale": "1000000",
            **prov,
        }
        for cell in ch2
    ]


def _recon_error(detail: str, excerpt: str | None) -> dict[str, Any]:
    return {
        "error_class": "ReconciliationFailed",
        "error_detail": detail,
        "source_excerpt": excerpt,
    }


def reconcile_beruju(
    ch2: list[BerujuCell],
    totals: dict[SubjectClass, ClassScalar],
    settlement: dict[SubjectClass, dict[str, ClassScalar]],
) -> list[dict[str, Any]]:
    """Level-aware, multi-source reconciliation (ADR-0027):

    1. per tier, the summed `detail` leaves equal the printed total (exact);
    2. per (tier, main category), the leaves equal the printed `subtotal` row;
    3. the settlement table's current-year column cross-checks the
       classification total per tier (independent source; rounding-tolerant).
    """
    errors: list[dict[str, Any]] = []

    # 1. detail leaves -> printed per-tier total (exact).
    detail_by_class: dict[SubjectClass, Decimal] = {}
    for cell in ch2:
        if cell.aggregation_role != "detail":
            continue
        detail_by_class[cell.subject_class] = (
            detail_by_class.get(cell.subject_class, Decimal(0)) + cell.amount_npr
        )
    for cls, printed in totals.items():
        variance = detail_by_class.get(cls, Decimal(0)) - printed.npr
        if variance != 0:
            errors.append(
                _recon_error(
                    f"{cls}: detail leaves sum to {detail_by_class.get(cls, Decimal(0))} NPR "
                    f"but printed total is {printed.npr} NPR (variance {variance})",
                    printed.raw,
                )
            )

    # 2. detail leaves -> printed subtotal, per (tier, main category) (exact).
    subtotal: dict[tuple[SubjectClass, MainCategory], Decimal] = {}
    leaf_sum: dict[tuple[SubjectClass, MainCategory], Decimal] = {}
    for cell in ch2:
        key = (cell.subject_class, cell.main_category)
        if cell.aggregation_role == "subtotal":
            subtotal[key] = cell.amount_npr
        elif cell.aggregation_role == "detail":
            leaf_sum[key] = leaf_sum.get(key, Decimal(0)) + cell.amount_npr
    for key, sub_npr in subtotal.items():
        variance = leaf_sum.get(key, Decimal(0)) - sub_npr
        if variance != 0:
            cls, main = key
            errors.append(
                _recon_error(
                    f"{cls}/{main}: detail leaves sum to {leaf_sum.get(key, Decimal(0))} NPR "
                    f"but printed subtotal is {sub_npr} NPR (variance {variance})",
                    None,
                )
            )

    # 3. settlement current-year column cross-checks the classification total
    #    (two independent printed tables; tolerate small report rounding).
    for cls, scalars in settlement.items():
        current = scalars.get("current")
        total_scalar = totals.get(cls)
        if current is None or total_scalar is None:
            continue
        drift = abs(current.npr - total_scalar.npr)
        if drift > _CROSS_CHECK_TOLERANCE_NPR:
            errors.append(
                _recon_error(
                    f"{cls}: settlement current-year {current.npr} NPR vs classification total "
                    f"{total_scalar.npr} NPR drift {drift} exceeds tolerance "
                    f"{_CROSS_CHECK_TOLERANCE_NPR}",
                    current.raw,
                )
            )
    return errors


def build_output(
    *,
    fiscal_year_bs: str,
    source_document_id: str,
    ch1: list[AuditedEntityRow],
    ch2: list[BerujuCell],
    totals: dict[SubjectClass, ClassScalar],
    settlement: dict[SubjectClass, dict[str, ClassScalar]],
) -> dict[str, Any]:
    """Assemble the AuditParserOutput contract dict, reconciling the beruju
    lines against the printed totals/subtotals + the settlement cross-check."""
    prov = _provenance(source_document_id)
    errors = reconcile_beruju(ch2, totals, settlement)
    return {
        "status": "success" if not errors else "partial",
        "parser_version": PARSER_VERSION,
        "source_id": SOURCE_ID,
        "source_document_id": source_document_id,
        "fiscal_year_bs": fiscal_year_bs,
        "summaries": _summary_drafts(fiscal_year_bs, ch1, totals, settlement, prov),
        "beruju_lines": _beruju_line_drafts(fiscal_year_bs, ch2, prov),
        "financial_stocks": [],
        "paragraph_metrics": [],
        "findings": [],
        "errors": errors,
    }


def _find_table(
    all_tables: list[list[list[str | None]]], needles: tuple[str, ...]
) -> list[list[str | None]] | None:
    """Return the first extracted table whose flattened text contains all needles."""
    for tb in all_tables:
        flat = " ".join((c or "") for row in tb for c in row).lower()
        if all(n in flat for n in needles):
            return tb
    return None


def parse(
    source_document_path: str,
    source_document_id: str,
    *,
    fiscal_year_bs: str | None = None,
) -> dict[str, Any]:
    """Read the OAG Annual Report PDF and return the AuditParserOutput dict.

    Locates the Ch.1 audited-entities table, the Ch.2 irregularity-by-category
    table, the printed "Total irregularity" row, and the Ch.2 settlement table
    by content (robust to page-number drift across editions). The audited FY is
    taken from ``fiscal_year_bs`` when the orchestrator already knows it (from
    the discovery ReportRef); otherwise it is derived from the cover-page title's
    edition ordinal.
    """
    import pdfplumber  # local import: keeps the pure logic above PDF-free + testable

    path = Path(source_document_path)
    with pdfplumber.open(path) as pdf:
        title_text = "\n".join(pg.extract_text() or "" for pg in pdf.pages[:3])
        all_tables = [tb for pg in pdf.pages for tb in pg.extract_tables()]

    fy = fiscal_year_bs or fiscal_year_from_title(title_text)
    if fy is None:
        raise ParserError(
            "could not determine the audited fiscal year (no edition ordinal in "
            "the title; pass fiscal_year_bs explicitly)"
        )

    ch1_tb = _find_table(all_tables, ("federal", "provincial", "local", "corporate"))
    ch2_tb = _find_table(all_tables, ("recoverable", "irregular", "advance"))
    if ch1_tb is None or ch2_tb is None:
        raise ParserError("Chapter-1 and/or Chapter-2 aggregate tables not located")

    ch1 = parse_ch1_audited(ch1_tb)

    # The Ch.2 classification table spans the page break: pdfplumber emits the
    # head (recoverable…advance) and the continuation (the 3.x advance sub-rows +
    # the printed "Total irregularity" row) as separate tables. Concatenate them
    # so every detail leaf is captured and the leaves reconcile to the totals.
    ch2_rows: list[list[str | None]] = list(ch2_tb)
    cont_tb = next(
        (tb for tb in all_tables if any("total irregularity" in _norm(r[0] or "") for r in tb)),
        None,
    )
    if cont_tb is not None and cont_tb is not ch2_tb:
        ch2_rows += cont_tb
    ch2 = parse_ch2_beruju(ch2_rows)
    totals = parse_ch2_total_row(ch2_rows)

    settlement_tb = _find_table(all_tables, ("cumulative", "adjustment", "settled"))
    settlement = parse_settlement_table(settlement_tb) if settlement_tb else {}

    return build_output(
        fiscal_year_bs=fy,
        source_document_id=source_document_id,
        ch1=ch1,
        ch2=ch2,
        totals=totals,
        settlement=settlement,
    )


if __name__ == "__main__":
    import json
    import sys

    _NIL_DOC_ID = "00000000-0000-4000-8000-000000000000"
    doc_id = sys.argv[2] if len(sys.argv) > 2 else _NIL_DOC_ID  # noqa: PLR2004
    out = parse(sys.argv[1], doc_id)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
