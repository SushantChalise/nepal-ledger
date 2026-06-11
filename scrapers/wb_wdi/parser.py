"""World Bank WDI (Nepal) parser — deterministic Python.

Source id: ``wb-wdi``

Input format:
    A JSON file with the shape produced by the ingest CLI (``scripts/ingest-wdi.ts``):

    .. code-block:: json

        {
          "fetched_at": "2026-06-11T00:00:00Z",
          "country_code": "NPL",
          "indicators": {
            "NY.GDP.MKTP.CD": [
              {"date": "2023", "value": 40835000000.0},
              {"date": "2022", "value": 36291000000.0}
            ],
            "FP.CPI.TOTL.ZG": [
              {"date": "2023", "value": 7.74},
              {"date": "2022", "value": null}
            ]
          }
        }

    ``date`` is the AD year-string that the World Bank assigns to Nepal's fiscal
    year (see "Period dating" below).  ``value`` may be ``null`` for years where
    WB has no observation; those rows are silently skipped.

Period dating (Nepal fiscal year):
    The World Bank reports Nepal national-accounts data on a fiscal-year basis
    starting in July.  ``date`` field "Y" corresponds to the FY beginning in
    Shrawan of BS year (Y + 57), i.e.:
      - WB date "2024" → FY July 2024 – June 2025 → BS FY 2081/82
      - reporting_period_bs = "2081/82"
      - reporting_period_ad_start ≈ 2024-07-15 UTC
      - reporting_period_ad_end   ≈ 2025-07-15 UTC

    The ±2-day tolerance at the TS validation layer accommodates the
    mid-month-15 approximation (see docs/CALENDAR_AND_PERIODS.md).

Indicator mapping (15 codes):
    Slug prefix ``wdi-``; unit conversion applied at parse time so the DB
    stores values in the declared canonical unit.

    .. list-table::
       :header-rows: 1

       * - WB code
         - slug
         - unit
         - scale
       * - NY.GDP.MKTP.CD
         - wdi-gdp-current-usd
         - usd_million
         - ÷1 000 000
       * - NY.GDP.MKTP.KD
         - wdi-gdp-constant-2015-usd
         - usd_million
         - ÷1 000 000
       * - NY.GDP.MKTP.KD.ZG
         - wdi-gdp-growth-annual-pct
         - percent
         - ×1
       * - NY.GDP.PCAP.CD
         - wdi-gdp-per-capita-current-usd
         - usd
         - ×1
       * - NY.GDP.PCAP.KD.ZG
         - wdi-gdp-per-capita-growth-pct
         - percent
         - ×1
       * - FP.CPI.TOTL.ZG
         - wdi-cpi-inflation-annual-pct
         - percent
         - ×1
       * - BX.TRF.PWKR.CD.DT
         - wdi-remittances-received-usd
         - usd_million
         - ÷1 000 000
       * - BX.TRF.PWKR.DT.GD.ZS
         - wdi-remittances-pct-gdp
         - percent
         - ×1
       * - NY.GNP.MKTP.CD
         - wdi-gni-current-usd
         - usd_million
         - ÷1 000 000
       * - NY.GNP.PCAP.CD
         - wdi-gni-per-capita-current-usd
         - usd
         - ×1
       * - SI.POV.NAHC
         - wdi-poverty-headcount-national-pct
         - percent
         - ×1
       * - SI.POV.GINI
         - wdi-gini-index
         - index_points
         - ×1
       * - NE.GDI.TOTL.ZS
         - wdi-gross-capital-formation-pct-gdp
         - percent
         - ×1
       * - GC.DOD.TOTL.GD.ZS
         - wdi-central-govt-debt-pct-gdp
         - percent
         - ×1
       * - BN.CAB.XOKA.GD.ZS
         - wdi-current-account-balance-pct-gdp
         - percent
         - ×1

Confidence: ``A`` — WB WDI aggregates from national statistical offices with
its own quality controls; for Nepal it largely mirrors CBS/NRB published data.

ADR-0003: no LLM / AI calls.  Deterministic file-in → dataclass-out.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, TypedDict

from _common.periods import fiscal_year_ad_label, fiscal_year_label
from _common.types import ParserError, ParserResult, ParserStatus, StagingRowDraft

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "wb-wdi"

# Each entry: WB indicator code → (slug, unit, scale_factor)
# scale_factor converts from raw WB API value to the stored canonical unit.
_INDICATOR_CONFIG: Final[dict[str, tuple[str, str, float]]] = {
    "NY.GDP.MKTP.CD":    ("wdi-gdp-current-usd",                  "usd_million", 1e-6),
    "NY.GDP.MKTP.KD":    ("wdi-gdp-constant-2015-usd",            "usd_million", 1e-6),
    "NY.GDP.MKTP.KD.ZG": ("wdi-gdp-growth-annual-pct",            "percent",     1.0),
    "NY.GDP.PCAP.CD":    ("wdi-gdp-per-capita-current-usd",        "usd",         1.0),
    "NY.GDP.PCAP.KD.ZG": ("wdi-gdp-per-capita-growth-pct",        "percent",     1.0),
    "FP.CPI.TOTL.ZG":    ("wdi-cpi-inflation-annual-pct",          "percent",     1.0),
    "BX.TRF.PWKR.CD.DT": ("wdi-remittances-received-usd",         "usd_million", 1e-6),
    "BX.TRF.PWKR.DT.GD.ZS": ("wdi-remittances-pct-gdp",          "percent",     1.0),
    "NY.GNP.MKTP.CD":    ("wdi-gni-current-usd",                   "usd_million", 1e-6),
    "NY.GNP.PCAP.CD":    ("wdi-gni-per-capita-current-usd",        "usd",         1.0),
    "SI.POV.NAHC":       ("wdi-poverty-headcount-national-pct",    "percent",     1.0),
    "SI.POV.GINI":       ("wdi-gini-index",                        "index_points",1.0),
    "NE.GDI.TOTL.ZS":    ("wdi-gross-capital-formation-pct-gdp",  "percent",     1.0),
    "GC.DOD.TOTL.GD.ZS": ("wdi-central-govt-debt-pct-gdp",        "percent",     1.0),
    "BN.CAB.XOKA.GD.ZS": ("wdi-current-account-balance-pct-gdp", "percent",     1.0),
}

# WB date year Y → Nepal FY starting Shrawan of BS year (Y + 57)
_BS_AD_OFFSET: Final[int] = 57


class _DataPoint(TypedDict):
    date: str
    value: float | None


class _FixtureDoc(TypedDict):
    fetched_at: str
    country_code: str
    indicators: dict[str, list[_DataPoint]]


def _wb_year_to_period(wb_year: int) -> tuple[str, str, datetime, datetime, str]:
    """Return (fy_bs, fy_ad, ad_start, ad_end, pub_date_bs) for a WB AD year.

    WB year Y for Nepal = FY July Y – July (Y+1) ≈ BS FY (Y+57)/(Y+58 mod 100).
    Mid-month approximation: ad_start = July 15, Y; ad_end = July 15, Y+1.
    """
    bs_start = wb_year + _BS_AD_OFFSET
    fy_bs = fiscal_year_label(bs_start)
    fy_ad = fiscal_year_ad_label(bs_start)
    ad_start = datetime(wb_year, 7, 15, tzinfo=UTC)
    ad_end = datetime(wb_year + 1, 7, 15, tzinfo=UTC)
    return fy_bs, fy_ad, ad_start, ad_end, fy_bs


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse a WDI combined JSON fixture; see module docstring for contract.

    Arguments:
        source_document_path: filesystem path to the combined JSON blob.
        source_document_id: opaque FK from ``source_documents``; not used
            internally but threaded through per the parser contract.

    Returns:
        ``ParserResult`` with status, staging_rows (one per indicator×year),
        and errors for unrecognised codes or unparseable years.
    """
    _ = source_document_id  # contract parameter — unused by this parser

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
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(error_class="EncodingError", error_detail=f"json read failed: {exc}")
            ],
        )

    if not isinstance(raw, dict):
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(error_class="Other", error_detail="root is not a JSON object")
            ],
        )

    fetched_at_str: str = raw.get("fetched_at", "")
    try:
        pub_date_ad = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pub_date_ad = datetime(2026, 1, 1, tzinfo=UTC)

    indicators_raw = raw.get("indicators")
    if not isinstance(indicators_raw, dict):
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail='missing or invalid "indicators" key in JSON',
                )
            ],
        )

    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for code, datapoints in indicators_raw.items():
        config = _INDICATOR_CONFIG.get(code)
        if config is None:
            errors.append(
                ParserError(
                    error_class="Other",
                    error_detail=f"unrecognised indicator code '{code}' — add to _INDICATOR_CONFIG or exclude from fixture",
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

            # Null observations: WB uses null for missing years — skip silently.
            if raw_value is None:
                continue

            try:
                wb_year = int(date_str)
            except (ValueError, TypeError):
                errors.append(
                    ParserError(
                        error_class="PeriodAmbiguous",
                        error_detail=f"{code}: unparseable date '{date_str}'",
                        source_excerpt=date_str,
                    )
                )
                continue

            try:
                value_raw = float(raw_value)
            except (ValueError, TypeError):
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=f"{code} / {date_str}: value '{raw_value!r}' is not numeric",
                        source_excerpt=str(raw_value),
                    )
                )
                continue

            if not (wb_year >= 1960 and wb_year <= 2100):
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
                    parser_notes=f"WB code {code}; raw={value_raw}; scale={scale}",
                )
            )

    if not staging_rows and not errors:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail="no data rows produced (all indicators empty or null)",
                )
            ],
        )

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors,
        )

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

    import json as _json

    result = parse(sys.argv[1], sys.argv[2])
    _json.dump(_serialize_result(result), sys.stdout)


if __name__ == "__main__":
    _main()
