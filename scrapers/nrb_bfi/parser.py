"""NRB BFI monthly XLSX parser — canonical month (Bhadau 2082).

Source id: ``nrb-bfi-monthly-xlsx``.

Scope (this version):
    Parses sheet **C5** (Statement of Assets & Liabilities) for the canonical
    publication ``Bhadau_2082_Publish.xlsx``. Emits one row per
    (indicator, bank_class) for the latest snapshot column (Mid-Sept 2025).

    Schema drift across the 49-month corpus is documented in
    ``docs/research/nrb-bfi-schema-probe.md`` (output of
    ``scrapers.nrb_bfi.schema_probe``). Follow-up parsers for the remaining 48
    months are batched per the brief at
    ``docs/tasks/worker-P2-followup-bfi-batches.md``.

C5 layout (canonical month):
    Sheet has four side-by-side sub-tables, one per bank class. Each sub-table
    shares the descriptive label column (col index 2) and uses a fixed
    column stride of 8 for value columns. Mid-Sept (latest) value column
    indices are: BFI total -> 7, Commercial -> 15, Development -> 23,
    Finance -> 31. Numeric ordinal column (col 1) groups L/A side-of-balance
    rows; the descriptive label (col 2) is the indicator name.

Indicator slug convention:
    ``bfi-c5-<bank-class>-<slugified-label>`` (e.g.
    ``bfi-c5-commercial-deposits``). Bank-class is also emitted as a typed
    dimension via ``BankingSectorFactRow.bank_class``; encoding it in the slug
    keeps the slug unique across bank classes and makes the staging table
    legible.

Output:
    Emits ``BankingSectorFactRow`` dataclasses (NOT ``StagingRowDraft``) —
    the BFI corpus targets ``banking_sector_facts`` directly, not the
    indicator-values staging pipeline. The Node CLI
    ``scripts/ingest-bfi-monthly.ts`` consumes the JSON output via
    ``BankingSectorFactRow.to_json_dict()``.

Versioning:
    Bump PARSER_VERSION on any behaviour change.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

import openpyxl

from _common.periods import fiscal_year_label, mid_month_ad
from _common.types import ParserError, ParserStatus

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "nrb-bfi-monthly-xlsx"

BankClass = Literal["commercial", "development", "finance", "system_total"]

# Canonical month metadata. When the ingest CLI wires the source-registry row,
# the parser will receive these via metadata; pinned here for the v0.1.0 shell.
_CANONICAL_FILENAME: Final[str] = "Bhadau_2082_Publish.xlsx"
_BS_FY_START: Final[int] = 2082
_BS_MONTH: Final[str] = "Bhadra"  # Bhadau == Bhadra
_REPORTING_PERIOD_BS: Final[str] = "Bhadra 2082"
# NRB BFI files are typically released ~6 weeks after period close.
_PUBLICATION_DATE_AD: Final[datetime] = datetime(2025, 10, 15, tzinfo=UTC)
_PUBLICATION_DATE_BS: Final[str] = "2082 Ashwin 30 (approx)"

# C5 sheet column layout (0-indexed). Mid-Sept (latest snapshot) value column
# per bank-class sub-table.
_LATEST_VALUE_COL_BY_CLASS: Final[dict[BankClass, int]] = {
    "system_total": 7,
    "commercial": 15,
    "development": 23,
    "finance": 31,
}
_LABEL_COL: Final[int] = 2

# C5 indicator labels we lift in v0.1.0. Hand-picked to anchor the canonical
# month: the rows we expect to find on every snapshot. Adding more rows is a
# parser-version bump; do not silently expand.
_C5_INDICATORS: Final[tuple[tuple[str, str], ...]] = (
    # (descriptive label in col 2, slug stem after bank-class)
    ("CAPITAL FUND", "capital-fund"),
    ("a. Paid-up Capital", "paid-up-capital"),
    ("b. Statutory Reserves", "statutory-reserves"),
    ("BORROWINGS", "borrowings-total"),
    ("DEPOSITS", "deposits-total"),
    ("a. Current", "deposits-current"),
    ("b. Savings", "deposits-savings"),
    ("c. Fixed", "deposits-fixed"),
    ("LIQUID FUNDS", "liquid-funds"),
)

_UNIT: Final[str] = "npr_million"


@dataclass(frozen=True)
class BankingSectorFactRow:
    """Python mirror of ``banking_sector_facts.$inferInsert`` minus FKs and
    server-side fields (``id``, ``source_document_id``, ``promoted_*``)
    which the Node ingest layer fills in.
    """

    bank_class: BankClass
    bank_entity_id: str | None  # null for class-aggregate rows
    source_sheet: str
    indicator_slug: str
    value: float
    unit: str
    reporting_period_type: Literal["monthly"]
    reporting_period_bs: str
    reporting_period_ad_start: datetime
    reporting_period_ad_end: datetime
    publication_date_ad: datetime
    publication_date_bs: str
    fiscal_year_bs: str
    confidence_grade: Literal["A", "B", "C"]
    parser_notes: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for k in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            out[k] = getattr(self, k).isoformat()
        return out


@dataclass(frozen=True)
class ParserResult:
    """Top-level result. Mirrors ``_common.types.ParserResult`` shape but
    carries ``BankingSectorFactRow`` rather than ``StagingRowDraft``.
    """

    status: ParserStatus
    parser_version: str
    fact_rows: list[BankingSectorFactRow] = field(default_factory=list)
    errors: list[ParserError] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "parser_version": self.parser_version,
            "fact_rows": [r.to_json_dict() for r in self.fact_rows],
            "errors": [e.to_json_dict() for e in self.errors],
        }


def _safe_float(raw: object) -> float | None:
    """Coerce a cell value to float; reject NaN, empty, and non-numeric."""
    if raw is None:
        return None
    try:
        v = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN; openpyxl can return float('nan')  # noqa: PLR0124
        return None
    return v


def _norm_label(raw: object) -> str:
    return "" if raw is None else " ".join(str(raw).split())


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse the canonical Bhadau 2082 BFI XLSX.

    Arguments:
        source_document_path: filesystem path to the XLSX.
        source_document_id: opaque ID (threaded through; not embedded in rows).

    Returns:
        ``ParserResult`` with ``status``, ``fact_rows``, ``errors``.
    """
    _ = source_document_id

    path = Path(source_document_path)
    if not path.exists():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"source file not found: {path}",
                )
            ],
        )

    try:
        wb = openpyxl.load_workbook(filename=str(path), read_only=True, data_only=True)
    except (OSError, KeyError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"openpyxl could not open {path.name}: {exc}",
                )
            ],
        )

    if "C5" not in wb.sheetnames:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail=f"expected sheet C5 not present in {path.name}",
                )
            ],
        )

    ws = wb["C5"]
    rows = list(ws.iter_rows(values_only=True))

    # Build label -> row index map (first occurrence wins).
    label_to_row: dict[str, int] = {}
    for r_idx, row in enumerate(rows):
        if len(row) <= _LABEL_COL:
            continue
        lbl = _norm_label(row[_LABEL_COL])
        if lbl and lbl not in label_to_row:
            label_to_row[lbl] = r_idx

    # AD span for the canonical month (Bhadau 2082 == Bhadra BS). Uses
    # mid_month_ad placeholders; tolerance ±2 days at the TS validator.
    _mid = mid_month_ad("Bhadra", _BS_FY_START)
    ad_start = datetime(_mid.year, _mid.month, 1, tzinfo=UTC)
    ad_end = datetime(_mid.year, _mid.month, 15, tzinfo=UTC)

    fact_rows: list[BankingSectorFactRow] = []
    errors: list[ParserError] = []

    for label, slug_stem in _C5_INDICATORS:
        r_idx = label_to_row.get(label)
        if r_idx is None:
            errors.append(
                ParserError(
                    error_class="RegexMismatch",
                    error_detail=f"C5 label not found: {label!r}",
                    source_excerpt=label,
                )
            )
            continue
        row = rows[r_idx]
        for bank_class, col_idx in _LATEST_VALUE_COL_BY_CLASS.items():
            if col_idx >= len(row):
                errors.append(
                    ParserError(
                        error_class="ColumnMissing",
                        error_detail=(
                            f"row {r_idx} ({label!r}/{bank_class}): "
                            f"value column {col_idx} out of range (row len {len(row)})"
                        ),
                        source_excerpt=label,
                    )
                )
                continue
            value = _safe_float(row[col_idx])
            if value is None:
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=(
                            f"row {r_idx} ({label!r}/{bank_class}): "
                            f"could not parse {row[col_idx]!r} as float"
                        ),
                        source_excerpt=label,
                    )
                )
                continue
            fact_rows.append(
                BankingSectorFactRow(
                    bank_class=bank_class,
                    bank_entity_id=None,
                    source_sheet="C5",
                    indicator_slug=f"bfi-c5-{bank_class.replace('_', '-')}-{slug_stem}",
                    value=value,
                    unit=_UNIT,
                    reporting_period_type="monthly",
                    reporting_period_bs=_REPORTING_PERIOD_BS,
                    reporting_period_ad_start=ad_start,
                    reporting_period_ad_end=ad_end,
                    publication_date_ad=_PUBLICATION_DATE_AD,
                    publication_date_bs=_PUBLICATION_DATE_BS,
                    fiscal_year_bs=fiscal_year_label(_BS_FY_START),
                    confidence_grade="A",
                    parser_notes=None,
                )
            )

    _ = _BS_MONTH  # reserved for future expansion (sheet-driven period inference)

    if not fact_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors
            or [
                ParserError(
                    error_class="Other",
                    error_detail="no recognised C5 rows found",
                )
            ],
        )

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        fact_rows=fact_rows,
        errors=errors,
    )


def _main() -> None:
    """CLI entrypoint used by ``scripts/ingest-bfi-monthly.ts``.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes ``ParserResult.to_json_dict()`` to stdout.
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
