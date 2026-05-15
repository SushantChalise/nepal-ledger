"""MoF Local Fiscal Transfers parser — deterministic Python.

Source: Ministry of Finance / NNRFC intergovernmental fiscal transfer
allocations to Nepal's 753 local levels, FY 2082/83. Reads the cleaned XLSX
at ``Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx``
which lives in the gitignored ``Financial Data/`` tree (see
``_common._common_paths``).

Behavior:
    Reads the *transfer* sheet (Sheet1 / first non-canonical sheet) and
    emits one ``FiscalTransferRow`` per (local_level x grant_type) cell.
    Column-header detection is keyword-based and case-insensitive — see
    ``_GRANT_HEADER_KEYWORDS`` — so the parser tolerates the cosmetic
    column-naming drift typical of MoF spreadsheets.

    Municipality names are normalised + fuzzy-resolved through
    ``_common.municipality_resolver`` (the canonical 753-row table lives on
    Sheet2 of the SAME XLSX). Unresolvable rows surface as warnings, not
    silent skips.

Output contract:
    JSON to stdout, validated by ``src/lib/ingestion/types.ts`` →
    ``FiscalTransferParserOutputSchema`` on the Node side. Top-level shape:
        {
          "status": "success"|"partial"|"failure",
          "parser_version": "0.1.0",
          "rows": [FiscalTransferRow.to_json_dict, ...],
          "errors": [ParserError.to_json_dict, ...],
        }

Versioning:
    Bump ``PARSER_VERSION`` on any behaviour change.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Literal

import pandas as pd

from _common.municipality_resolver import (
    MunicipalityMatch,
    resolve_municipality,
)
from _common.types import ParserError, ParserStatus

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "local-fiscal-transfers-cleaned"

# Fiscal year + confidence anchors. The cleaned XLSX covers FY 2082/83 only.
_DEFAULT_FISCAL_YEAR_BS: Final[str] = "2082/83"
_DEFAULT_CONFIDENCE: Final[Literal["A", "B", "C"]] = "A"
_DEFAULT_UNIT: Final[str] = "NPR_thousand"
_DEFAULT_TRANSFER_SHEET: Final[str] = "Sheet1"
_NAME_COLUMN_KEYWORDS: Final[tuple[str, ...]] = ("local level", "municipality", "name", "स्थानीय")
_DISTRICT_COLUMN_KEYWORDS: Final[tuple[str, ...]] = ("district", "जिल्ला")

# Each entry: (set of required substrings, enum value). A column header
# matches if ALL substrings appear (lower-cased). Order matters — the first
# match wins, so list the most specific entries first. This shape tolerates
# the MoF "X Grant (Y)" pattern AND short-form headers like "Conditional
# Current" without depending on punctuation or budget-head codes.
_GRANT_HEADER_RULES: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    # Equalization (3 sub-types) — order: most-specific keyword first.
    (("equalization", "minimum"), "equalization_minimum"),
    (("equalization", "formula"), "equalization_formula"),
    (("equalization", "performance"), "equalization_performance"),
    # Conditional (current + capital)
    (("conditional", "current"), "conditional_current"),
    (("conditional", "recurrent"), "conditional_current"),
    (("conditional", "capital"), "conditional_capital"),
    # Special (current + capital)
    (("special", "current"), "special_current"),
    (("special", "recurrent"), "special_current"),
    (("special", "capital"), "special_capital"),
    # Complementary / matching (capital only)
    (("complementary",), "complementary_capital"),
    (("matching",), "complementary_capital"),
)


@dataclass(frozen=True)
class FiscalTransferRow:
    """One (local_level x grant_type) fiscal-transfer fact.

    Mirrors ``src/lib/db/schema/fiscal-transfers.ts`` —
    ``local_government_fiscal_transfers``. The Node-side ingest script
    resolves ``federal_code`` -> ``local_level_entity_id`` (entities table)
    before inserting; the parser deliberately does not embed UUIDs.
    """

    federal_code: str  # 8-digit zero-padded; matches entities.slug for kind='local_level'.
    municipality_name_en: str
    municipality_name_ne: str
    local_level_type: str  # snake_case slug from municipality_resolver
    district_en: str
    fiscal_year_bs: str
    grant_type: str  # one of grantTypeEnum values
    amount_npr: float
    unit: str
    confidence_grade: Literal["A", "B", "C"]
    notes: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = _cell_text(value).replace(",", "")
    if not text or text in {"-", "—", "N/A", "n/a"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _match_grant_type(header_text: str) -> str | None:
    lowered = header_text.lower()
    for required, enum_value in _GRANT_HEADER_RULES:
        if all(token in lowered for token in required):
            return enum_value
    return None


def _detect_header_row(df: pd.DataFrame) -> tuple[int, dict[int, str]] | None:
    """Find the first row whose cells contain at least one grant-type keyword.

    Returns ``(row_index, {col_index: grant_type})`` or ``None`` if no row
    qualifies. A header row must yield at least 2 distinct grant types to be
    accepted — guards against false positives where one stray cell mentions
    a keyword.
    """
    min_distinct = 2
    for row_idx in range(min(len(df), 20)):
        col_to_grant: dict[int, str] = {}
        for col_idx in range(len(df.columns)):
            text = _cell_text(df.iat[row_idx, col_idx])
            if not text:
                continue
            grant = _match_grant_type(text)
            if grant is not None:
                col_to_grant[col_idx] = grant
        if len(set(col_to_grant.values())) >= min_distinct:
            return row_idx, col_to_grant
    return None


def _detect_name_columns(
    df: pd.DataFrame,
    header_row: int,
) -> tuple[int | None, int | None]:
    """Return ``(name_col, district_col)`` indices from the header row."""
    name_col: int | None = None
    district_col: int | None = None
    for col_idx in range(len(df.columns)):
        text = _cell_text(df.iat[header_row, col_idx]).lower()
        if not text:
            continue
        if district_col is None and any(k in text for k in _DISTRICT_COLUMN_KEYWORDS):
            district_col = col_idx
            continue
        if name_col is None and any(k in text for k in _NAME_COLUMN_KEYWORDS):
            name_col = col_idx
    return name_col, district_col


def _read_workbook(path: Path) -> tuple[pd.DataFrame | None, ParserError | None]:
    try:
        # `engine='openpyxl'` is the canonical XLSX reader (openpyxl is a
        # pinned dependency in scrapers/pyproject.toml).
        df = pd.read_excel(
            path,
            sheet_name=_DEFAULT_TRANSFER_SHEET,
            header=None,
            dtype=object,
            engine="openpyxl",
        )
    except FileNotFoundError as exc:
        return None, ParserError(error_class="Other", error_detail=f"source file not found: {exc}")
    except (OSError, ValueError) as exc:
        return None, ParserError(
            error_class="EncodingError",
            error_detail=f"xlsx read failed: {exc}",
        )
    return df, None


def _resolve_row(
    name_raw: str,
    district_raw: str,
) -> tuple[MunicipalityMatch | None, ParserError | None]:
    if not name_raw:
        return None, ParserError(
            error_class="ValueUnparseable",
            error_detail="empty municipality name",
        )
    try:
        match = resolve_municipality(name_raw, district_hint=district_raw or None)
    except FileNotFoundError as exc:
        # Canonical 753-row table not on disk — surface clearly.
        return None, ParserError(
            error_class="Other",
            error_detail=f"canonical municipality table unavailable: {exc}",
        )
    if match is None:
        return None, ParserError(
            error_class="RegexMismatch",
            error_detail=f"could not resolve municipality: {name_raw!r}",
            source_excerpt=district_raw or None,
        )
    return match, None


def parse(
    source_document_path: str,
    source_document_id: str,
    fiscal_year_bs: str = _DEFAULT_FISCAL_YEAR_BS,
) -> dict[str, Any]:
    """Parse the cleaned XLSX; see module docstring for contract.

    Returns a serialisable dict (the top-level JSON shape). ``status`` is
    ``failure`` on any catastrophic miss (file not found, no header row,
    zero rows resolved), ``partial`` when warnings exist but at least one
    row resolved, ``success`` on a clean parse.
    """
    _ = source_document_id  # threaded for symmetry with other parsers

    errors: list[ParserError] = []
    rows: list[FiscalTransferRow] = []

    path = Path(source_document_path)
    df, read_err = _read_workbook(path)
    if df is None or read_err is not None:
        if read_err is not None:
            errors.append(read_err)
        return _result("failure", rows, errors)

    detected = _detect_header_row(df)
    if detected is None:
        errors.append(
            ParserError(
                error_class="ColumnMissing",
                error_detail=(
                    "could not locate header row (need >=2 distinct grant-type keywords); "
                    f"scanned first 20 rows of {_DEFAULT_TRANSFER_SHEET!r}"
                ),
            ),
        )
        return _result("failure", rows, errors)

    header_row, grant_columns = detected
    name_col, district_col = _detect_name_columns(df, header_row)
    if name_col is None:
        errors.append(
            ParserError(
                error_class="ColumnMissing",
                error_detail="could not locate municipality-name column in header row",
            ),
        )
        return _result("failure", rows, errors)

    for raw_idx in range(header_row + 1, len(df)):
        name_raw = _cell_text(df.iat[raw_idx, name_col])
        district_raw = _cell_text(df.iat[raw_idx, district_col]) if district_col is not None else ""
        if not name_raw:
            # blank line — skip silently (separators / totals rows commonly empty)
            continue

        # Skip aggregator rows whose name contains 'Total' / 'जम्मा' etc.
        name_lower = name_raw.lower()
        if any(tok in name_lower for tok in ("total", "जम्मा", "कुल")):
            continue

        match, resolve_err = _resolve_row(name_raw, district_raw)
        if match is None:
            if resolve_err is not None:
                errors.append(resolve_err)
            continue

        for col_idx, grant_type in grant_columns.items():
            amount = _safe_float(df.iat[raw_idx, col_idx])
            if amount is None:
                continue  # blank cell — common; not an error
            rows.append(
                FiscalTransferRow(
                    federal_code=match.federal_code,
                    municipality_name_en=match.name_en,
                    municipality_name_ne=match.name_ne,
                    local_level_type=match.local_level_type,
                    district_en=match.district_en,
                    fiscal_year_bs=fiscal_year_bs,
                    grant_type=grant_type,
                    amount_npr=amount,
                    unit=_DEFAULT_UNIT,
                    confidence_grade=_DEFAULT_CONFIDENCE,
                    notes=None,
                ),
            )

    if not rows:
        return _result(
            "failure",
            rows,
            errors
            or [
                ParserError(
                    error_class="Other",
                    error_detail="parsed zero fiscal-transfer rows from workbook",
                ),
            ],
        )

    status: ParserStatus = "partial" if errors else "success"
    return _result(status, rows, errors)


def _result(
    status: ParserStatus,
    rows: list[FiscalTransferRow],
    errors: list[ParserError],
) -> dict[str, Any]:
    # ``asdict`` is used directly instead of the dataclass ``to_json_dict``
    # method because direct-script invocation (``python parser.py``) can
    # produce two distinct class identities for ``_common.types.ParserError``
    # — one via ``__main__`` and one via ``_common.types`` — and the
    # method-bound version may not be visible on every instance. ``asdict``
    # is duck-typed and works on any dataclass instance regardless of
    # module identity.
    return {
        "status": status,
        "parser_version": PARSER_VERSION,
        "rows": [asdict(r) for r in rows],
        "errors": [asdict(e) for e in errors],
    }


def _main() -> None:
    """CLI entrypoint used by ``scripts/ingest-fiscal-transfers.ts``.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Exit codes:
      - 0: parser ran (status may still be ``failure``; consumer reads stdout)
      - 2: usage error
      - 1: catastrophic crash (uncaught)
    """
    import json
    import sys

    expected_argc = 3
    if len(sys.argv) != expected_argc:
        sys.stderr.write(
            "usage: parser.py <source_document_path> <source_document_id>\n",
        )
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    _main()
