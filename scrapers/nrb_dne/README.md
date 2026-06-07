# NRB Database on Nepalese Economy (DNE) XLSX Parser

Deterministic Python parser for the NRB "Database on Nepalese Economy" (DNE) portal XLSX files.
See [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md): no LLM / AI calls; pure file-in → dataclass-out.

## Source

| Field | Value |
|---|---|
| `SOURCE_ID` | `nrb-dne-xlsx` |
| Agency | Nepal Rastra Bank (NRB) |
| Portal | https://www.nrb.org.np/database-on-nepalese-economy/ |
| Format | XLSX |
| Source profile | `docs/sources/nrb-dne-xlsx.md` (pending registration — see NOTE below) |

> NOTE: Source-registry reconciliation required before a live ingest. The parser's
> `SOURCE_ID` is `nrb-dne-xlsx`, but the current seed uses per-sector IDs
> (`nrb-db-external-sector`, `nrb-db-fiscal-sector`, `nrb-db-financial-sector`,
> `nrb-db-real-sector`). Mother must decide whether to register `nrb-dne-xlsx`
> as an umbrella source or map each XLSX download to its sector ID at ingest time
> via `--source-id`. Until the FK exists in `source_registry`, live ingests will
> fail. Dry-run (`pnpm ingest:dne --dry-run`) is always safe.

## What it parses — the 5 sectoral pages

The NRB DNE portal organises XLSX files into five sections:

| Sector page | URL path | Representative indicators |
|---|---|---|
| **Real** | `/real-sector/` | GDP, CPI, agriculture output, energy, tourism |
| **External** | `/external-sector/` | BoP, forex reserves, trade, remittances, tourist arrivals |
| **Fiscal** | `/fiscal-sector/` | Government revenue, expenditure, outstanding debt |
| **Monetary** | (monetary sector page) | Monetary survey, broad money, NRB's own accounts |
| **Financial** | `/financial-sector/` | BFI assets, deposits, loans, interest rates, NEPSE |

Each XLSX uses the same **wide format**: indicators as rows, fiscal periods as columns.
The parser handles all five pages identically.

## PARSER_VERSION

`0.5.0`

Defined in `parser.py` as `PARSER_VERSION: Final[str] = "0.5.0"`. Bump on any
behavior change (see [CONVENTIONS.md](../../docs/CONVENTIONS.md)).

### v0.5.0 changes (2026-06-07)

Two changes, per [ADR-0015](../../docs/decisions/0015-dne-dimensional-fact-model.md).

**(A) Foreign Trade → `dimensional_rows`.** `Foreign-Trade.xlsx` is a dimensional
matrix, not a single series. Its **"Export Import Major Commodities"** sheet breaks
merchandise trade down by COMMODITY. The parser now routes this file (by filename
stem) to a dimensional path that emits a **`dimensional_rows`** array (ADR-0015
contract) instead of `staging_rows`:

- New public entry `parse_dne(path, id) -> DneParserResult` carries BOTH
  `staging_rows` (single-series files) and `dimensional_rows` (matrix files); the
  CLI `__main__` now dumps `parse_dne(...).to_json_dict()`, adding the
  `dimensional_rows` key the DNE ingest CLI reads. The shared `ParserResult` in
  `_common/types.py` is **unchanged**; `DimensionalRowDraft`/`DneParserResult` are
  DNE-local dataclasses. `parse()` is unchanged for single-series files and now
  short-circuits dimensional files to empty `staging_rows` + an explanatory note.
- Each dimensional row: `base_indicator_slug`, `base_indicator_name`,
  `dimension_kind="commodity"`, `dimension_value` (bare kebab of the commodity
  label), `dimension_label` (raw), `value`, `unit="npr_million"`, monthly period
  fields (BS + exact-Gregorian AD span), `confidence_grade="B"`.
- **Base-slug partner qualification (deviation, flagged).** ADR-0015 names the base
  measures `dne-merchandise-exports` / `dne-merchandise-imports`. The sheet carries
  separate **India / China / Other Countries** sections for the SAME commodity and
  period; emitting them all under one base slug would collide on the `dne_facts`
  unique index and silently drop 2 of every 3 partner facts under `ON CONFLICT DO
  NOTHING`. We therefore qualify the base slug with the trade partner
  (`dne-merchandise-exports-india`, `…-china`, `…-other-countries`) — derivable from
  the section header ("…to India"). The partner-agnostic headline total may be
  registered as a single indicator later.
