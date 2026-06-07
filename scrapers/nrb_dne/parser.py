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

Period detection (four layouts, tried in priority order):
    1. Long panel — FY label in col 0 (sparse, forward-filled) + AD month name in
       col 1 + numeric value columns to the right (Exchange-rate).  Detected FIRST
       because the standard header detector would otherwise mis-claim it.
    2. Standard wide — indicators as rows, fiscal-period labels as column headers.
       Annual FY: "2079/80", "2079-80" (BS) or "2022/23" (AD, converted via the
       +57 offset, ADR-0013).  Monthly BS: "<bs_month_name> <bs_year>", e.g.
       "Shrawan 2082".
    3. Two-row monthly header — a row of integer AD YEARS over a row of AD MONTH
       names (Foreign-exchange-reserves).  Each (year, month) column is a monthly
       period; the sparse year row is forward-filled.  A repeated (year, month)
       column (source mislabel) keeps both values, flags them, and emits one
       ``PeriodAmbiguous``.
    4. Transposed — AD MONTH names as column headers with integer AD YEARS as row
       labels down col 0 (Tourist-arrivals); long-formatted to one row per
       year×month.

    AD calendar months are mapped to the BS month containing their 15th (a
    documented mid-month approximation, the exact inverse of
    ``_common.periods._BS_MONTH_TO_AD_MONTH``); every such row is flagged in
    ``parser_notes`` and the AD month span stored is the exact Gregorian month.
    Unparseable period column headers → ``PeriodUnparseable`` error; the column is
    skipped.  Sheets matching no layout fail loud with ``PeriodUnparseable`` when
    year-like tokens are present (never a silent drop).

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
    fiscal_year_label,
    mid_month_ad,
)
from _common.types import (
    ParserError,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.4.0"
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
# (≤2039). The two ranges cannot overlap for any data this project ingests:
# BS 2040 ≈ AD 1983; AD 2039 is the future. ADR-0013.
_BS_YEAR_MIN: Final[int] = 2040

# Maximum AD fiscal-year start accepted for AD→BS conversion (exclusive upper
# bound = _BS_YEAR_MIN - 1). Any lead year ≥ _BS_YEAR_MIN is treated as BS.
_AD_YEAR_FY_MAX: Final[int] = _BS_YEAR_MIN - 1  # 2039

# AD Gregorian month-name → month-number (1-12). NRB month-header rows mix
# abbreviated and full English names ("Aug" vs "August", "Sept" vs "September",
# "March", "April", "June", "July"), so every common variant is mapped. Keys are
# lowercased before lookup.  Used by the integer-year+monthly, long-panel, and
# transposed AD layouts (ADR-0013 follow-up; the wide BS layout uses BS months).
_AD_MONTH_NAME_TO_NUM: Final[dict[str, int]] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# AD Gregorian month-number → BS month name. This is the exact inverse of
# `_common.periods._BS_MONTH_TO_AD_MONTH` and round-trips with `mid_month_ad`:
# the BS month listed for AD month M is the one whose mid-point (the 15th of M)
# falls inside it. This is a DOCUMENTED MID-MONTH APPROXIMATION — an AD calendar
# month overlaps two BS months (e.g. AD January spans the tail of Poush and the
# head of Magh); we attribute the whole AD month to the BS month containing its
# 15th. The TS validation layer refines to exact BS-calendar boundaries. We never
# fabricate a period: the BS label stored is a real, defensible monthly period,
# explicitly flagged via `parser_notes`. Kept local (not in _common) per the
# scope fence; mirrors the same mid-July break-month rule as `mid_month_ad`.
_AD_MONTH_NUM_TO_BS_MONTH: Final[dict[int, BsMonth]] = {
    1: "Magh",
    2: "Falgun",
    3: "Chait",
    4: "Baisakh",
    5: "Jestha",
    6: "Ashadh",
    7: "Shrawan",
    8: "Bhadra",
    9: "Ashwin",
    10: "Kartik",
    11: "Mangsir",
    12: "Poush",
}

# Mirror of `_common.periods._AD_YEAR_BREAK_MONTH`: AD months ≥ July belong to BS
# year (ad_year + 57); months < July belong to BS year (ad_year + 56).
_AD_YEAR_BREAK_MONTH: Final[int] = 7

# Fiscal-year offset between BS and AD lead years (ADR-0013): BS = AD + 57.
_BS_AD_FY_OFFSET: Final[int] = 57

# Note appended to every monthly draft built from an AD calendar month, recording
# the mid-month BS approximation so the validator (and any auditor) sees it.
_AD_MONTHLY_APPROX_NOTE: Final[str] = (
    "AD calendar month mapped to BS month containing its 15th (mid-month "
    "approximation per ADR-0013 follow-up); validator refines exact BS boundaries"
)

# Minimum number of integer-year cells a row must contain to be considered the
# "years" row of a two-row (year-over-month) monthly header.
_MIN_YEAR_HEADER_CELLS: Final[int] = 3

# Minimum number of AD-month-name cells a row must contain to be considered the
# "months" row of a two-row monthly header, OR the column header of a transposed
# (years-as-rows) sheet.
_MIN_MONTH_HEADER_CELLS: Final[int] = 6

# Labels that mark a non-period column in transposed/long layouts (annual totals,
# the row-label header itself). Lowercased before comparison.
_NON_MONTH_COL_LABELS: Final[frozenset[str]] = frozenset(
    {"total", "annual", "annual total", "year total", "sum", "year"}
)

# Month-1-of-fiscal-year (Shrawan = AD July) — used to derive the FY a monthly
# AD period belongs to when no explicit FY column is present.
_FY_FIRST_AD_MONTH: Final[int] = 7

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

    Accepts BS fiscal years (lead year ≥ 2040) and AD fiscal years (lead year
    ≤ 2039), as per ADR-0013.  The magnitude heuristic is deterministic: the
    two ranges cannot overlap for any data this project ingests.

    BS inputs (lead ≥ 2040):
    - "2079/80", "2079-80"            — standard BS format
    - "2079/80R", "2079/80P"          — NRB revised/provisional suffix
    - "2079/2080"                     — 4-digit tail (some SITC sheets)

    AD inputs (lead ≤ 2039) — converted to BS via the +57 fiscal-year offset:
    - "2022/23", "2022/23R"           — plain AD FY (External Sector files)
    - "(2071-72) 2014/15"             — bracketed BS label + AD year prefix
      (The bracketed part is stripped by the regex; the AD lead year is used.)

    The AD→BS conversion is done via ``fiscal_year_label(ad_start + 57)``
    which mirrors ``fiscal_year_ad_label`` in reverse.  Known pair:
    AD 2022/23 → BS 2079/80; AD 2023/24 → BS 2080/81.

    Returns None if the regex does not match or the tail is inconsistent.
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

    if start >= _BS_YEAR_MIN:
        # BS fiscal year — keep as-is, derive AD label from periods helper.
        fy_bs = f"{start}/{expected_tail:02d}"
        fy_ad = fiscal_year_ad_label(start)
        return fy_bs, fy_ad

    if start <= _AD_YEAR_FY_MAX:
        # AD fiscal year — convert to BS by adding 57 to the lead year.
        # The Nepal fiscal year runs mid-July to mid-July, so AD YYYY/(YY+1)
        # corresponds 1:1 to BS (YYYY+57)/((YYYY+58)%100).  ADR-0013.
        bs_start = start + 57
        fy_bs = fiscal_year_label(bs_start)
        fy_ad = f"{start}/{expected_tail:02d}"
        return fy_bs, fy_ad

    return None


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


def _parse_ad_month_name(label: str) -> int | None:
    """Parse an AD Gregorian month name → month number (1-12), or None.

    Accepts NRB's mixed abbreviated/full English month names (case-insensitive,
    surrounding whitespace stripped): "Aug", "August", "Sept", "March", "June".
    """
    key = label.strip().lower()
    return _AD_MONTH_NAME_TO_NUM.get(key)


def _ad_month_to_bs(ad_year: int, ad_month: int) -> tuple[BsMonth, int]:
    """Map an AD (year, month) to its (BS month, BS year) — mid-month approximation.

    The BS month is the one containing the 15th of the AD month (the exact inverse
    of `_common.periods._BS_MONTH_TO_AD_MONTH`); the BS year follows the same
    mid-July break rule as `mid_month_ad`. Documented approximation per ADR-0013
    follow-up — see ``_AD_MONTH_NUM_TO_BS_MONTH``. Never fabricates: the result is
    a real BS month/year pair, and callers flag the approximation in parser_notes.
    """
    bs_month = _AD_MONTH_NUM_TO_BS_MONTH[ad_month]
    bs_year = (
        ad_year + _BS_AD_FY_OFFSET
        if ad_month >= _AD_YEAR_BREAK_MONTH
        else ad_year + _BS_AD_FY_OFFSET - 1
    )
    return bs_month, bs_year


def _ad_monthly_to_draft_fields(
    ad_year: int,
    ad_month: int,
    unit: str,
    slug: str,
    value: float,
    extra_note: str | None = None,
) -> StagingRowDraft:
    """Build a monthly StagingRowDraft from an AD (Gregorian) year+month cell.

    The AD month span is exact (1st → 28th of the Gregorian month — a safe lower
    bound the validator widens). Only the BS *label* is the mid-month
    approximation, flagged in ``parser_notes`` via ``_AD_MONTHLY_APPROX_NOTE``.
    The fiscal year is derived from the AD month: AD July (Shrawan) begins FY
    ``ad_year/ad_year+1``; AD Jan–Jun belong to the FY that began the prior July.

    ``extra_note`` is appended to ``parser_notes`` (used to flag source-level
    quirks such as a repeated (year, month) column in the header).
    """
    bs_month, bs_year = _ad_month_to_bs(ad_year, ad_month)
    ad_start = datetime(ad_year, ad_month, 1, tzinfo=UTC)
    ad_end = datetime(ad_year, ad_month, 28, tzinfo=UTC)
    # FY lead (AD): months Jul..Dec → this AD year; Jan..Jun → previous AD year.
    fy_ad_start = ad_year if ad_month >= _FY_FIRST_AD_MONTH else ad_year - 1
    fy_ad = f"{fy_ad_start}/{(fy_ad_start + 1) % 100:02d}"
    bs_fy_start = fy_ad_start + _BS_AD_FY_OFFSET
    fy_bs = fiscal_year_label(bs_fy_start)
    notes = (
        _AD_MONTHLY_APPROX_NOTE
        if extra_note is None
        else f"{_AD_MONTHLY_APPROX_NOTE}; {extra_note}"
    )
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
        parser_notes=notes,
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


def _as_year_int(cell: object) -> int | None:
    """Return the AD year an integer-ish cell encodes, or None.

    Accepts ints/floats (2001, 2001.0) and digit strings ("2001"). Bounded to the
    AD calendar-year window so stray numeric data is never mistaken for a year.
    """
    if isinstance(cell, bool):  # bool is an int subclass — exclude explicitly
        return None
    if isinstance(cell, int | float):
        if cell != int(cell):
            return None
        n = int(cell)
    else:
        s = _norm_text(cell)
        if not s.isdigit():
            return None
        n = int(s)
    if _AD_YEAR_INT_MIN <= n <= _AD_YEAR_INT_MAX:
        return n
    return None


def _row_year_cols(row: tuple[object, ...]) -> dict[int, int]:
    """Map column index → AD year for every integer-AD-year cell in a row."""
    return {ci: y for ci, cell in enumerate(row) if (y := _as_year_int(cell)) is not None}


def _row_month_cols(row: tuple[object, ...]) -> dict[int, int]:
    """Map column index → AD month number for every AD-month-name cell in a row."""
    out: dict[int, int] = {}
    for ci, cell in enumerate(row):
        if cell is None:
            continue
        m = _parse_ad_month_name(_norm_text(cell))
        if m is not None:
            out[ci] = m
    return out


def _detect_year_month_header(
    rows: list[tuple[object, ...]],
) -> tuple[int, dict[int, tuple[int, int]]] | None:
    """Detect a two-row header: a row of integer AD YEARS directly above a row of
    AD MONTH names (the Foreign-exchange-reserves layout).

    Returns ``(month_row_idx, {col_idx: (ad_year, ad_month)})`` or None.

    Strategy: scan for an adjacent (year_row, month_row) pair within the preamble.
    The year row is sparse — a year value typically appears only in the first
    column of each year's month-block (e.g. 2001 over "Aug", blanks over the rest)
    OR repeats per month. We forward-fill the year across the month columns so each
    monthly column gets the most recent year seen at or before it.
    """
    scan = min(len(rows) - 1, _PREAMBLE_SCAN_ROWS)
    for ri in range(scan):
        year_cols = _row_year_cols(rows[ri])
        if len(year_cols) < _MIN_YEAR_HEADER_CELLS:
            continue
        month_cols = _row_month_cols(rows[ri + 1])
        if len(month_cols) < _MIN_MONTH_HEADER_CELLS:
            continue
        # Forward-fill the year across month columns. Walk columns left→right;
        # carry the last year seen in the year row at or before this column.
        first_year_col = min(year_cols)
        paired: dict[int, tuple[int, int]] = {}
        current_year: int | None = None
        max_col = max(*year_cols, *month_cols)
        for ci in range(first_year_col, max_col + 1):
            if ci in year_cols:
                current_year = year_cols[ci]
            if ci in month_cols and current_year is not None:
                paired[ci] = (current_year, month_cols[ci])
        if len(paired) >= _MIN_MONTH_HEADER_CELLS:
            return ri + 1, paired
    return None


def _parse_year_month_layout(
    rows: list[tuple[object, ...]],
    month_row_idx: int,
    paired: dict[int, tuple[int, int]],
    unit_hint: str | None,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Emit one monthly draft per (indicator-row × paired year/month column).

    NRB occasionally ships a repeated (year, month) column in the header (e.g.
    two "Oct 2025" columns with *different* values — a source-side mislabel we
    cannot disambiguate without fabricating). We never drop either value: both
    rows are emitted, the duplicate-period columns are flagged in ``parser_notes``,
    and a single ``PeriodAmbiguous`` error surfaces the issue for the validator.
    """
    staging: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    seen_slugs: set[str] = set()
    first_period_col = min(paired)

    # Identify columns whose (year, month) repeats an earlier column (left→right).
    dup_cols: set[int] = set()
    seen_periods: set[tuple[int, int]] = set()
    for col_idx in sorted(paired):
        ym = paired[col_idx]
        if ym in seen_periods:
            dup_cols.add(col_idx)
        else:
            seen_periods.add(ym)
    if dup_cols:
        dup_sample = ", ".join(
            dict.fromkeys(
                f"{_AD_MONTH_NUM_TO_BS_MONTH[paired[c][1]]} (AD {paired[c][0]}-{paired[c][1]:02d})"
                for c in sorted(dup_cols)
            )
        )
        errors.append(
            ParserError(
                error_class="PeriodAmbiguous",
                error_detail=(
                    f"sheet={sheet_name!r}: header has repeated (year, month) "
                    f"columns ({dup_sample}); both values emitted and flagged — "
                    f"validator must adjudicate the source-side duplicate"
                ),
                source_excerpt=dup_sample,
            )
        )

    for row_idx in range(month_row_idx + 1, len(rows)):
        row = rows[row_idx]
        # Label may sit in col 0 or, for indented sub-items, col 1. Join the
        # non-empty label cells that precede the first period column.
        label_parts = [
            _norm_text(row[c])
            for c in range(min(first_period_col, len(row)))
            if c < len(row) and _norm_text(row[c])
        ]
        label_raw = " ".join(label_parts)
        if not label_raw or label_raw.lower() in _SKIP_LABELS:
            continue

        slug = _slugify(label_raw)
        if slug in seen_slugs:
            slug = f"{slug}-r{row_idx}"
        seen_slugs.add(slug)

        row_unit, unit_err = _resolve_unit(unit_hint, label_raw, row_idx, slug, sheet_name)
        if unit_err:
            errors.append(unit_err)

        for col_idx, (ad_year, ad_month) in paired.items():
            if col_idx >= len(row):
                continue
            value = _safe_float(row[col_idx])
            if value is None:
                continue
            dup_note = (
                f"source header had a repeated column for this (year, month) at "
                f"col {col_idx}; value not dropped"
                if col_idx in dup_cols
                else None
            )
            staging.append(
                _ad_monthly_to_draft_fields(
                    ad_year, ad_month, row_unit, slug, value, extra_note=dup_note
                )
            )
    return staging, errors


def _detect_long_panel(
    rows: list[tuple[object, ...]],
) -> tuple[int, int, int, list[int]] | None:
    """Detect the long-panel layout (Exchange-rate): an AD fiscal-year label in
    col 0 (sparse — present only on the first month of each FY, forward-filled),
    an AD month name in col 1, and numeric value columns to the right.

    Returns ``(first_data_row, fy_col, month_col, value_cols)`` or None.
    """
    fy_col, month_col = 0, 1
    # Find the first data row: col0 parses as an annual FY (AD or BS) and col1 is
    # an AD month name. Scan a generous window past any multi-row header.
    scan = min(len(rows), _PREAMBLE_SCAN_ROWS * 2)
    for ri in range(scan):
        row = rows[ri]
        if len(row) <= month_col:
            continue
        if _parse_annual_fy(_norm_text(row[fy_col])) is None:
            continue
        if _parse_ad_month_name(_norm_text(row[month_col])) is None:
            continue
        # Value columns: every column ≥ 2 that holds a float somewhere in the
        # next few rows. Use this row plus a couple after it as the probe.
        value_cols: list[int] = []
        probe = rows[ri : ri + 4]
        max_col = max(len(r) for r in probe)
        for c in range(month_col + 1, max_col):
            if any(c < len(r) and _safe_float(r[c]) is not None for r in probe):
                value_cols.append(c)
        if value_cols:
            return ri, fy_col, month_col, value_cols
    return None


def _value_col_label(rows: list[tuple[object, ...]], header_rows: int, col: int) -> str:
    """Build a value-column sub-label by joining header cells above a value column.

    The long-panel sheet has a 3-4 row header naming each numeric column
    (e.g. "Month End Buying", "Monthly Average Middle Rate"). We concatenate the
    non-empty header cells in this column to disambiguate the indicator slug.
    """
    parts = [
        _norm_text(rows[r][col])
        for r in range(header_rows)
        if col < len(rows[r]) and _norm_text(rows[r][col])
    ]
    return " ".join(parts)


def _parse_long_panel_layout(
    rows: list[tuple[object, ...]],
    first_data_row: int,
    fy_col: int,
    month_col: int,
    value_cols: list[int],
    unit_hint: str | None,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Long-format the Exchange-rate panel: one monthly draft per (row × value col).

    The FY label in col 0 is forward-filled. Each value column carries its own
    sub-label (from the multi-row header) so distinct series get distinct slugs.
    Rows whose month cell is an aggregate ("Annual Average") are skipped — they
    are not a single calendar month and would corrupt the monthly period.
    """
    staging: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    col_labels = {c: _value_col_label(rows, first_data_row, c) for c in value_cols}
    current_fy_ad: str | None = None
    # Resolve each value column's unit ONCE, and only from a positively-known
    # sheet-level hint. We deliberately do NOT keyword-match the column sub-labels
    # ("Month End Buying", etc.): those contain noise words ("month") that the
    # substring matcher would mis-resolve to a wrong vocab unit. When no hint is
    # known (e.g. an FX-rate panel — there is no controlled-vocab "NPR per USD"
    # unit), we emit one UnitAmbiguous per column and carry the raw sub-label so
    # the validator flags it for human unit assignment — never a silent wrong unit.
    col_units: dict[int, str] = {}
    for col in value_cols:
        sub = col_labels.get(col) or f"col{col}"
        if unit_hint is not None:
            col_units[col] = unit_hint
            continue
        col_units[col] = sub
        errors.append(
            ParserError(
                error_class="UnitAmbiguous",
                error_detail=(
                    f"sheet={sheet_name!r} col={col}: unit not resolved for the "
                    f"long-panel value column; raw column label used as unit"
                ),
                source_excerpt=sub,
            )
        )

    for row_idx in range(first_data_row, len(rows)):
        row = rows[row_idx]
        if fy_col < len(row):
            fy_parsed = _parse_annual_fy(_norm_text(row[fy_col]))
            if fy_parsed is not None:
                current_fy_ad = fy_parsed[1]  # AD label "YYYY/YY"
        if month_col >= len(row):
            continue
        month_text = _norm_text(row[month_col])
        if month_text.lower() in _NON_MONTH_COL_LABELS or "average" in month_text.lower():
            # "Annual Average" / "Monthly Average" aggregate rows — not a month.
            continue
        ad_month = _parse_ad_month_name(month_text)
        if ad_month is None or current_fy_ad is None:
            continue
        ad_year = _fy_label_to_calendar_year(current_fy_ad, ad_month)
        if ad_year is None:
            continue
        for col in value_cols:
            if col >= len(row):
                continue
            value = _safe_float(row[col])
            if value is None:
                continue
            sub = col_labels.get(col) or f"col{col}"
            slug = _slugify(f"{sheet_name} {sub}")
            staging.append(
                _ad_monthly_to_draft_fields(
                    ad_year, ad_month, col_units[col], slug, value
                )
            )
    return staging, errors


def _fy_label_to_calendar_year(fy_ad_label: str, ad_month: int) -> int | None:
    """Resolve the AD calendar year of ``ad_month`` within an AD FY label.

    NRB fiscal year runs mid-July→mid-July. For AD FY "2022/23": months Jul–Dec
    fall in the lead calendar year (2022); months Jan–Jun fall in the trailing
    year (2023). Returns None on a malformed label.
    """
    m = re.match(r"^\s*(\d{4})\s*/\s*(\d{2,4})\s*$", fy_ad_label)
    if not m:
        return None
    lead = int(m.group(1))
    return lead if ad_month >= _FY_FIRST_AD_MONTH else lead + 1


def _detect_transposed(
    rows: list[tuple[object, ...]],
) -> tuple[int, int, dict[int, int]] | None:
    """Detect the transposed layout (Tourist-arrivals): a header row of AD MONTH
    names across columns, with integer AD YEARS as row labels down col 0.

    Returns ``(header_row_idx, year_col, {col_idx: ad_month})`` or None.

    Requires both signals to avoid false positives: (a) ≥6 month-name column
    headers, and (b) the rows beneath carry integer AD years in the label column.
    """
    year_col = 0
    scan = min(len(rows), _PREAMBLE_SCAN_ROWS)
    for ri in range(scan):
        month_cols = _row_month_cols(rows[ri])
        if len(month_cols) < _MIN_MONTH_HEADER_CELLS:
            continue
        # Confirm: at least two data rows below carry an AD year in col 0.
        year_rows = sum(
            1
            for r in rows[ri + 1 : ri + 6]
            if year_col < len(r) and _as_year_int(r[year_col]) is not None
        )
        if year_rows >= 2:  # noqa: PLR2004 — need ≥2 year rows to confirm orientation
            return ri, year_col, month_cols
    return None


def _parse_transposed_layout(
    rows: list[tuple[object, ...]],
    header_row_idx: int,
    year_col: int,
    month_cols: dict[int, int],
    unit_hint: str | None,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Long-format a transposed (years-as-rows, months-as-columns) sheet.

    One monthly draft per (year row × month column). Non-month columns (e.g. an
    annual "Total") are ignored because they are not in ``month_cols``. The
    indicator slug is the sheet name (the sheet is a single indicator surface,
    e.g. "Tourist Arrival"), since the row label is the year, not an indicator.
    """
    staging: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    slug = _slugify(sheet_name)
    row_unit, unit_err = _resolve_unit(unit_hint, sheet_name, header_row_idx, slug, sheet_name)
    if unit_err:
        errors.append(unit_err)

    for row_idx in range(header_row_idx + 1, len(rows)):
        row = rows[row_idx]
        if year_col >= len(row):
            continue
        ad_year = _as_year_int(row[year_col])
        if ad_year is None:
            continue
        for col_idx, ad_month in month_cols.items():
            if col_idx >= len(row):
                continue
            value = _safe_float(row[col_idx])
            if value is None:
                continue
            staging.append(
                _ad_monthly_to_draft_fields(ad_year, ad_month, row_unit, slug, value)
            )
    return staging, errors


def _try_alternate_layouts(
    rows: list[tuple[object, ...]],
    unit_hint: str | None,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]] | None:
    """Try the non-standard AD layouts that only apply once the standard wide
    header detection has already failed:

    1. Two-row integer-year + month header (Foreign-exchange-reserves).
    2. Transposed: years-as-rows, months-as-columns (Tourist-arrivals).

    (The long-panel layout is detected earlier in ``_parse_sheet`` because its
    signature would otherwise be mis-claimed by the standard header detector.)

    Returns the first layout that yields ≥1 staging row, else None (so the caller
    falls through to the fail-loud deferral diagnostic).
    """
    ym = _detect_year_month_header(rows)
    if ym is not None:
        staging, errs = _parse_year_month_layout(rows, ym[0], ym[1], unit_hint, sheet_name)
        if staging:
            return staging, errs

    tp = _detect_transposed(rows)
    if tp is not None:
        staging, errs = _parse_transposed_layout(
            rows, tp[0], tp[1], tp[2], unit_hint, sheet_name
        )
        if staging:
            return staging, errs

    return None


def _defer_unparseable_sheet(
    rows: list[tuple[object, ...]],
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Fail-loud diagnostic for a sheet no layout matched.

    Emits a ``PeriodUnparseable`` error if AD-year-like tokens are present (so an
    unhandled real shape is visible, never silently dropped); otherwise returns
    empty (a genuinely blank sheet → NoDataExtracted at the top level).
    """
    ad_year_tokens: list[str] = []
    for row in rows[:_PREAMBLE_SCAN_ROWS]:
        for cell in row:
            if cell is None:
                continue
            text = _norm_text(cell)
            yint = _as_year_int(cell)
            if yint is not None or re.search(
                r"\b(20\d{2}|19\d{2})\s*[/\-]\s*\d{2}[RPEQrpeq]?\b", text
            ):
                ad_year_tokens.append(text if text else str(cell))
    if ad_year_tokens:
        sample = ", ".join(dict.fromkeys(ad_year_tokens[:3]))
        return [], [
            ParserError(
                error_class="PeriodUnparseable",
                error_detail=(
                    f"sheet={sheet_name!r}: no parseable period header found; "
                    f"year-like tokens detected (e.g. {sample!r}) but the layout "
                    f"matched no known shape (standard wide, two-row monthly, "
                    f"long panel, or transposed) — deferred per ADR-0013"
                ),
                source_excerpt=sample,
            )
        ]
    return [], []


def _parse_sheet(
    ws: object,
    sheet_name: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Parse one DNE worksheet into staging rows + errors.

    Tries the standard wide BS/AD fiscal-year layout first, then the three
    non-standard AD layouts (two-row monthly, long panel, transposed), then a
    fail-loud deferral diagnostic. Never silently drops year-bearing data.
    """
    rows: list[tuple[object, ...]] = list(ws.iter_rows(values_only=True))  # type: ignore[attr-defined]
    if not rows:
        return [], []

    unit_hint = _scan_unit_hint(rows, sheet_name)

    # Long panel FIRST: its signature (FY label in col 0 + AD month name in col 1
    # + value columns to the right) would otherwise be mis-claimed by the standard
    # wide-header detector, which sees the col-0 FY label as a single period column.
    lp = _detect_long_panel(rows)
    if lp is not None:
        # Pass unit_hint=None: the long panel's preamble is dominated by month-name
        # and column-header noise, so the blob-derived hint is unreliable here.
        # The panel parser resolves units per value column and fails loud
        # (UnitAmbiguous) rather than risk a wrong substring match.
        staging, errs = _parse_long_panel_layout(
            rows, lp[0], lp[1], lp[2], lp[3], None, sheet_name
        )
        if staging:
            return staging, errs

    header_row_idx, period_cols = _detect_header(rows)
    if header_row_idx is None or not period_cols:
        alt = _try_alternate_layouts(rows, unit_hint, sheet_name)
        if alt is not None:
            return alt
        return _defer_unparseable_sheet(rows, sheet_name)

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
