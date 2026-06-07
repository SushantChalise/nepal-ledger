"""NRB Database on Nepalese Economy (DNE) XLSX parser — deterministic Python.

Source id: ``nrb-dne-xlsx``.

Layout contract (all DNE XLSX files share this wide-format):
    - First column(s): indicator label / row descriptor text.
    - Header row(s): period labels, e.g. "2079/80", "2080/81" (annual FY) or
      "Shrawan 2082", "Bhadra 2082" (monthly BS period).  The header row is
      detected as the first row that contains at least one parseable period
      token.
    - Data rows: each non-empty label row contains float (or int) values
      keyed to the column period headers.
    - Some files have a title row / unit annotation row above the header.
      The unit string ("in million US$", "Rs. in million", etc.) is extracted
      from these preamble rows.

Slug convention:
    ``dne-<kebab-case-label>`` (prefix ``dne-`` + slugified row label).

Unit detection:
    Scanned from preamble rows (rows before the detected header row) and the
    sheet title.  Mapping table follows NRB's common phrasings.  If the unit
    cannot be resolved, a ``UnitAmbiguous`` error is emitted but parsing
    continues — the raw unit string is used as the ``unit`` field so the
    validator can flag it rather than dropping data.

Period detection:
    Annual FY patterns: "2079/80", "2079-80".  Both treated as annual FY.
    Monthly patterns: "<bs_month_name> <bs_year>", e.g. "Shrawan 2082".
    Unparseable period column headers → ``PeriodUnparseable`` error; the
    column is skipped.

Confidence: ``B`` default for all DNE rows (NRB compiles from multiple
agencies; figures revised across publications).

ADR: ADR-0003 — no LLM / AI calls. Pure file-in → dataclass-out.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import openpyxl

from _common.periods import (
    BS_MONTHS,
    BsMonth,
    fiscal_year_ad_label,
    mid_month_ad,
)
from _common.types import (
    ParserError,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.2.0"
SOURCE_ID: Final[str] = "nrb-dne-xlsx"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Confidence default for all DNE rows — NRB compiles from multiple agencies;
# figures are revised.  Validation layer may promote individual rows to 'A'.
_CONFIDENCE: Final = "B"

# Publication date placeholder — DNE files carry no embedded publication date;
# the orchestrator supplies the actual download timestamp.  We use a sentinel
# that is clearly approximate so the TS validator can flag it.
_PUB_DATE_SENTINEL: Final[datetime] = datetime(1970, 1, 1, tzinfo=UTC)
_PUB_DATE_BS_SENTINEL: Final[str] = "unknown"

# Regex: annual FY label like "2079/80", "2079-80", "2079/80R", "2079/80P",
# "2079/2080" (4-digit tail used in some SITC sheets), optionally prefixed
# with a bracketed BS label like "(2071-72) 2014/15".
# Groups: (1) = BS/AD start year 4-digit, (2) = tail 2- or 4-digit.
# Revision suffix [R/P/E] is stripped before matching.
_ANNUAL_FY_RE: Final = re.compile(
    r"^\s*(?:\(\d{4}[-/]\d{2,4}\)\s+)?"  # optional "(YYYY-YY) " prefix
    r"(\d{4})\s*[/\-]\s*(\d{2,4})\s*[RPEQrpeq]?\s*$"
)

# Regex: monthly BS period like "Shrawan 2082", "Bhadra 2081", case-insensitive.
# Build from the canonical month list so it stays in sync with _common.periods.
_MONTH_NAMES_PATTERN: Final[str] = "|".join(BS_MONTHS)
_MONTHLY_BS_RE: Final = re.compile(
    rf"^\s*({_MONTH_NAMES_PATTERN})\s+(\d{{4}})\s*$",
    re.IGNORECASE,
)

# Unit string mapping — NRB phrasing → canonical vocab.
# Keys are lowercased and whitespace-normalised before lookup.
_UNIT_MAP: Final[dict[str, str]] = {
    "in million us$": "usd_million",
    "in million us dollars": "usd_million",
    "million us$": "usd_million",
    "million usd": "usd_million",
    "us$ million": "usd_million",
    "usd million": "usd_million",
    "in us$ million": "usd_million",
    "in usd million": "usd_million",
    "in million usd": "usd_million",
    "rs. in million": "npr_million",
    "rs in million": "npr_million",
    "nrs. in million": "npr_million",
    "nrs in million": "npr_million",
    "rs. million": "npr_million",
    "rs million": "npr_million",
    "npr million": "npr_million",
    "million rs.": "npr_million",
    "million rs": "npr_million",
    "in million rs.": "npr_million",
    "in million rs": "npr_million",
    "in rs. million": "npr_million",
    "npr in million": "npr_million",
    "in npr million": "npr_million",
    "nrs million": "npr_million",
    "rs. in billion": "npr_billion",
    "rs in billion": "npr_billion",
    "nrs. in billion": "npr_billion",
    "npr billion": "npr_billion",
    "billion rs.": "npr_billion",
    "billion rs": "npr_billion",
    "in billion rs.": "npr_billion",
    "in npr billion": "npr_billion",
    "percent": "percent",
    "percentage": "percent",
    "in percent": "percent",
    "%": "percent",
    "number": "count",
    "nos.": "count",
    "nos": "count",
    "no.": "count",
    "no": "count",
    "count": "count",
    "in number": "count",
    "metric ton": "metric_ton",
    "metric tons": "metric_ton",
    "in metric tons": "metric_ton",
    "kwh": "kwh",
    "mwh": "mwh",
    "gwh": "gwh",
    "kilowatt hour": "kwh",
    "months": "months",
    "month": "months",
}

# Max rows to scan before the detected header row when searching for a unit.
_PREAMBLE_SCAN_ROWS: Final[int] = 10

# AD calendar year bounds for bare integer year detection in preamble rows.
# NRB uses bare integers like 2001, 2002 as year-row labels in the FX-reserves
# file; these are AD years, not BS.
_AD_YEAR_INT_MIN: Final[int] = 1990
_AD_YEAR_INT_MAX: Final[int] = 2040  # same as _BS_YEAR_MIN; ambiguous zone deferred

# Minimum parseable period columns required to call a sheet non-empty.
_MIN_PERIOD_COLS: Final[int] = 1

# Minimum BS fiscal-year start to distinguish BS years (2040+) from AD years
# (e.g. 2006/07 in Foreign Trade sheets). AD-year FY headers are skipped.
_BS_YEAR_MIN: Final[int] = 2040

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(label: str) -> str:
    """Convert an indicator label to a dne-prefixed kebab-case slug.

    E.g. "Total Foreign Exchange Reserves" → "dne-total-foreign-exchange-reserves".
    """
    # Lowercase, keep alphanumeric and spaces, strip other chars, then hyphenate.
    slug = label.lower()
    slug = re.sub(r"[^a-z0-9\s]+", " ", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return f"dne-{slug}"


def _norm_text(raw: object) -> str:
    """Stringify a cell value and normalise internal whitespace."""
    if raw is None:
        return ""
    return " ".join(str(raw).split())


def _safe_float(raw: object) -> float | None:
    """Coerce cell value to float; return None for empty / non-numeric / NaN."""
    if raw is None:
        return None
    s = str(raw).strip()
    # NRB sometimes uses "-" or "--" for missing data.
    if s in ("", "-", "--", "N/A", "n/a", "NA", "..."):
        return None
    try:
        v = float(s.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN  # noqa: PLR0124
        return None
    return v


def _detect_unit_from_text(text: str) -> str | None:
    """Look up a raw unit string in the unit map. Returns canonical vocab or None.

    Strips surrounding parentheses before lookup to handle NRB's common pattern
    of writing unit annotations as "(Rs in Million)" or "(NPR in Million)".
    """
    # Strip leading/trailing parentheses that NRB wraps around unit strings.
    stripped = text.strip()
    if stripped.startswith("(") and stripped.endswith(")"):
        stripped = stripped[1:-1]
    normalised = " ".join(stripped.lower().split())
    # Direct match first.
    if normalised in _UNIT_MAP:
        return _UNIT_MAP[normalised]
    # Substring match: check if any key is contained in the normalised text.
    for key, vocab in _UNIT_MAP.items():
        if key in normalised:
            return vocab
    return None


def _parse_annual_fy(label: str) -> tuple[str, str] | None:
    """Parse annual FY label → (fiscal_year_bs "YYYY/YY", fiscal_year_ad_label).

    Accepts:
    - "2079/80", "2079-80"            — standard BS format
    - "2079/80R", "2079/80P"          — NRB revised/provisional suffix
    - "2079/2080"                     — 4-digit tail (some SITC sheets)
    - "(2071-72) 2014/15"             — bracketed BS label + AD year prefix

    Accepts ONLY BS fiscal years (start year >= 2040) to avoid misclassifying
    AD calendar years (e.g. 2006/07) as BS years. AD-year FY headers are out
    of scope for this parser and logged as PeriodUnparseable by the caller.

    Returns None if not a match or not a plausible BS year.
    """
    m = _ANNUAL_FY_RE.match(label)
    if not m:
        return None
    start = int(m.group(1))
    tail_raw = m.group(2)
    tail_int = int(tail_raw) % 100  # normalise 4-digit "2080" → 80

    # Validate: tail must equal (start + 1) mod 100.
    expected_tail = (start + 1) % 100
    if tail_int != expected_tail:
        return None

    # Reject AD-era years (< 2040 = implausible as BS FY start).
    # BS fiscal years currently run ~2040–2090; AD fiscal years like 2006/07
    # start with 2006 which is below this threshold.
    if start < _BS_YEAR_MIN:
        return None

    fy_bs = f"{start}/{expected_tail:02d}"
    fy_ad = fiscal_year_ad_label(start)
    return fy_bs, fy_ad


def _parse_monthly_bs(label: str) -> tuple[BsMonth, int] | None:
    """Parse "Shrawan 2082" → (BsMonth, bs_year). Returns None if no match."""
    m = _MONTHLY_BS_RE.match(label)
    if not m:
        return None
    # Capitalise so it matches the BsMonth literal exactly.
    month_raw = m.group(1).capitalize()
    # "Chait" is used in the codebase; also accept "Chaitra".
    if month_raw == "Chaitra":
        month_raw = "Chait"
    if month_raw not in BS_MONTHS:
        return None
    return month_raw, int(m.group(2))  # type: ignore[return-value]


def _annual_fy_to_draft_fields(
    fy_bs: str,
    fy_ad: str,
    unit: str,
    slug: str,
    value: float,
    parser_notes: str | None = None,
) -> StagingRowDraft:
    """Build a StagingRowDraft for an annual FY cell."""
    bs_start = int(fy_bs.split("/")[0])
    # NRB annual FY runs mid-July (Shrawan 1) to mid-July (Asar 31).
    # Approximate: start = 15 July of AD start year, end = 15 July of AD end year.
    ad_start_year = bs_start - 57
    ad_start = datetime(ad_start_year, 7, 15, tzinfo=UTC)
    ad_end = datetime(ad_start_year + 1, 7, 15, tzinfo=UTC)
    return StagingRowDraft(
        indicator_slug_raw=slug,
        value=value,
        unit=unit,
        reporting_period_type="annual",
        reporting_period_bs=fy_bs,
        reporting_period_ad_start=ad_start,
        reporting_period_ad_end=ad_end,
        publication_date_ad=_PUB_DATE_SENTINEL,
        publication_date_bs=_PUB_DATE_BS_SENTINEL,
        fiscal_year_bs=fy_bs,
        fiscal_year_ad_label=fy_ad,
        confidence_grade_proposed=_CONFIDENCE,
        parser_notes=parser_notes,
    )


def _monthly_bs_to_draft_fields(
    bs_month: BsMonth,
    bs_year: int,
    unit: str,
    slug: str,
    value: float,
    parser_notes: str | None = None,
) -> StagingRowDraft:
    """Build a StagingRowDraft for a monthly BS cell."""
    mid = mid_month_ad(bs_month, bs_year)
    # Month span: 1st to 28th of the AD month (safe lower bound for mid-month to
    # mid-month; the TS validator refines to exact BS calendar boundaries).
    ad_start = datetime(mid.year, mid.month, 1, tzinfo=UTC)
    ad_end = datetime(mid.year, mid.month, 28, tzinfo=UTC)
    # Fiscal year: if month is Magh..Ashadh → FY starts in bs_year - 1.
    _late_months: Final = {"Magh", "Falgun", "Chait", "Baisakh", "Jestha", "Ashadh"}
    fy_start = bs_year - 1 if bs_month in _late_months else bs_year
    fy_bs = f"{fy_start}/{(fy_start + 1) % 100:02d}"
    fy_ad = fiscal_year_ad_label(fy_start)
    return StagingRowDraft(
        indicator_slug_raw=slug,
        value=value,
        unit=unit,
        reporting_period_type="monthly",
        reporting_period_bs=f"{bs_month} {bs_year}",
        reporting_period_ad_start=ad_start,
        reporting_period_ad_end=ad_end,
        publication_date_ad=_PUB_DATE_SENTINEL,
        publication_date_bs=_PUB_DATE_BS_SENTINEL,
        fiscal_year_bs=fy_bs,
        fiscal_year_ad_label=fy_ad,
        confidence_grade_proposed=_CONFIDENCE,
        parser_notes=parser_notes,
    )


# ---------------------------------------------------------------------------
# Sheet-level parser — broken into focused sub-functions to satisfy ruff
# PLR0912 (branches ≤ 12) and PLR0915 (statements ≤ 50).
# ---------------------------------------------------------------------------


def _scan_unit_hint(rows: list[tuple[object, ...]], sheet_name: str) -> str | None:
    """Return a canonical unit string from preamble rows or the sheet name."""
    preamble_chunks: list[str] = []
    for row in rows[:_PREAMBLE_SCAN_ROWS]:
        for cell in row:
            if cell is not None:
                preamble_chunks.append(_norm_text(cell))
    blob = " ".join(preamble_chunks).lower()
    hint = _detect_unit_from_text(blob)
    if hint is None:
        hint = _detect_unit_from_text(sheet_name.lower())
    return hint


def _detect_header(
    rows: list[tuple[object, ...]],
) -> tuple[int | None, dict[int, tuple[str, object]]]:
    """Find the first row with ≥1 parseable period; return (row_idx, period_cols)."""
    for row_idx, row in enumerate(rows):
        col_periods: dict[int, tuple[str, object]] = {}
        for col_idx, cell in enumerate(row):
            label = _norm_text(cell)
            annual = _parse_annual_fy(label)
            if annual:
                col_periods[col_idx] = ("annual", annual)
                continue
            monthly = _parse_monthly_bs(label)
            if monthly:
                col_periods[col_idx] = ("monthly", monthly)
        if len(col_periods) >= _MIN_PERIOD_COLS:
            return row_idx, col_periods
    return None, {}


def _find_label_col(
    header_row: tuple[object, ...],
    first_period_col: int,
) -> int:
    """Return the rightmost non-period column index before first_period_col."""
    for c in range(first_period_col - 1, -1, -1):
        if c < len(header_row) and _norm_text(header_row[c]):
            return c
    return 0


def _collect_period_errors(
    header_row: tuple[object, ...],
    period_cols: dict[int, tuple[str, object]],
    first_period_col: int,
    sheet_name: str,
) -> list[ParserError]:
    """Emit PeriodUnparseable errors for year-like header cells that didn't parse."""
    errors: list[ParserError] = []
    for col_idx in range(first_period_col, len(header_row)):
        if col_idx in period_cols:
            continue
        cell_text = _norm_text(header_row[col_idx] if col_idx < len(header_row) else None)
        if not cell_text:
            continue
        if re.search(r"\b(20\d{2}|19\d{2})\b", cell_text):
            errors.append(
                ParserError(
                    error_class="PeriodUnparseable",
                    error_detail=(
                        f"sheet={sheet_name!r} col={col_idx}: "
                        f"period header {cell_text!r} could not be parsed; column skipped"
                    ),
                    source_excerpt=cell_text,
                )
            )
    return errors


