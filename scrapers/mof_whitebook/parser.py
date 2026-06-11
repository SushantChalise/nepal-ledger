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
      2. LEGACY PREETI/SIDDHI editions (FY 2062/63, 2064/65, 2065/66, 2066/67,
         2067/68 = AD 2005/06–2010/11): the text layer is a legacy 8-bit Nepali
         font byte-map. The COVER is Preeti (``dGqfnout`` = "मन्त्रालयगत"); the two
         SUMMARY TABLES are typeset in **SiddhiNormal** (a Preeti-family face that
         shares Preeti's consonant/vowel layout but paints Arabic digits on the
         ASCII digit row and relocates a few retroflex glyphs). This is
         **deterministically recoverable** (ADR-0021 Tier 1a) by the byte-map +
         reordering in ``_common/preeti.py`` — NOT OCR, NOT AI. The summary-table
         GEOMETRY is identical to the clean editions (same 12-/13-column block),
         so only the LABEL cells need transliteration; the VALUE cells are already
         ASCII Arabic digits. Recovered with confidence ``B`` (see
         ``_parse_legacy_edition``). The unit is stamped in Devanagari
         (``(रू.हजारमा)`` = Rs in thousand → ``npr_thousand``) and the BS fiscal
         year is printed as ASCII digits in the caption (``2065/66``).
      3. A MISLABELLED file ("...White Book FY 2021-22_azz4yjf.pdf") whose content
         is actually the **Intergovernmental Fiscal Transfer** book (Devanagari)
         and is **CID-broken** (``(cid:N)`` glyphs, no ToUnicode). Not a White
         Book; **deferred** (it belongs to a different source).
      4. MODERN editions (FY 2023/24 / BS 2080/81 onward, hosted under the new MoF
         IERD "Source Book / सेतो किताब" division section): clean English, but the
         summary tables changed shape — the member code+name are MERGED into one
         cell and the value rows have no horizontal rules, so pdfplumber collapses
         them. Handled by a WORD-POSITIONAL reader (``_parse_modern_edition`` /
         ``extract_dimensional_rows_modern``) that anchors columns on the
         "Total Grant" / "Total Loan" header labels (v0.3.0). Verified donor==
         sector on FY 2023/24, 2024/25, 2025/26. Unit is "(Rs. in '00000')" →
         npr_lakh.

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

Wrapped-name row recovery (v0.2.1): when a member name wraps to a second visual
line, pdfplumber occasionally fails to split that row into the table grid and dumps
the WHOLE row into col 0 as one space-joined blob (other cells empty). The value
columns are the maximal contiguous money-token run in that blob, so the row is
reconstructed deterministically into ``[code, name, *values]`` (see
``_expand_merged_row``) — no AI, no OCR. This recovered two ministry rows silently
dropped from the FY2070/71 sector table (its total read 95,934,658 instead of the
printed 113,240,000 = the donor total), the DATA_AUDIT §5 G3 reconciliation flag.

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

from _common.devanagari_normalization import normalize_devanagari_text
from _common.periods import (
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
)
from _common.preeti import legacy_font_for, to_unicode
from _common.types import ParserError, ParserStatus, ReportingPeriodType

PARSER_VERSION: Final[str] = "0.3.0"
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


# Devanagari unit annotation (legacy editions stamp "(रू.हजारमा)" = Rs in
# thousand, or "(रू.लाखमा)" = Rs in lakh) — matched on the TRANSLITERATED page
# text. हजार = thousand, लाख = lakh. Kept separate from the English forms above so
# the clean-edition path is untouched.
_UNIT_DEV_LAKH_RE: Final = re.compile(r"लाख")
_UNIT_DEV_THOUSAND_RE: Final = re.compile(r"हजार")


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


def detect_unit_devanagari(decoded_text: str) -> str | None:
    """Return the unit for a legacy edition from its TRANSLITERATED page text.

    The Preeti/Siddhi editions stamp the unit in Devanagari (``(रू.हजारमा)`` /
    ``(रू.लाखमा)``). Lakh (लाख) is checked first by symmetry with ``detect_unit``.
    Returns None when neither marker is present.
    """
    if _UNIT_DEV_LAKH_RE.search(decoded_text):
        return _UNIT_NPR_LAKH
    if _UNIT_DEV_THOUSAND_RE.search(decoded_text):
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


