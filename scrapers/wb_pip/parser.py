"""World Bank PIP (Poverty and Inequality Platform, Nepal) parser — deterministic Python.

Source id: ``wb-pip``

Input format:
    A JSON file with the shape produced by the ingest CLI (``scripts/ingest-pip.ts``).
    The CLI queries PIP at three poverty lines (survey-anchor mode) plus the
    $3.65 fill-gaps series, and merges them into:

    .. code-block:: json

        {
          "fetched_at": "2026-06-11T00:00:00Z",
          "country_code": "NPL",
          "reporting_level": "national",
          "anchors": [
            {
              "reporting_year": 2022, "survey_year": 2022.5,
              "survey_acronym": "LSS-IV", "welfare_type": "consumption",
              "headcount_215": 0.0021, "headcount_365": 0.0538, "headcount_685": 0.3755,
              "poverty_gap_365": 0.0093, "poverty_severity_365": 0.0024,
              "gini": 0.3002, "mean": 9.4669, "median": 8.0324,
              "decile1": 0.0367, "decile10": 0.2418
            }
          ],
          "series_365": [
            {"reporting_year": 2011, "headcount": 0.30,
             "estimation_type": "interpolation", "estimate_type": "projection"}
          ]
        }

    ``anchors`` are actual survey rounds (5 for Nepal: 1984 MHBS, 1995 LSS-I,
    2003 LSS-II, 2010 LSS-III, 2022 LSS-IV) — the only rows PIP populates with
    distributional detail (gini, deciles, mean, median). They become
    ``observation_type='actual'`` / confidence A.

    ``series_365`` is the $3.65 headcount filled across all years; rows for
    NON-anchor years are emitted as the modelled poverty trend with
    ``observation_type`` derived from PIP's ``estimation_type`` (ADR-0025) and
    confidence B. Anchor years are taken from ``anchors`` (authoritative),
    never from the filled series.

Period dating (Nepal fiscal year):
    PIP ``reporting_year`` is a calendar AD year, but it labels the same Nepal
    survey rounds the World Bank WDI ingest already maps onto Nepal's July
    fiscal year (WDI's Gini for Nepal is itself sourced from PIP). To keep
    ``pip-*`` and ``wdi-*`` aligned for the same survey, we reuse the WDI
    convention: ``date`` "Y" → FY beginning Shrawan of BS year (Y + 57):
      - PIP year "2022" → BS FY 2079/80 → AD Jul 2022 – Jul 2023.
    The ±2-day tolerance at the TS validation layer accommodates the
    mid-month-15 approximation (see docs/CALENDAR_AND_PERIODS.md).

Units:
    PIP returns headcount / gap / severity / decile shares as ratios in [0,1]
    → ×100 to ``percent``. Gini is a [0,1] ratio → ×100 to ``index_points``
    (matching ``wdi-gini-index`` so the two cross-check). Mean and median are
    daily consumption in 2017-PPP international dollars → ``intl_dollar_per_day``.

Confidence: ``A`` for survey anchors; ``B`` for the modelled (interpolated /
extrapolated / projected) headcount series.

ADR-0003: no LLM / AI calls. Deterministic file-in → dataclass-out.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, TypedDict

from _common.periods import fiscal_year_ad_label, fiscal_year_label
from _common.types import (
    ConfidenceGrade,
    ObservationType,
    ParserError,
    ParserErrorClass,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "wb-pip"

# PIP year Y → Nepal FY starting Shrawan of BS year (Y + 57). Same convention as
# wb_wdi/imf_weo (WDI's Nepal Gini is itself fed by PIP, so labels match).
_BS_AD_OFFSET: Final[int] = 57

# Anchor field → (slug, unit, scale). Emitted only when the field is non-null.
# All anchor rows are observation_type='actual', confidence A.
_ANCHOR_FIELDS: Final[list[tuple[str, str, str, float]]] = [
    ("headcount_215",       "pip-poverty-headcount-215",  "percent",              100.0),
    ("headcount_365",       "pip-poverty-headcount-365",  "percent",              100.0),
    ("headcount_685",       "pip-poverty-headcount-685",  "percent",              100.0),
    ("poverty_gap_365",     "pip-poverty-gap-365",        "percent",              100.0),
    ("poverty_severity_365", "pip-poverty-severity-365",  "percent",              100.0),
    ("gini",                "pip-gini",                   "index_points",         100.0),
    ("mean",                "pip-mean-consumption",       "intl_dollar_per_day",    1.0),
    ("median",              "pip-median-consumption",     "intl_dollar_per_day",    1.0),
    ("decile1",             "pip-decile1-share",          "percent",              100.0),
    ("decile10",            "pip-decile10-share",         "percent",              100.0),
]

_SERIES_SLUG: Final[str] = "pip-poverty-headcount-365"
_SERIES_SCALE: Final[float] = 100.0

_MIN_YEAR: Final[int] = 1960
_MAX_YEAR: Final[int] = 2100


class _AnchorRow(TypedDict, total=False):
    reporting_year: int
    survey_acronym: str | None
    welfare_type: str | None


def _fail(error_class: ParserErrorClass, detail: str) -> ParserResult:
    return ParserResult(
        status="failure",
        parser_version=PARSER_VERSION,
        errors=[ParserError(error_class=error_class, error_detail=detail)],
    )


def _period(year: int) -> tuple[str, str, datetime, datetime]:
    """Return (fy_bs, fy_ad, ad_start, ad_end) for a PIP reporting year."""
    bs_start = year + _BS_AD_OFFSET
    return (
        fiscal_year_label(bs_start),
        fiscal_year_ad_label(bs_start),
        datetime(year, 7, 15, tzinfo=UTC),
        datetime(year + 1, 7, 15, tzinfo=UTC),
    )


def _series_observation_type(
    estimation_type: str, year: int, min_anchor: int, max_anchor: int
) -> ObservationType:
    """Map PIP's estimation_type + position relative to the survey range.

    interpolation between surveys → 'interpolated'; extrapolation forward of the
    last survey → 'projection'; extrapolation before the first survey →
    'estimate' (ADR-0025).
    """
    if estimation_type == "interpolation":
        return "interpolated"
    if year > max_anchor:
        return "projection"
    if year < min_anchor:
        return "estimate"
    # extrapolation inside the survey range is not expected; treat as estimate.
    return "estimate"


def _row(
    *,
    slug: str,
    value: float,
    unit: str,
    year: int,
    pub_date_ad: datetime,
    confidence: ConfidenceGrade,
    observation_type: ObservationType,
    notes: str,
) -> StagingRowDraft:
    fy_bs, fy_ad, ad_start, ad_end = _period(year)
    return StagingRowDraft(
        indicator_slug_raw=slug,
        value=value,
        unit=unit,
        reporting_period_type="annual",
        reporting_period_bs=fy_bs,
        reporting_period_ad_start=ad_start,
        reporting_period_ad_end=ad_end,
        publication_date_ad=pub_date_ad,
        publication_date_bs=fy_bs,
        fiscal_year_bs=fy_bs,
        fiscal_year_ad_label=fy_ad,
        confidence_grade_proposed=confidence,
        observation_type=observation_type,
        parser_notes=notes,
    )


def _coerce_year(value: Any) -> int | None:
    try:
        year = int(value)
    except (ValueError, TypeError):
        return None
    return year if _MIN_YEAR <= year <= _MAX_YEAR else None


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse a PIP combined JSON fixture; see module docstring for the contract."""
    _ = source_document_id  # contract parameter — unused by this parser

    path = Path(source_document_path)
    if not path.exists():
        return _fail("Other", f"source file not found: {path}")

    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _fail("EncodingError", f"json read failed: {exc}")

    if not isinstance(raw, dict):
        return _fail("Other", "root is not a JSON object")

    try:
        pub_date_ad = datetime.fromisoformat(str(raw.get("fetched_at", "")).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pub_date_ad = datetime(2026, 1, 1, tzinfo=UTC)

    anchors = raw.get("anchors")
    series = raw.get("series_365", [])
    if not isinstance(anchors, list):
        return _fail("Other", 'missing or invalid "anchors" array')
    if not isinstance(series, list):
        return _fail("Other", '"series_365" must be an array when present')

    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    anchor_years: set[int] = set()

    # ── Survey anchors (actual, confidence A) ──────────────────────────────
    for anchor in anchors:
        if not isinstance(anchor, dict):
            errors.append(ParserError(error_class="Other", error_detail="anchor is not an object"))
            continue
        year = _coerce_year(anchor.get("reporting_year"))
        if year is None:
            errors.append(
                ParserError(
                    error_class="PeriodAmbiguous",
                    error_detail=f"anchor reporting_year invalid: {anchor.get('reporting_year')!r}",
                )
            )
            continue
        anchor_years.add(year)
        acr = anchor.get("survey_acronym") or "survey"

        for field, slug, unit, scale in _ANCHOR_FIELDS:
            raw_value = anchor.get(field)
            if raw_value is None:
                continue
            try:
                value = float(raw_value) * scale
            except (ValueError, TypeError):
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=f"{slug} {year}: value {raw_value!r} not numeric",
                        source_excerpt=str(raw_value),
                    )
                )
                continue
            rows.append(
                _row(
                    slug=slug,
                    value=value,
                    unit=unit,
                    year=year,
                    pub_date_ad=pub_date_ad,
                    confidence="A",
                    observation_type="actual",
                    notes=f"PIP {acr} survey anchor; field {field}; raw={raw_value}",
                )
            )

    if not anchor_years:
        return _fail("Other", "no valid survey anchors in input")

    min_anchor, max_anchor = min(anchor_years), max(anchor_years)

    # ── Modelled $3.65 headcount series for NON-anchor years (confidence B) ──
    for point in series:
        if not isinstance(point, dict):
            errors.append(ParserError(error_class="Other", error_detail="series point is not an object"))
            continue
        year = _coerce_year(point.get("reporting_year"))
        if year is None:
            errors.append(
                ParserError(
                    error_class="PeriodAmbiguous",
                    error_detail=f"series reporting_year invalid: {point.get('reporting_year')!r}",
                )
            )
            continue
        if year in anchor_years:
            continue  # survey years are authoritative via the anchor block
        raw_value = point.get("headcount")
        if raw_value is None:
            continue
        try:
            value = float(raw_value) * _SERIES_SCALE
        except (ValueError, TypeError):
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=f"series headcount {year}: value {raw_value!r} not numeric",
                    source_excerpt=str(raw_value),
                )
            )
            continue
        estimation_type = str(point.get("estimation_type", ""))
        observation_type = _series_observation_type(estimation_type, year, min_anchor, max_anchor)
        rows.append(
            _row(
                slug=_SERIES_SLUG,
                value=value,
                unit="percent",
                year=year,
                pub_date_ad=pub_date_ad,
                confidence="B",
                observation_type=observation_type,
                notes=f"PIP $3.65 filled series; estimation_type={estimation_type}; raw={raw_value}",
            )
        )

    if not rows:
        return _fail("Other", "no data rows produced")

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=rows,
        errors=errors,
    )


def _serialize_result(result: ParserResult) -> dict[str, Any]:
    """Serialize ``ParserResult`` to the JSON shape expected by ParserOutputSchema."""
    out_rows: list[dict[str, Any]] = []
    for row in result.staging_rows:
        d = asdict(row)
        for k in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            v = d.get(k)
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        out_rows.append(d)
    return {
        "status": result.status,
        "parser_version": result.parser_version,
        "staging_rows": out_rows,
        "errors": [asdict(e) for e in result.errors],
    }


def _main() -> None:
    """CLI entry-point: ``parser.py <source_document_path> <source_document_id>``."""
    import sys

    if len(sys.argv) != 3:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    json.dump(_serialize_result(result), sys.stdout)


if __name__ == "__main__":
    _main()
