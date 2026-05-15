"""NRB CMEFs English-edition PDF parser — deterministic Python.

Source: NRB "Current Macroeconomic and Financial Situation of Nepal" monthly
bulletin (English edition only — Path B1, ADR pending). The bundled fixture
is the nine-month publication for FY 2082/83 (AD 2025/26).

Strategy:
    NRB's CMEFs bulletin re-uses stable narrative phrasings issue after
    issue ("merchandise exports increased X percent to Rs.Y billion",
    "Balance of Payments (BOP) remained at a surplus of Rs.Z billion",
    etc.). The PDF text layer is clean Latin-script — no OCR is needed,
    no Devanagari is touched. The parser extracts text with ``pdfplumber``
    and applies anchored regex patterns to lift the seven headline
    indicators that feed Pulse v0.

    We deliberately match narrative prose rather than tables: tables in
    this bulletin shift columns and page numbers across FY boundaries
    (see source profile §"Known breakage modes"), but the prose patterns
    are stable. When the prose shifts, the parser emits a typed
    ``PageLayoutChanged`` error for that indicator instead of inventing a
    value.

Target indicators (v0.1.0, headline set per Path B1 brief):
    - ``cmefs-ncpi-yoy-overall`` (percent_yoy, end-of-period)
    - ``cmefs-remittance-inflow-ytd`` (npr_billion, nine_months_cumulative)
    - ``cmefs-merchandise-imports-ytd`` (npr_billion, nine_months_cumulative)
    - ``cmefs-trade-deficit-ytd`` (npr_billion, nine_months_cumulative)
    - ``cmefs-bop-surplus-ytd`` (npr_billion, nine_months_cumulative)
    - ``cmefs-gross-forex-reserves`` (npr_billion, end-of-period)
    - ``cmefs-forex-reserves-months-of-import-cover`` (months,
      end-of-period; "merchandise and services" cover, not the
      merchandise-only figure)

Confidence: ``A`` by default. If any value carries an inline ``P``
(provisional) annotation in the narrative, the parser downgrades that row
to ``B`` and stamps ``parser_notes`` accordingly. (The provisional flag
in the current fixture appears only in the bracketed BoP table footer
``P=Provisional`` — we treat the bulletin's narrative figures as final
until a future release introduces an inline ``P`` marker, in which case
the regex below picks it up.)

Period dating:
    Mid-month placeholders from ``_common.periods``; the TS validator
    refines (±2 days tolerance). For "end of nine-month period"
    indicators (NCPI YoY, forex reserves, months of cover), both
    ``period_ad_start`` and ``period_ad_end`` are anchored to mid-Chait;
    for ``nine_months_cumulative`` indicators the span runs
    mid-Shrawan..mid-Chait.

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
    nine_months_span_ad,
)
from _common.types import (
    ConfidenceGrade,
    ParserError,
    ParserResult,
    ParserStatus,
    ReportingPeriodType,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "nrb-cmefs-monthly"

# Fiscal year and publication anchor for the bundled fixture
# (Nine-Months FY 2082/83, published May 11, 2026). When the orchestrator
# wires source-registry metadata through, these will be derived from the
# release header rather than hard-coded.
_BS_FY_START: Final[int] = 2082
_PUBLICATION_DATE_AD: Final[datetime] = datetime(2026, 5, 11, tzinfo=UTC)
_PUBLICATION_DATE_BS: Final[str] = "2083 Baisakh 28"

# Provisional-marker pattern: bracketed ``P`` or trailing ``P`` after a
# numeric value in the narrative. Conservative: only single-letter ``P``
# directly adjacent to a digit, not the ``P=Provisional`` legend itself.
_PROVISIONAL_INLINE_RE: Final[re.Pattern[str]] = re.compile(
    r"\d+(?:\.\d+)?\s*[Pp]\b(?!ercent|rovisional|rovincial|aid|er\b)"
)


@dataclass(frozen=True)
class _IndicatorSpec:
    """How to find one headline indicator in the bulletin text.

    ``pattern`` must contain exactly one capture group: the numeric value
    (decimal allowed, no thousands separators in the CMEFs prose). The
    regex is applied against the full document text with
    ``re.IGNORECASE`` and ``re.DOTALL`` disabled — we want line-locality.
    """

    slug: str
    unit: str
    period_type: ReportingPeriodType
    pattern: re.Pattern[str]
    # When True, the indicator describes the state at end of period
    # (e.g. NCPI YoY at mid-Chait, forex reserves at mid-Chait). Otherwise
    # it spans Shrawan..Chait (nine-months cumulative).
    end_of_period: bool


# Anchored narrative patterns. Each capture group lifts the numeric value
# NRB highlights in the executive narrative. The phrasings here have been
# stable across the FY 2080/81, 2081/82 and 2082/83 nine-month releases.
# Tolerances: allow 0 or more spaces around punctuation; allow "Rs." with
# or without trailing space; accept percent values with or without the
# percent sign (NRB sometimes writes "stood at 4.47 percent" and
# sometimes uses a chart-only figure).
_INDICATORS: Final[tuple[_IndicatorSpec, ...]] = (
    _IndicatorSpec(
        slug="cmefs-ncpi-yoy-overall",
        unit="percent_yoy",
        period_type="nine_months_cumulative",
        # NRB phrases this both in para 1 ("The y-o-y consumer price
        # inflation stood at X percent") and again in para 12 ("The y-o-y
        # consumer price inflation in Nepal remained at X percent in
        # mid-Month YYYY"). Para 1 collides with the Chart 1 axis labels
        # under pdfplumber's column-aware extraction; we anchor on para 12
        # instead because its line is clean and the phrasing has been
        # stable across recent FY releases.
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
        period_type="nine_months_cumulative",
        # "Remittance inflows increased 39.1 percent to Rs.1659.41 billion"
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
        period_type="nine_months_cumulative",
        # "mercandise imports increased 13.8 percent to Rs.1490.50 billion"
        # NB: NRB's own copy contains the typo "mercandise"; we accept both.
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
        period_type="nine_months_cumulative",
        # "Total trade deficit increased 13.0 percent to Rs.1267.56 billion"
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
        period_type="nine_months_cumulative",
        # "Balance of Payments (BOP) remained at a surplus of Rs.731.16 billion"
        # Captures positive; if BOP is in deficit we still capture the magnitude
        # and stamp parser_notes (handled post-match).
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
        period_type="nine_months_cumulative",
        # "Gross foreign exchange reserves increased 30.5 percent to
        # Rs.3494.73 billion". Under pdfplumber's column-aware extraction
        # the Chart 3 axis labels and title interleave between
        # "reserves" and "increased"; we tolerate up to ~250 chars of
        # chart-noise in between using a non-greedy DOTALL window. The
        # ``\bChart\b`` and ``(Mid-April)`` tokens we expect in that gap
        # are harmless because the percent/Rs anchors that bracket the
        # capture are highly specific.
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
        period_type="nine_months_cumulative",
        # "merchandise and services imports of 18.4 months"
        # We anchor to "and services imports of N months" to avoid
        # collision with the bare "merchandise imports of N months" figure.
        pattern=re.compile(
            r"merchandise\s+and\s+services\s+imports\s+of\s+"
            r"(\d+\.\d+)\s+months",
            re.IGNORECASE,
        ),
        end_of_period=True,
    ),
)


def _extract_pdf_text(path: Path) -> str:
    """Concatenate page text from a PDF. Single space joins; line breaks
    preserved within pages and ``\\n`` between pages so line-locality is
    retained for regex matching.
    """
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            parts.append(page_text)
    # Collapse soft hyphenation NRB occasionally inserts ("merchan-\ndise")
    # so the regex anchors don't trip on it.
    raw = "\n".join(parts)
    return re.sub(r"-\s*\n\s*", "", raw)


def _is_provisional(window: str) -> bool:
    """True iff the matched-value window carries an inline ``P`` flag."""
    return bool(_PROVISIONAL_INLINE_RE.search(window))


def _period_bounds(
    bs_fy_start: int, end_of_period: bool
) -> tuple[datetime, datetime]:
    """Resolve AD bounds for an indicator's reporting period."""
    if end_of_period:
        chait_mid = mid_month_ad("Chait", bs_fy_start)
        return chait_mid, chait_mid
    start, _ = nine_months_span_ad(bs_fy_start)
    return start, mid_month_ad("Chait", bs_fy_start)


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one NRB CMEFs English-edition PDF; emit headline indicators.

    Arguments:
        source_document_path: filesystem path to the downloaded PDF.
        source_document_id: opaque ID from ``source_documents``; threaded
            through for symmetry with the orchestrator contract.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``, ``errors``.
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

    ad_start_span, ad_end_span = _period_bounds(_BS_FY_START, end_of_period=False)
    ad_chait_mid = mid_month_ad("Chait", _BS_FY_START)

    base = StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="",
        reporting_period_type="nine_months_cumulative",
        reporting_period_bs=f"FY {fiscal_year_label(_BS_FY_START)} 9M",
        reporting_period_ad_start=ad_start_span,
        reporting_period_ad_end=ad_end_span,
        publication_date_ad=_PUBLICATION_DATE_AD,
        publication_date_bs=_PUBLICATION_DATE_BS,
        fiscal_year_bs=fiscal_year_label(_BS_FY_START),
        fiscal_year_ad_label=fiscal_year_ad_label(_BS_FY_START),
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
                        f"indicator {spec.slug!r}: narrative anchor not "
                        f"found — bulletin phrasing may have shifted"
                    ),
                )
            )
            continue

        raw_value = match.group(1)
        try:
            value = float(raw_value)
        except ValueError:
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=(
                        f"indicator {spec.slug!r}: could not parse {raw_value!r}"
                    ),
                    source_excerpt=match.group(0),
                )
            )
            continue

        # Inspect a 32-char window around the value for an inline provisional flag.
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

        # BoP can be a surplus or deficit; preserve sign in parser_notes
        # so downstream consumers can interpret. We always emit the
        # magnitude; the qualifier is captured in match.group(0).
        if spec.slug == "cmefs-bop-surplus-ytd" and "deficit" in match.group(0).lower():
            notes = (notes + "; " if notes else "") + "BoP in deficit (negative)"

        if spec.end_of_period:
            row = replace(
                base,
                indicator_slug_raw=spec.slug,
                value=value,
                unit=spec.unit,
                reporting_period_ad_start=ad_chait_mid,
                reporting_period_ad_end=ad_chait_mid,
                confidence_grade_proposed=confidence,
                parser_notes=notes,
            )
        else:
            row = replace(
                base,
                indicator_slug_raw=spec.slug,
                value=value,
                unit=spec.unit,
                confidence_grade_proposed=confidence,
                parser_notes=notes,
            )
        staging_rows.append(row)

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors
            or [
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail="no headline indicators matched",
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


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes JSON to stdout via ``dataclasses.asdict`` (mirrors Worker P1's
    fix; do NOT use ``ParserResult.to_json_dict()`` directly — see brief).
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
    # Datetime fields under staging_rows aren't JSON-serialisable raw;
    # walk and ISO-format them (mirrors StagingRowDraft.to_json_dict but
    # built on asdict so the row dict shape stays in lock-step with the
    # dataclass).
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