- **Period mapping.** The panel is a wide MONTHLY layout: a sparse fiscal-year
  label every 12 columns (Aug → next Jul) over a repeating AD month row. The FY is
  forward-filled AND advanced **structurally** at each new "Aug" column when the
  label cell is blank (a real merged-cell artifact in some sections) — without this
  two physically-distinct year-blocks collapse onto identical periods. The
  calendar-year split is August-started (Aug–Dec → lead year, Jan–Jul → trailing),
  distinct from the July-started long panel.
- **Deferred (same contract, next round):** the "Export Import SITC Groupwise"
  sheet (a *different* classification of the same totals — would double-count if
  mixed under one base measure), the two "Direction of Foreign Trade" partner
  sheets (USD + by-partner, not by-commodity), and the "Working" sheet. Remittance
  by country/district (ADR-0015) also follows next.

**(B) Single-series slug cleanup (FX-reserves / BoP).** Slug derivation now:

- **Strips leading outline enumerators** ("A. Nepal Rastra Bank" →
  `dne-nepal-rastra-bank`; "1. Gold…" → `dne-gold…`; BoP "1.A.a.1 …") and trailing
  aggregation hints ("(1+2)", "(A+B)"). Genuine abbreviations like "O/W" (of which)
  are preserved.
- **Resolves `-rNN` duplicate-label collisions by qualifier** instead of the
  volatile row-index suffix: the **outline code** in the S.N. column for BoP
  (`3.4.1.1 NRB` → `dne-nrb-3-4-1-1`) or the **section parent** for FX-reserves
  (`Convertible` under "C. Gross Foreign Exchange Reserve" →
  `dne-convertible-gross-foreign-exchange-reserve`). `-rNN` remains only as a
  last-resort fallback when no qualifier is determinable.
- Dimension (commodity) slugs deliberately do NOT strip enumerators/parentheticals:
  "G.I. pipe" vs "M.S. Pipe" and "Ghee (Clarified)" vs "Ghee (Vegetable)" must stay
  distinct or facts collide and drop.

### v0.4.0 changes (2026-06-07)

Adds the three non-standard AD period layouts that previously produced 0 rows
(ADR-0013 follow-up). The parser now tries four layouts in priority order:

1. **Long panel** (Exchange-rate): FY label in col 0 (sparse, forward-filled) +
   AD month name in col 1 + numeric value columns. Detected *first* because the
   standard header detector would otherwise mis-claim the col-0 FY label as its
   only period column. Each value column gets its own slug from its multi-row
   sub-header; aggregate rows ("Annual Average") are skipped.
2. **Standard wide** (unchanged from v0.3.0).
3. **Two-row monthly header** (Foreign-exchange-reserves): a row of integer AD
   years over a row of AD month names; each (year, month) column is a monthly
   period, the sparse year row forward-filled. A repeated (year, month) column
   (a real NRB source mislabel — two "Oct 2025" columns with different values)
   keeps **both** values, flags them in `parser_notes`, and emits one
   `PeriodAmbiguous`. Never drops or fabricates.
4. **Transposed** (Tourist-arrivals): AD month names as column headers, integer
   AD years as row labels; long-formatted to one row per year×month. The annual
   "Total" column is ignored.

**AD calendar month → BS period mapping.** An AD Gregorian month is mapped to the
BS month containing its 15th — the exact inverse of
`_common.periods._BS_MONTH_TO_AD_MONTH`, round-trip-verified against `mid_month_ad`.
The BS year follows the same mid-July break rule (AD month ≥ July → BS year
`AD+57`; < July → `AD+56`). This is a **documented mid-month approximation** (an AD
calendar month overlaps two BS months); it is flagged on every such row's
`parser_notes`, and the stored AD month span is the *exact* Gregorian month (1st–28th,
widened by the validator). No BS-AD library is added (Year-1 scope, see
`_common/periods.py`); the map lives locally in the parser, not in `_common/`.

Other v0.4.0 notes:
- New monthly draft builder `_ad_monthly_to_draft_fields` stores both
  `reporting_period_bs` (BS month label) and `fiscal_year_ad_label` (AD FY), as
  ADR-0013 requires.
- Units for the FX-rate panel are deliberately left `UnitAmbiguous` (no
  controlled-vocab unit exists for "NPR per USD"); the raw column sub-label is
  carried so the validator flags it rather than stamping a wrong unit.

### v0.2.0 changes (2026-06-07)

- `_parse_annual_fy`: accepts NRB revision/provisional suffixes (`R`, `P`, `E`) on
  BS FY labels — e.g. `"2079/80R"` now parses to `("2079/80", "2022/23")`.
- `_parse_annual_fy`: accepts `YYYY/YYYY` 4-digit tail (e.g. `"2079/2080"`) used
  in some SITC sheets.
