"""FCGO Consolidated Financial Statements PDF parser — deterministic Python.

Source: Financial Comptroller General Office (FCGO) "Consolidated Financial
Statement" — the audited all-of-government fiscal outturn covering the
federal government, 7 provinces, and 753 local governments in consolidated
form (NPSAS cash-basis). English edition, FY 2018/19 onward. The bundled
test exercises the FY 2022/23 publication (BS 2079/80).

Strategy:
    v0.1.0 used pdfplumber, which reads vertical-direction text as reversed
    ("Receipts" → "stpieceR"). 165 of 325 pages are landscape tables
    rotated into portrait with writing direction (0, −1). pdfplumber cannot
    handle this; pymupdf reads it correctly.

    v1.0.0 switches to pymupdf for ALL text extraction. The regex-anchor
    strategy is unchanged: scan the Executive Summary / Treasury-Position
    prose for stable phrasings. This also unlocks Phase 2 table extraction
    (pymupdf ``find_tables()`` reads the detail pages correctly).

    Derived indicators are computed from extracted values — no additional
    regex needed. Federal expenditure = total − provincial − local; fiscal
    balance = total revenue − total expenditure.

Target headline aggregates (v1.0.0):
    6 extracted from prose (unchanged from v0.2.0):
    - ``fcgo-total-revenue-outturn-annual`` (npr_million)
    - ``fcgo-total-expenditure-outturn-annual`` (npr_million)
    - ``fcgo-recurrent-expenditure-outturn-annual`` (npr_million)
    - ``fcgo-capital-expenditure-outturn-annual`` (npr_million)
    - ``fcgo-provincial-expenditure-consolidated-annual`` (npr_million)
    - ``fcgo-local-level-expenditure-consolidated-annual`` (npr_million)

    1 newly extracted (was captured but not emitted in v0.2.0):
    - ``fcgo-financing-disbursements-outturn-annual`` (npr_million)

    2 derived from the extracted values:
    - ``fcgo-federal-expenditure-outturn-annual`` (npr_million)
      = total − provincial − local
    - ``fcgo-fiscal-balance-outturn-annual`` (npr_million)
      = total revenue − total expenditure (negative = deficit)

Unit:
    All values are ``npr_million``. The FY 2022/23 total revenue
    utilization is NPR 1,506,321.46 million (≈ NPR 1.5 trillion), the
    correct order of magnitude for Nepal's 3-tier consolidated revenue.

Period dating (ADR-0013):
    AD fiscal year → BS via +57 on the lead year. AD 2022/23 → BS 2079/80.
    ``reporting_period_type`` is ``annual``.

Confidence:
    ``A`` by default — audited outturn (OAG opinion bound into the document).

Versioning:
    Bump PARSER_VERSION on any behavior change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pymupdf

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

PARSER_VERSION: Final[str] = "1.1.0"
SOURCE_ID: Final[str] = "fcgo-consolidated-financial-statements"

_AD_FY_START: Final[int] = 2022

_AD_TO_BS_FY_OFFSET: Final[int] = 57

_FY_LABEL_RE: Final[re.Pattern[str]] = re.compile(r"\bFY\s+(\d{4})/(\d{2})\b")


def _ad_fy_to_bs_start(ad_fy_start: int) -> int:
    """Map an AD fiscal-year lead year to its BS fiscal-year lead year.

    Nepal's fiscal year (mid-July → mid-July) maps 1:1 between calendars,
    so the BS lead year is the AD lead year + 57 (ADR-0013). Local helper
    by design — ``_common/periods`` is the canonical period vocabulary and
    is not edited for source-specific calendar logic.
    """
    return ad_fy_start + _AD_TO_BS_FY_OFFSET


def _detect_ad_fy_start(text: str) -> int | None:
    """Extract the AD fiscal-year lead year from CFS Executive Summary prose.

    Scans for the first ``FY YYYY/YY`` occurrence (e.g. ``FY 2022/23``).
    Validates that the two-digit suffix equals ``(lead+1) mod 100``.
    Returns ``None`` on mismatch, no match, or implausible year (< 2018).
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
    """Approximate FCGO CFS publication date: Jestha 15 of BS year (bs_start+2)."""
    bs_fy_start = _ad_fy_to_bs_start(ad_fy_start)
    pub_bs_year = bs_fy_start + 2
    pub_ad_year = ad_fy_start + 2
    pub_ad = datetime(pub_ad_year, 5, 15, tzinfo=UTC)
    pub_bs = f"{pub_bs_year} Jestha 15"
    return pub_ad, pub_bs


@dataclass(frozen=True)
class _IndicatorSpec:
    """How to find one headline aggregate in the CFS prose."""

    slug: str
    unit: str
    pattern: re.Pattern[str]
    group_index: int
    basis_note: str | None


_NUM: Final[str] = r"([\d,]+\.\d+)"

_GROSS_BASIS_NOTE: Final[str] = (
    "gross consolidated sum across all three tiers (before elimination of "
    "intergovernmental transfers); not directly comparable to "
    "total-expenditure, which is after-elimination"
)
_AFTER_ELIM_NOTE: Final[str] = (
    "after eliminating intergovernmental fiscal transfers (excluding EBUs)"
)

