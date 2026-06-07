"""MoF Economic Survey statistical-annex parser — deterministic Python.

Source: Ministry of Finance, **Economic Survey** (आर्थिक सर्वेक्षण) — the
canonical annual macro compendium. Source id ``mof-economic-survey-annual``.
In-repo corpus: three editions at
``Financial Data/mof_documents/economic_survey/``:
  - ``Economic_Survey_2023-24_EN.pdf``  (English "unofficial translation", 536 pp)
  - ``Economic_Survey_2080-81_NP.pdf``  (Nepali / Devanagari, 547 pp)
  - ``Economic_Survey_2081-82.pdf``     (Nepali body + English annex, 517 pp)

Decision policy (ADR-0016): **annex-only parsing** — extract ONLY tables that are
cleanly, deterministically parseable; DEFER (document) anything CID-broken or
RTL-mirrored. The Economic Survey is the *hardest* ingest item: its encoding is
wildly mixed page-to-page.

PDF-acquisition assessment (STEP 0 — recorded so the next maintainer does not
re-discover it; page numbers are 0-based ``pdfplumber`` indices, EN 2023/24):

    The English edition has THREE distinct encoding zones:
      1. Narrative chapters (pp ~3–298): **CID-broken** (15–50 ``(cid:N)`` per
         word, no ToUnicode). Unusable.
      2. The headline MACRO statistical annex — "Macroeconomic Indicators"
         summary (pp 299–303) and the numbered Annex 1.1 … macro tables
         (GDP/GVA/prices/fiscal, from p 313): free of ``(cid:N)`` but
         **RTL-MIRRORED**. Every cell is character-reversed (GDP ``8.4075`` =
         "5704.8" reversed; ``P42/3202`` = "2023/24P"), the COLUMN order is
         reversed (row-label column lands LAST), the ROW order is reversed, and
         multi-line row labels are word-reversed AND line-wrap-fragmented
         (``"noitacifissalC\\nlai"``). The NUMBERS decode by string-reversal
         (magnitude-checks: ``8.4075``→5704.8 ⇒ nominal GDP ≈ NPR 5.7 trillion,
         in the ADR-0011 NPR 5–6 trillion band) but the row-label↔value GEOMETRY
         is not deterministically reconstructable — un-mirroring it is the
         font/layout reverse-engineering ADR-0003 forbids (it is what the FCGO
         parser DEFERRED for the same reversed-glyph reason). **Deferred.**
      3. A subset of SOCIAL-SECTOR annex tables (labour, tourism, health,
         education — pp ~405–488) that are **CLEAN forward English tables** with
         stable column geometry. These ARE deterministically parseable.

    The two Nepali editions' annex/English zone is **CID-broken** (the Devanagari
    narrative body is clean Unicode but is prose — no parseable statistical
    tables). So they yield nothing.

Scope (mirrors the Yellow Book ADR-0020 "one clean table" discipline):
    Of the ~11 clean EN social-sector annex tables, this parser extracts the
    single highest-value, most stable one — **Annex 6.1: Number of Workers having
    Foreign Employment Permit** (a clean 4-column ``Fiscal Year | Female | Male |
    Total`` matrix). Labour migration is the front-end of Nepal's remittance
    economy — directly on-mission ("does Nepal's money become wealth"). The other
    clean tables (hotels/Annex 8.14, medical specialists/Annex 11.7, education/
    Annex 11.x) have heterogeneous merged-cell / multi-row-header geometry; a
    robust extractor spanning all of them would blow the diff budget and be
    fragile, so they are DEFERRED and documented (a follow-up item can add them).

Output (Annex 6.1 → three single-series indicators, one value per FULL fiscal
year, routed to ``approved_indicator_values`` after Mother seeds slugs):
    - ``economic-survey-foreign-employment-permits-total``  (unit ``count``)
    - ``economic-survey-foreign-employment-permits-female`` (unit ``count``)
    - ``economic-survey-foreign-employment-permits-male``   (unit ``count``)
    Cumulative rows ("Upto July 2015", "Upto Mid March 2024") and the partial,
    starred current-year row ("2023/24*") are SKIPPED — they are not full-year
    annual values and emitting them as ``annual`` would mislead.

Period dating (ADR-0013): the annex labels each row by AD fiscal year
(``2023/24``). Nepal's mid-July→mid-July FY maps 1:1 to BS via +57 on the lead
year (AD 2023/24 → BS 2080/81). ``reporting_period_type='annual'``; the AD
start/end bound the BS-fiscal-year span (mid-Shrawan..mid-Ashadh) via the
canonical period helpers. A LOCAL helper converts AD-FY→BS-FY so
``_common/periods`` is untouched (same pattern as ``fcgo_consolidated``).

Confidence: ``B`` — PDF table extraction (the brief's grade for this source).

Versioning: bump ``PARSER_VERSION`` on any behaviour change.
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
    ReportingPeriodType,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
# Registered source id (verified against scripts/seed-source-registry.ts —
# the registry row is `mof-economic-survey-annual`, status 'active',
# ingestionMode 'reference_only'). NOT `mof-economic-survey`.
SOURCE_ID: Final[str] = "mof-economic-survey-annual"

# Confidence default for every emitted Economic Survey fact (PDF table extraction).
_CONFIDENCE: Final[str] = "B"

# AD→BS fiscal-year offset on the lead year (mid-July→mid-July FY maps 1:1;
# AD 2023/24 == BS 2080/81). Pinned to the period helpers' +57 (ADR-0013), same
# as the FCGO parser. Local by design — `_common/periods` stays untouched.
_AD_TO_BS_FY_OFFSET: Final[int] = 57

# Publication anchor for the EN 2023/24 edition (Economic Survey is tabled with
# the budget each Jestha; the FY2023/24 edition was published mid-2024). Used for
# `publication_date_*`. When the orchestrator threads release metadata it can
# override; until then this is the bundled edition's date.
_PUBLICATION_DATE_AD: Final[datetime] = datetime(2024, 5, 28, tzinfo=UTC)
_PUBLICATION_DATE_BS: Final[str] = "2081 Jestha 15"


def _ad_fy_to_bs_start(ad_fy_start: int) -> int:
    """Map an AD fiscal-year lead year to its BS fiscal-year lead year (+57).

    Local helper (ADR-0013); symmetric with
    ``_common.periods.fiscal_year_ad_label`` (which subtracts 57). A unit test
    asserts the round-trip.
    """
    return ad_fy_start + _AD_TO_BS_FY_OFFSET


# ---------------------------------------------------------------------------
# Annex-6.1 (Foreign Employment Permit) clean-table extractor — the parseable
# target. Anchored on the table caption + header so the page number is never
# hard-coded (annex pagination drifts across editions).
# ---------------------------------------------------------------------------

# Caption anchor — distinctive, appears once on the Annex-6.1 page.
_ANNEX_6_1_CAPTION_RE: Final = re.compile(
    r"Annex\s*6\.1\b.*?Foreign\s+Employment\s+Permit",
    re.IGNORECASE | re.DOTALL,
)

# The three measure columns, in the source header's order. Index 0 is the
# Fiscal-Year label column; 1/2/3 are Female/Male/Total.
_COL_FY: Final[int] = 0
_COL_FEMALE: Final[int] = 1
_COL_MALE: Final[int] = 2
_COL_TOTAL: Final[int] = 3
_ANNEX_6_1_MIN_COLS: Final[int] = 4

# Expected header tokens (lower-cased) for validation — confirms we located the
# right table and the columns are in the assumed order before reading any value.
_ANNEX_6_1_HEADER: Final[tuple[str, str, str, str]] = (
    "fiscal year",
    "female",
    "male",
    "total",
)

# One emitted measure per data column.
@dataclass(frozen=True)
class _Measure:
    slug: str
    col: int


_ANNEX_6_1_MEASURES: Final[tuple[_Measure, ...]] = (
    _Measure("economic-survey-foreign-employment-permits-total", _COL_TOTAL),
    _Measure("economic-survey-foreign-employment-permits-female", _COL_FEMALE),
    _Measure("economic-survey-foreign-employment-permits-male", _COL_MALE),
)

# A FULL-YEAR fiscal label: "YYYY/YY" exactly (e.g. "2015/16"). A trailing "*"
# (partial / provisional current year, e.g. "2023/24*") or a cumulative label
# ("Upto July 2015", "Upto Mid March 2024") does NOT match — those are skipped
# because they are not complete annual values.
_FY_LABEL_RE: Final = re.compile(r"^(\d{4})/(\d{2})$")


def _norm_cell(cell: object) -> str:
    """Stringify a table cell and collapse internal whitespace/newlines."""
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def _parse_count(raw: str) -> float | None:
    """Parse an integer count cell (optional thousands separators) to float.

    Blank / dash / non-numeric → None (never fabricated as 0; a genuine source
    ``0`` is preserved as ``0.0``).
    """
    s = raw.strip()
    if s in ("", "-", "--", "–", "—", "N/A", "n/a", "NA", "...", "."):
        return None
    try:
        v = float(s.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN  # noqa: PLR0124
        return None
    return v


def _full_year_lead(fy_label: str) -> int | None:
    """Return the AD lead year of a FULL-YEAR "YYYY/YY" label, else None.

    Validates the two-digit tail equals (lead + 1) mod 100, so a stray pair like
    "2020/99" is rejected rather than misread as a fiscal year.
    """
    m = _FY_LABEL_RE.match(fy_label)
    if not m:
        return None
    lead = int(m.group(1))
    tail = int(m.group(2))
    if tail != (lead + 1) % 100:
        return None
    return lead


def _row_is_header(cells: list[str]) -> bool:
    """True if a row is the Annex-6.1 column header (Fiscal Year/Female/Male/Total)."""
    lowered = [c.lower() for c in cells[:_ANNEX_6_1_MIN_COLS]]
    return lowered == list(_ANNEX_6_1_HEADER)


def extract_foreign_employment_rows(
    table_rows: list[list[object]],
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Convert the Annex-6.1 table → annual single-series staging rows.

    ``table_rows`` is the raw ``page.extract_tables()`` output for Annex-6.1
    (col 0 fiscal-year label, col 1 Female, col 2 Male, col 3 Total). Emits, per
    FULL fiscal year and per measure (Total/Female/Male), one ``StagingRowDraft``.
    Cumulative ("Upto …") and partial/starred ("2023/24*") rows are skipped.
    Never raises.

    A full-year row whose measure cell is non-empty but unparseable surfaces a
    typed ``ValueUnparseable`` so data loss is visible, never silent (Rule 6).
    """
    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    period_type: ReportingPeriodType = "annual"

    for raw in table_rows:
        if len(raw) < _ANNEX_6_1_MIN_COLS:
            continue
        cells = [_norm_cell(c) for c in raw]
        if _row_is_header(cells):
            continue

        fy_label = cells[_COL_FY]
        lead = _full_year_lead(fy_label)
        if lead is None:
            # Cumulative / partial / blank row — not a full annual value. Skipped
            # silently (these are expected non-data rows, not parse failures).
            continue

        bs_fy_start = _ad_fy_to_bs_start(lead)
        period_start = mid_month_ad("Shrawan", bs_fy_start)
        period_end = mid_month_ad("Ashadh", bs_fy_start)
        base = StagingRowDraft(
            indicator_slug_raw="",
            value=0.0,
            unit="count",
            reporting_period_type=period_type,
            reporting_period_bs=f"FY {fiscal_year_label(bs_fy_start)}",
            reporting_period_ad_start=period_start,
            reporting_period_ad_end=period_end,
            publication_date_ad=_PUBLICATION_DATE_AD,
            publication_date_bs=_PUBLICATION_DATE_BS,
            fiscal_year_bs=fiscal_year_label(bs_fy_start),
            fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
            confidence_grade_proposed=_CONFIDENCE,
            parser_notes=(
                "MoF Economic Survey Annex 6.1 (Number of Workers having Foreign "
                "Employment Permit); excludes EPS (Korea) per the source note"
            ),
        )

        for measure in _ANNEX_6_1_MEASURES:
            cell = cells[measure.col]
            value = _parse_count(cell)
            if value is None:
                if cell:  # non-empty but unparseable → visible error
                    errors.append(
                        ParserError(
                            error_class="ValueUnparseable",
                            error_detail=(
                                f"Annex 6.1 FY {fy_label} {measure.slug!r}: "
                                f"could not parse {cell!r}"
                            ),
                            source_excerpt=" | ".join(cells[:_ANNEX_6_1_MIN_COLS]),
                        )
                    )
                continue
            rows.append(
                replace(
                    base,
                    indicator_slug_raw=measure.slug,
                    value=value,
                )
            )

    return rows, errors


