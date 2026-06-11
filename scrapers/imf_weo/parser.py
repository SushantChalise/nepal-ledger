"""IMF World Economic Outlook (Nepal) parser — deterministic Python.

Source id: ``imf-weo``

Input format:
    A JSON file with the shape produced by the ingest CLI
    (``scripts/ingest-imf-weo.ts``):

    .. code-block:: json

        {
          "fetched_at": "2026-06-11T00:00:00Z",
          "country_code": "NPL",
          "vintage": "2026-04",
          "projection_from_year": 2025,
          "indicators": {
            "NGDPD": [
              {"date": "2023", "value": 40.835},
              {"date": "2026", "value": 49.1}
            ],
            "GGXWDG_NGDP": [
              {"date": "2024", "value": 42.1},
              {"date": "2025", "value": null}
            ]
          }
        }

    ``date`` is the AD year-string the IMF assigns to Nepal's fiscal year (see
    "Period dating").  ``value`` may be ``null`` for years IMF has no figure;
    those rows are skipped silently.

    ``projection_from_year`` is the first AD year that is an IMF **projection**
    rather than a realised actual (the published "estimates start after" year
    + 1 for the vintage).  Every datapoint whose year >= this value is emitted
    with ``observation_type='projection'``; earlier years are ``'actual'``
    (ADR-0025).  When the key is absent or null, every row is ``'actual'``
    (conservative — we never label a realised value as a forecast, and we only
    label forecasts when the operator supplies the published boundary).

Period dating (Nepal fiscal year):
    The IMF reports Nepal on a fiscal-year basis starting mid-July, identical
    to the World Bank convention used by ``wb_wdi``.  ``date`` field "Y"
    corresponds to the FY beginning Shrawan of BS year (Y + 57):
      - WEO date "2024" → FY July 2024 – July 2025 → BS FY 2081/82
      - reporting_period_ad_start ≈ 2024-07-15 UTC
      - reporting_period_ad_end   ≈ 2025-07-15 UTC
    The ±2-day tolerance at the TS validation layer accommodates the
    mid-month-15 approximation (see docs/CALENDAR_AND_PERIODS.md).

Indicator mapping (13 codes):
    Slug prefix ``weo-``; unit conversion applied at parse time.  IMF WEO
    reports USD/PPP levels in **billions**, so NGDPD and PPPGDP are scaled
    ×1000 to land in ``usd_million`` / ``intl_dollar_million`` (matching the
    ``wb_wdi`` USD-level unit so the two sources benchmark in one unit).

    .. list-table::
       :header-rows: 1

       * - WEO code
         - slug
         - unit
         - scale
       * - NGDPD
         - weo-gdp-current-usd
         - usd_million
         - ×1000
       * - NGDP_RPCH
         - weo-gdp-real-growth-pct
         - percent
         - ×1
       * - NGDPDPC
         - weo-gdp-per-capita-current-usd
         - usd
         - ×1
       * - PPPGDP
         - weo-gdp-ppp-intl-dollar
         - intl_dollar_million
         - ×1000
       * - PCPIPCH
         - weo-inflation-avg-pct
         - percent
         - ×1
       * - BCA_NGDPD
         - weo-current-account-pct-gdp
         - percent
         - ×1
       * - GGR_NGDP
         - weo-govt-revenue-pct-gdp
         - percent
         - ×1
       * - GGXCNL_NGDP
         - weo-fiscal-balance-pct-gdp
         - percent
         - ×1
       * - GGXWDG_NGDP
         - weo-govt-gross-debt-pct-gdp
         - percent
         - ×1
       * - NGSD_NGDP
         - weo-gross-national-savings-pct-gdp
         - percent
         - ×1
       * - NID_NGDP
         - weo-total-investment-pct-gdp
         - percent
         - ×1
       * - LUR
         - weo-unemployment-rate-pct
         - percent
         - ×1
       * - LP
         - weo-population
         - persons_million
         - ×1

Confidence: ``A`` — IMF WEO is authoritative IMF research data.  Projections
carry confidence A AND observation_type 'projection' — high-authority forecast,
not a realised fact (ADR-0025).

ADR-0003: no LLM / AI calls.  Deterministic file-in → dataclass-out.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, TypedDict

from _common.periods import fiscal_year_ad_label, fiscal_year_label
from _common.types import (
    ObservationType,
    ParserError,
    ParserErrorClass,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "imf-weo"

# Each entry: WEO indicator code → (slug, unit, scale_factor).
# scale_factor converts the raw WEO value to the stored canonical unit
# (USD/PPP levels are published in billions → ×1000 to reach *_million).
_INDICATOR_CONFIG: Final[dict[str, tuple[str, str, float]]] = {
    "NGDPD":       ("weo-gdp-current-usd",                  "usd_million",         1000.0),
    "NGDP_RPCH":   ("weo-gdp-real-growth-pct",              "percent",                1.0),
    "NGDPDPC":     ("weo-gdp-per-capita-current-usd",       "usd",                    1.0),
    "PPPGDP":      ("weo-gdp-ppp-intl-dollar",              "intl_dollar_million", 1000.0),
    "PCPIPCH":     ("weo-inflation-avg-pct",                "percent",                1.0),
    "BCA_NGDPD":   ("weo-current-account-pct-gdp",          "percent",                1.0),
    "GGR_NGDP":    ("weo-govt-revenue-pct-gdp",             "percent",                1.0),
    "GGXCNL_NGDP": ("weo-fiscal-balance-pct-gdp",           "percent",                1.0),
    "GGXWDG_NGDP": ("weo-govt-gross-debt-pct-gdp",          "percent",                1.0),
    "NGSD_NGDP":   ("weo-gross-national-savings-pct-gdp",   "percent",                1.0),
    "NID_NGDP":    ("weo-total-investment-pct-gdp",         "percent",                1.0),
    "LUR":         ("weo-unemployment-rate-pct",            "percent",                1.0),
    "LP":          ("weo-population",                       "persons_million",        1.0),
}

# WEO date year Y → Nepal FY starting Shrawan of BS year (Y + 57). Same
# convention as wb_wdi (the IMF dates Nepal series on the July fiscal year).
_BS_AD_OFFSET: Final[int] = 57


class _DataPoint(TypedDict):
    date: str
    value: float | None


def _wb_year_to_period(wb_year: int) -> tuple[str, str, datetime, datetime, str]:
    """Return (fy_bs, fy_ad, ad_start, ad_end, pub_date_bs) for a WEO AD year."""
    bs_start = wb_year + _BS_AD_OFFSET
    fy_bs = fiscal_year_label(bs_start)
    fy_ad = fiscal_year_ad_label(bs_start)
    ad_start = datetime(wb_year, 7, 15, tzinfo=UTC)
    ad_end = datetime(wb_year + 1, 7, 15, tzinfo=UTC)
    return fy_bs, fy_ad, ad_start, ad_end, fy_bs


def _fail(error_class: ParserErrorClass, detail: str) -> ParserResult:
    return ParserResult(
        status="failure",
        parser_version=PARSER_VERSION,
        errors=[ParserError(error_class=error_class, error_detail=detail)],
    )


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse an IMF WEO combined JSON fixture; see module docstring for contract.

    Arguments:
        source_document_path: filesystem path to the combined JSON blob.
        source_document_id: opaque FK from ``source_documents``; threaded
            through per the parser contract but unused internally.

    Returns:
        ``ParserResult`` with status, staging_rows (one per indicator×year),
        and errors for unrecognised codes or unparseable years.
    """
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

    fetched_at_str: str = raw.get("fetched_at", "")
    try:
        pub_date_ad = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pub_date_ad = datetime(2026, 1, 1, tzinfo=UTC)

    # First projected AD year. None/absent → treat every row as 'actual'.
    projection_from_year = raw.get("projection_from_year")
    if projection_from_year is not None and not isinstance(projection_from_year, int):
        return _fail("Other", "projection_from_year must be an integer or null")

    indicators_raw = raw.get("indicators")
    if not isinstance(indicators_raw, dict):
        return _fail("Other", 'missing or invalid "indicators" key in JSON')

    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for code, datapoints in indicators_raw.items():
        config = _INDICATOR_CONFIG.get(code)
        if config is None:
            errors.append(
                ParserError(
                    error_class="Other",
                    error_detail=f"unrecognised WEO code '{code}' — add to _INDICATOR_CONFIG or exclude",
                    source_excerpt=code,
                )
            )
            continue

        slug, unit, scale = config

        if not isinstance(datapoints, list):
            errors.append(
                ParserError(
                    error_class="Other",
                    error_detail=f"{code}: datapoints is not a list",
                    source_excerpt=code,
                )
            )
            continue

        for dp in datapoints:
            if not isinstance(dp, dict):
                errors.append(
                    ParserError(
                        error_class="Other",
                        error_detail=f"{code}: datapoint is not an object",
                        source_excerpt=code,
                    )
                )
                continue

            date_str = dp.get("date", "")
            raw_value = dp.get("value")

            # Null observations: IMF uses null for missing years — skip silently.
            if raw_value is None:
                continue

            try:
                wb_year = int(date_str)
            except (ValueError, TypeError):
                errors.append(
                    ParserError(
                        error_class="PeriodAmbiguous",
                        error_detail=f"{code}: unparseable date '{date_str}'",
                        source_excerpt=str(date_str),
                    )
                )
                continue

            try:
                value_raw = float(raw_value)
            except (ValueError, TypeError):
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=f"{code} / {date_str}: value {raw_value!r} is not numeric",
                        source_excerpt=str(raw_value),
                    )
                )
                continue

            if not (1960 <= wb_year <= 2100):
                errors.append(
                    ParserError(
                        error_class="PeriodAmbiguous",
                        error_detail=f"{code}: year {wb_year} outside plausible range 1960–2100",
                        source_excerpt=date_str,
                    )
                )
                continue

            value = value_raw * scale
            fy_bs, fy_ad, ad_start, ad_end, pub_bs = _wb_year_to_period(wb_year)

            observation_type: ObservationType = (
                "projection"
                if projection_from_year is not None and wb_year >= projection_from_year
                else "actual"
            )

            staging_rows.append(
                StagingRowDraft(
                    indicator_slug_raw=slug,
                    value=value,
                    unit=unit,
                    reporting_period_type="annual",
                    reporting_period_bs=fy_bs,
                    reporting_period_ad_start=ad_start,
                    reporting_period_ad_end=ad_end,
                    publication_date_ad=pub_date_ad,
                    publication_date_bs=pub_bs,
                    fiscal_year_bs=fy_bs,
                    fiscal_year_ad_label=fy_ad,
                    confidence_grade_proposed="A",
                    observation_type=observation_type,
                    parser_notes=f"WEO code {code}; raw={value_raw}; scale={scale}",
                )
            )

    if not staging_rows and not errors:
        return _fail("Other", "no data rows produced (all indicators empty or null)")

    if not staging_rows:
        return ParserResult(status="failure", parser_version=PARSER_VERSION, errors=errors)

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def _serialize_result(result: ParserResult) -> dict[str, Any]:
    """Serialize ``ParserResult`` to the JSON shape expected by ParserOutputSchema."""
    rows: list[dict[str, Any]] = []
    for row in result.staging_rows:
        d = asdict(row)
        for k in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            v = d.get(k)
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        rows.append(d)
    return {
        "status": result.status,
        "parser_version": result.parser_version,
        "staging_rows": rows,
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
