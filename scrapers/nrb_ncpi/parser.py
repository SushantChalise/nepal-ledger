"""NRB NCPI Table 2(B) parser — deterministic Python.

Source: NRB CMEFs nine-month publication, Table 2(B) — National Consumer
Price Index, base year 2023/24 = 100.

Behavior:
    Reads the CSV at ``source_document_path`` and emits one ``StagingRowDraft``
    per (indicator x geography). The emitted measure is the headline
    year-on-year percent change at the close of the publication's 9th month
    (Mid-Chait of the current fiscal year vs. Mid-Chait of the prior FY) —
    which is the figure NRB highlights in the CMEFs nine-month report.

    ``reporting_period_type`` is ``'nine_months_cumulative'`` and
    ``reporting_period_bs`` is ``'FY 2082/83 9M'`` for every row in this
    parse, matching the schema used elsewhere for CMEFs nine-month outputs.

Indicator slug convention:
    ``ncpi-<group-or-code>-<geo>-yoy`` where:
      - ``<group-or-code>`` is lower-cased & hyphen-joined from the CSV label
        (e.g. ``overall-index``, ``food-and-beverages``, ``a-1-cereal-grains``)
      - ``<geo>`` is one of ``overall``, ``rural``, ``urban``

Period dating:
    AD timestamps use the lightweight mid-month placeholder from
    ``_common.periods`` (15th of corresponding AD month). The validation
    layer on the TS side refines these (CALENDAR_AND_PERIODS.md). Tolerance
    at the test layer is ±2 days.

Versioning:
    Bump PARSER_VERSION on any behavior change.
"""

from __future__ import annotations

import re
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pandas as pd

