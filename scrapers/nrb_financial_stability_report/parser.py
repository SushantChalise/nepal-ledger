"""NRB Financial Stability Report (FSR) PDF parser — deterministic Python.

Source: NRB "Financial Stability Report" — annual bulletin from the Banks and
Financial Institutions Regulation Department. Issue 16 covers FY 2023/24.

Strategy:
    The FSR is an annual narrative PDF. The primary aggregate table (Table 2.3,
    "Financial Soundness Indicators of BFIs") appears mid-report and presents
    columns for Commercial Banks, Development Banks, Finance Companies, and an
    "Overall" aggregate covering A+B+C class BFIs. The table has two sub-columns
    per institution type (prior year and current year values).

    The two-column page layout causes pdfplumber's table extractor to produce
    fragmented, None-padded rows. We therefore extract full-page text and apply
    anchored regex patterns to identify each indicator row by its label, then
    capture the trailing numeric tokens to find the Overall-current-year value.

Period detection:
    The cover page / disclaimer contains "Fiscal year YYYY/YYYY" or "Fiscal Year
    YYYY/YYYY". Mid-July of the closing year marks the end of the fiscal year
    (Nepali BS Ashadh end). FY 2023/24 → mid-July 2024 → BS Ashadh 2081.

Target indicators (v0.1.0):
    - nrb-fsr-npl-ratio-annual            NPL/ Total loan (%), Overall
    - nrb-fsr-capital-adequacy-annual     Tier 1 & Tier 2 Capital /RWE (%), Overall
    - nrb-fsr-credit-deposit-ratio-annual CD Ratio (%), Overall

Sample values (FY2023/24, mid-July 2024):
    NPL ratio          3.86
    Capital adequacy  12.92
    CD Ratio          79.09

Known breakage modes:
    - Table 2.3 lives on a two-column page; pdfplumber renders both columns in
      interleaved order. Regex extraction on plain text is robust to this.
    - The row label "CD Ratio" appears in a section whose header is
      "Credit and Deposit-Related Indicators". Prior year then current year
      values appear as two numbers after the label in the extracted text stream.
    - The capital adequacy row label is "Tier 1 & Tier 2 Capital /RWE" in older
      issues and may shift; the pattern is anchored loosely.

Versioning:
    Bump PARSER_VERSION on any behaviour change.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "nrb-financial-stability-report"

# ── Period detection ─────────────────────────────────────────────────────────

# "Fiscal year 2023/2024" or "Fiscal Year 2023/24" — the first year is the
# start of the AD fiscal year (which approximates to BS FY start + 57).
_FY_TITLE_RE: Final[re.Pattern[str]] = re.compile(
    r"[Ff]iscal\s+[Yy]ear\s+(\d{4})/(\d{2,4})",
    re.IGNORECASE,
)

# Typical NRB FSR publication lag (months after FY close):
_NRB_FSR_PUB_LAG_DAYS: Final[int] = 90


def _detect_fy(text: str, errors: list[ParserError]) -> tuple[int, int] | None:
    """Detect AD fiscal year start and end from the document header text.

    Returns (ad_fy_start, ad_fy_end) e.g. (2023, 2024) for FY2023/24.
    Appends to *errors* and returns None if the title pattern is not found.
    """
    m = _FY_TITLE_RE.search(text[:4000])
    if not m:
        errors.append(ParserError(
            error_class="PeriodAmbiguous",
            error_detail=(
                "FSR cover page title not found in first 4000 chars — "
                "cannot determine fiscal year. Expected 'Fiscal year YYYY/YYYY'."
            ),
        ))
        return None
    ad_start = int(m.group(1))
    raw_end = m.group(2)
    # Handle both "2023/24" (2-digit) and "2023/2024" (4-digit) endings.
    if len(raw_end) == 2:
        ad_end = (ad_start // 100) * 100 + int(raw_end)
    else:
        ad_end = int(raw_end)
    return ad_start, ad_end


# ── Indicator specs ───────────────────────────────────────────────────────────
#
# Table 2.3 column layout (extracted text order, two-column page interleave):
#   <Row label>  <CommBanks_prev> <CommBanks_cur> <DevBanks_prev> <DevBanks_cur>
#                <FinCos_prev> <FinCos_cur> <Overall_prev> <Overall_cur>
#
# We anchor on the row label and capture all trailing numbers, then take the
# last two as (prev_year, current_year) for the Overall column.
# Exception: some rows have fewer numbers (e.g. weighted average rates show
# only two values with no class breakdown). We apply a minimum token check.
#
# The patterns below capture the entire row text (label + all numbers) via
# DOTALL up to a known next row label or end-of-section marker.

# Minimum number of numeric tokens expected per row in the Overall section:
# 8 values = 2 per class × 4 classes. Some rows may show fewer due to layout.
_MIN_OVERALL_TOKENS: Final[int] = 2  # at minimum: prev + current Overall


def _extract_last_two_floats(text_fragment: str) -> tuple[float, float] | None:
    """Return the last two floats found in a text fragment as (prev, current)."""
    nums = re.findall(r"\d+\.\d+", text_fragment)
    if len(nums) < _MIN_OVERALL_TOKENS:
        return None
    return float(nums[-2]), float(nums[-1])


# ── Indicator row extractor patterns ─────────────────────────────────────────
#
# Each pattern searches the full-document text for its row. Capture group 1
# is the block of text that follows the label (containing all numeric columns).
# We then apply _extract_last_two_floats to get Overall prev/current.

_NPL_ROW_RE: Final[re.Pattern[str]] = re.compile(
    # "NPL/ Total loan" followed by 8 numbers (or fewer on layout artifacts)
    r"NPL/\s*Total\s+loan\s+((?:\d+\.\d+\s*){2,8})",
    re.IGNORECASE,
)

_CAPITAL_ROW_RE: Final[re.Pattern[str]] = re.compile(
    # "Tier 1 & Tier 2 Capital /RWE" followed by numbers
    r"Tier\s+1\s+&\s+Tier\s+2\s+Capital\s*/RWE\s+((?:\d+\.\d+\s*){2,8})",
    re.IGNORECASE,
)

_CD_RATIO_ROW_RE: Final[re.Pattern[str]] = re.compile(
    # "CD Ratio" followed by numbers (not to be confused with other rows)
    r"\bCD\s+Ratio\s+((?:\d+\.\d+\s*){2,8})",
    re.IGNORECASE,
)


def _extract_pdf_text(path: Path) -> str:
    """Concatenate page text from all PDF pages; collapse soft-hyphenation."""
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    raw = "\n".join(parts)
    # Collapse soft-hyphenated line breaks.
    return re.sub(r"-\s*\n\s*", "", raw)


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one NRB FSR PDF; emit financial soundness indicators.

    Arguments:
        source_document_path: filesystem path to the downloaded PDF.
        source_document_id: opaque FK from ``source_documents``; threaded
            through for orchestrator symmetry.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``, ``errors``.
    """
    _ = source_document_id

    path = Path(source_document_path)
    if not path.exists():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[ParserError(
                error_class="Other",
                error_detail=f"source file not found: {path}",
            )],
        )

    try:
        text = _extract_pdf_text(path)
    except (OSError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[ParserError(
                error_class="EncodingError",
                error_detail=f"pdf extract failed: {exc}",
            )],
        )

    if not text.strip():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[ParserError(
                error_class="PageLayoutChanged",
                error_detail="pdf yielded no text — possible image-only scan",
            )],
        )

    errors: list[ParserError] = []

    # ── Period detection ──────────────────────────────────────────────────────
    fy_years = _detect_fy(text, errors)
    if fy_years is None:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors,
        )

    ad_fy_start, ad_fy_end = fy_years

    # The FSR covers the full fiscal year ending mid-July (≈ BS Ashadh end).
    # BS year arithmetic: BS FY start = AD FY start + 57.
    # e.g. AD FY 2023/24 → BS FY 2080/81.
    bs_fy_start = ad_fy_start + 57

    # Period end: BS Ashadh of bs_fy_start (month 12 of the FY).
    # mid_month_ad("Ashadh", bs_fy_start) gives the AD mid-month proxy.
    # For FY span: Shrawan of bs_fy_start → Ashadh of bs_fy_start.
    period_start = mid_month_ad("Shrawan", bs_fy_start)
    period_end = mid_month_ad("Ashadh", bs_fy_start)

    fy_bs_label = fiscal_year_label(bs_fy_start)        # e.g. "2080/81"
    fy_ad_label = fiscal_year_ad_label(bs_fy_start)     # e.g. "2023/24"

    # Approximate publication date: FSR is typically published 3–10 months
    # after fiscal-year close (mid-July). We use mid-Ashadh + 90 days.
    pub_ad = period_end + timedelta(days=_NRB_FSR_PUB_LAG_DAYS)
    pub_bs = f"~{fy_bs_label} (heuristic)"

    # BS label for reporting period: full fiscal year.
    reporting_period_bs = f"FY {fy_bs_label}"

    # Base row template.
    base = StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="percent",
        reporting_period_type="annual",
        reporting_period_bs=reporting_period_bs,
        reporting_period_ad_start=period_start,
        reporting_period_ad_end=period_end,
        publication_date_ad=pub_ad,
        publication_date_bs=pub_bs,
        fiscal_year_bs=fy_bs_label,
        fiscal_year_ad_label=fy_ad_label,
        confidence_grade_proposed="A",
        parser_notes=None,
    )

    staging_rows: list[StagingRowDraft] = []

    # ── Extract indicator rows ────────────────────────────────────────────────

    # 1. NPL / Total loan — Overall current year.
    npl_match = _NPL_ROW_RE.search(text)
    if npl_match is None:
        errors.append(ParserError(
            error_class="ColumnMissing",
            error_detail=(
                "nrb-fsr-npl-ratio-annual: 'NPL/ Total loan' row not found "
                "in Table 2.3 — PDF layout may have changed"
            ),
        ))
    else:
        pair = _extract_last_two_floats(npl_match.group(1))
        if pair is None:
            errors.append(ParserError(
                error_class="ValueUnparseable",
                error_detail=(
                    "nrb-fsr-npl-ratio-annual: fewer than 2 numeric tokens "
                    f"found in NPL row: {npl_match.group(1)!r}"
                ),
                source_excerpt=npl_match.group(0),
            ))
        else:
            _prev, current = pair
            staging_rows.append(replace(
                base,
                indicator_slug_raw="nrb-fsr-npl-ratio-annual",
                value=current,
                unit="percent",
                parser_notes=(
                    f"Overall NPL/Total loan ratio; prior year = {_prev}; "
                    "source: Table 2.3 Assets Quality-Related Indicators"
                ),
            ))

    # 2. Tier 1 & Tier 2 Capital / RWE — Overall current year.
    cap_match = _CAPITAL_ROW_RE.search(text)
    if cap_match is None:
        errors.append(ParserError(
            error_class="ColumnMissing",
            error_detail=(
                "nrb-fsr-capital-adequacy-annual: 'Tier 1 & Tier 2 Capital /RWE' "
                "row not found in Table 2.3 — PDF layout may have changed"
            ),
        ))
    else:
        pair = _extract_last_two_floats(cap_match.group(1))
        if pair is None:
            errors.append(ParserError(
                error_class="ValueUnparseable",
                error_detail=(
                    "nrb-fsr-capital-adequacy-annual: fewer than 2 numeric tokens "
                    f"found in capital row: {cap_match.group(1)!r}"
                ),
                source_excerpt=cap_match.group(0),
            ))
        else:
            _prev, current = pair
            staging_rows.append(replace(
                base,
                indicator_slug_raw="nrb-fsr-capital-adequacy-annual",
                value=current,
                unit="percent",
                parser_notes=(
                    f"Overall Tier 1 & Tier 2 Capital/RWE; prior year = {_prev}; "
                    "source: Table 2.3 Capital adequacy related indicators"
                ),
            ))

    # 3. CD Ratio — Overall current year.
    cd_match = _CD_RATIO_ROW_RE.search(text)
    if cd_match is None:
        errors.append(ParserError(
            error_class="ColumnMissing",
            error_detail=(
                "nrb-fsr-credit-deposit-ratio-annual: 'CD Ratio' row not found "
                "in Table 2.3 — PDF layout may have changed"
            ),
        ))
    else:
        pair = _extract_last_two_floats(cd_match.group(1))
        if pair is None:
            errors.append(ParserError(
                error_class="ValueUnparseable",
                error_detail=(
                    "nrb-fsr-credit-deposit-ratio-annual: fewer than 2 numeric tokens "
                    f"found in CD Ratio row: {cd_match.group(1)!r}"
                ),
                source_excerpt=cd_match.group(0),
            ))
        else:
            _prev, current = pair
            staging_rows.append(replace(
                base,
                indicator_slug_raw="nrb-fsr-credit-deposit-ratio-annual",
                value=current,
                unit="percent",
                parser_notes=(
                    f"Overall CD Ratio; prior year = {_prev}; "
                    "source: Table 2.3 Credit and Deposit-Related Indicators"
                ),
            ))

    # ── Determine status ──────────────────────────────────────────────────────
    _target_slugs = frozenset({
        "nrb-fsr-npl-ratio-annual",
        "nrb-fsr-capital-adequacy-annual",
        "nrb-fsr-credit-deposit-ratio-annual",
    })
    found_slugs = {row.indicator_slug_raw for row in staging_rows}

    if not staging_rows:
        status: ParserStatus = "failure"
    elif found_slugs < _target_slugs:
        status = "partial"
    else:
        status = "success"

    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes JSON to stdout. Exit codes:
      0: parser ran (status may still be 'failure'; consumer reads stdout)
      2: usage error
      1: catastrophic crash (let Python propagate)
    """
    import json
    import sys
    from dataclasses import asdict

    if len(sys.argv) != 3:
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
