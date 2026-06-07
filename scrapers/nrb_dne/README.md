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

`0.2.0`

Defined in `parser.py` as `PARSER_VERSION: Final[str] = "0.2.0"`. Bump on any
behavior change (see [CONVENTIONS.md](../../docs/CONVENTIONS.md)).

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

### Real-file compatibility matrix (tested 2026-06-07)

| File | Sheets | Period type | Parser result |
|------|--------|-------------|---------------|
| `Foreign-exchange-reserves.xlsx` | FX Reserves | AD year+month (2001–2025) | `partial` — `PeriodUnparseable` (AD-year layout, out of scope) |
| `Balance-of-Payments-BPM6.xlsx` | BOP BPM6 | AD FY with R/P suffix | `partial` — `PeriodUnparseable` (AD-year layout) |
| `Foreign-Trade.xlsx` (main sheets) | 2 | AD FY "2006/07" | `partial` — `PeriodUnparseable` (AD-year) |
| `Foreign-Trade.xlsx` (SITC sheet) | 1 | Mixed `"(2071-72) 2014/15"` | `partial` — `PeriodUnparseable` |
| `Migrant-Workers-Remittance.xlsx` | 3 | AD FY "2021/22" | `partial` — `PeriodUnparseable` (was silently wrong before) |
| `Tourist-arrivals.xlsx` | Tourist Arrival | Integer AD years (1992–2025) | `partial` — `PeriodUnparseable` |
| `Exchange-rate.xlsx` | Time series | Rows-not-columns layout | `partial` — `PeriodUnparseable` |

**Root finding:** All 6 tested External Sector files use AD calendar years as period
labels, not BS. The parser is designed for the BS-year wide-format layout described
in the NRB CATALOG AUDIT (External Sector section). The External Sector files
prioritised for ingestion require an **AD-year extension** to handle their period
headers (see blocker note in INGEST_RUNBOOK or raise ADR). Files in other sectors
(Fiscal, Financial, Real) may use BS FY headers — test them separately.

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

**Period detection:**

- Annual: `"2079/80"` or `"2079-80"` → `reporting_period_type = "annual"`
- Monthly: `"Shrawan 2082"`, `"Bhadra 2081"`, etc. → `reporting_period_type = "monthly"`
- Unparseable column headers → `PeriodUnparseable` error; that column is skipped.

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

## Cross-reference

- [docs/DATA_PIPELINE.md](../../docs/DATA_PIPELINE.md) — staging → validation → approved flow
- [docs/CALENDAR_AND_PERIODS.md](../../docs/CALENDAR_AND_PERIODS.md) — BS/AD period handling
- [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md) — no LLM in production parsers
- [ADR-0009](../../docs/decisions/0009-source-registry-single-source-of-truth.md) — source must be in seed before live ingest
- `scrapers/README.md` — parser contract, BS<->AD date conventions, venv setup