- `_parse_annual_fy`: rejects AD-era year labels (`< 2040`) so that AD fiscal
  years like `"2006/07"` (Foreign Trade) or `"2022/23R"` (BoP BPM6) are correctly
  classified as unparseable rather than silently stamped with wrong BC-era AD dates.
- `_detect_unit_from_text`: strips surrounding parentheses before lookup, handling
  NRB's common `"(Rs in Million)"` and `"(NPR in Million)"` annotation style.
- `_parse_sheet`: when no BS header is found, emits an explicit `PeriodUnparseable`
  error listing the AD-year tokens found, making incompatibility visible to Mother.
- Unit map: added `"npr in million"`, `"in npr million"`, `"nrs million"` variants.

### Real-file compatibility matrix (tested 2026-06-07, v0.4.0)

| File | Layout | Rows | Parser result |
|------|--------|------|---------------|
| `Balance-of-Payments-BPM6.xlsx` | standard wide, AD FY | 360 | `success` (annual, npr_million) — **v0.5.0: slugs cleaned, no `-rNN`** |
| `Foreign-Trade.xlsx` | **dimensional matrix (v0.5.0)** | **38490 `dimensional_rows`** | `success` — Major-Commodities by commodity × 6 partner-qualified base measures; `staging_rows` empty (ADR-0015). Was a bogus 11334 single-series rows pre-v0.5.0. |
| `Foreign-exchange-reserves.xlsx` | two-row integer-year + monthly | 6716 | `partial` — `PeriodAmbiguous`×1 (repeated Oct 2025 column, both values kept + flagged); **v0.5.0: slugs cleaned, no enumerator prefix / `-rNN`** |
| `Exchange-rate.xlsx` | long panel (FY col + month col) | 2172 | `partial` — `UnitAmbiguous`×3 (no vocab unit for FX rate; raw label carried) |
| `Tourist-arrivals.xlsx` | transposed (years-as-rows) | 407 | `success` (monthly, count) |
| `Migrant-Workers-Remittance.xlsx` | standard wide (Country sheet) | 1407 | `partial` — `PeriodUnparseable`×1 (the `Migrant Worker` sheet uses datetime-object period columns — still deferred) |

**v0.4.0 status:** All six External Sector files now ingest. The three previously-
unparseable layouts (FX-reserves two-row monthly header, Exchange-rate long panel,
Tourist-arrivals transposed) are handled. Remaining `partial`/error notes are
honest data-quality flags, not parse failures:
- FX-reserves: one source-side repeated `(year, month)` column → `PeriodAmbiguous`
  (both values emitted and flagged; validator adjudicates).
