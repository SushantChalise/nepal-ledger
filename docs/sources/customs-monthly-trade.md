# Source: Department of Customs — Monthly trade statistics (imports + exports)

**source_id:** `customs-monthly-trade`  
**Status:** paused (parser landed; flip to `active` on first live ingest — pending Mother)  
**Tier:** Tier 1  
**Registered at:** 2026-05-14  
**Last verified:** 2026-06-08 (parser v0.2.0 — added commodity×partner cross-tabs, sheets 4 & 6)

> Parser landed (v0.2.0): `scrapers/customs_trade/` emits ADR-0015 dimensional
> facts (dimension = commodity HS-code / country / customs office, plus the
> commodity×partner cross-tabs via a composite `<hs>__<country>` dimension —
> ADR-0018) from the Foreign Trade Statistics (FTS) XLSX workbooks. Ingest via
> `scripts/ingest-customs-trade.ts` → `dne_facts`.

## Publication

- URL: https://www.customs.gov.np/
- Frequency: monthly (cumulative-to-date) + an annual workbook per fiscal year
- Format: xlsx
- Reporting period type: monthly (`year_to_date` for the cumulative files; `annual` for the year file)
- Requires table extraction: no (clean, fully machine-readable XLSX)

### Acquisition path

Homepage → "FTS" category per Nepali fiscal year
(`/category/fts-2081-082/`, `/category/fts-2080-081/`, …) → a single statistics
post (`/content/10/statistics-a--and-2081-82/`) whose body links the XLSX files on
the CDN host `https://giwmscdnone.gov.np/media/files/`. Each FY page lists one
**annual** workbook plus a **cumulative-to-date** workbook for every month
(श्रावण Shrawan, … जेष्ठसम्म up-to-Jestha). The CDN filenames are opaque hashes
(`FTS_Annual_2081_82_twybrul.xlsx`); the stable handle is the FY content page.

Downloaded for this build (under `Financial Data/customs/`, gitignored):
`FTS_Annual_2081_82.xlsx`, `FTS_UptoJestha_2081_82.xlsx`, `FTS_Shrawan_2081_82.xlsx`.

## Provenance

- Confidence default: A
- License: gov_open
- Ingestion mode: automated_cron

## Notes

Money Out Pulse + flagship #2 (border arbitrage). Compiled from the ASYCUDA World
customs-declaration system. Each workbook shares a fixed 10-sheet layout (verified
identical across the annual / Shrawan / up-to-Jestha editions); the column header
is on row index 2 (0-based), data from row 3.

### Extracted indicators (ADR-0015 dimensional, `dne_facts`)

| base_indicator_slug             | dimensions (kind)                       | source sheets         | unit          | confidence |
|---------------------------------|-----------------------------------------|-----------------------|---------------|:----------:|
| `customs-merchandise-imports`   | `commodity` (HS), `country`, `customs_office`, `customs-import-source` (composite) | 5, 3, 9, **4** | `npr_thousand`| A          |
| `customs-merchandise-exports`   | `commodity` (HS), `country`, `customs_office`, `customs-export-destination` (composite) | 7, 3, 9, **6** | `npr_thousand`| A          |

- Commodity `dimension_value` = the **HS code** (6/8-digit, verbatim);
  `dimension_label` = description. Country / customs office `dimension_value` =
  kebab slug of the name; `dimension_label` = raw name.
- **Composite dimension (ADR-0018)** — the commodity×partner cross-tabs (sheets 4
  & 6, long form) encode TWO dimensions into the one-dimension `dne_facts`
  contract: `dimension_kind` = `customs-import-source` / `customs-export-destination`;
  `dimension_value` = `<hs-code>__<country-slug>` (joined by `__`, separator-stable);
  `dimension_label` = `<description> → <country>`. The base measure slug is the
  SAME single-dimension slug, so the cross-tab is a strict disaggregation that
  reconciles to the commodity totals (verified: worst relative diff 0.0% across
  all 5,264 import + 1,236 export commodities).
- The single trailing "Total" row of each sheet (blank code/SN, or blank HS for
  the cross-tabs) is **excluded** (ADR-0015 aggregate rule). Genuine `0` values
  are preserved; only blank/dash is dropped (never fabricated/zero-filled).
- Real-file dry-run (FY 2081/82 annual): **45,770 facts** — imports 5,264
  commodity + 164 country + 29 customs + 33,887 import-source; exports 1,236 + 164
  + 29 + 4,997 export-destination. `status=success`, 0 errors.

**Unit (ADR-0011):** every value sheet states "(figures are in Rs. Thousands)" /
"(... in Rs. Thousand)" and the headline writes "Imports (Rs.in \`000)" → NPR
**thousand**, NOT million, NOT lakh. Magnitude verified (FY 2081/82 annual): total
imports = 1,804,122,731 thousand ≈ **NPR 1.80 trillion** (~150 bn/month); total
exports = 277,030,202 thousand ≈ **NPR 277 billion** (~23 bn/month). Shrawan single
month: imports ≈ NPR 128 bn, exports ≈ NPR 12 bn — in the expected Nepal band.

**Period dating:** read from the index sheet's self-describing row-0 descriptor
("Based on <scope> of FY YYYY/YY (Mid <Mon> <Yr> to Mid <Mon> <Yr>)"). Annual →
`annual` (label = BS FY); First Month (Shrawan) → `monthly` ("Shrawan 2081");
First N Months → `year_to_date` (label = end BS month, e.g. "Jestha 2082", with the
cumulative span recorded in `base_indicator_name`). The end BS month is read from
the scope parenthetical (the source's own BS names; "Asar" = Ashadh), never
inferred from the AD edge — the AD bounds are mid-month edges.

### Deferred (not fabricated)

- **`Imports_Revenue`** (duty collected) and derived **`Trade_Balance`** / share
  columns — separate measures, promotable later with their own base slugs.
- sheet 2 (chapter balance, redundant), sheet 8 (ID value comparison), sheet 1
  (headline totals — single series, not dimensional).

## Known breakage modes

- **Sheet-name / header drift.** The parser keys off the fixed sheet names
  (`5_Imports_By_Commodity`, …) and the row-2 header. A missing expected sheet
  emits a typed `PageLayoutChanged` (not a crash) and degrades `status` to
  `partial`. A renamed/reordered layout in a future FY edition surfaces as missing
  sheets — re-verify and bump `PARSER_VERSION`.
- **Period-descriptor wording change.** The regex expects "Based on … of FY
  YYYY/YY (Mid … to Mid …)". A wording change → typed `RegexMismatch` → the file
  is rejected loud (never a silently mis-dated fact).
- **Opaque CDN filenames.** Hash-suffixed file URLs are not stable; resolve via
  the FY content page each cycle.
- **Cumulative, not discrete months.** The monthly files are year-to-date
  cumulative (Shrawan → end month), not single-month deltas (except the Shrawan
  file, which is month 1). Modelled as `year_to_date`; consumers must not difference
  them blindly without accounting for the cumulative base.

## Revision policy

Later cumulative files within a fiscal year supersede earlier ones for the same
FY (figures are restated as declarations settle); the annual file is the final
revision. Each workbook is a separate `source_documents` row; `dne_facts` is keyed
by `source_document_id`, and the natural key includes `reporting_period_bs` +
`reporting_period_type`, so re-ingesting the same workbook is idempotent
(`ON CONFLICT DO NOTHING`) and distinct periods (Shrawan / up-to-Bhadra / annual)
coexist without overwriting — preserving the revision trail (Data Continuity
Protocol). Never merge across editions on `(slug, dimension, period)` alone.