from _common.periods import (
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
    nine_months_span_ad,
)
from _common.types import (
    ParserError,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "nrb-ncpi-table"

# Fiscal year and publication anchor for the bundled fixture
# (``NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv``). When the
# orchestrator wires the source-registry row, the parser will receive these
# via metadata rather than hard-coding. For the v0.1.0 shell we anchor to
# the fixture's FY 2082/83 nine-month publication.
_BS_FY_START: Final[int] = 2082
_PUBLICATION_DATE_AD: Final[datetime] = datetime(2026, 5, 8, tzinfo=UTC)
_PUBLICATION_DATE_BS: Final[str] = "2083 Baisakh 25"

# Recognised group codes in column A (besides blank for Overall Index).
_VALID_CODE_RE: Final[re.Pattern[str]] = re.compile(r"^[AB](\.\d{1,2})?$")


def _slugify(label: str, code: str) -> str:
    """Build the indicator slug stem from the CSV label + group code."""
    cleaned = label.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    if code and code.strip():
        code_part = code.strip().lower().replace(".", "-")
        return f"{code_part}-{cleaned}"
    return cleaned


def _safe_float(raw: object) -> float | None:
    """Best-effort parse to float; returns None for blank/NaN/non-numeric."""
    if raw is None:
        return None
    if isinstance(raw, float) and pd.isna(raw):
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _resolve_columns(df: pd.DataFrame) -> dict[str, int] | None:
    """Inspect the header rows to find the YoY (% change) column index per geo.

    The CSV labels them ``3 over 1`` (Overall), ``6 over 4`` (Rural), and
    ``9 over 7`` (Urban). Returns ``None`` if any are missing.
    """
    needles = {"overall": "3 over 1", "rural": "6 over 4", "urban": "9 over 7"}
    found: dict[str, int] = {}
    for _, row in df.iterrows():
        for col_idx, cell in enumerate(row.tolist()):
            if cell is None or (isinstance(cell, float) and pd.isna(cell)):
                cell_text = ""
            else:
                cell_text = str(cell).strip()
            for geo, needle in needles.items():
                if geo not in found and cell_text == needle:
                    found[geo] = col_idx
        if len(found) == len(needles):
            return found
    return None


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse the NRB NCPI Table 2(B) CSV; see module docstring for contract.

    Arguments:
        source_document_path: filesystem path to the downloaded CSV.
        source_document_id: opaque ID from ``source_documents``; not consumed
            by this parser but threaded through for symmetry.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``, ``errors``.
    """
    # source_document_id is part of the contract; the parser does not embed
    # it in rows (the orchestrator joins on parser_runs). Touch it so static
    # analysers don't flag the unused parameter.
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
        df = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(error_class="EncodingError", error_detail=f"csv read failed: {exc}"),
            ],
        )

    yoy_columns = _resolve_columns(df)
    if yoy_columns is None:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="ColumnMissing",
                    error_detail=(
                        "could not find YoY % change columns (expected headers "
                        "'3 over 1', '6 over 4', '9 over 7')"
                    ),
                )
            ],
        )

    ad_start, ad_end = nine_months_span_ad(_BS_FY_START)
    # The 9th month is Chait; report period ends at mid-Chait.
    chait_mid = mid_month_ad("Chait", _BS_FY_START)
    ad_end = chait_mid

    base = StagingRowDraft(
        indicator_slug_raw="",  # filled per-row
        value=0.0,
        unit="percent_yoy",
        reporting_period_type="nine_months_cumulative",
        reporting_period_bs=f"FY {fiscal_year_label(_BS_FY_START)} 9M",
        reporting_period_ad_start=ad_start,
        reporting_period_ad_end=ad_end,
        publication_date_ad=_PUBLICATION_DATE_AD,
        publication_date_bs=_PUBLICATION_DATE_BS,
        fiscal_year_bs=fiscal_year_label(_BS_FY_START),
        fiscal_year_ad_label=fiscal_year_ad_label(_BS_FY_START),
        confidence_grade_proposed="A",
        parser_notes=None,
    )

    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for raw_idx, row in df.iterrows():
        code_cell = str(row.iloc[0]).strip() if len(row) > 0 else ""
        label_cell = str(row.iloc[1]).strip() if len(row) > 1 else ""

        is_overall_index = not code_cell and label_cell == "Overall Index"
        is_grouped = bool(code_cell) and _VALID_CODE_RE.match(code_cell) is not None
        if not (is_overall_index or is_grouped):
            continue
        if not label_cell:
            continue

        slug_stem = _slugify(label_cell, code_cell)

        for geo, col_idx in yoy_columns.items():
            if col_idx >= len(row):
                errors.append(
                    ParserError(
                        error_class="ColumnMissing",
                        error_detail=f"row {raw_idx}: missing column {col_idx} for {geo}",
                        source_excerpt=label_cell,
                    )
                )
                continue
            value = _safe_float(row.iloc[col_idx])
            if value is None:
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=(
                            f"row {raw_idx} ({slug_stem}/{geo}): "
                            f"could not parse '{row.iloc[col_idx]!r}' as float"
                        ),
                        source_excerpt=label_cell,
                    )
                )
                continue
            staging_rows.append(
                replace(
                    base,
                    indicator_slug_raw=f"ncpi-{slug_stem}-{geo}-yoy",
                    value=value,
                )
            )

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors
            or [
                ParserError(
                    error_class="Other",
                    error_detail="no recognised data rows found in CSV",
                )
            ],
        )

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def _serialize_result(result: ParserResult) -> dict[str, Any]:
    """Serialize ``ParserResult`` to the JSON shape expected by the TS Zod
    schema (`src/lib/ingestion/types.ts` > ``ParserOutputSchema``).

    Uses ``dataclasses.asdict`` directly rather than the dataclass
    ``to_json_dict`` method because direct-script invocation (``python -m
    scrapers.nrb_ncpi.parser``) can produce two distinct class identities
    for ``_common.types.*`` dataclasses — one via ``__main__`` and one via
    ``_common.types`` — and the method-bound version may not be visible on
    every instance. ``asdict`` is duck-typed and works on any dataclass
    instance regardless of module identity. Datetime fields are then
    coerced to ISO 8601 strings explicitly.
    """
    rows: list[dict[str, Any]] = []
    for row in result.staging_rows:
        d = asdict(row)
        for k in (
            "reporting_period_ad_start",
            "reporting_period_ad_end",
            "publication_date_ad",
        ):
            v = d.get(k)
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        rows.append(d)
    return {
        "status": result.status,
        "parser_version": result.parser_version,
        "staging_rows": rows,
        "errors": [asdict(e) for e in result.errors],
    }


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes the serialized ``ParserResult`` as JSON to stdout. Exit codes
    follow the subprocess contract in ``src/lib/ingestion/run-parser.ts``:
      - 0: parser ran (status may still be 'failure'; consumer reads stdout)
      - 2: usage error
      - 1: catastrophic crash
    """
    import json
    import sys

    if len(sys.argv) != 3:
        sys.stderr.write(
            "usage: parser.py <source_document_path> <source_document_id>\n"
        )
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    json.dump(_serialize_result(result), sys.stdout)


if __name__ == "__main__":
    _main()