- Exchange-rate: FX rate has no controlled-vocab unit → `UnitAmbiguous` (expected).
- Migrant-Workers-Remittance: one sheet (`Migrant Worker`) uses `datetime`-object
  period columns — **still deferred** (a separate layout, not in this task's scope).

**Files NOT yet tested:** Fiscal Sector (`Government-budgetary-operation.xlsx`,
`Outstanding-government-debt-1.xlsx`) and Financial Sector files, which may
use BS FY notation. Prioritise those for next ingestion batch.

## Slug and unit conventions

**Slug convention:** `dne-<kebab-case-row-label>`

Example: `"Total Foreign Exchange Reserves"` → `dne-total-foreign-exchange-reserves`.

Slugify logic: lowercase → strip non-alphanumeric (replace with space) → collapse spaces → hyphenate → prepend `dne-`.

**Unit detection:** scanned from preamble rows above the header row and from the sheet name.
NRB's common phrasings are mapped to canonical vocab:

| NRB phrasing | Canonical unit |
|---|---|
| `Rs. in million` / `Nrs. in million` | `npr_million` |
| `Rs. in billion` / `Nrs. in billion` | `npr_billion` |
| `in million US$` / `usd million` | `usd_million` |
| `percent` / `%` | `percent` |
| `number` / `nos.` | `count` |
| `metric ton` | `metric_ton` |
| `kwh` / `mwh` / `gwh` | `kwh` / `mwh` / `gwh` |
| `months` | `months` |

If the unit cannot be resolved, the parser emits a `UnitAmbiguous` error but
continues — the raw unit string is used so the validator can flag it.

**Period detection (four layouts, tried in priority order — see `parser.py` module
docstring and the v0.4.0 changes above for full detail):**

- **Long panel** (detected first): FY in col 0 + AD month name in col 1 + value cols.
- **Standard wide**: annual `"2079/80"`/`"2022/23"` or monthly `"Shrawan 2082"` column headers.
- **Two-row monthly header**: integer AD years over AD month names; per-(year,month) monthly periods.
- **Transposed**: AD month columns × integer-AD-year rows → long-format monthly.
- Annual → `reporting_period_type = "annual"`; monthly layouts → `"monthly"`.
- AD calendar months map to the BS month containing their 15th (documented mid-month
  approximation, flagged in `parser_notes`; exact Gregorian span stored).
- Repeated `(year, month)` columns keep both values + emit `PeriodAmbiguous`.
- Unparseable column headers / unmatched sheets with year tokens → `PeriodUnparseable`
  (fail-loud; never a silent drop).

**Confidence:** `B` for all DNE rows. NRB compiles from multiple agencies; figures
are revised across publications. The validation layer may promote individual rows to A.

## Output contract

The parser implements the standard scraper contract (see `scrapers/README.md`):

```python
from nrb_dne import parse, PARSER_VERSION, SOURCE_ID

result = parse(source_document_path: str, source_document_id: str)
# result: ParserResult
# result.staging_rows: list[StagingRowDraft]
# result.errors: list[ParserError]
# result.status: "success" | "partial" | "failure"
```

`parse()` never raises on bad data — it returns `status="partial"` or `"failure"`
with structured `errors[]`.

## CLI invocation (orchestrator contract)

```powershell
# From scrapers/.venv, with PYTHON set:
python scrapers/nrb_dne/parser.py <source_document_path> <source_document_id>
# Writes ParserResult JSON to stdout; exit 0 = ran (status may be failure), 2 = usage error.
```

## Ingest command

```powershell
# Dry-run (no DB writes, no DATABASE_URL needed):
pnpm ingest:dne --dry-run --input "scrapers/nrb_dne/tests/fixtures/happy_path.xlsx"

# Live ingest — source-registry FK must exist first:
pnpm ingest:dne --input "Financial Data/nrb_dne/external_sector_YYYY-MM-DD.xlsx" --source-id nrb-db-external-sector
```

Wired via `ingest:dne` in `package.json`. No real DNE files are downloaded yet;
source-id to registry reconciliation is pending Mother's decision.

## Tests

All tests use programmatically generated XLSX fixtures from `tests/conftest.py` —
no network calls, no binary fixtures committed.

```powershell
# From scrapers/.venv (activate first):
python -m pytest scrapers/nrb_dne/tests -q
```

Test matrix:

| Test group | What it exercises |
|---|---|
| `test_happy_path_*` | Main parser logic — 3 indicators × (3 annual + 2 monthly) periods |
| `test_empty_workbook_*` | Empty sheet → `partial` status, `NoDataExtracted` error |
| `test_ambiguous_unit_*` | Missing unit → `UnitAmbiguous` error, rows still parsed |
| `test_bad_period_*` | Malformed period header → `PeriodUnparseable` error |
| `test_missing_file_*` | Non-existent path → `failure` status |
| `test_idempotent` | Same input → same output |
| `test_json_serialisable` | `asdict(result)` round-trips through `json.dumps` |
| `test_bs_fy_suffix_*` | BS FY with R/P/E revision suffixes (v0.2.0) |
| `test_ad_year_sheet_*` | AD fiscal-year headers → BS via +57 (ADR-0013, v0.3.0) |
| `test_ym_*` | Two-row integer-year + month header; forward-fill; exact Gregorian span; approximation flag (v0.4.0) |
| `test_ym_dup_*` | Repeated `(year, month)` column → both values kept + `PeriodAmbiguous` (v0.4.0) |
| `test_long_panel_*` | Long panel: FY/month cols, forward-fill, aggregate-row skip, `UnitAmbiguous` (v0.4.0) |
| `test_transposed_*` | Transposed years-as-rows; Total column ignored; AD→BS month mapping (v0.4.0) |
| `test_ft_*` | Foreign-Trade → `dimensional_rows` (ADR-0015): shape, partner-qualified base slugs, commodity dimension, `npr_million`, no over-stripped commodity slug, structural FY-advance / no unique-key collisions, JSON round-trip (v0.5.0) |
| `test_fx_slug_*` | Single-series slug cleanup: no enumerator prefix, no `-rNN`, enumerator + `(1+2)` stripped, collision qualified by section parent (v0.5.0) |

## Cross-reference

- [docs/DATA_PIPELINE.md](../../docs/DATA_PIPELINE.md) — staging → validation → approved flow
- [docs/CALENDAR_AND_PERIODS.md](../../docs/CALENDAR_AND_PERIODS.md) — BS/AD period handling
- [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md) — no LLM in production parsers
- [ADR-0009](../../docs/decisions/0009-source-registry-single-source-of-truth.md) — source must be in seed before live ingest
- `scrapers/README.md` — parser contract, BS<->AD date conventions, venv setup