def _resolve_unit(
    unit_hint: str | None,
    label_raw: str,
    row_idx: int,
    slug: str,
    sheet_name: str,
) -> tuple[str, ParserError | None]:
    """Return (canonical_unit, optional_UnitAmbiguous_error)."""
    if unit_hint is not None:
        return unit_hint, None
    detected = _detect_unit_from_text(label_raw)
    if detected:
        return detected, None
    err = ParserError(
        error_class="UnitAmbiguous",
        error_detail=(
            f"sheet={sheet_name!r} row={row_idx} slug={slug!r}: "
            f"unit not resolved; literal label used as unit"
        ),
        source_excerpt=label_raw,
    )
    return label_raw, err


def _build_draft(
    period_type: str,
    period_meta: object,
    row_unit: str,
    slug: str,
    value: float,
    row_idx: int,
    col_idx: int,
    label_raw: str,
    sheet_name: str,
) -> tuple[StagingRowDraft | None, ParserError | None]:
    """Convert a single (period, value) cell into a draft or a typed error."""
    try:
        if period_type == "annual":
            fy_bs, fy_ad = period_meta  # type: ignore[misc]
            draft = _annual_fy_to_draft_fields(
                fy_bs=fy_bs, fy_ad=fy_ad, unit=row_unit, slug=slug, value=value
            )
        else:
            bs_month, bs_year = period_meta  # type: ignore[misc]
            draft = _monthly_bs_to_draft_fields(
                bs_month=bs_month, bs_year=bs_year, unit=row_unit, slug=slug, value=value
            )
    except (ValueError, KeyError) as exc:
        err = ParserError(
            error_class="PeriodUnparseable",
            error_detail=(
                f"sheet={sheet_name!r} row={row_idx} col={col_idx}: "
                f"period conversion failed: {exc}"
            ),
            source_excerpt=label_raw,
        )
        return None, err
    return draft, None


