# IMF Article IV — Nepal Selected Economic Indicators Parser

**Source id:** `imf-article-iv`  
**Ingestion mode:** `manual_upload`  
**Parser version:** `0.1.0`

Extracts the "Selected Economic Indicators" appendix table from IMF Article IV
consultation report PDFs for Nepal.

## What it produces

Six indicator kinds, each split into an `-actual` (historical outturn) and a
`-forecast` (estimate/projection) slug:

| Indicator | Unit |
|-----------|------|
| Real GDP growth | `percent` |
| CPI inflation, annual average | `percent` |
| Overall fiscal balance | `percent_gdp` |
| Current account balance | `percent_gdp` |
| Public sector / central govt debt | `percent_gdp` |
| Gross official reserves (months of imports) | `months` |

The `-actual` vs `-forecast` split is determined by column markers in the
source table (`E` / `Est` = estimate → forecast; `P` / `Proj` = projection →
forecast; no marker = historical outturn → actual).

## How to ingest

1. Download the Nepal Article IV PDF from <https://www.imf.org/en/Countries/NPL>.
2. Archive it under `Financial Data/imf_article_iv/YYYY-MM-DD/` with the
   original filename.
3. Run: `pnpm ingest:imf-article-iv --input "<path-to-pdf>"`

See [INGEST_RUNBOOK.md](../../docs/INGEST_RUNBOOK.md) for the full command.

## Testing

```sh
cd scrapers
pytest imf_article_iv/tests/ -v
```

Core extraction logic is tested with a synthesized table (no PDF required).
To run integration tests against a real PDF, place it at:
`imf_article_iv/tests/fixtures/imf_article_iv_sample.pdf`

## Known breakage modes

- Table layout shifts between Article IV editions (column heading format,
  row label wording). Parser emits `PageLayoutChanged` errors and continues
  with partial extraction.
- Some editions prefix year columns with `FY` (e.g., `FY2023/24P`); handled.
- Bracketed negatives `(6.2)` used for fiscal/current account values;
  converted to `-6.2` automatically.

## Source profile

[docs/sources/imf-article-iv.md](../../docs/sources/imf-article-iv.md)
