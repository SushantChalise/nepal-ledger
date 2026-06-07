"""MoF White Book → foreign-aid dimensional facts — deterministic Python.

Source: Ministry of Finance, **"Source Book for Projects Financed with Foreign
Assistance"** (the *White Book* / वैदेशिक सहायता आयोजनाहरुको स्रोत पुस्तिका) — the
annual budget-book record of foreign aid (grants + loans) entering Nepal, broken
out by development partner (donor) and by spending ministry (sector). This is the
"Money In" external-financing story. Source id ``mof-whitebook-foreign-aid``
(PROPOSED this batch — see the source profile / FOR MOTHER notes; not yet in
``seed-source-registry.ts``).

In-repo corpus: ``Financial Data/mof_documents/whitebook/`` (multiple editions).

STEP-0 PDF-acquisition assessment (ADR-0011/0003 — recorded so the next
maintainer does not re-discover it; page numbers are 0-based ``pdfplumber``
indices):

    The corpus splits three ways by encoding:
      1. CLEAN ENGLISH editions (the parseable target): FY 2015/16, FY 2020/21,
         and the FY 2013/14 + FY 2014/15 editions (whose FILENAMES are Devanagari
         but whose BODY is the English "Unofficial Translation"). Each opens with
         two summary tables in clean forward Unicode with a STABLE 12-column
         geometry:
           - "Summary of Ministrywise Development Partners" (dimension = MINISTRY
             / budget head; carries an extra leading "GoN Budget" column → its
             value columns are offset by one vs the donor table).
           - "Development Partnerwise Summary"              (dimension = DONOR).
         Both tables share the column block: ``Cash | Reimbursable | Direct
         Payment | Commodity | TOTAL GRANT | Direct Payment | Reimbursable | Cash
         | TOTAL LOAN | Total``. This parser extracts the two headline measures —
         **Total Grant** and **Total Loan** — per dimension member.
      2. LEGACY PREETI editions (FY 2062/63, 2064/65, 2065/66, 2067/68): the text
         layer is a Preeti font byte-map (e.g. ``dGqfnout`` = "मन्त्रालयगत"), not
         Unicode. Un-mapping it is reverse-engineering a font (the OCR/translit
         ADR-0003 forbids). **Deferred.**
      3. A MISLABELLED file ("...White Book FY 2021-22_azz4yjf.pdf") whose content
         is actually the **Intergovernmental Fiscal Transfer** book (Devanagari)
         and is **CID-broken** (``(cid:N)`` glyphs, no ToUnicode). Not a White
         Book; **deferred** (it belongs to a different source).

Unit (ADR-0011 — DON'T fuzzy-match; READ the annotation on the table page):
    The unit is stamped on each summary-table page and VARIES BY EDITION:
      - FY 2020/21  : "(Rs. in '00000')"  = Rs in 100,000 = **lakh**  → npr_lakh
      - FY 2015/16 / 2013/14 / 2014/15 : "(NRs'000s)" / "( Rs. 000 )" = Rs in
        1,000 = **thousand**                                          → npr_thousand
    We DETECT the annotation per page and emit the matching unit VERBATIM (never
    assume). Magnitude sanity (donor Total rows):
      - FY 2015/16 grants 110,929,407 + loans 94,964,704 thousand
        = NPR 205.9 billion total assistance — in the NPR 100–250 bn/yr band.
      - FY 2020/21 grants 605,277 + loans 2,994,993 lakh = NPR 360.0 billion —
        a COVID-year surge (IMF RCF, ADB-CARES, IDA budget support all present);
        elevated but plausible for that year.
    Mixing is avoided structurally: each row carries the unit detected on its own
    page, so a thousand-edition row and a lakh-edition row never silently combine.

Dimensional model (ADR-0015 / ADR-0017): each summary table is a matrix of
(member × measure), so the parser emits ``dimensional_rows`` (NOT single-series
``staging_rows``), routed into ``foreign_aid_facts``:
    - base measures: ``foreign-aid-grant`` (Total Grant col), ``foreign-aid-loan``
      (Total Loan col).
    - ``dimension_kind`` ∈ {``donor``, ``sector``}; ``dimension_value`` is the
      kebab slug of the member name; ``dimension_label`` preserves the raw name.
    A genuine source ``0`` is preserved (a real "no grant"/"no loan"); only
    blank/dash becomes None and emits no fact. The ``Total`` row is skipped.

Period dating (ADR-0013): the cover/table caption labels the AD fiscal year
("Fiscal Year 2020/21"). Nepal's mid-July→mid-July FY maps 1:1 to BS via +57 on
the lead year (AD 2020/21 → BS 2077/78). ``reporting_period_type='annual'``; the
AD start/end bound the BS-fiscal-year span (mid-Shrawan..mid-Ashadh) via the
canonical period helpers. A LOCAL helper does AD-FY→BS-FY so ``_common/periods``
stays untouched (same pattern as ``fcgo_consolidated`` / ``mof_economic_survey``).

Confidence: ``B`` — MoF "unofficial translation" budget source book; the figures
are budgeted/disbursement allocations that are revised across editions.

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
# Registered source id. PROPOSED this batch — Mother seeds the registry row
# (`mof-whitebook-foreign-aid`); not yet present in seed-source-registry.ts.
SOURCE_ID: Final[str] = "mof-whitebook-foreign-aid"

# Confidence default for every White Book fact (see module docstring).
_CONFIDENCE: Final[str] = "B"

# Two base measures (the headline grant/loan totals per dimension member).
_GRANT_SLUG: Final[str] = "foreign-aid-grant"
_GRANT_NAME: Final[str] = "Foreign grant assistance (total)"
_LOAN_SLUG: Final[str] = "foreign-aid-loan"
_LOAN_NAME: Final[str] = "Foreign loan assistance (total)"

# AD→BS fiscal-year offset on the lead year (mid-July→mid-July FY maps 1:1;
# AD 2020/21 == BS 2077/78). Pinned to the period helpers' +57 (ADR-0013), same
# as fcgo_consolidated / mof_economic_survey. Local by design.
_AD_TO_BS_FY_OFFSET: Final[int] = 57


def _ad_fy_to_bs_start(ad_fy_start: int) -> int:
    """Map an AD fiscal-year lead year to its BS fiscal-year lead year (+57).

    Local helper (ADR-0013); symmetric with ``_common.periods.fiscal_year_ad_label``
    (which subtracts 57). A unit test asserts the round-trip.
    """
    return ad_fy_start + _AD_TO_BS_FY_OFFSET


# ---------------------------------------------------------------------------
# Unit detection (ADR-0011) — read the annotation stamped on the table page.
# ---------------------------------------------------------------------------

_UNIT_NPR_LAKH: Final[str] = "npr_lakh"
_UNIT_NPR_THOUSAND: Final[str] = "npr_thousand"

# "(Rs. in '00000')" — five zeros = 100,000 = lakh. Tolerant of inner spaces.
_UNIT_LAKH_RE: Final = re.compile(r"\(\s*Rs\.?\s*in\s*'?0{5}'?\s*\)", re.IGNORECASE)
# "(NRs'000s)" / "( Rs. 000 )" — three zeros = thousand.
_UNIT_THOUSAND_RE: Final = re.compile(
    r"\(\s*N?Rs\.?\s*'?\s*0{3}\s*'?\s*s?\s*\)", re.IGNORECASE
)


def detect_unit(page_text: str) -> str | None:
    """Return the emitted unit string for a summary-table page, or None.

    Reads the per-page unit annotation (the White Book stamps it on each summary
    table and it VARIES by edition — ADR-0011). Lakh is checked first so the
    five-zero form is never misread as the three-zero thousand form.
    """
    if _UNIT_LAKH_RE.search(page_text):
        return _UNIT_NPR_LAKH
    if _UNIT_THOUSAND_RE.search(page_text):
        return _UNIT_NPR_THOUSAND
    return None


# ---------------------------------------------------------------------------
# Fiscal-year detection — from the cover / table caption ("Fiscal Year 2020/21").
# ---------------------------------------------------------------------------

# Matches "Fiscal Year 2020/21" or "Fiscal Year 2015-16" (lead year + 2-digit
# tail). Tail is validated == (lead + 1) mod 100 in `_full_year_lead`.
_FY_RE: Final = re.compile(
    r"Fiscal\s+Year\s*(\d{4})\s*[/-]\s*(\d{2})\b", re.IGNORECASE
)


def _full_year_lead(lead: int, tail: int) -> int | None:
    """Return the AD lead year if ``tail == (lead+1) mod 100``, else None."""
    if tail != (lead + 1) % 100:
        return None
    return lead


def detect_ad_fiscal_year(text: str) -> int | None:
    """Return the AD fiscal-year lead year from a 'Fiscal Year YYYY/YY' label.

    Validates the two-digit tail equals (lead + 1) mod 100 so a stray pair is not
    misread as a fiscal year. Returns None when no valid label is present.
    """
    m = _FY_RE.search(text)
    if not m:
        return None
    return _full_year_lead(int(m.group(1)), int(m.group(2)))


# ---------------------------------------------------------------------------
# Table-caption anchors. The REAL summary tables co-occur with the unit
# annotation on the page; the Table-of-Contents page carries the captions but no
# unit annotation and yields no extractable 12-col table — so requiring BOTH the
# caption and a detected unit excludes the ToC deterministically.
# ---------------------------------------------------------------------------

_MINISTRYWISE_RE: Final = re.compile(r"Summary\s+of\s+Ministrywise", re.IGNORECASE)
# Donor table caption. Newer editions: "Development Partnerwise Summary" (with an
# optional "(DPs)"); older editions: a bare "Donor Summary". Either anchors the
# per-donor table; both forms verified in-corpus (FY2020/21 vs FY2013/14).
_PARTNERWISE_RE: Final = re.compile(
    r"(?:Development\s+Partner\w*\s*(?:\(?DPs\)?\s*)?Summary|\bDonor\s+Summary\b)",
    re.IGNORECASE,
)

# Dimension kinds.
_KIND_DONOR: Final[str] = "donor"
_KIND_SECTOR: Final[str] = "sector"

# Column layout. Both tables share the trailing block; the ministrywise table has
# ONE extra leading "GoN Budget" value column, so its value columns are shifted by
# +1. We address columns RELATIVE TO THE Total-Grant / Total-Loan positions, which
# are the only two we emit. For the 12-col donor table the layout is:
#   0 code | 1 name | 2 cash | 3 reimb | 4 direct | 5 commodity | 6 TOTAL GRANT
#   | 7 loan-direct | 8 loan-reimb | 9 loan-cash | 10 TOTAL LOAN | 11 Total
# Ministrywise inserts GoN Budget at col 2, pushing every later column +1
#   (13 cols; TOTAL GRANT at 7, TOTAL LOAN at 11, Total at 12).
_DONOR_TOTAL_GRANT_COL: Final[int] = 6
_DONOR_TOTAL_LOAN_COL: Final[int] = 10
_SECTOR_TOTAL_GRANT_COL: Final[int] = 7
_SECTOR_TOTAL_LOAN_COL: Final[int] = 11

# Minimum column counts to treat a row as a data row of each table.
_DONOR_MIN_COLS: Final[int] = 12
_SECTOR_MIN_COLS: Final[int] = 13

# A member CODE cell is a pure digit run (donor codes like "2101001"; budget heads
# like "305"). Used to reject header / caption / total rows.
_CODE_RE: Final = re.compile(r"^\d{2,8}$")

# Total / footer row markers (first cell). The grand-total row's first cell is
# "Total"; we skip it (its split sub-cells are a pdfplumber merge artifact anyway).
_TOTAL_TOKENS: Final[frozenset[str]] = frozenset({"total", "grand total", "कुल", "जम्मा"})


@dataclass(frozen=True)
class _TableSpec:
    """How to read one summary table: its dimension kind + Total-col positions."""

    kind: str
    min_cols: int
    grant_col: int
    loan_col: int


_DONOR_SPEC: Final = _TableSpec(
    kind=_KIND_DONOR,
    min_cols=_DONOR_MIN_COLS,
    grant_col=_DONOR_TOTAL_GRANT_COL,
    loan_col=_DONOR_TOTAL_LOAN_COL,
)
_SECTOR_SPEC: Final = _TableSpec(
    kind=_KIND_SECTOR,
    min_cols=_SECTOR_MIN_COLS,
    grant_col=_SECTOR_TOTAL_GRANT_COL,
    loan_col=_SECTOR_TOTAL_LOAN_COL,
)


# ---------------------------------------------------------------------------
# Dimensional fact contract (ADR-0015/0017) — mirrors the Yellow Book parser's
# DimensionalRowDraft / result wrapper field-for-field so the cloned ingest CLI
# reads the same ``dimensional_rows`` JSON.
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
class WhitebookResult:
    """White Book parser result carrying dimensional output only.

    The White Book emits no single-series ``staging_rows`` (the summary tables are
    dimensional matrices), so this wrapper mirrors the DNE/Yellow Book CLI's
    expected JSON shape: a ``dimensional_rows`` array plus ``status`` / ``errors``.
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