# Legacy editions print the BS fiscal year as plain ASCII digits in the caption
# (the summary-table caption decodes to "आर्थिक वर्ष 2065/66" with 2065/66 already
# ASCII). BS lead years are 20xx (2062..2067 in-corpus). The tail is validated ==
# (lead+1) mod 100, same discipline as the AD detector.
_BS_FY_RE: Final = re.compile(r"\b(20\d{2})\s*[/-]\s*(\d{2})\b")
# Plausible BS fiscal-year window for the White-Book corpus (BS 2060..2090 ≈ AD
# 2003..2033). Excludes a stray AD year like 2015 that would also match \b20\d\d.
_BS_FY_MIN: Final[int] = 2060
_BS_FY_MAX: Final[int] = 2090


def detect_bs_fiscal_year(text: str) -> int | None:
    """Return the BS fiscal-year lead year from a legacy edition's ASCII caption.

    Scans for a ``20YY/YY`` pair, validates the tail == (lead+1) mod 100, and
    requires the lead to fall inside the BS White-Book window so an AD year
    (e.g. a publication "2015") is not misread as a BS fiscal year. Returns the
    first plausible BS lead year, or None.
    """
    for m in _BS_FY_RE.finditer(text):
        lead = int(m.group(1))
        if lead < _BS_FY_MIN or lead > _BS_FY_MAX:
            continue
        if _full_year_lead(lead, int(m.group(2))) is not None:
            return lead
    return None


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

# Devanagari caption anchors for the legacy editions (matched on TRANSLITERATED
# page text). मन्त्रालयगत = "Ministrywise" (sector table); दातृ = "donor" (दातृगत
# सारांश / दातृ राष्ट्र-संस्था — both head the per-donor table). Verified across
# the in-corpus FY2062/63..2067/68 editions.
_MINISTRYWISE_DEV_RE: Final = re.compile(r"मन्त्रालयगत")
_PARTNERWISE_DEV_RE: Final = re.compile(r"दातृ")

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

# A money token inside a merged-row blob: an Arabic-digit run with optional
# thousands commas and optional decimal/sign. Anchored so a name word never
# matches. Used ONLY by the merged-row recovery (`_expand_merged_row`).
_MONEY_TOKEN_RE: Final = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")

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
# MODERN layout (FY 2023/24 / BS 2080/81 onward) — added v0.3.0.
#
# From the FY 2023/24 edition the summary tables changed shape (verified on FY
# 2023/24, 2024/25, 2025/26 — all reconcile donor==sector to the rupee):
#   1. The member CODE and NAME are MERGED ("301 Office of Prime Minister...",
#      "2101001 ADB - General") — older editions split them into two cells.
#   2. The summary pages carry ruled VERTICAL column lines but NO horizontal row
#      rules, so pdfplumber's table extraction collapses every right-aligned VALUE
#      into one cell — the header row splits cleanly but the data rows do not.
#
# So the modern path is WORD-POSITIONAL, not table-based: cluster the page's words
# into visual lines, anchor the two columns we emit on the UNIQUE "Total Grant" /
# "Total Loan" sub-header labels (their right-edge x), and match each data row's
# right-aligned numeric words to those anchors by nearest right edge. This needs
# no hardcoded x-coordinates — the anchors are read from each table's own header,
# so it survives the small per-edition column drift (anchors ranged 517–533 for
# the grant column, 729–759 for the loan column across the three editions).
#
# The trailing value block is Cash | Reimbursable | Direct Payment | Commodity |
# TOTAL GRANT | Direct Payment | Reimbursable | Cash | TOTAL LOAN | Total Budget;
# the ministrywise table additionally carries a leading GoN-Budget column. We emit
# only the two headline totals, so the block's internal columns are never read.
#
# The donor summary may span several pages; only the FIRST carries the caption +
# sub-header. A continuation page has no header, so its anchors are inherited from
# the caption page (the column x-positions are identical across a table's pages).
# The summary section ends at the first "Details of Sources" detail page.

# A member CODE is a standalone digit word (donor codes like "2101001"; budget
# heads like "301"). Reuses the same shape as `_CODE_RE` / `_is_code`.
_MODERN_CODE_RE: Final = re.compile(r"^\d{2,8}$")

# A value word: an Arabic-digit run with optional thousands commas / decimal /
# sign. Same shape as `_MONEY_TOKEN_RE`; named here for the word-positional reader.
_MODERN_VALUE_RE: Final = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")