# ---------------------------------------------------------------------------
# Annex-zone encoding diagnostics — for the deferred (un-parseable) tables.
# These do NOT drive extraction (that is anchor-based above); they document the
# breakage modes as typed errors so the deferral is auditable, never silent.
# ---------------------------------------------------------------------------

AnnexTextClass = Literal["empty", "cid_broken", "rtl_mirrored", "clean"]

_CID_RE: Final = re.compile(r"\(cid:\d+\)")
# A page with this many CID placeholders is treated as CID-broken regardless of
# how many ASCII digits it also carries (some Nepali-edition annex pages mix long
# ASCII number runs with otherwise-CID Devanagari, dipping the per-word ratio).
_CID_ABSOLUTE_THRESHOLD: Final[int] = 30
_CID_WORD_RATIO_THRESHOLD: Final[float] = 0.20

# Reversed spellings of stable macro-annex SINGLE-WORD vocabulary. The RTL-
# mirror reverses character order AND wraps multi-word labels across lines, so
# multi-word phrases do NOT survive as contiguous substrings — but single words
# do (verified on the EN macro annex: "GDP"→"PDG", "Product"→"tcudorP",
# "Price"→"ecirP", "Inflation"→"noitalfnI", "Annex"→"xennA", "Indicators"→
# "srotacidnI"). We require at least two distinct reversed tokens (and no forward
# spelling) to mark a page mirrored — robust against a stray reversed substring.
_FORWARD_MACRO_TOKENS: Final[tuple[str, ...]] = (
    "Annex",
    "GDP",
    "Product",
    "Price",
    "Inflation",
    "Indicators",
)
_REVERSED_MACRO_TOKENS: Final[tuple[str, ...]] = tuple(
    t[::-1] for t in _FORWARD_MACRO_TOKENS
)
_MIRROR_MIN_REVERSED_HITS: Final[int] = 2