def _norm(cell: object) -> str:
    """Stringify a cell and collapse internal whitespace/newlines to a space."""
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def _is_code(cell_text: str) -> bool:
    """True if a cell is a pure budget-head / donor code (digits only)."""
    return bool(_CODE_RE.match(cell_text.strip()))


def _is_total_row(name: str) -> bool:
    """True for the grand-total / footer row (first cell is a total token)."""
    low = name.strip().lower()
    return low in _TOTAL_TOKENS or any(low.startswith(t) for t in _TOTAL_TOKENS)


def _parse_value(cell_text: str) -> float | None:
    """Parse a money cell to float; None for empty / dash / non-numeric.

    NRB/MoF use "-"/"–"/blank for "not applicable"; those become None (never
    fabricated as 0). A genuine source ``0`` is preserved as ``0.0``.
    """
    s = cell_text.strip()
    if s in ("", "-", "--", "–", "—", "N/A", "n/a", "NA", "...", "."):
        return None
    try:
        v = float(s.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN  # noqa: PLR0124
        return None
    return v


def _slugify_member(label: str) -> str:
    """Kebab slug of a donor / ministry name for ``dimension_value``.

    ASCII is lowercased; punctuation collapses to hyphens; whitespace runs fold to
    a single hyphen. The RAW label is kept as ``dimension_label`` so the original
    (including any pdfplumber artifact) stays traceable. Distinct member names do
    not collapse to one slug for the White Book's English vocabulary.
    """
    s = label.lower()
    s = re.sub(r"[\s.,/()\[\]{}:;\"'`*&+]+", " ", s)
    return re.sub(r"\s+", "-", s.strip())


def _annual_span(bs_fy_start: int) -> tuple[datetime, datetime]:
    """AD start/end bounding the BS fiscal-year span (mid-Shrawan..mid-Ashadh)."""
    start = mid_month_ad("Shrawan", bs_fy_start)
    end = mid_month_ad("Ashadh", bs_fy_start)
    return start, end


def _make_row(
    base_slug: str,
    base_name: str,
    kind: str,
    name_raw: str,
    value: float,
    unit: str,
    bs_fy_start: int,
    ad_start: datetime,
    ad_end: datetime,
) -> DimensionalRowDraft:
    """Build one dimensional fact for a base measure + value."""
    return DimensionalRowDraft(
        base_indicator_slug=base_slug,
        base_indicator_name=base_name,
        dimension_kind=kind,
        dimension_value=_slugify_member(name_raw),
        dimension_label=name_raw,
        value=value,
        unit=unit,
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
    spec: _TableSpec,
    unit: str,
    bs_fy_start: int,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Convert one summary table → per-member grant/loan dimensional facts.

    ``table_rows`` is the raw ``page.extract_tables()`` output for one summary
    table; ``spec`` names the dimension kind and the Total-Grant / Total-Loan
    column positions (which differ between the donor and ministrywise tables).
    A data row is code-led (col 0 a digit code) with a name in col 1; it emits a
    ``foreign-aid-grant`` fact when the Total-Grant cell parses and a
    ``foreign-aid-loan`` fact when the Total-Loan cell parses (a real ``0`` is
    kept; blank/dash is dropped). Header / caption / Total rows are skipped.
    Never raises.

    A code-led row whose BOTH total cells are non-empty but unparseable surfaces a
    single ``ValueUnparseable`` so data loss is visible, never silent (Rule 6).
    """
    ad_start, ad_end = _annual_span(bs_fy_start)
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    seen: set[tuple[str, str]] = set()

    for raw in table_rows:
        if len(raw) < spec.min_cols:
            continue
        code = _norm(raw[0])
        name = _norm(raw[1])
        if not name or _is_total_row(name) or _is_total_row(code):
            continue
        # A genuine member row is code-led. Rows without a code that survived the
        # skip filters are header / wrapped-label fragments.
        if not _is_code(code):
            continue

        grant_text = _norm(raw[spec.grant_col])
        loan_text = _norm(raw[spec.loan_col])
        grant = _parse_value(grant_text)
        loan = _parse_value(loan_text)
        if grant is None and loan is None:
            if grant_text or loan_text:  # non-empty but unparseable → visible
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=(
                            f"{spec.kind} {name!r}: neither Total Grant nor Total "
                            f"Loan parsed (grant={grant_text!r}, loan={loan_text!r})"
                        ),
                        source_excerpt=f"{code} | {name}",
                    )
                )
            continue

        if grant is not None:
            key = (_GRANT_SLUG, _slugify_member(name))
            if key not in seen:
                seen.add(key)
                rows.append(
                    _make_row(
                        _GRANT_SLUG, _GRANT_NAME, spec.kind, name, grant,
                        unit, bs_fy_start, ad_start, ad_end,
                    )
                )
        if loan is not None:
            key = (_LOAN_SLUG, _slugify_member(name))
            if key not in seen:
                seen.add(key)
                rows.append(
                    _make_row(
                        _LOAN_SLUG, _LOAN_NAME, spec.kind, name, loan,
                        unit, bs_fy_start, ad_start, ad_end,
                    )
                )

    return rows, errors


# ---------------------------------------------------------------------------
# PDF reading — locate the two summary tables and feed them to the core.
# ---------------------------------------------------------------------------


def _largest_table(page: object) -> list[list[object]] | None:
    """Return the page's largest extracted table (by row count), or None."""
    tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
    if not tables:
        return None
    return max(tables, key=len)


def parse_whitebook(source_document_path: str, source_document_id: str) -> WhitebookResult:
    """Parse one White Book PDF → foreign-aid dimensional facts (ADR-0017).

    Scans every page; on a page that carries a summary-table caption AND a
    detected unit annotation (which the Table-of-Contents page lacks), extracts
    that table and emits per-member ``foreign-aid-grant`` / ``foreign-aid-loan``
    facts. The donor table → ``dimension_kind='donor'``; the ministrywise table →
    ``dimension_kind='sector'``. The AD fiscal year is read from the cover / table
    caption and converted to BS via +57. Never raises on bad data: an
    unreadable / Preeti / CID / mislabelled edition yields typed errors and
    ``status='failure'``.
    """
    _ = source_document_id  # threaded for orchestrator-contract symmetry

    path = Path(source_document_path)
    if not path.exists():
        return WhitebookResult(
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
    summary_pages = 0

    try:
        with pdfplumber.open(str(path)) as pdf:
            page_texts = [page.extract_text() or "" for page in pdf.pages]

            # First pass: detect the AD fiscal year ANYWHERE in the document. The
            # ministrywise page can lack the English "Fiscal Year YYYY/YY" label
            # while the donor pages carry it (older editions), so we read the whole
            # document before dating any fact (ADR-0011 "read the document").
            ad_fy_start: int | None = None
            for text in page_texts:
                detected_fy = detect_ad_fiscal_year(text)
                if detected_fy is not None:
                    ad_fy_start = detected_fy
                    break

            # Second pass: extract the summary tables.
            for page, text in zip(pdf.pages, page_texts, strict=True):
                has_ministrywise = bool(_MINISTRYWISE_RE.search(text))
                has_partnerwise = bool(_PARTNERWISE_RE.search(text))
                if not (has_ministrywise or has_partnerwise):
                    continue
                unit = detect_unit(text)
                if unit is None:
                    # Caption but no unit annotation → Table-of-Contents page.
                    continue

                table = _largest_table(page)
                if table is None:
                    continue

                # The fiscal year must be known to date the facts.
                page_fy = ad_fy_start if ad_fy_start is not None else detect_ad_fiscal_year(text)
                if page_fy is None:
                    all_errors.append(
                        ParserError(
                            error_class="PeriodAmbiguous",
                            error_detail=(
                                "summary table found but no 'Fiscal Year YYYY/YY' "
                                "label located anywhere in the document — cannot "
                                "date the facts"
                            ),
                        )
                    )
                    continue
                bs_fy_start = _ad_fy_to_bs_start(page_fy)

                # A page may legitimately carry both captions (the donor table can
                # follow the ministrywise summary on one page); prefer the donor
                # spec when partnerwise is present so its narrower geometry wins.
                spec = _DONOR_SPEC if has_partnerwise else _SECTOR_SPEC
                summary_pages += 1
                page_rows, page_errors = extract_dimensional_rows(
                    table, spec, unit, bs_fy_start
                )
                all_rows.extend(page_rows)
                all_errors.extend(page_errors)
    except (OSError, ValueError) as exc:
        return WhitebookResult(
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

    if summary_pages == 0:
        all_errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    "No clean English summary table (with a unit annotation) found "
                    "on any page — this edition is likely Preeti-encoded, CID-broken,"
                    " or a mislabelled non-White-Book document. Documented "
                    "infeasibility per ADR-0017; no values fabricated. See "
                    "scrapers/mof_whitebook/parser.py STEP-0 assessment."
                ),
            )
        )

    if not all_rows:
        return WhitebookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=all_errors
            or [
                ParserError(
                    error_class="Other",
                    error_detail=(
                        "NoDataExtracted: summary table present but no member rows "
                        "parsed"
                    ),
                )
            ],
        )

    status: ParserStatus = "partial" if all_errors else "success"
    return WhitebookResult(
        status=status,
        parser_version=PARSER_VERSION,
        dimensional_rows=all_rows,
        errors=all_errors,
    )


def _main() -> None:
    """CLI entrypoint (orchestrator contract — mirror of mof_yellowbook.parser).

    Argv: ``parser.py <source_document_path> <source_document_id>``. Writes the
    result JSON (including the ``dimensional_rows`` key the ingest CLI reads) to
    stdout. Datetimes are ISO-8601 strings. Exit codes: 0 = ran (status may be
    failure), 2 = usage error.
    """
    expected_argv = 3  # progname + path + doc id
    if len(sys.argv) != expected_argv:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse_whitebook(sys.argv[1], sys.argv[2])
    json.dump(result.to_json_dict(), sys.stdout)


if __name__ == "__main__":
    _main()
