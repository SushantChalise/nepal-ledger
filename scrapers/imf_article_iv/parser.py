"""IMF Article IV Consultation — Nepal Selected Economic Indicators parser.

Source: IMF Article IV consultation reports for Nepal (annual).
Source id: ``imf-article-iv``. Ingestion mode: ``manual_upload``.

Extracts the "Selected Economic Indicators" appendix table that appears in
every Article IV report. Emits six indicator pairs — each indicator has an
``-actual`` slug (historical outturns, no column marker) and a ``-forecast``
slug (projections, columns marked E/Est/P/Proj or equivalent). This split
ensures projections never mix with confirmed outturns in
``approved_indicator_values``.

Indicators extracted:
    Actuals   → slug suffix ``-actual``
    Forecasts → slug suffix ``-forecast``

    ┌─────────────────────────────────────┬────────────────┐
    │ Indicator                           │ Unit           │
    ├─────────────────────────────────────┼────────────────┤
    │ Real GDP growth                     │ percent        │
    │ CPI inflation (annual average)      │ percent        │
    │ Overall fiscal balance (% of GDP)   │ percent_gdp    │
    │ Current account balance (% of GDP)  │ percent_gdp    │
    │ Public sector / govt debt (% of GDP)│ percent_gdp    │
    │ Gross official reserves (months imp)│ months         │
    └─────────────────────────────────────┴────────────────┘

Period:
    Nepal fiscal year (mid-July → mid-July). Column header ``"2023/24"``
    maps to BS 2080/81 (AD lead year + 57). Period bounds: mid-Shrawan
    (≈15 Jul) .. mid-Ashadh (≈15 Jun) via ``_common.periods.mid_month_ad``.
    Forecast rows use identical period bounds but the ``-forecast`` slug
    marks them as projections.

Table detection:
    Scans every page for the anchor phrase "selected economic indicators".
    On candidate pages, calls ``pdfplumber.extract_tables()`` and selects
    the table whose header row has the most parseable fiscal-year columns.

Column-marker classification:
    ● No marker  → actual  (historical outturn)
    ● E, Est     → estimate → treated as forecast (not yet finalised)
    ● P, Proj    → projection → forecast
    ● e, p, f    → same as above (lower-case variants some editions use)
    Marker is recorded in ``parser_notes`` alongside the report year.

Report-year extraction:
    Tries to find "© YYYY International Monetary Fund" or
    "IMF Country Report No. YY/" in the first 5 pages. Falls back to
    file-name year if present. Used in ``parser_notes`` for traceability;
    does not affect indicator values.

Confidence: A — official IMF primary assessment.
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
SOURCE_ID: Final[str] = "imf-article-iv"
_CONFIDENCE: Final[str] = "A"

# Nepal FY column header: optional "FY" prefix, 4-digit year, "/" or "-",
# 2-or-4 digit end year, optional projection marker.
_FY_COL_RE: Final = re.compile(
    r"(?:FY\s*)?(\d{4})[/\-](\d{2,4})\s*([A-Za-z.]*)",
    re.IGNORECASE,
)
# Forecast-marker tokens (lower-cased).
_FORECAST_MARKERS: Final[frozenset[str]] = frozenset(
    {"e", "est", "p", "proj", "projection", "f", "fct", "forecast"}
)
# Report-year extraction: "© 2024 International Monetary Fund"
_COPYRIGHT_YEAR_RE: Final = re.compile(r"©\s*(\d{4})\s*International Monetary Fund")
# "IMF Country Report No. 24/" → extract 2-digit year
_REPORT_NO_RE: Final = re.compile(r"Country Report No\.\s*(\d{2})/", re.IGNORECASE)
# Anchor phrase for the target table section.
_ANCHOR_RE: Final = re.compile(r"selected\s+economic\s+indicators", re.IGNORECASE)
# Minimum parseable FY columns in a table header to qualify as the target table.
_MIN_FY_COLS: Final[int] = 3


# ──────────────────────────────────────────────────────────────────────────────
# Row-kind registry
# ──────────────────────────────────────────────────────────────────────────────

RowKind = Literal[
    "gdp_real_growth",
    "cpi_inflation_avg",
    "fiscal_balance",
    "current_account",
    "public_debt",
    "gross_reserves_months",
]

_SLUG_MAP: Final[dict[RowKind, tuple[str, str]]] = {
    "gdp_real_growth": ("imf-gdp-real-growth-actual", "imf-gdp-real-growth-forecast"),
    "cpi_inflation_avg": ("imf-cpi-inflation-avg-actual", "imf-cpi-inflation-avg-forecast"),
    "fiscal_balance": (
        "imf-fiscal-balance-pct-gdp-actual",
        "imf-fiscal-balance-pct-gdp-forecast",
    ),
    "current_account": (
        "imf-current-account-pct-gdp-actual",
        "imf-current-account-pct-gdp-forecast",
    ),
    "public_debt": (
        "imf-public-debt-pct-gdp-actual",
        "imf-public-debt-pct-gdp-forecast",
    ),
    "gross_reserves_months": (
        "imf-gross-reserves-months-actual",
        "imf-gross-reserves-months-forecast",
    ),
}

_UNIT_MAP: Final[dict[RowKind, str]] = {
    "gdp_real_growth": "percent",
    "cpi_inflation_avg": "percent",
    "fiscal_balance": "percent_gdp",
    "current_account": "percent_gdp",
    "public_debt": "percent_gdp",
    "gross_reserves_months": "months",
}


def _classify_row(label: str) -> RowKind | None:
    """Map a (normalised) row label to its RowKind, or None if not a target."""
    lbl = " ".join(label.lower().split())
    # Gross reserves (months) — explicit month/import sub-row ("In months of imports")
    # and the parent row with "reserves" + "months" both map here.
    if "month" in lbl and "import" in lbl:
        return "gross_reserves_months"
    if "reserve" in lbl and "month" in lbl:
        return "gross_reserves_months"
    if "official reserve" in lbl and "month" in lbl:
        return "gross_reserves_months"
    if "real gdp growth" in lbl or ("gdp growth" in lbl):
        return "gdp_real_growth"
    if ("cpi" in lbl and "inflation" in lbl) or "consumer price inflation" in lbl:
        return "cpi_inflation_avg"
    if "headline inflation" in lbl or ("inflation" in lbl and ("average" in lbl or "avg" in lbl)):
        return "cpi_inflation_avg"
    if "fiscal balance" in lbl or "overall balance" in lbl or "government balance" in lbl:
        return "fiscal_balance"
    if "current account" in lbl:
        return "current_account"
    if "public sector debt" in lbl or "public debt" in lbl or "central government debt" in lbl or "government debt" in lbl:
        return "public_debt"
    return None


@dataclass(frozen=True)
class _FYCol:
    """Parsed metadata for one fiscal-year data column."""

    col_idx: int
    ad_lead_year: int  # e.g. 2023 for "2023/24"
    is_forecast: bool
    marker: str  # raw marker string, e.g. "E", "P", ""


def _parse_fy_columns(header_row: list[str]) -> list[_FYCol]:
    """Extract _FYCol metadata for every fiscal-year column in the header."""
    cols: list[_FYCol] = []
    for idx, cell in enumerate(header_row):
        m = _FY_COL_RE.match(cell.strip())
        if not m:
            continue
        lead = int(m.group(1))
        if not (2000 <= lead <= 2045):
            continue
        marker = m.group(3).lower().rstrip(".")
        is_fc = marker in _FORECAST_MARKERS
        cols.append(_FYCol(col_idx=idx, ad_lead_year=lead, is_forecast=is_fc, marker=m.group(3)))
    return cols


def _parse_value(raw: str) -> float | None:
    """Parse a numeric cell (may be negative, may have commas). None if blank/dash."""
    s = raw.strip().replace(",", "")
    if s in ("", "-", "--", "–", "—", "N/A", "n/a", "...", "."):
        return None
    # Handle bracketed negatives "(6.2)" → -6.2
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if v == v else None  # reject NaN


def extract_rows_from_table(
    header_row: list[str],
    data_rows: list[list[str]],
    report_context: str,
    publication_date_ad: datetime,
    publication_date_bs: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Core extraction: parse data rows against a header with fiscal-year columns.

    ``report_context`` is a short string embedded in ``parser_notes``
    (e.g. "IMF Article IV 2024") for traceability.

    Returns ``(staging_rows, errors)``. Never raises.
    """
    fy_cols = _parse_fy_columns(header_row)
    if len(fy_cols) < _MIN_FY_COLS:
        return [], [
            ParserError(
                error_class="ColumnMissing",
                error_detail=(
                    f"Expected ≥{_MIN_FY_COLS} fiscal-year columns in header; "
                    f"found {len(fy_cols)}: {header_row!r}"
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

        for fy_col in fy_cols:
            if fy_col.col_idx >= len(raw_row):
                continue
            raw_val = str(raw_row[fy_col.col_idx]) if raw_row[fy_col.col_idx] is not None else ""
            value = _parse_value(raw_val)
            if value is None:
                if raw_val.strip():  # non-empty but unparseable
                    errors.append(
                        ParserError(
                            error_class="ValueUnparseable",
                            error_detail=(
                                f"{kind} col {fy_col.ad_lead_year}/{(fy_col.ad_lead_year+1)%100:02d}"
                                f"{fy_col.marker}: could not parse {raw_val!r}"
                            ),
                            source_excerpt=f"{label} | {raw_val}",
                        )
                    )
                continue

            bs_start = fy_col.ad_lead_year + 57
            period_start = mid_month_ad("Shrawan", bs_start)
            period_end = mid_month_ad("Ashadh", bs_start)
            slug = forecast_slug if fy_col.is_forecast else actual_slug
            marker_note = (
                f"col marker: {fy_col.marker!r}" if fy_col.marker else "no marker (outturn)"
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
    """Try to extract the 4-digit publication year from early pages."""
    for text in pages_text[:5]:
        m = _COPYRIGHT_YEAR_RE.search(text)
        if m:
            return int(m.group(1))
        m2 = _REPORT_NO_RE.search(text)
        if m2:
            return 2000 + int(m2.group(1))
    return None


def _best_table_on_page(page: object) -> tuple[list[list[str]], int] | None:
    """Return (table, fy_col_count) for the table with the most FY columns, or None."""
    tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
    best: tuple[list[list[str]], int] | None = None
    for tbl in tables:
        if not tbl:
            continue
        str_tbl = [[str(c) if c is not None else "" for c in row] for row in tbl]
        fy_count = len(_parse_fy_columns(str_tbl[0]))
        if fy_count >= _MIN_FY_COLS:
            if best is None or fy_count > best[1]:
                best = (str_tbl, fy_count)
    return best


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one IMF Article IV PDF; extract Selected Economic Indicators table.

    Scans every page for the "Selected Economic Indicators" anchor. On
    candidate pages, picks the table with the most fiscal-year columns.
    Emits -actual and -forecast indicator pairs per column marker.

    Status:
      - ``success``: all six indicator kinds found with no errors.
      - ``partial``: some rows extracted, some missing or with errors.
      - ``failure``: no usable table found, or file unreadable.
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
                text = page.extract_text() or ""
                pages_text.append(text)

            report_year = _extract_report_year(pages_text)
            report_context = (
                f"IMF Article IV {report_year}" if report_year else "IMF Article IV (year unknown)"
            )
            pub_year = report_year or datetime.now(UTC).year
            publication_date_ad = datetime(pub_year, 1, 1, tzinfo=UTC)
            publication_date_bs = f"{pub_year - 57} Baisakh 1"

            for page_idx, (page, text) in enumerate(zip(pdf.pages, pages_text, strict=False)):
                if not _ANCHOR_RE.search(text):
                    continue
                result = _best_table_on_page(page)
                if result is None:
                    errors.append(
                        ParserError(
                            error_class="PageLayoutChanged",
                            error_detail=(
                                f"Anchor 'Selected Economic Indicators' found on page {page_idx} "
                                f"but no table with ≥{_MIN_FY_COLS} FY columns extracted"
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
                    "No 'Selected Economic Indicators' table found — the PDF may be image-only, "
                    "or the table heading has changed from the expected anchor phrase."
                ),
            )
        )
        return ParserResult(status="failure", parser_version=PARSER_VERSION, errors=errors)

    # Warn if any of the six kinds produced zero rows (partial coverage).
    found_kinds = {slug.rsplit("-actual", 1)[0].rsplit("-forecast", 1)[0] for row in staging_rows
                   for slug in (row.indicator_slug_raw,)}
    expected_prefixes = {
        "imf-gdp-real-growth",
        "imf-cpi-inflation-avg",
        "imf-fiscal-balance-pct-gdp",
        "imf-current-account-pct-gdp",
        "imf-public-debt-pct-gdp",
        "imf-gross-reserves-months",
    }
    missing = expected_prefixes - found_kinds
    for m_prefix in missing:
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
    """CLI: ``python -m imf_article_iv.parser <path> <source_doc_id>``."""
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
