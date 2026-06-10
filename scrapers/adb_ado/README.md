# ADB ADO Nepal — Selected Economic Indicators Parser

**Source id:** `adb-ado-nepal`  
**Ingestion mode:** `manual_upload`  
**Parser version:** `0.1.0`

Extracts the Nepal Selected Economic Indicators summary table from ADB
Asian Development Outlook (ADO) PDF reports.

## What it produces

Five indicator kinds, each split into an `-actual` (historical outturn) and a
`-forecast` (estimate/projection) slug:

| Indicator | Unit |
|-----------|------|
| Real GDP growth | `percent` |
| CPI inflation, annual average | `percent` |
| Fiscal balance (% of GDP) | `percent_gdp` |
| Current account balance (% of GDP) | `percent_gdp` |
| Gross reserves (months of imports) | `months` |

Column markers: `e`/`est` = estimate → forecast; `f`/`fct` = forecast;
no marker = historical outturn → actual.

## How to ingest

1. Download the ADB ADO PDF from <https://www.adb.org/countries/nepal/economy>.
2. Archive it under `Financial Data/adb_ado/YYYY-MM-DD/`.
3. Run: `pnpm ingest:adb-ado --input "<path-to-pdf>"`

See [INGEST_RUNBOOK.md](../../docs/INGEST_RUNBOOK.md) for the full command.

## Testing

```sh
cd scrapers
pytest adb_ado/tests/ -v
```

Core extraction is tested with synthesized FY and calendar-year tables.
For integration tests, place the PDF at:
`adb_ado/tests/fixtures/adb_ado_nepal_sample.pdf`

## Known breakage modes

- ADB alternates between Nepal FY (`2022/23`) and calendar year (`2023`)
  notation across editions; both are handled by the column-year parser.
- The Nepal section page number drifts across editions; the parser scans
  all pages for the Nepal anchor, not a hard-coded page.
- Bare "Inflation" row (no qualifier) is classified as CPI annual average.

## Source profile

[docs/sources/adb-ado-nepal.md](../../docs/sources/adb-ado-nepal.md)
