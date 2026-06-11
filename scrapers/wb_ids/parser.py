"""World Bank International Debt Statistics (Nepal) parser — deterministic Python.

Source id: ``wb-ids``

Input format:
    A JSON file produced by the ingest CLI (``scripts/ingest-ids.ts``). The CLI
    runs the IDS creditor-breakdown queries
    (``api.worldbank.org/v2/sources/6/country/NPL/series/<CODE>/counterpart-area/all/time/all``),
    extracts the relevant counterparts (World aggregate + named creditors), and
    emits one pre-resolved ``ids-*`` slug series per indicator:

    .. code-block:: json

        {
          "fetched_at": "2026-06-11T00:00:00Z",
          "country_code": "NPL",
          "series": {
            "ids-external-debt-total-usd": [
              {"date": "2023", "value": 9982808324.0}
            ],
            "ids-debt-bilateral-japan-usd": [
              {"date": "2023", "value": 411084490.0}
            ]
          }
        }

    ``date`` is the IDS calendar year; ``value`` may be ``null`` (skipped). The
    slug is already resolved by the CLI (it knows which counterpart maps to
    which creditor slug), so the parser only applies the unit/scale and the
    period contract.

Period dating:
    IDS years are calendar year-end. For consistency with the other WB-family
    Nepal series, the parser maps year "Y" onto Nepal's FY via the shared
    ``nepal_wb_year_period`` convention (Y → BS Y+57). The ~6-month
    calendar-vs-fiscal nuance is within the system's annual tolerance.

Indicators (12):
    Slug prefix ``ids-``. Debt stocks / service / short-term are current US$
    → ``usd_million`` (÷1e6, matching wb_wdi). Debt-to-GNI is ``percent``.
    All ``observation_type='actual'``, confidence A (WB compiled creditor data).

ADR-0003: no LLM / AI calls. Deterministic file-in → dataclass-out.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from _common.periods import nepal_wb_year_period
from _common.types import (
    ParserError,
    ParserErrorClass,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "wb-ids"

# slug → (unit, scale_factor). USD levels ÷1e6 → usd_million; ratios ×1.
_INDICATOR_CONFIG: Final[dict[str, tuple[str, float]]] = {
    # Aggregates (World counterpart)
    "ids-external-debt-total-usd":            ("usd_million", 1e-6),
    "ids-external-debt-pct-gni":              ("percent",     1.0),
    "ids-debt-service-total-usd":             ("usd_million", 1e-6),
    "ids-short-term-debt-usd":                ("usd_million", 1e-6),
    "ids-ppg-bilateral-total-usd":            ("usd_million", 1e-6),
    "ids-ppg-multilateral-total-usd":         ("usd_million", 1e-6),
    # Bilateral creditors
    "ids-debt-bilateral-japan-usd":           ("usd_million", 1e-6),
    "ids-debt-bilateral-india-usd":           ("usd_million", 1e-6),
    "ids-debt-bilateral-china-usd":           ("usd_million", 1e-6),
    "ids-debt-bilateral-korea-usd":           ("usd_million", 1e-6),
    # Multilateral creditors
    "ids-debt-multilateral-worldbank-ida-usd": ("usd_million", 1e-6),
    "ids-debt-multilateral-adb-usd":          ("usd_million", 1e-6),
}

_MIN_YEAR: Final[int] = 1960
_MAX_YEAR: Final[int] = 2100


def _fail(error_class: ParserErrorClass, detail: str) -> ParserResult:
    return ParserResult(
        status="failure",
        parser_version=PARSER_VERSION,
        errors=[ParserError(error_class=error_class, error_detail=detail)],
    )


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse an IDS combined JSON fixture; see module docstring for the contract."""
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

    series = raw.get("series")
    if not isinstance(series, dict):
        return _fail("Other", 'missing or invalid "series" object')

    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for slug, points in series.items():
        config = _INDICATOR_CONFIG.get(slug)
        if config is None:
            errors.append(
                ParserError(
                    error_class="Other",
                    error_detail=f"unrecognised IDS slug '{slug}' — add to _INDICATOR_CONFIG or exclude",
                    source_excerpt=slug,
                )
            )
            continue
        unit, scale = config

        if not isinstance(points, list):
            errors.append(
                ParserError(error_class="Other", error_detail=f"{slug}: points is not a list")
            )
            continue

        for dp in points:
            if not isinstance(dp, dict):
                continue
            raw_value = dp.get("value")
            if raw_value is None:
                continue
            try:
                year = int(dp.get("date", ""))
            except (ValueError, TypeError):
                errors.append(
                    ParserError(
                        error_class="PeriodAmbiguous",
                        error_detail=f"{slug}: unparseable date {dp.get('date')!r}",
                    )
                )
                continue
            if not (_MIN_YEAR <= year <= _MAX_YEAR):
                errors.append(
                    ParserError(
                        error_class="PeriodAmbiguous",
                        error_detail=f"{slug}: year {year} outside 1960–2100",
                    )
                )
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

            fy_bs, fy_ad, ad_start, ad_end = nepal_wb_year_period(year)
            rows.append(
                StagingRowDraft(
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
                    confidence_grade_proposed="A",
                    observation_type="actual",
                    parser_notes=f"IDS {slug}; raw={raw_value}; scale={scale}",
                )
            )

    if not rows:
        return _fail("Other", "no data rows produced")

    rows.sort(key=lambda r: (r.indicator_slug_raw, r.fiscal_year_bs))
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
