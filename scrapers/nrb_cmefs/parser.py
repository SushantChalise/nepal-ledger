"""NRB CMEFs English-edition PDF parser — deterministic Python.

Source: NRB "Current Macroeconomic and Financial Situation of Nepal" monthly
bulletin (English edition only — Path B1, ADR-0003).

Strategy:
    NRB's CMEFs bulletin re-uses stable narrative phrasings issue after
    issue. The PDF text layer is clean Latin-script — no OCR needed. The
    parser extracts text with ``pdfplumber`` and applies anchored regex
    patterns to lift indicators from the executive narrative.

    Prose over tables: tables shift columns at FY boundaries (source
    profile §"Known breakage modes"); prose phrasings are stable. When a
    pattern misses, the parser emits a typed ``PageLayoutChanged`` error
    instead of inventing a value.

Period detection (v0.2.0):
    The parser reads the bulletin title ("based on N Months of YYYY/YY"
    or "based on BS_Month BS_Year") to set the reporting period
    dynamically, replacing the hardcoded FY 2082/83 constants from v0.1.0.
    This unblocks monthly releases and full back-history ingestion.

Target indicators (v0.2.0):

    Headline (v0.1.0 — stable across FY 2080/81–2082/83):
        - cmefs-ncpi-yoy-overall              (percent_yoy, end-of-period)
        - cmefs-remittance-inflow-ytd         (npr_billion, cumulative)
        - cmefs-merchandise-imports-ytd       (npr_billion, cumulative)
        - cmefs-trade-deficit-ytd             (npr_billion, cumulative)
        - cmefs-bop-surplus-ytd               (npr_billion, cumulative)
        - cmefs-gross-forex-reserves          (npr_billion, end-of-period)
        - cmefs-forex-reserves-months-of-import-cover (months, end-of-period)

    Extended (v0.2.0):
        - cmefs-merchandise-exports-ytd       (npr_billion, cumulative)
        - cmefs-govt-revenue-total-ytd        (npr_billion, cumulative)
        - cmefs-govt-expenditure-total-ytd    (npr_billion, cumulative)
        - cmefs-govt-fiscal-balance-ytd       (npr_billion, cumulative; sign in notes)
        - cmefs-m2-yoy                        (percent_yoy, end-of-period)
        - cmefs-private-sector-credit-yoy     (percent_yoy, end-of-period)
        - cmefs-bfi-deposits-yoy              (percent_yoy, end-of-period)

Cross-validation hooks (enforced by the TS validation layer, not this parser):
    cmefs-ncpi-yoy-overall ↔ ncpi-overall-index-overall-yoy within ±0.01pp.
    cmefs-govt-revenue-total-ytd ↔ fcgo-total-revenue-outturn-annual (unit-scaled).
    cmefs-govt-expenditure-total-ytd ↔ fcgo-total-expenditure-outturn-annual.

Versioning:
    Bump PARSER_VERSION on any behaviour change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pdfplumber

from _common.periods import (
    BsMonth,
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
)
from _common.types import (
    ConfidenceGrade,
    ParserError,
    ParserResult,
    ParserStatus,
    ReportingPeriodType,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.2.0"
SOURCE_ID: Final[str] = "nrb-cmefs-monthly"

# Provisional-marker pattern: single ``P`` directly adjacent to a digit.
# Conservative: excludes ``P=Provisional`` legend and English words starting P.
_PROVISIONAL_INLINE_RE: Final[re.Pattern[str]] = re.compile(
    r"\d+(?:\.\d+)?\s*[Pp]\b(?!ercent|rovisional|rovincial|aid|er\b)"
)

# ── Period detection ──────────────────────────────────────────────────────────

_MONTH_ORDINALS: Final[dict[str, int]] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}

# BS months in fiscal-year order (month 1 = Shrawan, month 12 = Ashadh).
_FY_ORDINAL_TO_BS_MONTH: Final[tuple[BsMonth, ...]] = (
    "Shrawan", "Bhadra", "Ashwin", "Kartik", "Mangsir", "Poush",
    "Magh", "Falgun", "Chait", "Baisakh", "Jestha", "Ashadh",
)

# Fiscal-year position (1-based) for each BS month name.
_BS_MONTH_FY_POS: Final[dict[str, int]] = {
    m: i + 1 for i, m in enumerate(_FY_ORDINAL_TO_BS_MONTH)
}

# "based on Nine Months of 2025/26"  (simple form)
# "Based on Nine Months' Data (Ending Mid-April) of 2025/26"  (NRB extended form)
# The lazy [\s\S]{0,100}? bridges the apostrophe + optional parenthetical clause.
_TITLE_N_MONTHS_RE: Final[re.Pattern[str]] = re.compile(
    r"based\s+on\s+(\w+)\s+months?[\s\S]{0,100}?of\s+(\d{4})/\d{2,4}",
    re.IGNORECASE,
)

# "based on Magh 2082" — monthly release, BS month + BS year.
_TITLE_MONTHLY_RE: Final[re.Pattern[str]] = re.compile(
    r"based\s+on\s+(Shrawan|Bhadra|Ashwin|Kartik|Mangsir|Poush|Magh|"
    r"Falgun|Chait|Baisakh|Jestha|Ashadh)\s+(\d{4})",
    re.IGNORECASE,
)

# Typical NRB publication lag: end-of-period → actual bulletin release.
# Used only when the orchestrator does not supply the real publication date.
_NRB_PUB_LAG_DAYS: Final[int] = 45


@dataclass(frozen=True)
class _PeriodInfo:
    """Reporting-period metadata derived from the bulletin title."""

    bs_fy_start: int        # e.g. 2082 for FY 2082/83
    end_bs_month: BsMonth   # last BS month of the reporting window
    end_bs_year: int        # BS year in which end_bs_month falls
    num_months: int         # 1–12 months covered
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str
    fiscal_year_bs: str
    fiscal_year_ad_label: str


def _detect_period(text: str, errors: list[ParserError]) -> _PeriodInfo | None:
    """Detect the reporting period from the bulletin title (first 3000 chars).

    Searches for two NRB title patterns; appends to *errors* and returns
    None if neither matches or if the period word is unrecognised.
    """
    head = text[:3000]

    m_n = _TITLE_N_MONTHS_RE.search(head)
    if m_n:
        month_word = m_n.group(1).lower()
        num_months = _MONTH_ORDINALS.get(month_word)
        if num_months is None:
            errors.append(ParserError(
                error_class="PeriodAmbiguous",
                error_detail=f"unrecognised month-count word: {m_n.group(1)!r}",
                source_excerpt=m_n.group(0),
            ))
            return None
        ad_fy_start = int(m_n.group(2))
        bs_fy_start = ad_fy_start + 57
        end_bs_month = _FY_ORDINAL_TO_BS_MONTH[num_months - 1]
        end_bs_year = bs_fy_start if num_months <= 9 else bs_fy_start + 1
        if num_months == 9:
            period_type: ReportingPeriodType = "nine_months_cumulative"
            period_bs = f"FY {fiscal_year_label(bs_fy_start)} 9M"
        elif num_months == 1:
            period_type = "monthly"
            period_bs = f"{end_bs_year}/{(end_bs_year + 1) % 100:02d} {end_bs_month}"
        else:
            period_type = "year_to_date"
            period_bs = f"FY {fiscal_year_label(bs_fy_start)} {num_months}M"
        return _PeriodInfo(
            bs_fy_start=bs_fy_start,
            end_bs_month=end_bs_month,
            end_bs_year=end_bs_year,
            num_months=num_months,
            reporting_period_type=period_type,
            reporting_period_bs=period_bs,
            fiscal_year_bs=fiscal_year_label(bs_fy_start),
            fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        )

    m_mon = _TITLE_MONTHLY_RE.search(head)
    if m_mon:
        raw_month = m_mon.group(1)
        end_bs_month = next(
            (bm for bm in _FY_ORDINAL_TO_BS_MONTH if bm.lower() == raw_month.lower()),
            None,
        )
        if end_bs_month is None:
            errors.append(ParserError(
                error_class="PeriodAmbiguous",
                error_detail=f"unrecognised BS month: {raw_month!r}",
                source_excerpt=m_mon.group(0),
            ))
            return None
        end_bs_year = int(m_mon.group(2))
        num_months = _BS_MONTH_FY_POS[end_bs_month]
        bs_fy_start = end_bs_year if num_months <= 9 else end_bs_year - 1
        period_bs = f"{end_bs_year}/{(end_bs_year + 1) % 100:02d} {end_bs_month}"
        return _PeriodInfo(
            bs_fy_start=bs_fy_start,
            end_bs_month=end_bs_month,
            end_bs_year=end_bs_year,
            num_months=num_months,
            reporting_period_type="monthly",
            reporting_period_bs=period_bs,
            fiscal_year_bs=fiscal_year_label(bs_fy_start),
            fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        )

    errors.append(ParserError(
        error_class="PeriodAmbiguous",
        error_detail=(
            "bulletin title not found in first 3000 chars — "
            "cannot determine reporting period"
        ),
    ))
    return None


# ── Indicator specs ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _IndicatorSpec:
    """Extraction recipe for one indicator in the bulletin text.

    ``pattern`` has exactly one numeric capture group. Applied against the
    full document text. ``end_of_period=True`` → point-in-time (start ==
    end == end_bs_month mid-date); ``False`` → cumulative span (Shrawan …
    end_bs_month), or same point if num_months == 1 (monthly release).
    """

    slug: str
    unit: str
    pattern: re.Pattern[str]
    end_of_period: bool


_INDICATORS: Final[tuple[_IndicatorSpec, ...]] = (
    # ── v0.1.0 headline indicators ────────────────────────────────────────────
    _IndicatorSpec(
        slug="cmefs-ncpi-yoy-overall",
        unit="percent_yoy",
        pattern=re.compile(
            r"y-o-y\s+consumer\s+price\s+inflation\s+in\s+Nepal\s+"
            r"remained\s+at\s+(\d+\.\d+)\s*percent",
            re.IGNORECASE,
        ),
        end_of_period=True,
    ),
    _IndicatorSpec(
        slug="cmefs-remittance-inflow-ytd",
        unit="npr_billion",
        pattern=re.compile(
            r"Remittance\s+inflows\s+(?:increased|decreased)\s+\d+\.\d+\s*percent"
            r"\s+to\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    _IndicatorSpec(
        slug="cmefs-merchandise-imports-ytd",
        unit="npr_billion",
        # NRB typo "mercandise" accepted alongside correct spelling.
        pattern=re.compile(
            r"mer[c]?[h]?andise\s+imports\s+(?:increased|decreased)\s+\d+\.\d+\s*percent"
            r"\s+to\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    _IndicatorSpec(
        slug="cmefs-trade-deficit-ytd",
        unit="npr_billion",
        pattern=re.compile(
            r"Total\s+trade\s+deficit\s+(?:increased|decreased)\s+\d+\.\d+\s*percent"
            r"\s+to\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    _IndicatorSpec(
        slug="cmefs-bop-surplus-ytd",
        unit="npr_billion",
        pattern=re.compile(
            r"Balance\s+of\s+Payments\s+\(BOP\)\s+remained\s+at\s+a\s+"
            r"(?:surplus|deficit)\s+of\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    _IndicatorSpec(
        slug="cmefs-gross-forex-reserves",
        unit="npr_billion",
        # Chart-axis labels may interleave; tolerate up to ~250 chars of noise.
        pattern=re.compile(
            r"Gross\s+foreign\s+exchange\s+reserves\b.{0,250}?"
            r"(?:increased|decreased)\s+\d+\.\d+\s*percent\s+to\b"
            r".{0,80}?Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE | re.DOTALL,
        ),
        end_of_period=True,
    ),
    _IndicatorSpec(
        slug="cmefs-forex-reserves-months-of-import-cover",
        unit="months",
        pattern=re.compile(
            r"merchandise\s+and\s+services\s+imports\s+of\s+(\d+\.\d+)\s+months",
            re.IGNORECASE,
        ),
        end_of_period=True,
    ),
    # ── v0.2.0 extended — external sector ─────────────────────────────────────
    _IndicatorSpec(
        slug="cmefs-merchandise-exports-ytd",
        unit="npr_billion",
        # NRB typo "mercandise" accepted alongside correct spelling.
        pattern=re.compile(
            r"mer[c]?[h]?andise\s+exports\s+(?:increased|decreased)\s+\d+\.\d+\s*percent"
            r"\s+to\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    # ── v0.2.0 extended — government finance ─────────────────────────────────
    _IndicatorSpec(
        slug="cmefs-govt-revenue-total-ytd",
        unit="npr_billion",
        pattern=re.compile(
            r"[Tt]otal\s+(?:government\s+)?revenue\s+(?:increased|decreased)\s+\d+\.\d+\s*percent"
            r"\s+to\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    _IndicatorSpec(
        slug="cmefs-govt-expenditure-total-ytd",
        unit="npr_billion",
        pattern=re.compile(
            r"[Tt]otal\s+(?:government\s+)?expenditure\s+(?:increased|decreased)\s+\d+\.\d+\s*percent"
            r"\s+to\s+Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE,
        ),
        end_of_period=False,
    ),
    _IndicatorSpec(
        slug="cmefs-govt-fiscal-balance-ytd",
        unit="npr_billion",
        # Captures the magnitude; sign (surplus/deficit) recorded in parser_notes.
        pattern=re.compile(
            r"[Ff]iscal\s+(?:deficit|surplus)\s+.{0,60}?Rs\.?\s*(\d+\.\d+)\s*billion",
            re.IGNORECASE | re.DOTALL,
        ),
        end_of_period=False,
    ),
    # ── v0.2.0 extended — monetary ────────────────────────────────────────────
    _IndicatorSpec(
        slug="cmefs-m2-yoy",
        unit="percent_yoy",
        pattern=re.compile(
            r"[Bb]road\s+money\s+\(?M2\)?\s+(?:increased|decreased)\s+(\d+\.\d+)\s*percent",
            re.IGNORECASE,
        ),
        end_of_period=True,
    ),
    _IndicatorSpec(
        slug="cmefs-private-sector-credit-yoy",
        unit="percent_yoy",
        pattern=re.compile(
            r"[Pp]rivate\s+sector\s+credit\s+(?:increased|decreased)\s+(\d+\.\d+)\s*percent",
            re.IGNORECASE,
        ),
        end_of_period=True,
    ),
    _IndicatorSpec(
        slug="cmefs-bfi-deposits-yoy",
        unit="percent_yoy",
        pattern=re.compile(
            r"[Dd]eposits?\s+of\s+BFIs?\s+(?:increased|decreased)\s+(\d+\.\d+)\s*percent",
            re.IGNORECASE,
        ),
        end_of_period=True,
    ),
)

# v0.1.0 headline slugs — expected to match in every NRB CMEFs edition.
_HEADLINE_SLUGS: Final[frozenset[str]] = frozenset({
    "cmefs-ncpi-yoy-overall",
    "cmefs-remittance-inflow-ytd",
    "cmefs-merchandise-imports-ytd",
    "cmefs-trade-deficit-ytd",
    "cmefs-bop-surplus-ytd",
    "cmefs-gross-forex-reserves",
    "cmefs-forex-reserves-months-of-import-cover",
})


def _extract_pdf_text(path: Path) -> str:
    """Concatenate page text from a PDF; collapse soft-hyphenation."""
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    raw = "\n".join(parts)
    return re.sub(r"-\s*\n\s*", "", raw)


def _is_provisional(window: str) -> bool:
    """True iff the matched-value window carries an inline ``P`` flag."""
    return bool(_PROVISIONAL_INLINE_RE.search(window))


def _period_bounds(period: _PeriodInfo, end_of_period: bool) -> tuple[datetime, datetime]:
    """Resolve AD date bounds for one indicator given the document period.

    For monthly releases (num_months == 1) both bounds are always the same
    point regardless of end_of_period, since start == end for a single month.
    """
    end = mid_month_ad(period.end_bs_month, period.end_bs_year)
    if end_of_period or period.num_months == 1:
        return end, end
    start = mid_month_ad("Shrawan", period.bs_fy_start)
    return start, end


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one NRB CMEFs English-edition PDF; emit headline + extended indicators.

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
    period = _detect_period(text, errors)
    if period is None:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors,
        )

    # Approximate publication date (orchestrator can supply the real one via
    # source_documents.downloaded_at; this heuristic is used when that path
    # is unavailable — e.g. during offline testing).
    pub_ad = mid_month_ad(period.end_bs_month, period.end_bs_year) + timedelta(
        days=_NRB_PUB_LAG_DAYS
    )
    pub_bs = f"~{period.fiscal_year_bs} (heuristic)"

    cumul_start, cumul_end = _period_bounds(period, end_of_period=False)

    base = StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="",
        reporting_period_type=period.reporting_period_type,
        reporting_period_bs=period.reporting_period_bs,
        reporting_period_ad_start=cumul_start,
        reporting_period_ad_end=cumul_end,
        publication_date_ad=pub_ad,
        publication_date_bs=pub_bs,
        fiscal_year_bs=period.fiscal_year_bs,
        fiscal_year_ad_label=period.fiscal_year_ad_label,
        confidence_grade_proposed="A",
        parser_notes=None,
    )

    staging_rows: list[StagingRowDraft] = []

    for spec in _INDICATORS:
        match = spec.pattern.search(text)
        if match is None:
            errors.append(ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    f"indicator {spec.slug!r}: narrative anchor not found"
                    " — bulletin phrasing may have shifted"
                ),
            ))
            continue

        raw_value = match.group(1)
        try:
            value = float(raw_value)
        except ValueError:
            errors.append(ParserError(
                error_class="ValueUnparseable",
                error_detail=f"indicator {spec.slug!r}: could not parse {raw_value!r}",
                source_excerpt=match.group(0),
            ))
            continue

        window_start = max(0, match.start(1) - 4)
        window_end = min(len(text), match.end(1) + 28)
        window = text[window_start:window_end]
        provisional = _is_provisional(window)

        confidence: ConfidenceGrade = "B" if provisional else "A"
        notes: str | None = (
            "value carries inline 'P' provisional marker; downgraded A→B"
            if provisional
            else None
        )

        if spec.slug == "cmefs-bop-surplus-ytd" and "deficit" in match.group(0).lower():
            notes = (notes + "; " if notes else "") + "BoP in deficit (negative)"

        if spec.slug == "cmefs-govt-fiscal-balance-ytd":
            sign_note = (
                "fiscal deficit (negative)"
                if "deficit" in match.group(0).lower()
                else "fiscal surplus (positive)"
            )
            notes = (notes + "; " if notes else "") + sign_note

        period_start, period_end = _period_bounds(period, spec.end_of_period)

        row = replace(
            base,
            indicator_slug_raw=spec.slug,
            value=value,
            unit=spec.unit,
            reporting_period_ad_start=period_start,
            reporting_period_ad_end=period_end,
            confidence_grade_proposed=confidence,
            parser_notes=notes,
        )
        staging_rows.append(row)

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors or [ParserError(
                error_class="PageLayoutChanged",
                error_detail="no indicators matched",
            )],
        )

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
    Writes JSON to stdout via ``dataclasses.asdict``.
    Exit codes:
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
