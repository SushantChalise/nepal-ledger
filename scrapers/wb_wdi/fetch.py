"""
World Bank WDI API fetcher for Nepal macro benchmarks.

Downloads six indicator time series from the World Bank Data API and
writes a JSON snapshot suitable for ingestion via scrapers/wb_wdi/parser.py.
No LLM calls — purely deterministic HTTP fetch.

Indicator codes fetched for Nepal (NPL):
  NY.GDP.MKTP.KD.ZG — Real GDP growth (annual %)
  FP.CPI.TOTL.ZG    — CPI inflation, annual average
  GC.BAL.CASH.GD.ZS — Net lending/borrowing (fiscal balance, % of GDP)
  BN.CAB.XOKA.GD.ZS — Current account balance (% of GDP)
  GC.DOD.TOTL.GD.ZS — Central government debt (% of GDP)
  FI.RES.TOTL.MO    — Total reserves in months of imports

Usage:
    python -m scrapers.wb_wdi.fetch --output wb_wdi_snapshot_YYYYMMDD.json
    python -m scrapers.wb_wdi.fetch --output out.json --year-from 2000 --year-to 2024

The output file is then ingested via:
    pnpm ingest:wdi --input wb_wdi_snapshot_YYYYMMDD.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date

COUNTRY = "NPL"
BASE_URL = "https://api.worldbank.org/v2/country"
_SCHEMA_VERSION = "1"

# WDI indicator codes and their human-readable aliases.
INDICATORS: dict[str, str] = {
    "NY.GDP.MKTP.KD.ZG": "gdp_real_growth",
    "FP.CPI.TOTL.ZG": "cpi_inflation_avg",
    "GC.BAL.CASH.GD.ZS": "fiscal_balance_pct_gdp",
    "BN.CAB.XOKA.GD.ZS": "current_account_pct_gdp",
    "GC.DOD.TOTL.GD.ZS": "public_debt_pct_gdp",
    "FI.RES.TOTL.MO": "gross_reserves_months",
}

# Fetch up to 70 most-recent values per indicator (WDI history starts 1960).
_MRV = 70


def _fetch_series(code: str) -> list[dict[str, object]]:
    """Fetch one WDI indicator time series for Nepal. Returns [{year, value}]."""
    url = (
        f"{BASE_URL}/{COUNTRY}/indicator/{code}"
        f"?format=json&mrv={_MRV}&per_page={_MRV}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload: list = json.loads(resp.read().decode("utf-8"))

    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"unexpected WDI response shape for {code}: {payload!r:.200}")

    data_items = payload[1]
    if data_items is None:
        return []

    series: list[dict[str, object]] = []
    for item in data_items:
        raw_year = item.get("date")
        raw_value = item.get("value")
        if raw_year is None or raw_value is None:
            continue
        try:
            year = int(raw_year)
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        series.append({"year": year, "value": value})

    series.sort(key=lambda x: x["year"])
    return series


def build_snapshot(
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    """Fetch all six indicators and return a snapshot dict."""
    today = date.today().isoformat()
    indicators_data: dict[str, dict] = {}

    for code, alias in INDICATORS.items():
        sys.stderr.write(f"[wb_wdi.fetch] fetching {code} ({alias}) ...\n")
        series = _fetch_series(code)
        if year_from is not None:
            series = [r for r in series if int(r["year"]) >= year_from]
        if year_to is not None:
            series = [r for r in series if int(r["year"]) <= year_to]
        indicators_data[code] = {
            "alias": alias,
            "series": series,
            "count": len(series),
        }
        sys.stderr.write(f"  → {len(series)} data points\n")

    return {
        "schema_version": _SCHEMA_VERSION,
        "fetched_at": today,
        "country_code": COUNTRY,
        "indicators": indicators_data,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fetch WDI Nepal macro benchmark data and save as JSON snapshot."
    )
    ap.add_argument("--output", required=True, help="Path to write JSON snapshot file")
    ap.add_argument("--year-from", type=int, default=None, metavar="YYYY", help="Filter to years >= this")
    ap.add_argument("--year-to", type=int, default=None, metavar="YYYY", help="Filter to years <= this")
    args = ap.parse_args()

    snapshot = build_snapshot(year_from=args.year_from, year_to=args.year_to)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    total = sum(ind["count"] for ind in snapshot["indicators"].values())
    sys.stderr.write(
        f"[wb_wdi.fetch] wrote {total} data points across "
        f"{len(snapshot['indicators'])} indicators to {args.output}\n"
    )


if __name__ == "__main__":
    main()