_MIN_CONTENT_CHARS: Final[int] = 20


def _cid_count(text: str) -> int:
    return len(_CID_RE.findall(text))


def classify_annex_text(text: str) -> AnnexTextClass:
    """Classify one page's extracted text for DIAGNOSTIC reporting.

    Order matters: CID breakage is the dominant failure (checked first, by both
    an absolute count and a per-word ratio — a page with many ``(cid:N)`` is
    CID-broken even if long ASCII number runs dilute the ratio). Then the
    RTL-mirror test on macro-annex vocabulary. ``clean`` requires forward macro
    vocabulary; otherwise ``empty`` (a page may still hold a clean SOCIAL-sector
    table the anchor extractor finds — this classifier only tracks the macro
    annex's breakage and is not used to gate extraction).
    """
    if len(text.strip()) < _MIN_CONTENT_CHARS:
        return "empty"

    cids = _cid_count(text)
    if cids >= _CID_ABSOLUTE_THRESHOLD or (
        cids / max(len(text.split()), 1) >= _CID_WORD_RATIO_THRESHOLD
    ):
        return "cid_broken"

    reversed_hits = sum(1 for t in _REVERSED_MACRO_TOKENS if t in text)
    has_forward = any(t in text for t in _FORWARD_MACRO_TOKENS)
    if reversed_hits >= _MIRROR_MIN_REVERSED_HITS and not has_forward:
        return "rtl_mirrored"
    if has_forward:
        return "clean"
    return "empty"


