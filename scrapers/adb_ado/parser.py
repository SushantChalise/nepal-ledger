"""ADB Asian Development Outlook — Nepal Selected Economic Indicators parser.

Source: ADB Asian Development Outlook (ADO), Nepal chapter.
Source id: ``adb-ado-nepal``. Ingestion mode: ``manual_upload``.

Extracts the Selected Economic Indicators summary table from the Nepal
section of the ADB ADO PDF. Emits five indicator pairs (actual + forecast)
— the same -actual/-forecast split used by the IMF Article IV parser
ensures projections never mix with confirmed outturns.

Indicators extracted:
    Actuals   → slug suffix ``-actual``
    Forecasts → slug suffix ``-forecast``

    ┌─────────────────────────────────────┬────────────────┐
    │ Indicator                           │ Unit           │
    ├─────────────────────────────────────┼────────────────┤
    │ Real GDP growth                     │ percent        │
    │ CPI inflation (annual average)      │ percent        │
    │ Fiscal balance (% of GDP)           │ percent_gdp    │
    │ Current account balance (% of GDP)  │ percent_gdp    │
    │ Gross reserves (months of imports)  │ months         │
    └─────────────────────────────────────┴────────────────┘

Period:
    ADB reports Nepal data on the Nepal fiscal year (mid-July → mid-July),
    the same as the IMF. Column "2022/23" → AD lead year 2022 → BS 2079/80.
    Calendar-year columns ("2023", "2024e") are also handled: treated as the
    Nepal FY that starts in that AD year.

Column-marker classification (ADB conventions):
    ● No marker  → actual
    ● e, est     → estimate → treated as forecast
    ● f, fct     → forecast
    ● p, proj    → projection → forecast

Nepal-chapter anchor:
    Searches for "nepal" + "selected economic indicators" in page text;
    falls back to just "selected economic indicators" if the Nepal chapter
    is not separately titled. Picks the table with the most year-like
    column headers.

Confidence: A — official ADB primary assessment.
Versioning: bump PARSER_VERSION on any behaviour change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

import pdfplumber

from _common.periods import (
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
)
from _common.types import (
    ParserError,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "adb-ado-nepal"
_CONFIDENCE: Final[str] = "A"

# Nepal FY column header (ADB may use "2022/23" or "FY2022/23").
_FY_COL_RE: Final = re.compile(
    r"(?:FY\s*)?(\d{4})[/\-](\d{2,4})\s*([A-Za-z.]*)",
    re.IGNORECASE,
)
# Plain calendar year: "2024", "2024e", "2025f"
_CAL_YEAR_RE: Final = re.compile(r"^(20\d{2})\s*([A-Za-z.]*)?$", re.IGNORECASE)
_FORECAST_MARKERS: Final[frozenset[str]] = frozenset(
    {"e", "est", "p", "proj", "f", "fct", "forecast"}
)
_ANCHOR_RE: Final = re.compile(r"selected\s+economic\s+indicators", re.IGNORECASE)
_NEPAL_RE: Final = re.compile(r"\bnepal\b", re.IGNORECASE)
# ADB publication year from cover/header (e.g. "Asian Development Outlook 2024")
_ADO_YEAR_RE: Final = re.compile(r"Asian Development Outlook\s+(\d{4})", re.IGNORECASE)
_COPYRIGHT_YEAR_RE: Final = re.compile(r"©\s*(\d{4})\s*Asian Development Bank", re.IGNORECASE)
_MIN_YEAR_COLS: Final[int] = 2


# ──────────────────────────────────────────────────────────────────────────────
# Row-kind registry
# ──────────────────────────────────────────────────────────────────────────────

RowKind = Literal[
    "gdp_real_growth",
    "cpi_inflation_avg",
    "fiscal_balance",
    "current_account",
    "gross_reserves_months",
]

_SLUG_MAP: Final[dict[RowKind, tuple[str, str]]] = {
    "gdp_real_growth": ("adb-ado-gdp-real-growth-actual", "adb-ado-gdp-real-growth-forecast"),
    "cpi_inflation_avg": (
        "adb-ado-cpi-inflation-avg-actual",
        "adb-ado-cpi-inflation-avg-forecast",
    ),
    "fiscal_balance": (
        "adb-ado-fiscal-balance-pct-gdp-actual",
        "adb-ado-fiscal-balance-pct-gdp-forecast",
    ),
    "current_account": (
        "adb-ado-current-account-pct-gdp-actual",
        "adb-ado-current-account-pct-gdp-forecast",
    ),
    "gross_reserves_months": (
        "adb-ado-gross-reserves-months-actual",
        "adb-ado-gross-reserves-months-forecast",
    ),
}

_UNIT_MAP: Final[dict[RowKind, str]] = {
    "gdp_real_growth": "percent",
    "cpi_inflation_avg": "percent",
    "fiscal_balance": "percent_gdp",
    "current_account": "percent_gdp",
    "gross_reserves_months": "months",
}


def _classify_row(label: str) -> RowKind | None:
    """Map a normalised row label to its RowKind, or None."""
    lbl = " ".join(label.lower().split())
    # Reserves (months) before plain "reserves".
    if "reserve" in lbl and "month" in lbl:
        return "gross_reserves_months"
    if "gdp growth" in lbl:
        return "gdp_real_growth"
    if "inflation" in lbl and ("average" in lbl or "avg" in lbl or "annual" in lbl):
        return "cpi_inflation_avg"
    if "cpi" in lbl and "inflation" in lbl:
        return "cpi_inflation_avg"
    # ADB ADO summary often has a bare "Inflation" row for annual CPI.
    if lbl.strip() in ("inflation", "inflation (%)", "inflation (% change)"):
        return "cpi_inflation_avg"
    if "fiscal balance" in lbl or "overall balance" in lbl or "government balance" in lbl:
        return "fiscal_balance"
    if "current account" in lbl:
        return "current_account"
    return None


@dataclass(frozen=True)
class _YearCol:
    col_idx: int
    ad_lead_year: int  # calendar year or FY lead year
    is_forecast: bool
    marker: str


def _parse_year_columns(header_row: list[str]) -> list[_YearCol]:
    """Parse year column headers — handles both FY and calendar-year notation."""
    cols: list[_YearCol] = []
    for idx, cell in enumerate(header_row):
        raw = cell.strip()
        # Try FY notation first ("2022/23", "FY2022/23P").
        m_fy = _FY_COL_RE.match(raw)
        if m_fy:
            lead = int(m_fy.group(1))
            if 2000 <= lead <= 2045:
                marker = m_fy.group(3).lower().rstrip(".")
                cols.append(
                    _YearCol(
                        col_idx=idx,
                        ad_lead_year=lead,
                        is_forecast=marker in _FORECAST_MARKERS,
                        marker=m_fy.group(3),
                    )
                )
            continue
        # Try calendar year ("2024", "2024e").
        m_cal = _CAL_YEAR_RE.match(raw)
        if m_cal:
            year = int(m_cal.group(1))
            if 2000 <= year <= 2045:
                marker = (m_cal.group(2) or "").lower().rstrip(".")
                cols.append(
                    _YearCol(
                        col_idx=idx,
                        ad_lead_year=year,
                        is_forecast=marker in _FORECAST_MARKERS,
                        marker=m_cal.group(2) or "",
                    )
                )
    return cols


def _parse_value(raw: str) -> float | None:
    s = raw.strip().replace(",", "")
    if s in ("", "-", "--", "–", "—", "N/A", "n/a", "...", "."):
        return None
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def extract_rows_from_table(
    header_row: list[str],
    data_rows: list[list[str]],
    report_context: str,
    publication_date_ad: datetime,
    publication_date_bs: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Core extraction: parse data rows against a header with year columns.

    Handles both FY notation ("2022/23") and calendar year ("2024").
    Returns ``(staging_rows, errors)``. Never raises.
    """
    year_cols = _parse_year_columns(header_row)
    if len(year_cols) < _MIN_YEAR_COLS:
        return [], [
            ParserError(
                error_class="ColumnMissing",
                error_detail=(
                    f"Expected ≥{_MIN_YEAR_COLS} year columns; found {len(year_cols)}: "
                    f"{header_row!r}"
                ),
            )
        ]

    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for raw_row in data_rows:
        if not raw_row:
            continue
        label = str(raw_row[0]) if raw_row[0] is not None else ""
        kind = _classify_row(label)
        if kind is None:
            continue

        actual_slug, forecast_slug = _SLUG_MAP[kind]
        unit = _UNIT_MAP[kind]

        for yr_col in year_cols:
            if yr_col.col_idx >= len(raw_row):
                continue
            raw_val = str(raw_row[yr_col.col_idx]) if raw_row[yr_col.col_idx] is not None else ""
            value = _parse_value(raw_val)
            if value is None:
                if raw_val.strip():
                    errors.append(
                        ParserError(
                            error_class="ValueUnparseable",
                            error_detail=(
                                f"{kind} col {yr_col.ad_lead_year}{yr_col.marker}: "
                                f"could not parse {raw_val!r}"
                            ),
                            source_excerpt=f"{label} | {raw_val}",
                        )
                    )
                continue

            bs_start = yr_col.ad_lead_year + 57
            period_start = mid_month_ad("Shrawan", bs_start)
            period_end = mid_month_ad("Ashadh", bs_start)
            slug = forecast_slug if yr_col.is_forecast else actual_slug
            marker_note = (
                f"col marker: {yr_col.marker!r}" if yr_col.marker else "no marker (outturn)"
            )
            rows.append(
                StagingRowDraft(
                    indicator_slug_raw=slug,
                    value=value,
                    unit=unit,
                    reporting_period_type="annual",
                    reporting_period_bs=f"FY {fiscal_year_label(bs_start)}",
                    reporting_period_ad_start=period_start,
                    reporting_period_ad_end=period_end,
                    publication_date_ad=publication_date_ad,
                    publication_date_bs=publication_date_bs,
                    fiscal_year_bs=fiscal_year_label(bs_start),
                    fiscal_year_ad_label=fiscal_year_ad_label(bs_start),
                    confidence_grade_proposed=_CONFIDENCE,
                    parser_notes=f"{report_context}; {marker_note}",
                )
            )

    return rows, errors


