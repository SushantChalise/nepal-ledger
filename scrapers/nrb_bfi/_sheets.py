"""Per-sheet column resolvers and row iterators for NRB BFI XLSX files.

C4 — Major Financial Indicators
    Single block. Header row 4 declares column-by-column bank class
    (``Class "A"``, ``Class "B"``, ``Class "C"``, ``Overall``). Indicator
    labels are typically in column C with a section header in column B.

C5 — Statement of Assets and Liabilities
    Four bank-class blocks side-by-side (Banks&FIs / Commercial / Development
    / Finance). Within each block: 3 historical "Mid-July YYYY" columns, then
    a "Mid-{prev month} YYYY" column, then a "Mid-{current month} YYYY"
    column, then three % change columns we discard for v0.1.0. Indicator
    label in column C; column B holds an outline number (1, 2, ...) on
    section-header rows only.

C6 — Profit and Loss Statement
    Same 4-block layout as C5, but indicator label is in column B (no
    separate code column) and value columns start one column earlier.

C7 — Statement of Loans and Advances (Sectorwise)
    Same 4-block layout as C6. Indicator label in column B.

Rather than encode brittle column-letter constants, we discover the
column layout from the header rows: every block starts with a "Mid-July"
header in row 4 and a year integer in row 5. We collect those (column,
year, label) tuples per block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal

from _common.types import BankClass

from ._normalize import coerce_float, slugify

# Headers we expect to find inside row 2 of C5..C7 — used to align bank
# classes to column blocks. The cell value is sometimes truncated by
# openpyxl/read-only mode to ~60 chars, so we substring-match.
_BLOCK_NEEDLES: Final[tuple[tuple[str, BankClass], ...]] = (
    ("banks & financial in", "system_total"),
    ("commercial banks", "commercial"),
    ("development banks", "development"),
    ("finance companies", "finance"),
)

# Period column header text in row 4 (lowercased after strip).
_PERIOD_HEADER_RE = ("mid-july", "mid-aug", "mid-sept", "mid-sep", "mid-oct",
                     "mid-nov", "mid-dec", "mid-jan", "mid-feb", "mid-mar",
                     "mid-apr", "mid-may", "mid-jun")

# Constants for magic-number lint compliance and clarity.
_REQUIRED_BANK_BLOCKS: Final[int] = 4
_MIN_C4_CLASSES_DETECTED: Final[int] = 3
_MIN_C5LIKE_ROWS: Final[int] = 6
_MIN_HEADER_HITS: Final[int] = 4
_OUTLINE_ONE: Final[float] = 1.0
_OUTLINE_FIVE: Final[float] = 5.0
_MIN_LABEL_LEN: Final[int] = 4
_MIN_SECTION_LETTERS: Final[int] = 3
# NRB BFI corpus year bounds (loosely; the validator can tighten).
_YEAR_MIN: Final[int] = 2015
_YEAR_MAX: Final[int] = 2035
# Row indices we scan when locating period/year header rows (0-based).
_HEADER_SCAN_ROWS: Final[tuple[int, ...]] = (3, 4, 2)
_SAMPLE_DATA_ROWS_FOR_LABEL: Final[int] = 30

C4SheetName = Literal["C4"]
C5SheetName = Literal["C5", "C6", "C7"]


@dataclass(frozen=True)
class PeriodColumn:
    """A single time-period column inside a C-sheet block."""

    col_idx: int            # 0-based DataFrame column index
    period_label: str       # e.g. "Mid-July" (the row-4 header)
    period_year: int        # e.g. 2025 (the row-5 year)


@dataclass(frozen=True)
class BlockLayout:
    """A bank-class column block inside C5/C6/C7."""

    bank_class: BankClass
    first_col: int          # 0-based column index where this block starts
    last_col: int           # exclusive end col
    periods: tuple[PeriodColumn, ...]


@dataclass(frozen=True)
class C5LikeLayout:
    """Whole-sheet layout for a 4-block sheet (C5/C6/C7)."""

    label_col: int          # 0-based index of the indicator-label column
    blocks: tuple[BlockLayout, ...]
    unit: str               # always "NPR_million" for these sheets
    header_row_period: int  # row index of "Mid-..." headers (0-based)
    header_row_year: int    # row index of YYYY integers (0-based)
    first_data_row: int     # 0-based row index where data begins


# ─── C4 (Major Financial Indicators) ────────────────────────────────────


_C4_CLASS_HEADER_MAP: Final[dict[str, BankClass]] = {
    'class "a"': "commercial",
    "class a": "commercial",
    'class "b"': "development",
    "class b": "development",
    'class "c"': "finance",
    "class c": "finance",
    "overall": "system_total",
}


def find_c4_columns(
    rows: list[list[object]],
) -> tuple[dict[BankClass, int], int, int] | None:
    """Return ({bank_class: col_idx}, label_col, header_row) for sheet C4.

    Returns None if the header row cannot be located.
    """
    for row_idx, row in enumerate(rows[:10]):
        col_map: dict[BankClass, int] = {}
        for col_idx, cell in enumerate(row):
            if cell is None:
                continue
            key = str(cell).strip().lower()
            mapped = _C4_CLASS_HEADER_MAP.get(key)
            if mapped is not None and mapped not in col_map:
                col_map[mapped] = col_idx
        if len(col_map) >= _MIN_C4_CLASSES_DETECTED:
            # Label column: the rightmost text column to the LEFT of the
            # leftmost value column.
            leftmost_value_col = min(col_map.values())
            label_col = max(
                (
                    c
                    for c in range(leftmost_value_col)
                    if isinstance(row[c], str) is False  # row header is blank
                ),
                default=leftmost_value_col - 1,
            )
            # Empirically label is the column immediately left of the first
            # value column (col C in the sheet).
            label_col = leftmost_value_col - 1
            return col_map, label_col, row_idx
    return None


def iter_c4_indicators(
    rows: list[list[object]],
    col_map: dict[BankClass, int],
    label_col: int,
    header_row: int,
) -> list[tuple[str, dict[BankClass, float | None]]]:
    """Yield (slug, {bank_class: value or None}) for each indicator row in C4.

    Section header rows (e.g. ``A. Credit, Deposit Ratios (%)``) are skipped
    by detecting that none of the four value cells coerce to a float.
    """
    out: list[tuple[str, dict[BankClass, float | None]]] = []
    section_prefix: str | None = None
    for row in rows[header_row + 1:]:
        # Section heading: text in label_col, no numeric values anywhere.
        label_cell = row[label_col] if label_col < len(row) else None
        label = str(label_cell).strip() if label_cell is not None else ""

        values: dict[BankClass, float | None] = {}
        any_numeric = False
        for bc, col in col_map.items():
            v = coerce_float(row[col]) if col < len(row) else None
            values[bc] = v
            if v is not None:
                any_numeric = True

        if not any_numeric:
            # Section headers in C4 may sit in any text column left of the
            # first value column (label_col is sometimes too narrow).
            heading = label
            if not heading:
                leftmost_value_col = min(col_map.values())
                for c in range(leftmost_value_col):
                    cell = row[c] if c < len(row) else None
                    if cell is not None and str(cell).strip():
                        heading = str(cell).strip()
                        break
            if heading and not heading.startswith(("-", "_")):
                section_prefix = slugify(heading)
            continue

        if not label:
            continue
        slug = slugify(label)
        if not slug:
            continue
        if section_prefix:
            slug = f"{section_prefix}--{slug}"
        out.append((slug, values))
    return out


# ─── C5 / C6 / C7 (four-block sheets) ───────────────────────────────────


def _find_block_starts(
    row2: list[object],
) -> list[tuple[BankClass, int]]:
    """Locate the bank-class blocks by scanning row 2 for the title cells."""
    starts: list[tuple[BankClass, int]] = []
    for col_idx, cell in enumerate(row2):
        if cell is None:
            continue
        normalised = str(cell).strip().lower()
        for needle, bc in _BLOCK_NEEDLES:
            if needle in normalised and not any(s[0] == bc for s in starts):
                starts.append((bc, col_idx))
    starts.sort(key=lambda t: t[1])
    return starts


def _resolve_block_periods(
    period_row: list[object],
    year_row: list[object],
    block_start: int,
    block_end: int,
) -> list[PeriodColumn]:
    """Within a single block, return the period columns we will emit.

    Strategy: every column whose row-4 header starts with "Mid-" AND whose
    row-5 cell coerces to an int is a period column. We DROP "% Change"
    columns and outline-numbered columns (where row-4 is blank or non-Mid).
    """
    out: list[PeriodColumn] = []
    for col_idx in range(block_start, min(block_end, len(period_row))):
        header_cell = period_row[col_idx]
        year_cell = year_row[col_idx] if col_idx < len(year_row) else None
        if header_cell is None or year_cell is None:
            continue
        header_text = str(header_cell).strip().lower()
        if not header_text.startswith("mid-"):
            continue
        year_val = coerce_float(year_cell)
        if year_val is None:
            continue
        year = int(year_val)
        # Sanity: NRB BFI series spans 2018..2030 roughly.
        if not _YEAR_MIN <= year <= _YEAR_MAX:
            continue
        # Canonicalise the period label — keep trailing whitespace out.
        clean_label = str(header_cell).strip()
        out.append(
            PeriodColumn(
                col_idx=col_idx,
                period_label=clean_label,
                period_year=year,
            )
        )
    return out


def detect_c5like_layout(
    rows: list[list[object]],
    sheet_name: str,
) -> C5LikeLayout | None:
    """Discover the layout of a 4-block sheet (C5/C6/C7).

    Returns None if the header structure does not match the v0.1.0
    expectation; the parser then emits ``PageLayoutChanged``.
    """
    if len(rows) < _MIN_C5LIKE_ROWS:
        return None
    row2 = rows[1] if len(rows) > 1 else []
    block_starts = _find_block_starts(row2)
    if len(block_starts) < _REQUIRED_BANK_BLOCKS:
        return None

    header_row_period = _locate_period_header_row(rows)
    if header_row_period < 0:
        return None

    # Year row sits one row below the period header in all observed
    # variants.
    header_row_year = header_row_period + 1
    if header_row_year >= len(rows):
        return None

    period_row = rows[header_row_period]
    year_row = rows[header_row_year]

    # Compute block end columns: the column immediately before the next
    # block start, or the end of the period row.
    block_ends = [block_starts[i + 1][1] for i in range(len(block_starts) - 1)]
    block_ends.append(len(period_row))

    blocks: list[BlockLayout] = []
    for (bank_class, start), end in zip(block_starts, block_ends, strict=True):
        periods = tuple(_resolve_block_periods(period_row, year_row, start, end))
        if not periods:
            continue
        blocks.append(
            BlockLayout(
                bank_class=bank_class,
                first_col=start,
                last_col=end,
                periods=periods,
            )
        )

    if len(blocks) < _REQUIRED_BANK_BLOCKS:
        return None

    # Indicator label column: for C5 it's col index 2 (C), for C6/C7 it's
    # col index 1 (B). Detect heuristically: the column closest to (but
    # left of) the first block's first period column that has non-empty
    # text on data rows.
    first_period_col = blocks[0].periods[0].col_idx
    label_col = _find_label_col(rows, header_row_year + 1, first_period_col)

    first_data_row = header_row_year + 1
    # Skip the next row if it is the "1, 2, 3, 4, 5" outline-number row
    # (in C5 + C6 + C7 there is such a row immediately after the year row).
    if first_data_row < len(rows):
        outline_candidates = rows[first_data_row]
        if _looks_like_outline_row(outline_candidates, blocks[0].first_col):
            first_data_row += 1

    # Unit detection: scan row 3 for "Mn of Rs" / "Crore" / etc.
    unit = _detect_unit(rows)
    if sheet_name == "C4":
        # C4 is percentages-and-ratios; not reached here.
        unit = "percent"

    return C5LikeLayout(
        label_col=label_col,
        blocks=tuple(blocks),
        unit=unit,
        header_row_period=header_row_period,
        header_row_year=header_row_year,
        first_data_row=first_data_row,
    )


def _locate_period_header_row(rows: list[list[object]]) -> int:
    """Return the 0-based row index whose cells start with 'Mid-' most often.

    Returns -1 if no candidate row has at least ``_MIN_HEADER_HITS`` cells.
    """
    best_row = -1
    best_hits = 0
    for candidate in _HEADER_SCAN_ROWS:
        if candidate >= len(rows):
            continue
        hits = sum(
            1
            for c in rows[candidate]
            if c is not None and str(c).strip().lower().startswith("mid-")
        )
        if hits > best_hits:
            best_hits = hits
            best_row = candidate
    if best_hits < _MIN_HEADER_HITS:
        return -1
    return best_row


def _looks_like_outline_row(row: list[object], block_first_col: int) -> bool:
    """Return True if ``row`` is the "1, 2, 3, 4, 5" outline marker row."""
    seen_int_one = False
    seen_int_five = False
    for col_idx in range(block_first_col, min(block_first_col + 10, len(row))):
        v = coerce_float(row[col_idx])
        if v is None:
            continue
        if v == _OUTLINE_ONE:
            seen_int_one = True
        if v == _OUTLINE_FIVE:
            seen_int_five = True
    return seen_int_one and seen_int_five


def _find_label_col(
    rows: list[list[object]],
    data_start_row: int,
    first_period_col: int,
) -> int:
    """Heuristic: among columns to the left of ``first_period_col``, the
    label column is the one with the most non-numeric text in data rows.
    """
    if data_start_row >= len(rows):
        return max(0, first_period_col - 1)
    candidates = list(range(first_period_col))
    scores = {c: 0 for c in candidates}
    for row in rows[data_start_row : data_start_row + _SAMPLE_DATA_ROWS_FOR_LABEL]:
        for c in candidates:
            if c >= len(row):
                continue
            cell = row[c]
            if cell is None:
                continue
            text = str(cell).strip()
            if not text:
                continue
            if coerce_float(text) is not None:
                continue
            # Text length contributes — actual labels are >5 chars.
            if len(text) >= _MIN_LABEL_LEN:
                scores[c] += 1
    if not scores:
        return max(0, first_period_col - 1)
    return max(scores.items(), key=lambda kv: kv[1])[0]


def _detect_unit(rows: list[list[object]]) -> str:
    """Return canonical unit string by sniffing the first 6 rows."""
    haystack = " ".join(
        str(cell).lower()
        for row in rows[:7]
        for cell in row
        if cell is not None
    )
    if "mn of rs" in haystack or "rs in million" in haystack:
        return "NPR_million"
    if "crore" in haystack or "rs in crore" in haystack:
        return "NPR_crore"
    if "rs in bn" in haystack or "billion" in haystack:
        return "NPR_billion"
    # Empirical default for the C5..C7 statements is millions; row-3 unit
    # cells are absent in the earliest 2078 files but the values clearly
    # match the millions convention vs the later annotated files.
    return "NPR_million"


def iter_c5like_indicators(
    rows: list[list[object]],
    layout: C5LikeLayout,
) -> list[tuple[str, list[tuple[BankClass, PeriodColumn, float]]]]:
    """Yield (slug, [(bank_class, period_col, value), ...]) for each data row.

    Section-header rows (no numeric data) generate a ``section_prefix`` that
    is prepended to subsequent slugs until the next section, preserving the
    outline hierarchy of C5/C6.
    """
    out: list[tuple[str, list[tuple[BankClass, PeriodColumn, float]]]] = []
    section_prefix: str | None = None
    for row in rows[layout.first_data_row :]:
        label_cell = row[layout.label_col] if layout.label_col < len(row) else None
        label = str(label_cell).strip() if label_cell is not None else ""

        emissions: list[tuple[BankClass, PeriodColumn, float]] = []
        for block in layout.blocks:
            for period in block.periods:
                if period.col_idx >= len(row):
                    continue
                v = coerce_float(row[period.col_idx])
                if v is None:
                    continue
                emissions.append((block.bank_class, period, v))

        if not label:
            continue

        # Detect a "section header" row. Two signals, either is sufficient:
        #   (a) Label is entirely uppercase (with letters) — C5/C6 use ALL
        #       CAPS for top-level headers like CAPITAL FUND, DEPOSITS,
        #       INTEREST EXPENSES.
        #   (b) Label has no numeric prefix AND col B (immediately left of
        #       the label) contains an integer outline number. Sub-items
        #       use blank or whitespace there.
        is_section_header = _is_section_header(label, row, layout.label_col)
        if is_section_header:
            section_prefix = slugify(label)
            # Section-header rows also carry totals; emit them at the
            # section level so the totals are retrievable.
            if emissions:
                out.append((section_prefix or slugify(label), emissions))
            continue

        if not emissions:
            # Pure label row with no totals -> still treat as section
            # heading so any sub-rows below get prefixed.
            if not label.startswith(("-", "_")):
                section_prefix = slugify(label)
            continue

        slug = slugify(label)
        if not slug:
            continue
        if section_prefix and slug != section_prefix:
            slug = f"{section_prefix}--{slug}"
        out.append((slug, emissions))
    return out


def _is_section_header(label: str, row: list[object], label_col: int) -> bool:
    """Return True if ``label`` looks like a top-level section header.

    Signals (any sufficient):
      (a) All non-space characters in the label are uppercase letters,
          digits, or punctuation (and at least 3 letters).
      (b) The cell immediately to the left of ``label_col`` holds an
          integer (the outline number), e.g. B='1' / C='CAPITAL FUND'.
    """
    letters = [c for c in label if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) >= _MIN_SECTION_LETTERS:
        return True
    if label_col > 0 and label_col - 1 < len(row):
        prev = row[label_col - 1]
        prev_text = str(prev).strip() if prev is not None else ""
        if prev_text and prev_text.isdigit():
            return True
    return False


def sheet_to_rows(ws: Any) -> list[list[object]]:  # noqa: ANN401
    """Materialise the worksheet to a list of lists; tolerates ragged rows.

    Accepts ``openpyxl.worksheet.worksheet.Worksheet`` but typed as ``Any``
    because the openpyxl module is unfollowed under ``mypy --strict``.
    """
    out: list[list[object]] = []
    for row in ws.iter_rows(values_only=True):
        out.append(list(row))
    return out