def _page_index_ranges(indices: list[int]) -> str:
    """Render a sorted page-index list as compact ranges, e.g. "3-298, 313-380"."""
    if not indices:
        return ""
    ordered = sorted(indices)
    ranges: list[str] = []
    start = prev = ordered[0]
    for i in ordered[1:]:
        if i == prev + 1:
            prev = i
            continue
        ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
        start = prev = i
    ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(ranges)


def _deferral_errors(page_texts: list[str]) -> list[ParserError]:
    """Build typed errors documenting the un-parseable annex zones (deferred).

    Emits a ``PageLayoutChanged`` for the RTL-mirrored macro annex range and an
    ``EncodingError`` for the CID-broken range, naming the affected pages.
    """
    errors: list[ParserError] = []
    mirrored = [i for i, t in enumerate(page_texts) if classify_annex_text(t) == "rtl_mirrored"]
    cid = [i for i, t in enumerate(page_texts) if classify_annex_text(t) == "cid_broken"]

    if mirrored:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    f"Deferred: {len(mirrored)} RTL-mirrored macro-annex page(s) "
                    f"(pages {_page_index_ranges(mirrored)}) — GDP/GVA/prices/"
                    f"fiscal tables. Numbers decode by string-reversal but the "
                    f"row-label↔value geometry is not deterministically "
                    f"reconstructable; un-mirroring is the reverse-engineering "
                    f"ADR-0003 forbids. See ADR-0016."
                ),
            )
        )
    if cid:
        errors.append(
            ParserError(
                error_class="EncodingError",
                error_detail=(
                    f"Deferred: {len(cid)} CID-broken page(s) "
                    f"(pages {_page_index_ranges(cid)}) — no ToUnicode map; not "
                    f"parseable without OCR (forbidden, ADR-0003). See ADR-0016."
                ),
            )
        )
    return errors


