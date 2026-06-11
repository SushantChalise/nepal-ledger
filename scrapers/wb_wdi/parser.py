"""
Parser for World Bank WDI Nepal snapshot JSON files.

Reads a JSON snapshot produced by scrapers/wb_wdi/fetch.py and emits
staging_indicator_values rows. Each WDI calendar year value is mapped to
the approximate Nepal fiscal year (FY N/N+1) using: bs_start = cal_year + 57.

WDI provides historical outturns only — no forecast rows are emitted.

Parser contract:
  - Takes positional argv: (source_document_path, source_document_id)
  - Writes ParserResult.to_json_dict() as JSON to stdout
  - Never raises; returns "failure" status on unrecoverable errors
  - No network calls; no DB writes; idempotent

Usage (via ingest CLI — preferred):
    pnpm ingest:wdi --input wb_wdi_snapshot_YYYYMMDD.json

Usage (direct, for debugging):
    cd scrapers
    python -m wb_wdi.parser path/to/snapshot.json manual-doc-id
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _common.periods import fiscal_year_label, fiscal_year_ad_label, mid_month_ad
from _common.types import (
    ParserError,
    ParserResult,
    StagingRowDraft,
)

PARSER_VERSION = "0.1.0"
SOURCE_ID = "wb-wdi"
_SCHEMA_VERSION = "1"

# WDI indicator code → (output slug, unit string)
_CODE_TO_SLUG: dict[str, tuple[str, str]] = {
    "NY.GDP.MKTP.KD.ZG": ("wdi-gdp-real-growth", "percent"),
    "FP.CPI.TOTL.ZG": ("wdi-cpi-inflation-avg", "percent"),
    "GC.BAL.CASH.GD.ZS": ("wdi-fiscal-balance-pct-gdp", "percent_gdp"),
    "BN.CAB.XOKA.GD.ZS": ("wdi-current-account-pct-gdp", "percent_gdp"),
    "GC.DOD.TOTL.GD.ZS": ("wdi-public-debt-pct-gdp", "percent_gdp"),
    "FI.RES.TOTL.MO": ("wdi-gross-reserves-months", "months"),
}


def _parse_snapshot(
    snapshot: dict,
    fetched_at: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    indicators: dict = snapshot.get("indicators", {})

    # Publication date from the snapshot's fetched_at field.
    try:
        d = datetime.strptime(fetched_at, "%Y-%m-%d")
        pub_date_ad = d.replace(tzinfo=timezone.utc)
    except ValueError:
        pub_date_ad = datetime.now(tz=timezone.utc).replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

    # Approximate BS publication date (year only).
    pub_bs_year = pub_date_ad.year + 56  # Jan of AD year → previous BS year
    pub_date_bs = f"{pub_bs_year}-01-01"

    for code, ind_data in indicators.items():
        if code not in _CODE_TO_SLUG:
            errors.append(
                ParserError(
                    error_class="Other",
                    error_detail=(
                        f"WDI code {code!r} has no slug mapping — update _CODE_TO_SLUG"
                    ),
                )
            )
            continue

        slug, unit = _CODE_TO_SLUG[code]
        series: list[dict] = ind_data.get("series", [])

        for point in series:
            raw_year = point.get("year")
            raw_value = point.get("value")
            if raw_year is None or raw_value is None:
                continue
            try:
                cal_year = int(raw_year)
                value = float(raw_value)
            except (TypeError, ValueError):
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=(
                            f"{code} year={raw_year!r} value={raw_value!r}: not numeric"
                        ),
                    )
                )
                continue

            # Calendar year N → Nepal FY N/N+1 (bs_start = N + 57).
            # e.g. CY 2023 → FY 2080/81 (Shrawan 2080 .. Ashadh 2080).
            bs_start = cal_year + 57
            period_start = mid_month_ad("Shrawan", bs_start)
            period_end = mid_month_ad("Ashadh", bs_start)

            rows.append(
                StagingRowDraft(
                    indicator_slug_raw=slug,
                    value=value,
                    unit=unit,
                    reporting_period_type="annual",
                    reporting_period_bs=f"FY {fiscal_year_label(bs_start)}",
                    reporting_period_ad_start=period_start,
                    reporting_period_ad_end=period_end,
                    publication_date_ad=pub_date_ad,
                    publication_date_bs=pub_date_bs,
                    fiscal_year_bs=fiscal_year_label(bs_start),
                    fiscal_year_ad_label=fiscal_year_ad_label(bs_start),
                    confidence_grade_proposed="A",
                    parser_notes=(
                        f"WDI calendar year {cal_year} mapped to Nepal FY "
                        f"{fiscal_year_label(bs_start)} (approximate); "
                        f"code={code}; snapshot_fetched={fetched_at}"
                    ),
                )
            )

    # Warn on any expected code absent from the snapshot.
    for code in _CODE_TO_SLUG:
        if code not in indicators:
            errors.append(
                ParserError(
                    error_class="ColumnMissing",
                    error_detail=(
                        f"WDI code {code!r} absent from snapshot — "
                        "re-fetch with: python -m scrapers.wb_wdi.fetch --output <path>"
                    ),
                )
            )

    return rows, errors


def parse(source_document_path: str, _source_document_id: str) -> ParserResult:
    p = Path(source_document_path)
    if not p.exists():
        return ParserResult(
            parser_version=PARSER_VERSION,
            status="failure",
            staging_rows=[],
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"snapshot not found: {source_document_path}",
                )
            ],
        )

    try:
        with p.open("r", encoding="utf-8") as f:
            snapshot: dict = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return ParserResult(
            parser_version=PARSER_VERSION,
            status="failure",
            staging_rows=[],
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"snapshot parse error: {exc}",
                )
            ],
        )

    schema_ver = snapshot.get("schema_version")
    if schema_ver != _SCHEMA_VERSION:
        return ParserResult(
            parser_version=PARSER_VERSION,
            status="failure",
            staging_rows=[],
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=(
                        f"snapshot schema_version={schema_ver!r}, "
                        f"expected {_SCHEMA_VERSION!r}"
                    ),
                )
            ],
        )

    fetched_at: str = snapshot.get("fetched_at", "")
    rows, errors = _parse_snapshot(snapshot, fetched_at)

    status: str
    if any(e.error_class == "Other" for e in errors):
        # "Other" errors from snapshot-level failures are blocking.
        status = "failure"
    elif errors:
        status = "partial"
    else:
        status = "success"

    return ParserResult(
        parser_version=PARSER_VERSION,
        status=status,  # type: ignore[arg-type]
        staging_rows=rows,
        errors=errors,
    )


def _main() -> None:
    if len(sys.argv) < 3:
        sys.stderr.write(
            "usage: python -m wb_wdi.parser <snapshot.json> <source_document_id>\n"
        )
        sys.exit(1)

    result = parse(sys.argv[1], sys.argv[2])
    sys.stdout.write(json.dumps(result.to_json_dict(), indent=2))
    sys.stdout.write("\n")

    sys.stderr.write(
        f"[wb_wdi.parser] status={result.status} "
        f"rows={len(result.staging_rows)} "
        f"errors={len(result.errors)}\n"
    )


if __name__ == "__main__":
    _main()
