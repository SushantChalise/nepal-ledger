"""FCGO Consolidated Financial Statements PDF parser — deterministic Python.

Source: Financial Comptroller General Office (FCGO) "Consolidated Financial
Statement" — the audited all-of-government fiscal outturn covering the
federal government, 7 provinces, and 753 local governments in consolidated
form (NPSAS cash-basis). English edition, FY 2018/19 onward. The bundled
test exercises the FY 2022/23 publication (BS 2079/80).

Strategy:
    FCGO's CFS is a 300+ page document whose detailed financial-statement
    tables render with *reversed glyph order* under ``pdfplumber`` text
    extraction (a right-to-left layout artifact: "Receipts" comes out as
    "stpieceR"). Those tables are therefore unusable for deterministic
    regex extraction. The Executive Summary and the narrative paragraphs
    around the Treasury-Position table, however, are CLEAN forward Latin
    text and re-use stable phrasings ("total revenue utilization ...
    amounts to NPR X million", "Total expenditure stands at NPR Y
    million"). We anchor on that prose, exactly as the NRB CMEFs parser
    does, and scan ALL pages (the Executive Summary page number drifts
    across editions — never hard-code it).

    When the prose phrasing shifts, the parser emits a typed
    ``PageLayoutChanged`` error for that indicator instead of inventing a
    value. It never crashes on bad input.

Target headline aggregates (v0.1.0):
    - ``fcgo-total-revenue-outturn-annual`` (npr_million) — total revenue
      utilization of the three tiers after revenue-sharing settlements.
    - ``fcgo-total-expenditure-outturn-annual`` (npr_million) — total
      expenditure after eliminating intergovernmental fiscal transfers
      (excluding EBUs); the Executive Summary headline figure.
    - ``fcgo-recurrent-expenditure-outturn-annual`` (npr_million) —
      consolidated recurrent expenditure, summed across the three tiers
      (GROSS, before inter-government elimination).
    - ``fcgo-capital-expenditure-outturn-annual`` (npr_million) —
      consolidated capital expenditure, summed across the three tiers
      (GROSS, before inter-government elimination).
    - ``fcgo-provincial-expenditure-consolidated-annual`` (npr_million) —
      total expenditure of all seven provinces.
    - ``fcgo-local-level-expenditure-consolidated-annual`` (npr_million) —
      total expenditure of all 753 local governments.

    IMPORTANT basis mismatch (stamped in ``parser_notes``): total-revenue
    and total-expenditure are *after-elimination* figures, whereas
    recurrent and capital are the *gross* consolidated sums (Σ over the
    three tiers, before elimination of intergovernmental transfers). Hence
    recurrent + capital + financing (= NPR 2,079,823.31 million for
    FY 2022/23) does NOT equal total-expenditure (NPR 1,672,128.84
    million). Downstream consumers must not naively reconcile the two.

Unit:
    All values are ``npr_million``. The FY 2022/23 total revenue
    utilization is NPR 1,506,321.46 million (≈ NPR 1.5 trillion), the
    correct order of magnitude for Nepal's 3-tier consolidated revenue.
    (The source profile originally said "billion" — that was wrong; see
    ``docs/sources/fcgo-consolidated-financial-statements.md``.)

Period dating (ADR-0013):
    The CFS labels its fiscal year by AD ("Fiscal Year 2022/23"). Nepal's
    fiscal year is mid-July → mid-July, so the AD fiscal year maps 1:1 to
    a BS fiscal year via the +57 offset on the lead year:
    AD 2022/23 → BS 2079/80. ``reporting_period_type`` is ``annual`` and
    the AD start/end bound the BS-fiscal-year span (mid-Shrawan ..
    mid-Ashadh). Conversion uses a LOCAL helper (``_ad_fy_to_bs_start``)
    so ``_common/periods`` is untouched.

Confidence:
    ``A`` by default — this is the audited outturn (Office of the Auditor
    General opinion is bound into the document), the highest-confidence
    fiscal data the project ingests.

Versioning:
    Bump PARSER_VERSION on any behavior change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

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

PARSER_VERSION: Final[str] = "0.2.0"
SOURCE_ID: Final[str] = "fcgo-consolidated-financial-statements"

# Fallback AD fiscal-year lead year used only when auto-detection fails.
# v0.2.0: the parser detects the FY from "FY YYYY/YY" in the Executive
# Summary prose instead of relying on this constant.  It remains here as a
# safety net for edge-cases (e.g. stripped / image-only PDFs).
_AD_FY_START: Final[int] = 2022

# AD → BS fiscal-year offset on the lead year (mid-July → mid-July fiscal
# year; AD 2022/23 == BS 2079/80). ADR-0013 §"AD → BS via the fiscal-year
# offset" pins this to the period helpers' +57 rather than a bare literal.
_AD_TO_BS_FY_OFFSET: Final[int] = 57

# Pattern to detect the AD fiscal-year label from the CFS Executive Summary.
# The revenue sentence always names the FY: "...for FY 2022/23 amounts to..."
# We extract the lead year (≥ 2018 for any real CFS edition) and validate
# that the trailing two digits equal (lead+1) mod 100.
_FY_LABEL_RE: Final[re.Pattern[str]] = re.compile(r"\bFY\s+(\d{4})/(\d{2})\b")


def _ad_fy_to_bs_start(ad_fy_start: int) -> int:
    """Map an AD fiscal-year lead year to its BS fiscal-year lead year.

    Nepal's fiscal year (mid-July → mid-July) maps 1:1 between calendars,
    so the BS lead year is the AD lead year + 57 (ADR-0013). Local helper
    by design — ``_common/periods`` is the canonical period vocabulary and
    is not edited for source-specific calendar logic.

    The result is symmetric with ``_common.periods.fiscal_year_ad_label``
    (which subtracts 57 to go BS → AD); a unit test asserts the round-trip.
    """
    return ad_fy_start + _AD_TO_BS_FY_OFFSET


def _detect_ad_fy_start(text: str) -> int | None:
    """Extract the AD fiscal-year lead year from CFS Executive Summary prose.

    Scans for the first ``FY YYYY/YY`` occurrence (e.g. ``FY 2022/23``).
    Validates that the two-digit suffix equals ``(lead+1) mod 100``.
    Returns ``None`` on mismatch, no match, or implausible year (< 2018).

    Called by ``extract_indicators`` before constructing staging rows so
    every edition (FY 2018/19 → present) stamps correct period metadata
    without operator intervention.
    """
    match = _FY_LABEL_RE.search(text)
    if match is None:
        return None
    lead = int(match.group(1))
    suffix = int(match.group(2))
    if suffix != (lead + 1) % 100:
        return None
    if lead < 2018:
        return None
    return lead


def _approx_publication_date(ad_fy_start: int) -> tuple[datetime, str]:
    """Approximate FCGO CFS publication date: Jestha 15 of BS year (bs_start+2).

    FCGO publishes the audited CFS approximately in Jestha of the year
    following the FY close.  E.g. FY 2022/23 (BS 2079/80) audit opinion:
    May 26, 2024 (BS 2081 Jestha 13) — our approximation Jestha 15 of 2081
    lands May 15, 2024, within 11 days.

    Returns: ``(publication_date_ad, publication_date_bs)``
    """
    bs_fy_start = _ad_fy_to_bs_start(ad_fy_start)
    pub_bs_year = bs_fy_start + 2
    pub_ad_year = ad_fy_start + 2  # same arithmetic: ad_fy_start + 57 + 2 - 57
    pub_ad = datetime(pub_ad_year, 5, 15, tzinfo=UTC)
    pub_bs = f"{pub_bs_year} Jestha 15"
    return pub_ad, pub_bs


@dataclass(frozen=True)
class _IndicatorSpec:
    """How to find one headline aggregate in the CFS prose.

    ``pattern`` is applied against the full document text. ``group_index``
    selects which capture group holds this indicator's value (one prose
    sentence states recurrent + capital + financing together, so two
    indicators share a single pattern but read different groups).
    """

    slug: str
    unit: str
    pattern: re.Pattern[str]
    group_index: int
    # Free-text note appended to every emitted row for this indicator
    # (e.g. the after-elimination vs gross basis caveat). ``None`` = no note.
    basis_note: str | None


# Numeric capture: NPR figures in the CFS prose are written with thousands
# separators and two decimals (e.g. "1,506,321.46"). Allow optional commas
# so the same group also tolerates a comma-free reprint.
_NUM: Final[str] = r"([\d,]+\.\d+)"

# Anchored narrative patterns. Each uses alternation where FCGO's phrasing
# is known to drift across editions ("amounts to | stands at | totaling").
# The anchors are highly specific noun phrases that appear exactly once in
# the clean (forward-text) Executive Summary / Treasury-Position prose, so
# ``.search()`` lands on the intended figure and not a table fragment.
_GROSS_BASIS_NOTE: Final[str] = (
    "gross consolidated sum across all three tiers (before elimination of "
    "intergovernmental transfers); not directly comparable to "
    "total-expenditure, which is after-elimination"
)
_AFTER_ELIM_NOTE: Final[str] = (
    "after eliminating intergovernmental fiscal transfers (excluding EBUs)"
)

_INDICATORS: Final[tuple[_IndicatorSpec, ...]] = (
    _IndicatorSpec(
        slug="fcgo-total-revenue-outturn-annual",
        unit="npr_million",
        # "The total revenue utilization (excluding fiscal transfer) of the
        #  three tiers of government for FY 2022/23 amounts to NPR
        #  1,506,321.46 million after revenue sharing settlements."
        pattern=re.compile(
            r"total\s+revenue\s+utilization\b.{0,120}?"
            r"(?:amounts\s+to|stands\s+at|is)\s+NPR\s+" + _NUM + r"\s+million",
            re.IGNORECASE | re.DOTALL,
        ),
        group_index=1,
        basis_note="total revenue utilization after revenue-sharing settlements",
    ),
    _IndicatorSpec(
        slug="fcgo-total-expenditure-outturn-annual",
        unit="npr_million",
        # "Total expenditure stands at NPR 1,672,128.84 million after
        #  eliminating all types of intergovernmental fiscal transfers
        #  (excluding EBUs)."
        pattern=re.compile(
            r"Total\s+expenditure\s+(?:stands\s+at|amounts\s+to|is)\s+NPR\s+"
            + _NUM
            + r"\s+million\s+after\s+eliminating",
            re.IGNORECASE,
        ),
        group_index=1,
        basis_note=_AFTER_ELIM_NOTE,
    ),
    _IndicatorSpec(
        slug="fcgo-recurrent-expenditure-outturn-annual",
        unit="npr_million",
        # "These disbursements included recurrent expenditures, capital
        #  expenditures, and financing disbursements totaling NPR
        #  1,356,150.86 million, NPR 527,447.04 million, and NPR
        #  196,225.41 million, respectively."
        # Group 1 = recurrent, group 2 = capital, group 3 = financing.
        pattern=re.compile(
            r"recurrent\s+expenditures?,\s+capital\s+expenditures?,\s+and\s+"
            r"financing\s+disbursements\s+(?:totaling|totalling|amounting\s+to)"
            r"\s+NPR\s+" + _NUM + r"\s+million,\s+NPR\s+" + _NUM
            + r"\s+million,\s+and\s+NPR\s+" + _NUM + r"\s+million",
            re.IGNORECASE,
        ),
        group_index=1,
        basis_note=_GROSS_BASIS_NOTE,
    ),
    _IndicatorSpec(
        slug="fcgo-capital-expenditure-outturn-annual",
        unit="npr_million",
        # Same sentence as recurrent; group 2 = capital expenditures.
        pattern=re.compile(
            r"recurrent\s+expenditures?,\s+capital\s+expenditures?,\s+and\s+"
            r"financing\s+disbursements\s+(?:totaling|totalling|amounting\s+to)"
            r"\s+NPR\s+" + _NUM + r"\s+million,\s+NPR\s+" + _NUM
            + r"\s+million,\s+and\s+NPR\s+" + _NUM + r"\s+million",
            re.IGNORECASE,
        ),
        group_index=2,
        basis_note=_GROSS_BASIS_NOTE,
    ),
    _IndicatorSpec(
        slug="fcgo-provincial-expenditure-consolidated-annual",
        unit="npr_million",
        # "Total expenditure of all seven provinces amounts to NPR
        #  204,678.62 million, including fiscal transfers of NPR ... to
        #  local governments."
        pattern=re.compile(
            r"Total\s+expenditure\s+of\s+all\s+seven\s+provinces\s+"
            r"(?:amounts\s+to|stands\s+at|is)\s+NPR\s+" + _NUM + r"\s+million",
            re.IGNORECASE,
        ),
        group_index=1,
        basis_note="sum of all seven provincial governments' expenditure",
    ),
    _IndicatorSpec(
        slug="fcgo-local-level-expenditure-consolidated-annual",
        unit="npr_million",
        # "Total expenditure of all local governments amounts to NPR
        #  453,817.73 million."
        pattern=re.compile(
            r"Total\s+expenditure\s+of\s+all\s+local\s+governments\s+"
            r"(?:amounts\s+to|stands\s+at|is)\s+NPR\s+" + _NUM + r"\s+million",
            re.IGNORECASE,
        ),
        group_index=1,
        basis_note="sum of all 753 local governments' expenditure",
    ),
)


def _extract_pdf_text(path: Path) -> str:
    """Concatenate page text from a PDF; ``\\n`` between pages so regex
    line-locality is retained. Soft hyphenation across line breaks is
    collapsed so anchors don't trip on it.
    """
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    raw = "\n".join(parts)
    return re.sub(r"-\s*\n\s*", "", raw)


def _parse_npr(raw: str) -> float:
    """Parse an NPR figure with optional thousands separators to float."""
    return float(raw.replace(",", ""))


def extract_indicators(text: str) -> ParserResult:
    """Apply the headline-aggregate anchors to already-extracted CFS text.

    This is the deterministic core, split out from PDF reading so it can be
    exercised against synthesized text fixtures (no PDF-writing dependency
    is available in the venv, and we will not commit the 3.9 MB binary —
    see ADR-0003 / the source profile). ``parse`` wraps this with
    ``pdfplumber`` text extraction.

    Never raises on bad data: a missing anchor becomes a typed
    ``PageLayoutChanged`` error; an unparseable number becomes
    ``ValueUnparseable``. Empty/whitespace text fails with a single
    ``PageLayoutChanged``.
    """
    if not text.strip():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail="pdf yielded no text — possible image-only scan",
                )
            ],
        )

    # Auto-detect the AD fiscal-year lead from the Executive Summary prose.
    # Falls back to _AD_FY_START (2022) when the FY label is absent — this
    # covers the miss/partial-text test fixtures and any genuinely stripped
    # PDFs, but the caller should treat a fallback as a quality signal.
    ad_fy_start = _detect_ad_fy_start(text) or _AD_FY_START
    bs_fy_start = _ad_fy_to_bs_start(ad_fy_start)

    # Annual span: mid-Shrawan (FY open) .. mid-Ashadh (FY close).
    period_start = mid_month_ad("Shrawan", bs_fy_start)
    period_end = mid_month_ad("Ashadh", bs_fy_start)
    period_type: ReportingPeriodType = "annual"

    pub_ad, pub_bs = _approx_publication_date(ad_fy_start)

    base = StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="",
        reporting_period_type=period_type,
        reporting_period_bs=f"FY {fiscal_year_label(bs_fy_start)}",
        reporting_period_ad_start=period_start,
        reporting_period_ad_end=period_end,
        publication_date_ad=pub_ad,
        publication_date_bs=pub_bs,
        fiscal_year_bs=fiscal_year_label(bs_fy_start),
        fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        confidence_grade_proposed="A",
        parser_notes=None,
    )

    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for spec in _INDICATORS:
        match = spec.pattern.search(text)
        if match is None:
            errors.append(
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail=(
                        f"indicator {spec.slug!r}: narrative anchor not found "
                        f"— CFS phrasing may have shifted across editions"
                    ),
                )
            )
            continue

        raw_value = match.group(spec.group_index)
        try:
            value = _parse_npr(raw_value)
        except ValueError:
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=(
                        f"indicator {spec.slug!r}: could not parse {raw_value!r}"
                    ),
                    source_excerpt=match.group(0)[:200],
                )
            )
            continue

        staging_rows.append(
            replace(
                base,
                indicator_slug_raw=spec.slug,
                value=value,
                unit=spec.unit,
                parser_notes=spec.basis_note,
            )
        )

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors
            or [
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail="no headline aggregates matched",
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


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one FCGO CFS English-edition PDF; emit headline aggregates.

    Thin wrapper: reads the PDF text with ``pdfplumber`` and delegates the
    deterministic matching to ``extract_indicators``.

    Arguments:
        source_document_path: filesystem path to the downloaded PDF.
        source_document_id: opaque ID from ``source_documents``; threaded
            through for symmetry with the orchestrator contract.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``, ``errors``.
        Never raises on bad data (ADR-0003 / parser contract).
    """
    _ = source_document_id  # touch for static analysers

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
        text = _extract_pdf_text(path)
    except (OSError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdf extract failed: {exc}",
                )
            ],
        )

    return extract_indicators(text)


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes JSON to stdout via ``dataclasses.asdict`` (mirrors nrb_cmefs;
    do NOT use ``ParserResult.to_json_dict()`` directly — the orchestrator
    expects the asdict shape with ISO-formatted datetimes).
    Exit codes follow ``src/lib/ingestion/run-parser.ts``:
      - 0: parser ran (status may still be 'failure'; consumer reads stdout)
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