_REC_CAP_FIN_RE: Final[re.Pattern[str]] = re.compile(
    r"recurrent\s+expenditures?,\s+capital\s+expenditures?,\s+and\s+"
    r"financing\s+disbursements\s+(?:totaling|totalling|amounting\s+to)"
    r"\s+NPR\s+" + _NUM + r"\s+million,\s+NPR\s+" + _NUM
    + r"\s+million,\s+and\s+NPR\s+" + _NUM + r"\s+million",
    re.IGNORECASE,
)

_INDICATORS: Final[tuple[_IndicatorSpec, ...]] = (
    _IndicatorSpec(
        slug="fcgo-total-revenue-outturn-annual",
        unit="npr_million",
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
        pattern=_REC_CAP_FIN_RE,
        group_index=1,
        basis_note=_GROSS_BASIS_NOTE,
    ),
    _IndicatorSpec(
        slug="fcgo-capital-expenditure-outturn-annual",
        unit="npr_million",
        pattern=_REC_CAP_FIN_RE,
        group_index=2,
        basis_note=_GROSS_BASIS_NOTE,
    ),
    _IndicatorSpec(
        slug="fcgo-financing-disbursements-outturn-annual",
        unit="npr_million",
        pattern=_REC_CAP_FIN_RE,
        group_index=3,
        basis_note=_GROSS_BASIS_NOTE,
    ),
    _IndicatorSpec(
        slug="fcgo-provincial-expenditure-consolidated-annual",
        unit="npr_million",
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
    """Concatenate page text from a PDF using pymupdf.

    pymupdf correctly handles the vertical writing direction (0, −1) on the
    165 landscape-rotated table pages that pdfplumber reads reversed. Soft
    hyphenation across line breaks is collapsed.
    """
    doc = pymupdf.open(str(path))
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    raw = "\n".join(parts)
    return re.sub(r"-\s*\n\s*", "", raw)


def _parse_npr(raw: str) -> float:
    """Parse an NPR figure with optional thousands separators to float."""
    return float(raw.replace(",", ""))


def _derive_indicators(
    extracted: dict[str, float],
    base: StagingRowDraft,
) -> list[StagingRowDraft]:
    """Compute derived indicators from extracted headline values."""
    derived: list[StagingRowDraft] = []

    total_exp = extracted.get("fcgo-total-expenditure-outturn-annual")
    prov_exp = extracted.get("fcgo-provincial-expenditure-consolidated-annual")
    local_exp = extracted.get("fcgo-local-level-expenditure-consolidated-annual")
    if total_exp is not None and prov_exp is not None and local_exp is not None:
        federal_exp = total_exp - prov_exp - local_exp
        derived.append(
            replace(
                base,
                indicator_slug_raw="fcgo-federal-expenditure-outturn-annual",
                value=round(federal_exp, 2),
                unit="npr_million",
                parser_notes=(
                    "derived: total-expenditure minus provincial minus local "
                    "(all after-elimination figures)"
                ),
            )
        )

    total_rev = extracted.get("fcgo-total-revenue-outturn-annual")
    if total_rev is not None and total_exp is not None:
        balance = total_rev - total_exp
        derived.append(
            replace(
                base,
                indicator_slug_raw="fcgo-fiscal-balance-outturn-annual",
                value=round(balance, 2),
                unit="npr_million",
                parser_notes=(
                    "derived: total-revenue minus total-expenditure "
                    "(negative = deficit)"
                ),
            )
        )

    return derived


def extract_indicators(text: str) -> ParserResult:
    """Apply the headline-aggregate anchors to already-extracted CFS text.

    This is the deterministic core, split out from PDF reading so it can be
    exercised against synthesized text fixtures.
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

    ad_fy_start = _detect_ad_fy_start(text) or _AD_FY_START
    bs_fy_start = _ad_fy_to_bs_start(ad_fy_start)

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
    extracted_values: dict[str, float] = {}

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

        extracted_values[spec.slug] = value
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

    staging_rows.extend(_derive_indicators(extracted_values, base))

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one FCGO CFS English-edition PDF.

    v1.1.0: prose headline extraction (9 indicators) + overview table
    extraction (~200 staging rows from 5 key tables with 5-year series).
    """
    _ = source_document_id

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
        doc = pymupdf.open(str(path))
    except (OSError, ValueError, RuntimeError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdf open failed: {exc}",
                )
            ],
        )

    try:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
        raw = "\n".join(parts)
        text = re.sub(r"-\s*\n\s*", "", raw)

        prose_result = extract_indicators(text)

        ad_fy_start = _detect_ad_fy_start(text) or _AD_FY_START

        from fcgo_consolidated.table_extractor import extract_overview_tables

        table_rows, table_errors = extract_overview_tables(doc, ad_fy_start)
    finally:
        doc.close()

    all_rows = prose_result.staging_rows + table_rows
    all_errors = prose_result.errors + table_errors

    if not all_rows:
        status: ParserStatus = "failure"
    elif all_errors:
        status = "partial"
    else:
        status = "success"

    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=all_rows,
        errors=all_errors,
    )


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator."""
    import json
    import sys
    from dataclasses import asdict

    expected_argv_count = 3
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
