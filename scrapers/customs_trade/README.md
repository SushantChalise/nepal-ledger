# customs_trade — Department of Customs Foreign Trade Statistics parser

Deterministic Python parser (ADR-0003) for the **Foreign Trade Statistics (FTS)**
workbooks published by the **Department of Customs** (customs.gov.np), compiled
from the ASYCUDA World customs-declaration system.

- **Source id:** `customs-monthly-trade`
- **Acquisition:** Foreign Trade Statistics portal. Homepage → "FTS" category per
  Nepali fiscal year (`/category/fts-2081-082/`, `/category/fts-2080-081/`, …)
  → a single statistics post (`/content/10/statistics-a--and-2081-82/`) whose
  body links the XLSX files on the CDN host `giwmscdnone.gov.np/media/files/`.
  Each FY page lists one **annual** workbook plus a **cumulative-to-date**
  workbook for every month (Shrawan, up-to-Bhadra, … up-to-Jestha).
- **Corpus:** `Financial Data/customs/` (gitignored data dir; binaries not
  committed). Downloaded for this build: `FTS_Annual_2081_82.xlsx`,
  `FTS_UptoJestha_2081_82.xlsx`, `FTS_Shrawan_2081_82.xlsx`.
- **Output:** ADR-0015 **dimensional facts** → `dne_facts`. Emits a
  `dimensional_rows` JSON array; no single-series `staging_rows`.
- **Ingest CLI:** `scripts/ingest-customs-trade.ts`
  (`pnpm ingest:customs-trade` — script line pending Mother, see below).

## Format assessment

Each workbook is a clean, fully machine-readable Office Open XML spreadsheet
(~1–3 MB) with a **fixed 10-sheet layout** (verified identical across the annual,
Shrawan, and up-to-Jestha editions). Every value sheet has its column header on
**row index 2** (0-based) and data from row 3. No merged-cell ragged geometry, no
Devanagari/Preeti encoding issues, no OCR — this is the cleanest source in the
repo. We parse the four single-dimension sheets:

| sheet                       | columns                                                        | emitted                                            |
|-----------------------------|----------------------------------------------------------------|----------------------------------------------------|
| `5_Imports_By_Commodity`    | HSCode, Description, Unit, Quantity, **Imports_Value**, Imports_Revenue | `customs-merchandise-imports` × `commodity` (HS)   |
| `7_Exports_By_Commodity`    | HSCode, Description, Unit, Quantity, **Exports_Value**         | `customs-merchandise-exports` × `commodity` (HS)   |
| `3_Trade_Balance_Country`   | SN, Partner Countries, **Imports_Value**, **Exports_Value**, Trade_Balance | imports & exports × `country`            |
| `9_Customswise_Trade`       | SN, Customs, **Imports_Value**, Import_Share, **Exports_Value**, Export_Share | imports & exports × `customs_office`   |

- `dimension_value` for a commodity is the **HS code** (6- or 8-digit, preserved
  verbatim); `dimension_label` is the commodity description. For a country /
  customs office, `dimension_value` is the kebab slug of the name and
  `dimension_label` is the raw name.
- `unit` = `npr_thousand` — verbatim from every value sheet's header
  "(figures are in Rs. Thousands)" / "(... in Rs. Thousand)" and the headline
  table's "Imports (Rs.in \`000)". **NOT million, NOT lakh** (ADR-0011 magnitude
  verified below).
- `confidence_grade` = `A` — transaction-level ASYCUDA customs declarations (the
  authoritative trade record); the source registry sets `confidenceDefault: 'A'`.
- The single trailing **"Total"** row of each sheet (blank HS-code/SN cell) is
  **excluded** as an aggregate (ADR-0015). A genuine source `0` is preserved as a
  fact; only blank/dash cells are dropped (never fabricated, never zero-filled).

### Period dating (self-describing — no approximation)

The index sheet's row-0 descriptor states the period AND the exact AD span, e.g.:

```
Based on Annual data (Shrawan-Asar) of FY 2081/82 (Mid July 2024 to Mid July 2025)
Based on First Month (Shrawan) of FY 2081/82 (Mid July 2024 to Mid August 2024)
Based on First Eleven Months (Shrawan-Jestha) of FY 2081/82 (Mid July 2024 to Mid June 2025)
```

