"""MoF / DPM-Office Yellow Book public-enterprise parser — deterministic Python.

Source: Office of the Prime Minister & Council of Ministers (DPM Office),
"Annual Performance Review of Public Enterprises" (the *Yellow Book* /
सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा). Source id
``dpm-public-enterprises-annual``. In-repo corpus: six PDFs at
``Financial Data/mof_documents/yellowbook/``.

PDF-acquisition assessment (STEP 0, recorded so the next maintainer doesn't
re-discover it the hard way):
    The six editions are Devanagari documents (the "BIG 2080" / "Website
    Uploaded Yellow" filenames refer to the FISCAL YEAR, not an English text
    layer). Encoding QUALITY varies page-to-page and edition-to-edition:
      - Body prose in the older FY2079 edition is CID-broken (``(cid:N)``
        glyphs, no ToUnicode) — unusable.
      - The per-sector financial summary tables (revenue / net-profit /
        admin-cost) ARE Unicode but render with RAGGED, merged-cell geometry
        whose column count differs every sector (12 / 13 / 21 / 15 / 9 cols),
        and one sector renders in a legacy Preeti byte-mapping. Parsing those
        deterministically inside the diff budget is not feasible.
      - Annex tables differ too: Annex-2/3 are Preeti-encoded gibberish under
        text extraction, but **Annex-1** ("ऋण लगानी तथा साँवा असूली" — loan
        investment & principal recovery by enterprise) of the FY2080/81
        edition (``Webiste Uploaded Yellow_sdwyi9v.pdf``) is CLEAN Unicode with
        a STABLE 10-column geometry spanning two pages, grouped by sector, with
        ~42 enterprise rows. That table is the one deterministically parseable
        per-enterprise matrix, and it is this parser's target.

    No OCR is performed (ADR-0003). We never transliterate the Preeti pages
    (that is reverse-engineering a font byte-map — fragile and out of scope).

Dimensional model (ADR-0015):
    Annex-1 is a matrix of (enterprise × measure), so it emits ``dimensional_rows``
    (NOT single-series ``staging_rows``). Two base measures are extracted per
    enterprise from the two government-capital columns of the annex:
      - ``soe-government-share``  — शेयर: paid-in government equity/share capital.
      - ``soe-loan-principal``    — ऋण: outstanding government-loan principal.
    ``dimension_kind='public_enterprise'``; ``dimension_value`` is the kebab slug
    of the enterprise name; ``dimension_label`` preserves the raw Devanagari name.

Unit (ADR-0011 magnitude verification — DON'T fuzzy-match, read the header):
    The Annex-1 header literally states the unit as "(रु. हजारमा)" = NPR in
    THOUSAND (हजार = thousand), NOT million and NOT lakh. We emit
    ``unit='npr_thousand'`` verbatim from that header. Sanity check: Nepal Bank
    Ltd. government share = 7,493,951 thousand = NPR 7.49 billion — the right
    order of magnitude for a large listed SOE. (The per-sector summary tables,
    by contrast, are stated "रू. लाखमा" = lakh; they are not parsed here, so no
    cross-unit mixing occurs.)

Period dating (ADR-0013):
    The annex header names the fiscal year by BS ("आ.व.२०८०/८१ को अन्त्य") — a
    BS-labelled balance-sheet snapshot at the close of the fiscal year. We treat
    it as an ``annual`` fact; ``reporting_period_bs`` and ``fiscal_year_bs`` are
    the BS fiscal-year label, and the AD start/end bound the BS-fiscal-year span
    (mid-Shrawan .. mid-Ashadh) via the canonical period helpers. The default
    BS fiscal year is hard-coded for the bundled FY2080/81 edition; when the
    orchestrator threads release metadata it can override.

Confidence: ``B`` — government-published annual review compiled from
enterprise-submitted statements; figures are revised across editions.

Versioning: bump ``PARSER_VERSION`` on any behaviour change.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

import pdfplumber

from _common.periods import (
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
)
from _common.types import ParserError, ParserStatus, ReportingPeriodType

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "dpm-public-enterprises-annual"

# Confidence default for every Yellow Book fact (see module docstring).
_CONFIDENCE: Final[str] = "B"

# Unit verbatim from the Annex-1 header "(रु. हजारमा)" — NPR thousand (ADR-0011).
_UNIT_NPR_THOUSAND: Final[str] = "npr_thousand"

# Default BS fiscal year of the bundled edition (FY 2080/81). The annex header
# embeds this ("आ.व.२०८०/८१"); we also re-derive it from the header text when a
# match is found (``_detect_fiscal_year_bs``) and fall back to this otherwise.
_DEFAULT_FY_BS_START: Final[int] = 2080

# Two base measures read from the Annex-1 government-capital columns.
_SHARE_SLUG: Final[str] = "soe-government-share"
_SHARE_NAME: Final[str] = "Government share investment in public enterprise"
_LOAN_SLUG: Final[str] = "soe-loan-principal"
_LOAN_NAME: Final[str] = "Government loan principal to public enterprise"

# Annex-1 column indices (verified stable across both pages of the FY2080/81
# edition — a 10-column table; col 0 = serial no., col 1 = enterprise name,
# col 2 = शेयर/share, col 3 = ऋण/loan). See the module docstring.
_COL_SERIAL: Final[int] = 0
_COL_NAME: Final[int] = 1
_COL_SHARE: Final[int] = 2
_COL_LOAN: Final[int] = 3
_MIN_ANNEX_COLS: Final[int] = 4

# Devanagari digit → ASCII. The serial column and the BS fiscal year in the
# header are written in Devanagari numerals; values themselves are usually ASCII
# but we normalise defensively before float parsing.
_DEVA_DIGITS: Final[dict[str, str]] = {
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

# Sector sub-header marker. Annex-1 groups enterprises under sector rows whose
# name cell ends with "क्षेत्र" (sector) and whose value columns are blank. These
# rows set the running sector context but are not themselves facts. Devanagari
# "क्षेत्र" renders with a glyph-reordering artifact under pdfplumber as the
# substring "क्षे" followed by a combining "त्र"/"�"; we match the stable prefix.
_SECTOR_SUFFIX_RE: Final = re.compile(r"क्ष")

# Total / sub-total rows to skip (their name cell is one of these words).
_SKIP_NAME_TOKENS: Final[frozenset[str]] = frozenset(
    {"जम्मा", "कूल जम्मा", "कुल जम्मा", "जम्म", "total", "grand total"}
)

# Header / unit / source rows whose first cell starts with one of these and which
# carry no enterprise fact. Used to ignore the annex title, unit annotation, and
# the trailing "स्रोतः" (source:) footnote.
_NON_DATA_PREFIXES: Final[tuple[str, ...]] = (
    "आ.व", "अनसु", "अनुस", "(रु", "(रू", "रकम", "स्रोत", "�ोत", "�.सं", "स.नं", "क्र",
)

# BS fiscal-year detector for the annex header, e.g. "आ.व.२०८०/८१ को अन्त्य ...".
# Captures the BS lead year (Devanagari or ASCII digits) of the FY label.
_FY_HEADER_RE: Final = re.compile(r"आ\.?\s*व\.?\s*([०-९0-9]{4})\s*/\s*([०-९0-9]{2,4})")


# ---------------------------------------------------------------------------
# Dimensional fact contract (ADR-0015) — mirrors the DNE parser's
# DimensionalRowDraft / DneParserResult field-for-field so the cloned
# ``ingest-dne-yellowbook.ts`` CLI reads the same ``dimensional_rows`` JSON.
# Intentionally NOT in _common/types.py (DNE-local convention, ADR-0015).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionalRowDraft:
    """One dimensional fact: a base measure sliced by exactly one dimension."""

    base_indicator_slug: str
    base_indicator_name: str
    dimension_kind: str
    dimension_value: str
    dimension_label: str
    value: float
    unit: str
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str
    reporting_period_ad_start: datetime
    reporting_period_ad_end: datetime
    fiscal_year_bs: str
    fiscal_year_ad_label: str
    confidence_grade: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "base_indicator_slug": self.base_indicator_slug,
            "base_indicator_name": self.base_indicator_name,
            "dimension_kind": self.dimension_kind,
            "dimension_value": self.dimension_value,
            "dimension_label": self.dimension_label,
            "value": self.value,
            "unit": self.unit,
            "reporting_period_type": self.reporting_period_type,
            "reporting_period_bs": self.reporting_period_bs,
            "reporting_period_ad_start": self.reporting_period_ad_start.isoformat(),
            "reporting_period_ad_end": self.reporting_period_ad_end.isoformat(),
            "fiscal_year_bs": self.fiscal_year_bs,
            "fiscal_year_ad_label": self.fiscal_year_ad_label,
            "confidence_grade": self.confidence_grade,
        }


@dataclass(frozen=True)
class YellowbookResult:
    """Yellow Book parser result carrying dimensional output only.

    Yellow Book emits no single-series ``staging_rows`` (Annex-1 is a
    dimensional matrix), so this wrapper mirrors the DNE CLI's expected JSON
    shape: a ``dimensional_rows`` array plus ``status`` / ``errors``.
    """

    status: ParserStatus
    parser_version: str
    dimensional_rows: list[DimensionalRowDraft]
    errors: list[ParserError]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "parser_version": self.parser_version,
            "dimensional_rows": [r.to_json_dict() for r in self.dimensional_rows],
            "errors": [e.to_json_dict() for e in self.errors],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deva_to_ascii(text: str) -> str:
    """Map Devanagari digits to ASCII; leave other characters untouched."""
    return "".join(_DEVA_DIGITS.get(ch, ch) for ch in text)


def _norm(cell: object) -> str:
    """Stringify a cell and collapse internal whitespace/newlines to a space."""
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def _is_serial(cell_text: str) -> bool:
    """True if a cell is a pure (Devanagari or ASCII) integer serial number."""
    ascii_text = _deva_to_ascii(cell_text).strip()
    return bool(ascii_text) and ascii_text.isdigit()


def _parse_value(cell_text: str) -> float | None:
    """Parse a money cell to float; None for empty / dash / non-numeric.

    Handles ASCII or Devanagari digits and thousands separators. NRB/MoF use
    "-"/"–"/blank for "not applicable"; those become None (not zero — we never
    fabricate a value, and a real ``0`` in the source is preserved as ``0.0``).
    """
    s = _deva_to_ascii(cell_text).strip()
    if s in ("", "-", "--", "–", "—", "N/A", "n/a", "NA", "...", "."):
        return None
    try:
        v = float(s.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN  # noqa: PLR0124
        return None
    return v


def _slugify_enterprise(label: str) -> str:
    """Kebab slug of an enterprise name for ``dimension_value``.

    Devanagari is preserved (lowercasing is a no-op for it); only ASCII is
    lowercased, punctuation collapses to hyphens, runs of whitespace fold to a
    single hyphen. The RAW label is kept separately as ``dimension_label`` so the
    original (including any pdfplumber glyph-ordering artifact) stays traceable.
    Two distinct enterprise names never collapse to one slug because the slug
    keeps every Devanagari character.
    """
    s = label.lower()
    # Replace ASCII punctuation / standalone separators with spaces; keep letters
    # (incl. Devanagari, which is outside the ASCII-punctuation class) and digits.
    s = re.sub(r"[\s.,/()\[\]{}:;\"'`*&+]+", " ", s)
    return re.sub(r"\s+", "-", s.strip())


def _is_sector_header(name: str, share_text: str, loan_text: str) -> bool:
    """True if a row is a sector sub-header (name ends ~"क्षेत्र", no values).

    Requires BOTH signals: the name carries the sector marker AND neither
    government-capital column holds a number — so a real enterprise whose name
    merely contains "क्षेत्र" is never mistaken for a divider.
    """
    if not _SECTOR_SUFFIX_RE.search(name):
        return False
    return _parse_value(share_text) is None and _parse_value(loan_text) is None


def _is_skip_row(name: str) -> bool:
    """True for total/sub-total rows and header/unit/source rows (no fact)."""
    low = name.strip().lower()
    if name.strip() in _SKIP_NAME_TOKENS or low in _SKIP_NAME_TOKENS:
        return True
    return any(name.startswith(p) for p in _NON_DATA_PREFIXES)


def _detect_fiscal_year_bs(header_text: str) -> int | None:
    """Return the BS fiscal-year lead year from the annex header, or None.

    Matches "आ.व.२०८०/८१ ..." and validates the tail equals (lead + 1) mod 100,
    so a stray number is never read as a fiscal year.
    """
    m = _FY_HEADER_RE.search(header_text)
    if not m:
        return None
    lead = int(_deva_to_ascii(m.group(1)))
    tail = int(_deva_to_ascii(m.group(2))) % 100
    if tail != (lead + 1) % 100:
        return None
    return lead


def _annual_span(bs_fy_start: int) -> tuple[datetime, datetime]:
    """AD start/end bounding the BS fiscal-year span (mid-Shrawan..mid-Ashadh).

    Mirrors the FCGO parser: ``mid_month_ad`` maps Shrawan to the FY-open AD
    month and Ashadh to mid-July of the following AD year (the FY close).
    """
    start = mid_month_ad("Shrawan", bs_fy_start)
    end = mid_month_ad("Ashadh", bs_fy_start)
    return start, end


def _make_row(
    base_slug: str,
    base_name: str,
    name_raw: str,
    value: float,
    bs_fy_start: int,
    ad_start: datetime,
    ad_end: datetime,
) -> DimensionalRowDraft:
    """Build one enterprise DimensionalRowDraft for a base measure + value."""
    return DimensionalRowDraft(
        base_indicator_slug=base_slug,
        base_indicator_name=base_name,
        dimension_kind="public_enterprise",
        dimension_value=_slugify_enterprise(name_raw),
        dimension_label=name_raw,
        value=value,
        unit=_UNIT_NPR_THOUSAND,
        reporting_period_type="annual",
        reporting_period_bs=fiscal_year_label(bs_fy_start),
        reporting_period_ad_start=ad_start,
        reporting_period_ad_end=ad_end,
        fiscal_year_bs=fiscal_year_label(bs_fy_start),
        fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        confidence_grade=_CONFIDENCE,
    )


# ---------------------------------------------------------------------------
# Deterministic core — exercised against synthesized table fixtures.
# ---------------------------------------------------------------------------


def extract_dimensional_rows(
    table_rows: list[list[object]],
    bs_fy_start: int,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Convert Annex-1 table rows → per-enterprise dimensional facts.

    ``table_rows`` is the raw ``page.extract_tables()`` output for the Annex-1
    table (col 0 serial, col 1 enterprise name, col 2 share, col 3 loan). State
    machine: a sector sub-header sets the running sector (kept only to qualify
    the enterprise context — it is not stored on the fact); a serial-led row with
    a name and at least one parseable value emits up to two facts (share, loan).
    Total/header/source rows are skipped. Never raises.

    Emits, per enterprise: one ``soe-government-share`` fact when the share cell
    parses, and one ``soe-loan-principal`` fact when the loan cell parses (a
    genuine source ``0`` is kept; only blank/dash is dropped). A serial-led row
    whose share AND loan are both unparseable surfaces a single ``ValueUnparseable``
    so the data loss is visible, never silent (Rule 6).
    """
    ad_start, ad_end = _annual_span(bs_fy_start)
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    seen: set[tuple[str, str]] = set()

    for raw in table_rows:
        if len(raw) < _MIN_ANNEX_COLS:
            continue
        serial = _norm(raw[_COL_SERIAL])
        name = _norm(raw[_COL_NAME])
        share_text = _norm(raw[_COL_SHARE])
        loan_text = _norm(raw[_COL_LOAN])

        if not name or _is_skip_row(name):
            continue
        if _is_sector_header(name, share_text, loan_text):
            continue
        # A genuine enterprise row is serial-led. Rows without a serial that
        # survived the skip filters are layout noise (wrapped header fragments).
        if not _is_serial(serial):
            continue

        share = _parse_value(share_text)
        loan = _parse_value(loan_text)
        if share is None and loan is None:
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=(
                        f"enterprise {name!r}: neither share nor loan column "
                        f"parsed (share={share_text!r}, loan={loan_text!r})"
                    ),
                    source_excerpt=f"{serial} | {name}",
                )
            )
            continue

        if share is not None:
            key = (_SHARE_SLUG, _slugify_enterprise(name))
            if key not in seen:
                seen.add(key)
                rows.append(
                    _make_row(
                        _SHARE_SLUG, _SHARE_NAME, name, share,
                        bs_fy_start, ad_start, ad_end,
                    )
                )
        if loan is not None:
            key = (_LOAN_SLUG, _slugify_enterprise(name))
            if key not in seen:
                seen.add(key)
                rows.append(
                    _make_row(
                        _LOAN_SLUG, _LOAN_NAME, name, loan,
                        bs_fy_start, ad_start, ad_end,
                    )
                )

    return rows, errors