# A data row's value words are right-aligned; a value belongs to the Total-Grant
# (or Total-Loan) column when its right edge is within this many points of that
# header label's right edge. Columns are ~56 pt apart, so 25 pt is a safe margin.
_MODERN_ANCHOR_TOL: Final[float] = 25.0

# Words within this vertical distance share a visual line (font is ~9 pt; rows are
# ~12 pt apart). Used to cluster `extract_words()` output into table rows.
_MODERN_LINE_TOL: Final[float] = 3.0

# The per-project detail section opens "Details of Sources for Projects Financed
# with Foreign Assistance" — a modern-edition marker absent from the clean/legacy
# editions. It bounds the summary section (the donor summary may run several
# caption-less pages before it).
_DETAILS_RE: Final = re.compile(r"Details\s+of\s+Sources", re.IGNORECASE)


@dataclass(frozen=True)
class _ModernAnchors:
    """Right-edge x of the 'Total Grant' and 'Total Loan' header labels for one
    modern summary table. Read from the table's caption page, reused on its
    caption-less continuation pages."""

    grant_x1: float
    loan_x1: float


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
# Wrapped-row recovery — a pdfplumber column-merge artifact (no AI, deterministic).
#
# When a member's NAME wraps to a second visual line (e.g. "Ministry of Science
# Technology and / Environment"), pdfplumber occasionally fails to assign that
# row's cells to the table grid and instead dumps the WHOLE row into col 0 as a
# single space-joined blob, leaving the remaining cells empty:
#
#   ["331 Ministry of Science Technology and 2,559,691 0 711,218 2,063,869 0
#     2,775,087 0 306,180 0 306,180 5,640,958 Environment", "", "", ... ]
#
# The numeric VALUE columns are the maximal contiguous run of money tokens in that
# blob (the leading code is one isolated number, broken from the run by the name
# words; the wrapped name fragment trails after the numbers). Because the run has
# exactly ``spec.min_cols - 2`` values (the two non-value columns are code + name)
# in the SAME order as a normal row, we reconstruct ``[code, name, *values]`` — a
# faithful, spec-agnostic recovery that the normal row logic then reads via the
# spec's grant/loan column offsets. This was the FY2070/71 sector-table data loss
# (two ministry rows dropped → donor≠sector by ~15%); see README "Known breakage".
# ---------------------------------------------------------------------------


def _longest_numeric_run(tokens: list[str]) -> tuple[int, int]:
    """Return (start, length) of the longest contiguous money-token run, or (-1, 0).

    A money token is ``_MONEY_TOKEN_RE`` (digit run, optional commas/decimal/sign).
    The leading member code is a single isolated number separated from the value
    block by the name words, so it is never the longest run; the contiguous value
    block (length == column count − 2) wins.
    """
    best_start, best_len = -1, 0
    i, n = 0, len(tokens)
    while i < n:
        if _MONEY_TOKEN_RE.match(tokens[i]):
            j = i
            while j < n and _MONEY_TOKEN_RE.match(tokens[j]):
                j += 1
            if (j - i) > best_len:
                best_start, best_len = i, j - i
            i = j
        else:
            i += 1
    return best_start, best_len


def _expand_merged_row(raw: list[object], spec: _TableSpec) -> list[object] | None:
    """Reconstruct a merged-blob row → ``[code, name, *values]``, or None.

    Recognises the pdfplumber wrapped-name merge artifact: col 0 is a blob string
    whose first token is a member code, whose remaining table cells are all empty
    (so it is NOT a normally-split row), and which contains a contiguous money-token
    run of EXACTLY ``spec.min_cols - 2`` values (the full value block). Returns a
    reconstructed row of width ``spec.min_cols`` so the caller reads it identically
    to a clean row; returns None for anything that is not this exact artifact (so a
    real Total row, a header, or a normally-split row is untouched).
    """
    if not raw:
        return None
    blob = _norm(raw[0])
    # The artifact crams the whole row into col 0; every other cell must be empty.
    if any(_norm(c) for c in raw[1:]):
        return None
    tokens = blob.split()
    expected_min_tokens = 3  # code + ≥1 name word + ≥1 value
    if len(tokens) < expected_min_tokens or not _is_code(tokens[0]):
        return None
    expected_values = spec.min_cols - 2  # columns minus code + name
    start, length = _longest_numeric_run(tokens)
    if length != expected_values or start <= 0:
        return None
    code = tokens[0]
    values = tokens[start : start + length]
    # Name = the non-value tokens (between code and the run, plus any wrapped tail).
    name_tokens = tokens[1:start] + tokens[start + length :]
    name = " ".join(name_tokens)
    if not name:
        return None
    return [code, name, *values]


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

    for original in table_rows:
        # Recover a pdfplumber wrapped-name merge artifact (whole row dumped into
        # col 0, other cells empty) into a faithful [code, name, *values] row;
        # leaves a normally-split row untouched (returns None). Deterministic — no
        # AI. See `_expand_merged_row` and the README "Known breakage modes".
        raw = _expand_merged_row(original, spec) or original
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