_SKIP_LABELS: Final[frozenset[str]] = frozenset(
    {"total", "subtotal", "sub-total", "grand total", "memo"}
)


def _parse_data_rows(
    rows: list[tuple[object, ...]],
    header_row_idx: int,
    label_col_idx: int,
    period_cols: dict[int, tuple[str, object]],
    unit_hint: str | None,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Iterate data rows (after header) and emit staging drafts."""
    staging: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    seen_slugs: set[str] = set()

    for row_idx in range(header_row_idx + 1, len(rows)):
        row = rows[row_idx]
        if label_col_idx >= len(row):
            continue
        label_raw = _norm_text(row[label_col_idx])
        if not label_raw or label_raw.lower() in _SKIP_LABELS:
            continue

        slug = _slugify(label_raw)
        if slug in seen_slugs:
            slug = f"{slug}-r{row_idx}"
        seen_slugs.add(slug)

        row_unit, unit_err = _resolve_unit(unit_hint, label_raw, row_idx, slug, sheet_name)
        if unit_err:
            errors.append(unit_err)

        for col_idx, (period_type, period_meta) in period_cols.items():
            if col_idx >= len(row):
                continue
            value = _safe_float(row[col_idx])
            if value is None:
                continue
            draft, period_err = _build_draft(
                period_type, period_meta, row_unit, slug, value,
                row_idx, col_idx, label_raw, sheet_name,
            )
            if period_err:
                errors.append(period_err)
            elif draft is not None:
                staging.append(draft)

    return staging, errors


def _parse_sheet(
    ws: object,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Parse one DNE worksheet (wide format) into staging rows + errors."""
    rows: list[tuple[object, ...]] = list(ws.iter_rows(values_only=True))  # type: ignore[attr-defined]
    if not rows:
        return [], []

    unit_hint = _scan_unit_hint(rows, sheet_name)
    header_row_idx, period_cols = _detect_header(rows)
    if header_row_idx is None or not period_cols:
        # Emit diagnostic if there are AD-year-like FY tokens in preamble rows
        # (e.g. "2021/22" or "2022/23R") — these are AD-fiscal-year files that
        # the parser does not yet handle. This makes the incompatibility explicit
        # rather than silently producing NoDataExtracted.
        ad_year_tokens: list[str] = []
        for row in rows[:_PREAMBLE_SCAN_ROWS]:
            for cell in row:
                if cell is None:
                    continue
                text = _norm_text(cell)
                # Match AD-year FY labels ("2022/23R"), bare AD year integers
                # (2001, 2002...), or integer AD years in cell numeric values.
                cell_int = (
                    int(cell)  # type: ignore[call-overload]
                    if isinstance(cell, int | float) and cell == int(cell)  # type: ignore[call-overload]
                    else None
                )
                is_ad_int = (
                    cell_int is not None
                    and _AD_YEAR_INT_MIN <= cell_int <= _AD_YEAR_INT_MAX
                )
                if is_ad_int or re.search(
                    r"\b(20\d{2}|19\d{2})\s*[/\-]\s*\d{2}[RPEQrpeq]?\b", text
                ):
                    ad_year_tokens.append(text if text else str(cell))
        if ad_year_tokens:
            sample = ", ".join(dict.fromkeys(ad_year_tokens[:3]))
            return [], [
                ParserError(
                    error_class="PeriodUnparseable",
                    error_detail=(
                        f"sheet={sheet_name!r}: no BS fiscal-year header found; "
                        f"AD-calendar-year tokens detected (e.g. {sample!r}) — "
                        f"this sheet uses AD fiscal years which are out of scope"
                    ),
                    source_excerpt=sample,
                )
            ]
        return [], []

    first_period_col = min(period_cols.keys())
    header_row = rows[header_row_idx]
    label_col_idx = _find_label_col(header_row, first_period_col)
    period_errors = _collect_period_errors(header_row, period_cols, first_period_col, sheet_name)

    staging, data_errors = _parse_data_rows(
        rows, header_row_idx, label_col_idx, period_cols, unit_hint, sheet_name
    )
    return staging, period_errors + data_errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse a DNE XLSX file into ``StagingRowDraft`` rows.

    Arguments:
        source_document_path: filesystem path to the ``.xlsx`` file.
        source_document_id: opaque UUID threaded through to the orchestrator;
            not embedded in rows (the ingest layer handles FK wiring).

    Returns:
        ``ParserResult`` — never raises on bad data.
    """
    _ = source_document_id  # reserved for future provenance embedding

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
        wb = openpyxl.load_workbook(
            filename=str(path), read_only=True, data_only=True
        )
    except (OSError, KeyError, ValueError, Exception) as exc:  # noqa: BLE001
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

    all_staging: list[StagingRowDraft] = []
    all_errors: list[ParserError] = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_staging, sheet_errors = _parse_sheet(ws, sheet_name)
        all_staging.extend(sheet_staging)
        all_errors.extend(sheet_errors)

    if not all_staging:
        all_errors.append(
            ParserError(
                error_class="Other",
                error_detail="NoDataExtracted: no staging rows produced from any sheet",
            )
        )
        return ParserResult(
            status="partial",
            parser_version=PARSER_VERSION,
            staging_rows=[],
            errors=all_errors,
        )

    status: ParserStatus = "partial" if all_errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=all_staging,
        errors=all_errors,
    )


# ---------------------------------------------------------------------------
# CLI entrypoint (orchestrator contract — mirror of nrb_cmefs)
# ---------------------------------------------------------------------------


def _main() -> None:
    """Argv: ``parser.py <source_document_path> <source_document_id>``.

    Writes ``dataclasses.asdict(result)`` JSON to stdout (ISO-8601 datetimes).
    Exit codes: 0 = ran (status may be failure), 2 = usage error.
    """
    if len(sys.argv) != 3:  # noqa: PLR2004
        sys.stderr.write(
            "usage: parser.py <source_document_path> <source_document_id>\n"
        )
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    payload = asdict(result)
    for row in payload.get("staging_rows", []):
        for key in (
            "reporting_period_ad_start",
            "reporting_period_ad_end",
            "publication_date_ad",
        ):
            val = row.get(key)
            if isinstance(val, datetime):
                row[key] = val.isoformat()

    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    _main()