- **Annual** → `reporting_period_type='annual'`, label = the BS FY ("2081/82").
- **First Month (Shrawan)** → exactly month 1 → `'monthly'`, label = "Shrawan 2081".
- **First N Months** → **cumulative** year-to-date → `'year_to_date'`, label = the
  END BS month ("Jestha 2082"). The cumulative span is recorded in the fact's
  `base_indicator_name` (e.g. "… [cumulative Shrawan–Jestha (11 months) of FY 2081/82]")
  so YTD semantics travel with the row and never get silently treated as a single
  month.

The **end BS month is read from the scope parenthetical** (the source's own BS
month names — "Asar" = Ashadh, etc.), **not** inferred from the AD edge: the AD
bounds are month *edges* (mid-month), so "to Mid June" is the close of Jestha;
inferring a BS month from it would mislabel the period. The AD span start/end are
taken verbatim (the 15th of each named AD month). An unparseable descriptor is a
typed `RegexMismatch` and the file is rejected — never a silently mis-dated fact.

### ADR-0011 magnitude verification

FY 2081/82 **annual** (sum across the country dimension = the headline total):

| measure  | thousands         | NPR        | per-month (÷12) |
|----------|-------------------|------------|-----------------|
| imports  | 1,804,122,731     | ≈ 1.80 tn  | ≈ 150 bn        |
| exports  |   277,030,202     | ≈ 277 bn   | ≈ 23 bn         |

FY 2081/82 **Shrawan** (single month): imports 128,377,121 thousand ≈ **NPR 128 bn**,
exports 12,226,147 thousand ≈ **NPR 12 bn** — squarely in the expected
NPR 100–150 bn imports / NPR 15–20 bn exports monthly band. Unit and magnitude
confirmed.

## Deliberately deferred (kept honest; not fabricated)

- **Commodity × partner cross-tabs** (sheet 4 `Imports_By_Commodity_Partner` ~34k
  rows, sheet 6 `Exports_By_Commodity_Partner`): a fact there is sliced by **two**
  dimensions (HS code AND partner country) and does not fit the ADR-0015
  one-dimension-per-fact contract without a composite-dimension scheme. Deferred.
- **`Imports_Revenue`** (customs duty collected) and the derived **`Trade_Balance`**
  / **share** columns — separate measures, not part of the trade-volume brief;
  promotable later with their own base slugs.
- **sheet 2** (`Trade_Balance_Chapter`, redundant with the commodity sheets),
  **sheet 8** (`ID_Value_Comparison`), **sheet 1** (`Trade_Direction` headline
  totals — single series, not dimensional).

## Known breakage modes

- The parser keys off the fixed sheet **names** (`5_Imports_By_Commodity`, …) and
  the row-2 header. A missing expected sheet emits a typed `PageLayoutChanged`
  (not a crash) and degrades `status` to `partial`. A renamed/reordered layout in
  a future FY edition would surface as missing sheets — re-verify and bump
  `PARSER_VERSION`.
- The period descriptor regex expects the exact "Based on … of FY YYYY/YY (Mid …
  to Mid …)" phrasing. A wording change → `RegexMismatch` → file rejected loud.
- The CDN filenames are opaque hashes (`FTS_Annual_2081_82_twybrul.xlsx`); the
  stable handle is the FY content page, not the file URL.

## Tests

`tests/test_parser.py` exercises the deterministic core (per-sheet `extract_*`
functions + `parse_period_descriptor`) against **synthesized** tiny tables that
reproduce the real geometry (row-2 header, HS-code rows, country/customs rows, a
trailing blank-coded "Total" row, a preserved zero, a dropped dash, the three
real scope shapes). The real multi-MB workbooks are **not committed** (ADR-0003 /
source profile); three optional integration tests run against them when present
and are skipped otherwise.

```
cd scrapers
PYTHONPATH=<worktree>/scrapers <venv>/python -m pytest customs_trade/tests -q
```

Real-file dry-run (FY 2081/82 annual): **6,886 facts** (imports 5,264 commodity +
164 country + 29 customs; exports 1,236 + 164 + 29), `status=success`, 0 errors.

## Pending Mother (RETURN items — not edited here per scope fence)

- `scrapers/pyproject.toml`: add `"customs_trade*"` to
  `[tool.setuptools.packages.find].include` and `"customs_trade/tests"` to
  `[tool.pytest.ini_options].testpaths`.
- `package.json` scripts:
  `"ingest:customs-trade": "node --env-file=.env.local --conditions=react-server --import tsx scripts/ingest-customs-trade.ts"`.
- `scripts/seed-source-registry.ts`: flip `customs-monthly-trade`
  `status: 'paused'` → `'active'` once the first live ingest lands.