def _nearest_value(
    value_words: list[tuple[str, float]], anchor_x1: float
) -> float | None:
    """Return the parsed value whose right edge is nearest ``anchor_x1`` within
    ``_MODERN_ANCHOR_TOL``, else None (the column is blank for this row).

    ``value_words`` is ``[(text, x1), ...]`` for the numeric words on one row.
    """
    best: float | None = None
    best_dist = _MODERN_ANCHOR_TOL
    for text, x1 in value_words:
        dist = abs(x1 - anchor_x1)
        if dist < best_dist:
            best_dist = dist
            best = _parse_value(text)
    return best


def extract_dimensional_rows_modern(
    word_lines: list[list[dict[str, object]]],
    anchors: _ModernAnchors,
    kind: str,
    unit: str,
    bs_fy_start: int,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """MODERN-layout core (FY 2023/24+) — WORD-POSITIONAL, no table grid.

    ``word_lines`` is the page clustered into visual lines (``_word_lines``); each
    word is a pdfplumber dict with ``text`` / ``x0`` / ``x1``. A data row starts
    with a standalone digit CODE word, followed by the member-NAME words, then the
    right-aligned numeric value words. The Total-Grant / Total-Loan values are the
    numeric words whose right edge is nearest the ``anchors`` (read from the
    table's header). A real ``0`` is kept; a blank column yields None and emits no
    fact; the caption / header / Total rows (no leading code word) are skipped. A
    code-led row that has value words but matches NEITHER anchor surfaces one
    ``ValueUnparseable`` so data loss stays visible (Rule 6). Never raises.
    """
    ad_start, ad_end = _annual_span(bs_fy_start)
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    seen: set[tuple[str, str]] = set()

    for words in word_lines:
        if not words:
            continue
        head = _norm(words[0].get("text"))
        if not _MODERN_CODE_RE.match(head):
            # Header / caption / sub-header / Total row: no leading code word.
            continue
        # Name = leading non-numeric words; values = the numeric words after them.
        name_parts: list[str] = []
        value_words: list[tuple[str, float]] = []
        for w in words[1:]:
            text = _norm(w.get("text"))
            if _MODERN_VALUE_RE.match(text):
                x1 = w.get("x1")
                if isinstance(x1, (int, float)):
                    value_words.append((text, float(x1)))
            elif not value_words:
                name_parts.append(text)
            # A non-numeric word AFTER the value block began (e.g. a wrapped name
            # fragment trailing the row) is ignored — names never interleave.
        name = " ".join(name_parts).strip()
        if not name or _is_total_row(name):
            continue

        grant = _nearest_value(value_words, anchors.grant_x1)
        loan = _nearest_value(value_words, anchors.loan_x1)
        if grant is None and loan is None:
            if value_words:  # had numbers but neither hit an anchor → visible
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=(
                            f"{kind} {name!r}: value words present but none aligned "
                            f"to the Total-Grant/Total-Loan columns "
                            f"(values={[t for t, _ in value_words]})"
                        ),
                        source_excerpt=f"{head} | {name}",
                    )
                )
            continue

        if grant is not None:
            key = (_GRANT_SLUG, _slugify_member(name))
            if key not in seen:
                seen.add(key)
                rows.append(
                    _make_row(
                        _GRANT_SLUG, _GRANT_NAME, kind, name, grant,
                        unit, bs_fy_start, ad_start, ad_end,
                    )
                )
        if loan is not None:
            key = (_LOAN_SLUG, _slugify_member(name))
            if key not in seen:
                seen.add(key)
                rows.append(
                    _make_row(
                        _LOAN_SLUG, _LOAN_NAME, kind, name, loan,
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


# ---------------------------------------------------------------------------
# Legacy-font (Preeti/Siddhi) recovery — ADR-0021 Tier 1a.
# ---------------------------------------------------------------------------

# Minimum share of legacy-font glyphs on a page to treat it as a legacy edition.
# The summary-table pages are ~95% Siddhi (a few Latin column-rule glyphs); 0.5
# is a safe floor that still excludes the clean English editions (0% legacy).
_LEGACY_DOMINANCE_THRESHOLD: Final[float] = 0.5
# Only the LABEL columns (member name + total-row marker) are legacy text; the
# value cells are ASCII Arabic digits. Transliterating cols 0–1 leaves the
# numeric value columns untouched (digits pass straight through every map).
_LEGACY_LABEL_COLS: Final[tuple[int, ...]] = (0, 1)


def _summary_table_for_spec(
    page: object, spec: _TableSpec
) -> list[list[object]] | None:
    """Return the legacy page's summary table for ``spec``, or None.

    The legacy summary table has the SAME stable geometry as the clean editions:
    the donor table is exactly 12 columns and the ministrywise table 13. Late
    project-detail / annex pages in the legacy books also carry the donor caption
    and unit, but pdfplumber fragments them into wide (18–20 col) tables with no
    coherent code-led data rows. Selecting the largest-by-rows table **whose max
    width equals the spec's column count** picks the true summary and rejects the
    fragmented project pages deterministically (no heuristics, no page-order
    assumptions). Falls back to None when the page has no spec-width table.
    """
    tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
    qualifying = [
        t for t in tables if t and max(len(r) for r in t) == spec.min_cols
    ]
    if not qualifying:
        return None
    return max(qualifying, key=len)


def _dominant_legacy_font(page: object) -> str | None:
    """Return the legacy char-map name if a page is >50% legacy-font glyphs.

    Counts ``page.chars`` by ``fontname`` class (``_common.preeti.legacy_font_for``)
    and returns the dominant legacy map name when legacy glyphs clear the
    threshold, else None (a clean-Unicode/Latin page). Used to route a page to the
    Tier-1a transliteration branch.
    """
    chars: list[dict[str, object]] = getattr(page, "chars", [])  # type: ignore[assignment]
    if not chars:
        return None
    legacy = 0
    counts: dict[str, int] = {}
    for ch in chars:
        font = ch.get("fontname")
        map_name = legacy_font_for(font if isinstance(font, str) else None)
        if map_name is not None:
            legacy += 1
            counts[map_name] = counts.get(map_name, 0) + 1
    if not counts or legacy / len(chars) < _LEGACY_DOMINANCE_THRESHOLD:
        return None
    return max(counts, key=lambda k: counts[k])


def _decode_legacy(text: str, font: str) -> str:
    """Transliterate legacy-font text to Unicode, then apply the Devanagari
    OCR-substitution normalization pass (ADR-0021 sequencing: translit → normalize).
    """
    return normalize_devanagari_text(to_unicode(text, font))


def _transliterate_label_columns(
    table: list[list[object]], font: str
) -> list[list[object]]:
    """Return a copy of ``table`` with the label columns (0,1) transliterated.

    Only the member-name / total-marker columns carry legacy text; the value
    columns are ASCII digits and are copied verbatim (numbers must NOT be touched
    — ADR-0021 prioritizes value-correctness). The decoded label keeps its raw
    form's information so ``_slugify_member`` / ``dimension_label`` stay meaningful.
    """
    out: list[list[object]] = []
    for row in table:
        new_row = list(row)
        for col in _LEGACY_LABEL_COLS:
            if col < len(new_row) and isinstance(new_row[col], str):
                new_row[col] = _decode_legacy(new_row[col], font)
        out.append(new_row)
    return out


# ---------------------------------------------------------------------------
# Modern-edition reading (FY 2023/24+) — merged code+name, lines-v/text-h grid.
# ---------------------------------------------------------------------------


def _word_top(w: dict[str, object]) -> float | None:
    top = w.get("top")
    return float(top) if isinstance(top, (int, float)) else None


def _word_x0(w: dict[str, object]) -> float:
    x0 = w.get("x0")
    return float(x0) if isinstance(x0, (int, float)) else 0.0


def _word_lines(page: object) -> list[list[dict[str, object]]]:
    """Cluster a page's words into visual lines (rows), each sorted left→right.

    Words are grouped by vertical proximity: a word joins the current line while
    its ``top`` is within ``_MODERN_LINE_TOL`` of the line's first word; otherwise
    a new line starts. Proximity clustering (not fixed buckets) avoids splitting a
    single visual line across a rounding boundary. Returns lines top-to-bottom;
    each word is the pdfplumber dict (``text`` / ``x0`` / ``x1`` / ``top``).
    """
    words: list[dict[str, object]] = page.extract_words(  # type: ignore[attr-defined]
        use_text_flow=False, keep_blank_chars=False
    )
    # Pair each word with its resolved top, dropping words without a numeric top,
    # then sort by (top, x0). Keeping top alongside the word avoids re-deriving it
    # (and an Optional in the sort key).
    placed: list[tuple[float, dict[str, object]]] = []
    for w in words:
        top = _word_top(w)
        if top is not None:
            placed.append((top, w))
    placed.sort(key=lambda pair: (pair[0], _word_x0(pair[1])))
    lines: list[list[dict[str, object]]] = []
    line_top: float | None = None
    for top, w in placed:
        if line_top is None or top - line_top > _MODERN_LINE_TOL:
            lines.append([w])
            line_top = top
        else:
            lines[-1].append(w)
    for line in lines:
        line.sort(key=_word_x0)
    return lines


def _find_total_anchors(word_lines: list[list[dict[str, object]]]) -> _ModernAnchors | None:
    """Read the 'Total Grant' / 'Total Loan' header anchors from a summary page.

    Scans for the sub-header line where "Total" is immediately followed by "Grant"
    and (on the same or another line) by "Loan", taking the right edge of the
    "Grant" / "Loan" word as each column's anchor. Returns None when either label
    is absent (a caption-less continuation page — the caller reuses the caption
    page's anchors).
    """
    grant_x1: float | None = None
    loan_x1: float | None = None
    for words in word_lines:
        for i in range(len(words) - 1):
            if _norm(words[i].get("text")) != "Total":
                continue
            following = _norm(words[i + 1].get("text"))
            x1 = words[i + 1].get("x1")
            if not isinstance(x1, (int, float)):
                continue
            if following == "Grant":
                grant_x1 = float(x1)
            elif following == "Loan":
                loan_x1 = float(x1)
    if grant_x1 is None or loan_x1 is None:
        return None
    return _ModernAnchors(grant_x1=grant_x1, loan_x1=loan_x1)


def _is_modern_edition(pages: list[object], page_texts: list[str]) -> bool:
    """STRUCTURAL detection: does this edition use the MODERN merged-code+name
    layout? Decided on the FIRST summary page (caption + unit) by whether its
    pdfplumber table isolates the member CODE in its own cell.

    The "Details of Sources" detail section is NOT a reliable modern marker — the
    clean FY 2020/21 and FY 2070/71 editions carry it too. The reliable signal is
    the summary table's geometry: clean/legacy editions put the bare code in col 0
    (``"2101001"`` | ``"ADB - General"``); modern editions merge it with the name
    (``"301 Office of Prime Minister..."``), so the default table has no
    bare-code-led row. Returns False on any ambiguity so the established
    clean/legacy path remains the default.
    """
    for pidx, text in enumerate(page_texts):
        if _DETAILS_RE.search(text):
            break  # reached the detail section without a modern summary → not modern
        if not (_MINISTRYWISE_RE.search(text) or _PARTNERWISE_RE.search(text)):
            continue
        if detect_unit(text) is None:
            continue  # a Table-of-Contents page (caption but no unit annotation)
        page = pages[pidx]
        tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
        largest = max(tables, key=len) if tables else []
        if any(row and _is_code(_norm(row[0])) for row in largest):
            return False  # bare code isolated in col 0 → clean/legacy geometry
        # No isolated code: confirm the modern merged signature in the page words —
        # a code word immediately followed on the same line by a NON-numeric name
        # word. Guards against treating an unreadable page as "modern".
        for line in _word_lines(page):
            if (
                len(line) >= 2
                and _MODERN_CODE_RE.match(_norm(line[0].get("text")))
                and not _MODERN_VALUE_RE.match(_norm(line[1].get("text")))
            ):
                return True
        return False
    return False


def _parse_modern_edition(
    pages: list[object],
    page_texts: list[str],
    bs_fy_start: int | None,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Parse a MODERN-layout edition (FY 2023/24+); return ``([], [])`` when the
    edition is not modern so the caller falls back to the clean/legacy reader.

    The summary section is the page span before the first "Details of Sources"
    detail page. Within it the ministrywise summary comes first, then the donor
    summary, which may run across several caption-less continuation pages. A page
    is classified by its caption when it has one and otherwise inherits the
    current table kind + anchors (the column x-positions are identical across a
    table's pages). The modern path only fires when a summary page actually yields
    Total-Grant/Total-Loan anchors, so it never mis-handles a clean/legacy edition
    (which has no "Details of Sources" section anyway).
    """
    detail_start = next(
        (i for i, t in enumerate(page_texts) if _DETAILS_RE.search(t)), None
    )
    # No detail section, or it is the very first page → not a modern White Book.
    if not detail_start:
        return [], []

    # The unit annotation ("(Rs. in '00000')") is uniform across the summary
    # section and stamped only on the caption pages, not the continuation pages.
    # Detect it ONCE so continuation donors are not skipped for lack of a stamp.
    unit: str | None = None
    for text in page_texts[:detail_start]:
        unit = detect_unit(text)
        if unit is not None:
            break
    if unit is None:
        return [], []

    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    matched_modern = False
    kind: str | None = None
    anchors: _ModernAnchors | None = None

    for pidx in range(detail_start):
        text = page_texts[pidx]
        # A caption opens a new table: switch kind and reset the anchors so they
        # are re-read from THIS table's own header. The kind + anchors then PERSIST
        # onto the caption-less continuation pages (the donor summary overflows
        # several pages; only the first carries the caption + header).
        if _MINISTRYWISE_RE.search(text):
            kind, anchors = _KIND_SECTOR, None
        elif _PARTNERWISE_RE.search(text):
            kind, anchors = _KIND_DONOR, None
        if kind is None:
            continue  # a pre-summary page (cover / ToC) before the first caption

        lines = _word_lines(pages[pidx])
        if anchors is None:
            anchors = _find_total_anchors(lines)
        if anchors is None:
            continue  # header not yet seen for this table → cannot place columns
        matched_modern = True
        if bs_fy_start is None:
            errors.append(
                ParserError(
                    error_class="PeriodAmbiguous",
                    error_detail=(
                        "modern summary table found but no 'Fiscal Year YYYY/YY' "
                        "label located in the document — cannot date the facts"
                    ),
                )
            )
            continue
        page_rows, page_errors = extract_dimensional_rows_modern(
            lines, anchors, kind, unit, bs_fy_start
        )
        rows.extend(page_rows)
        errors.extend(page_errors)

    if not matched_modern:
        return [], []
    return rows, errors


def parse_whitebook(source_document_path: str, source_document_id: str) -> WhitebookResult:
    """Parse one White Book PDF → foreign-aid dimensional facts (ADR-0017).

    Scans every page; on a page that carries a summary-table caption AND a
    detected unit annotation (which the Table-of-Contents page lacks), extracts
    that table and emits per-member ``foreign-aid-grant`` / ``foreign-aid-loan``
    facts. The donor table → ``dimension_kind='donor'``; the ministrywise table →
    ``dimension_kind='sector'``.

    Two encodings are handled (ADR-0021):
      * CLEAN editions — English captions; AD fiscal year ("Fiscal Year YYYY/YY")
        → BS via +57; unit from the English annotation.
      * LEGACY Preeti/Siddhi editions (Tier 1a) — a page that is >50% legacy-font
        glyphs is transliterated via ``_common.preeti``; captions/unit are matched
        on the Devanagari decode, the BS fiscal year is read from the ASCII digits
        in the decoded caption (already BS — no offset), and only the LABEL columns
        are transliterated (value cells are ASCII and copied verbatim).

    Never raises on bad data: an unreadable / CID-broken / mislabelled edition
    yields typed errors and ``status='failure'``.
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
            # Per-page legacy-font map name (None for clean-Unicode pages). A whole
            # legacy summary page is one font class, so we transliterate its
            # extract_text() with that map for caption/unit/FY detection (ADR-0021).
            page_fonts = [_dominant_legacy_font(page) for page in pdf.pages]
            page_decoded = [
                _decode_legacy(text, font) if font else text
                for text, font in zip(page_texts, page_fonts, strict=True)
            ]

            # First pass: date the document ONCE (ADR-0011 "read the document").
            # Clean editions carry an English "Fiscal Year YYYY/YY" (AD → +57 to
            # BS); legacy editions carry the BS fiscal year as ASCII digits in the
            # decoded caption (already BS — no offset). Prefer the AD label when
            # present so a clean edition's behaviour is unchanged.
            bs_fy_start_doc: int | None = None
            for text in page_texts:
                ad_fy = detect_ad_fiscal_year(text)
                if ad_fy is not None:
                    bs_fy_start_doc = _ad_fy_to_bs_start(ad_fy)
                    break
            if bs_fy_start_doc is None:
                # Read the BS year from the RAW text: the legacy caption prints the
                # year as ASCII Arabic digits ("...jif{{2065/66"), so the year +
                # "/" survive verbatim. (Transliteration would turn "/" into र.)
                for text, font in zip(page_texts, page_fonts, strict=True):
                    if font is None:
                        continue
                    bs_fy = detect_bs_fiscal_year(text)
                    if bs_fy is not None:
                        bs_fy_start_doc = bs_fy
                        break

            # MODERN path (FY 2023/24+): word-positional summary reader, gated on a
            # STRUCTURAL check so it never hijacks a clean/legacy edition (both of
            # which also carry a "Details of Sources" section). ADR-0011 — read the
            # document's actual geometry, don't guess from the fiscal year.
            pages_list = list(pdf.pages)
            if _is_modern_edition(pages_list, page_texts):
                modern_rows, modern_errors = _parse_modern_edition(
                    pages_list, page_texts, bs_fy_start_doc
                )
                if modern_rows:
                    status_m: ParserStatus = "partial" if modern_errors else "success"
                    return WhitebookResult(
                        status=status_m,
                        parser_version=PARSER_VERSION,
                        dimensional_rows=modern_rows,
                        errors=modern_errors,
                    )

            # Second pass: extract the summary tables (clean and legacy paths).
            for page, raw, decoded, font in zip(
                pdf.pages, page_texts, page_decoded, page_fonts, strict=True
            ):
                is_legacy = font is not None
                caption_text = decoded if is_legacy else raw
                has_ministrywise = bool(
                    (_MINISTRYWISE_DEV_RE if is_legacy else _MINISTRYWISE_RE).search(
                        caption_text
                    )
                )
                has_partnerwise = bool(
                    (_PARTNERWISE_DEV_RE if is_legacy else _PARTNERWISE_RE).search(
                        caption_text
                    )
                )
                if not (has_ministrywise or has_partnerwise):
                    continue
                unit = (
                    detect_unit_devanagari(decoded) if is_legacy else detect_unit(raw)
                )
                if unit is None:
                    # Caption but no unit annotation → Table-of-Contents page.
                    continue

                # A page may legitimately carry both captions (the donor table can
                # follow the ministrywise summary on one page); prefer the donor
                # spec when partnerwise is present so its narrower geometry wins.
                spec = _DONOR_SPEC if has_partnerwise else _SECTOR_SPEC

                # Clean editions: largest table (status quo). Legacy editions: the
                # spec-WIDTH table, which rejects the wide fragmented project-detail
                # pages that also carry the caption+unit (ADR-0021 geometry guard).
                table = (
                    _summary_table_for_spec(page, spec)
                    if is_legacy
                    else _largest_table(page)
                )
                if table is None:
                    continue
                if is_legacy and font is not None:
                    # Transliterate ONLY the label columns; values stay ASCII.
                    table = _transliterate_label_columns(table, font)

                # The fiscal year must be known to date the facts. Legacy pages may
                # also carry the BS year (ASCII) in their own raw caption.
                page_fy = bs_fy_start_doc
                if page_fy is None and is_legacy:
                    page_fy = detect_bs_fiscal_year(raw)
                if page_fy is None:
                    all_errors.append(
                        ParserError(
                            error_class="PeriodAmbiguous",
                            error_detail=(
                                "summary table found but no fiscal-year label located "
                                "anywhere in the document — cannot date the facts"
                            ),
                        )
                    )
                    continue
                bs_fy_start = page_fy

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
                    "No summary table (with a unit annotation) found on any page — "
                    "neither a clean English nor a legacy Preeti/Siddhi edition. This "
                    "edition is likely CID-broken or a mislabelled non-White-Book "
                    "document. Documented infeasibility per ADR-0017/0021; no values "
                    "fabricated. See scrapers/mof_whitebook/parser.py STEP-0 assessment."
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