# ---------------------------------------------------------------------------
# PDF reading — locate Annex-1 and feed its table to the deterministic core.
# ---------------------------------------------------------------------------

# Marker phrases that identify the Annex-1 page (loan-investment annex). Both the
# annex label and the unit annotation must be present to avoid matching the body
# narrative that merely mentions "ऋण लगानी".
_ANNEX1_MARKERS: Final[tuple[str, ...]] = ("ऋण लगानी", "हजारमा")


def _page_is_annex1(text: str) -> bool:
    """True if a page is part of Annex-1 (loan-investment-by-enterprise)."""
    return all(m in text for m in _ANNEX1_MARKERS)


def _largest_table(page: object) -> list[list[object]] | None:
    """Return the page's largest extracted table (by row count), or None."""
    tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
    if not tables:
        return None
    return max(tables, key=len)


def parse_yellowbook(source_document_path: str, source_document_id: str) -> YellowbookResult:
    """Parse a Yellow Book PDF → per-enterprise dimensional facts (ADR-0015).

    Scans every page for Annex-1 (the clean-Unicode loan-investment-by-enterprise
    annex — the one deterministically parseable per-enterprise matrix; see module
    docstring), extracts its table, and emits ``dimensional_rows``. The BS fiscal
    year is read from the annex header and falls back to the bundled edition's
    default. Never raises on bad data: a missing annex / unreadable PDF yields a
    typed error and ``status='failure'`` or ``'partial'``.
    """
    _ = source_document_id  # threaded for orchestrator-contract symmetry

    path = Path(source_document_path)
    if not path.exists():
        return YellowbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"source file not found: {path}",
                )
            ],
        )

    all_rows: list[DimensionalRowDraft] = []
    all_errors: list[ParserError] = []
    fy_bs_start = _DEFAULT_FY_BS_START
    annex_pages = 0

    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not _page_is_annex1(text):
                    continue
                annex_pages += 1
                detected = _detect_fiscal_year_bs(text)
                if detected is not None:
                    fy_bs_start = detected
                table = _largest_table(page)
                if table is None:
                    continue
                page_rows, page_errors = extract_dimensional_rows(table, fy_bs_start)
                all_rows.extend(page_rows)
                all_errors.extend(page_errors)
    except (OSError, ValueError, Exception) as exc:  # noqa: BLE001
        return YellowbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdfplumber could not read {path.name}: {exc}",
                )
            ],
        )

    if annex_pages == 0:
        all_errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    "Annex-1 (loan-investment-by-enterprise) not found on any "
                    "page — edition layout differs from the FY2080/81 target; "
                    "see scrapers/mof_yellowbook/parser.py module docstring"
                ),
            )
        )

    if not all_rows:
        return YellowbookResult(
            status="failure" if annex_pages == 0 else "partial",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=all_errors
            or [
                ParserError(
                    error_class="Other",
                    error_detail="NoDataExtracted: Annex-1 present but no enterprise rows parsed",
                )
            ],
        )

    status: ParserStatus = "partial" if all_errors else "success"
    return YellowbookResult(
        status=status,
        parser_version=PARSER_VERSION,
        dimensional_rows=all_rows,
        errors=all_errors,
    )


def _main() -> None:
    """CLI entrypoint (orchestrator contract — mirror of nrb_dne.parser).

    Argv: ``parser.py <source_document_path> <source_document_id>``. Writes the
    result JSON (including the ``dimensional_rows`` key ADR-0015 / the Yellow Book
    ingest CLI reads) to stdout. Datetimes are ISO-8601 strings. Exit codes:
    0 = ran (status may be failure), 2 = usage error.
    """
    expected_argv = 3  # progname + path + doc id
    if len(sys.argv) != expected_argv:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse_yellowbook(sys.argv[1], sys.argv[2])
    json.dump(result.to_json_dict(), sys.stdout)


if __name__ == "__main__":
    _main()