# ---------------------------------------------------------------------------
# PDF reading — locate Annex-6.1, extract its table, attach deferral diagnostics.
# ---------------------------------------------------------------------------


def _largest_table(page: object) -> list[list[object]] | None:
    """Return the page's largest extracted table (by row count), or None."""
    tables: list[list[list[object]]] = page.extract_tables()  # type: ignore[attr-defined]
    if not tables:
        return None
    return max(tables, key=len)


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one Economic Survey PDF; extract the clean Annex-6.1 series.

    Scans every page for the Annex-6.1 caption (Foreign Employment Permit),
    extracts that clean ``Fiscal Year | Female | Male | Total`` table, and emits
    annual single-series staging rows (Total/Female/Male). The RTL-mirrored macro
    annex and any CID-broken pages are DEFERRED with typed, documented errors
    (ADR-0016). Never raises on bad data.

    Status:
      - ``partial`` when Annex-6.1 rows are emitted AND deferral errors exist
        (the normal EN-edition outcome — some extracted, much deferred).
      - ``failure`` when Annex-6.1 is absent (the Nepali editions: the annex is
        CID-broken, no clean Foreign-Employment table) — a documented
        infeasibility for that edition, not a fabricated value.
    """
    _ = source_document_id  # threaded for orchestrator-contract symmetry

    path = Path(source_document_path)
    if not path.exists():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            staging_rows=[],
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"source file not found: {path}",
                )
            ],
        )

    page_texts: list[str] = []
    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    annex_6_1_pages = 0

    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                page_texts.append(text)
                if not _ANNEX_6_1_CAPTION_RE.search(text):
                    continue
                annex_6_1_pages += 1
                table = _largest_table(page)
                if table is None:
                    errors.append(
                        ParserError(
                            error_class="PageLayoutChanged",
                            error_detail=(
                                "Annex 6.1 caption found but no table extracted on "
                                "that page — layout differs from the EN 2023/24 edition"
                            ),
                        )
                    )
                    continue
                page_rows, page_errors = extract_foreign_employment_rows(table)
                staging_rows.extend(page_rows)
                errors.extend(page_errors)
    except (OSError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            staging_rows=[],
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdfplumber could not read {path.name}: {exc}",
                )
            ],
        )

    # Attach deferral diagnostics for the un-parseable annex zones (mirrored
    # macro annex + CID-broken pages), so the deferral is auditable.
    errors.extend(_deferral_errors(page_texts))

    if not staging_rows:
        # No clean Annex-6.1 data (the Nepali editions, or a layout change).
        if annex_6_1_pages == 0:
            errors.append(
                ParserError(
                    error_class="Other",
                    error_detail=(
                        "NoCleanAnnexTable: Annex 6.1 (Foreign Employment Permit) "
                        "not found — this edition's annex is CID-broken or "
                        "RTL-mirrored (e.g. the Nepali editions). Documented "
                        "infeasibility per ADR-0016; no values fabricated."
                    ),
                )
            )
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            staging_rows=[],
            errors=errors,
        )

    # Some clean rows extracted; the deferred macro annex / CID pages remain as
    # documented errors → partial.
    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes JSON to stdout via ``dataclasses.asdict`` (mirrors fcgo_consolidated;
    the orchestrator's ``ParserOutputSchema`` reads the asdict shape with
    ISO-formatted datetimes). Exit codes follow ``run-parser.ts``:
      - 0: parser ran (status may be 'failure'/'partial'; consumer reads stdout)
      - 2: usage error
      - 1: catastrophic crash (let Python propagate)
    """
    import json
    import sys
    from dataclasses import asdict

    expected_argv_count = 3  # progname + source_path + source_doc_id
    if len(sys.argv) != expected_argv_count:
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
