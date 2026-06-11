# scrapers/wb_wdi

World Bank World Development Indicators (WDI) — Nepal macro benchmark fetcher and parser.

**source_id:** `wb-wdi`  
**Parser version:** 0.1.0  
**License:** CC-BY 4.0  
**Docs:** [docs/sources/wb-wdi.md](../../docs/sources/wb-wdi.md)

## What this ingests

Six historical macro indicators for Nepal from the World Bank API:

| WDI Code | Slug | Unit |
|---|---|---|
| `NY.GDP.MKTP.KD.ZG` | `wdi-gdp-real-growth` | `percent` |
| `FP.CPI.TOTL.ZG` | `wdi-cpi-inflation-avg` | `percent` |
| `GC.BAL.CASH.GD.ZS` | `wdi-fiscal-balance-pct-gdp` | `percent_gdp` |
| `BN.CAB.XOKA.GD.ZS` | `wdi-current-account-pct-gdp` | `percent_gdp` |
| `GC.DOD.TOTL.GD.ZS` | `wdi-public-debt-pct-gdp` | `percent_gdp` |
| `FI.RES.TOTL.MO` | `wdi-gross-reserves-months` | `months` |

All are calendar-year values mapped to the approximate Nepal fiscal year
(`bs_start = cal_year + 57`). No forecast rows — WDI is historical outturns only.

## Two-step ingest

```powershell
# Step 1: fetch snapshot from WB API (requires internet)
python -m scrapers.wb_wdi.fetch --output wb_wdi_snapshot_YYYYMMDD.json

# Step 2: ingest snapshot into staging (no internet required)
pnpm ingest:wdi --dry-run --input wb_wdi_snapshot_YYYYMMDD.json
pnpm ingest:wdi --input wb_wdi_snapshot_YYYYMMDD.json
```

## Modules

- **`fetch.py`** — downloads data from WB API, writes JSON snapshot
- **`parser.py`** — reads snapshot, emits `ParserResult` (no network, no DB)
- **`tests/test_parser.py`** — unit tests against synthesized snapshot

## Tests

```powershell
cd scrapers
pytest wb_wdi/tests/ -v
```

Integration test (requires real snapshot):
```powershell
python -m scrapers.wb_wdi.fetch --output wb_wdi/tests/fixtures/wb_wdi_sample.json
pytest wb_wdi/tests/test_parser.py -v -k integration
```

## Calendar year → Nepal FY mapping

WDI reports in calendar years. The approximation used:

```
cal_year 2023 → bs_start = 2023 + 57 = 2080 → FY 2080/81 (AD 2023/24)
period_start = mid_month_ad("Shrawan", 2080) = 2023-07-15
period_end   = mid_month_ad("Ashadh", 2080)  = 2024-06-15
```

This matches the convention used in the IMF Article IV and ADB ADO parsers.