# ──────────────────────────────────────────────────────────────────────────────
# PDF-level helpers
# ──────────────────────────────────────────────────────────────────────────────


def _extract_report_year(pages_text: list[str]) -> int | None:
    for text in pages_text[:5]:
        m = _ADO_YEAR_RE.search(text)
        if m:
            return int(m.group(1))
        m2 = _COPYRIGHT_YEAR_RE.search(text)
        if m2:
            return int(m2.group(1))
    return None


def _best_table_on_page(page: object) -> tuple[list[list[str]], int] | None:
    tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
    best: tuple[list[list[str]], int] | None = None
    for tbl in tables:
        if not tbl:
            continue
        str_tbl = [[str(c) if c is not None else "" for c in row] for row in tbl]
        yr_count = len(_parse_year_columns(str_tbl[0]))
        if yr_count >= _MIN_YEAR_COLS:
            if best is None or yr_count > best[1]:
                best = (str_tbl, yr_count)
    return best


def _is_nepal_page(text: str) -> bool:
    """True if the page text suggests it belongs to the Nepal chapter."""
    return bool(_NEPAL_RE.search(text) and _ANCHOR_RE.search(text))


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one ADB ADO PDF; extract Nepal Selected Economic Indicators table.

    Prefers pages that have both "Nepal" and "Selected Economic Indicators".
    Falls back to any page matching just the anchor if no Nepal-specific page
    is found.

    Status:
      - ``success``: all five indicator kinds found with no errors.
      - ``partial``: some rows extracted; some missing or errors.
      - ``failure``: no usable table, or file unreadable.
    """
    _ = source_document_id

    path = Path(source_document_path)
    if not path.exists():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[ParserError(error_class="Other", error_detail=f"file not found: {path}")],
        )

    pages_text: list[str] = []
    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                pages_text.append(page.extract_text() or "")

            report_year = _extract_report_year(pages_text)
            report_context = (
                f"ADB ADO {report_year}" if report_year else "ADB ADO (year unknown)"
            )
            pub_year = report_year or datetime.now(UTC).year
            publication_date_ad = datetime(pub_year, 1, 1, tzinfo=UTC)
            publication_date_bs = f"{pub_year - 57} Baisakh 1"

            # Prefer Nepal-specific anchor pages; fall back to any anchor page.
            candidate_pages = [
                (i, p)
                for i, (p, t) in enumerate(zip(pdf.pages, pages_text, strict=False))
                if _is_nepal_page(t)
            ]
            if not candidate_pages:
                candidate_pages = [
                    (i, p)
                    for i, (p, t) in enumerate(zip(pdf.pages, pages_text, strict=False))
                    if _ANCHOR_RE.search(t)
                ]

            for page_idx, page in candidate_pages:
                result = _best_table_on_page(page)
                if result is None:
                    errors.append(
                        ParserError(
                            error_class="PageLayoutChanged",
                            error_detail=(
                                f"Anchor found on page {page_idx} but no table with "
                                f"≥{_MIN_YEAR_COLS} year columns extracted"
                            ),
                        )
                    )
                    continue
                tbl, _ = result
                new_rows, new_errors = extract_rows_from_table(
                    header_row=tbl[0],
                    data_rows=tbl[1:],
                    report_context=report_context,
                    publication_date_ad=publication_date_ad,
                    publication_date_bs=publication_date_bs,
                )
                staging_rows.extend(new_rows)
                errors.extend(new_errors)

    except (OSError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdfplumber could not read {path.name}: {exc}",
                )
            ],
        )

    if not staging_rows:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    "No Nepal Selected Economic Indicators table found — PDF may be image-only, "
                    "the Nepal section may have no parseable table, or the anchor phrase changed."
                ),
            )
        )
        return ParserResult(status="failure", parser_version=PARSER_VERSION, errors=errors)

    found_prefixes = {
        row.indicator_slug_raw.rsplit("-actual", 1)[0].rsplit("-forecast", 1)[0]
        for row in staging_rows
    }
    expected_prefixes = {
        "adb-ado-gdp-real-growth",
        "adb-ado-cpi-inflation-avg",
        "adb-ado-fiscal-balance-pct-gdp",
        "adb-ado-current-account-pct-gdp",
        "adb-ado-gross-reserves-months",
    }
    for m_prefix in expected_prefixes - found_prefixes:
        errors.append(
            ParserError(
                error_class="ColumnMissing",
                error_detail=(
                    f"Indicator group '{m_prefix}' not found in table — "
                    f"row label may have changed in this edition"
                ),
            )
        )

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def _main() -> None:
    """CLI: ``python -m adb_ado.parser <path> <source_doc_id>``."""
    import json
    import sys
    from dataclasses import asdict

    if len(sys.argv) != 3:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    payload = asdict(result)
    for row in payload.get("staging_rows", []):
        for key in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            val = row.get(key)
            if isinstance(val, datetime):
                row[key] = val.isoformat()
    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    _main()
