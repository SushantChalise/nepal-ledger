# FCGO Consolidated Financial Statements PDF Parser

Deterministic Python parser for the Financial Comptroller General Office (FCGO)
**Consolidated Financial Statement** (CFS) — the audited all-of-government fiscal
outturn (federal + 7 provinces + 753 local governments) under NPSAS cash-basis.
See [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md): no LLM /
AI calls; pure file-in → dataclass-out.

## Source

| Field | Value |
|---|---|
| `SOURCE_ID` | `fcgo-consolidated-financial-statements` |
| Agency | Financial Comptroller General Office (FCGO), Ministry of Finance |
| Publication (English) | https://fcgo.gov.np/category/consolidated-us |
| Format | PDF |
| Frequency | Annual (published ~Poush of the following FY; ~9 months after FY close) |
| Source profile | `docs/sources/fcgo-consolidated-financial-statements.md` |
| Tested against | `Financial Data/fcgo_consolidated/FCGO_CFS_2022-23.pdf` (FY 2022/23, 325 pp) |

## What it parses — 6 headline aggregates (single series)

The CFS is a 300+ page document. Its **detailed financial-statement tables render
with reversed glyph order** under `pdfplumber` text extraction (a right-to-left
layout artifact: "Receipts" → "stpieceR"), so those tables are unusable for
deterministic regex. The **Executive Summary** (pp. 12–13) and the narrative
paragraphs around the **Treasury-Position table** (p. 31), however, are clean
forward Latin text. The parser anchors on that prose — exactly the NRB CMEFs
strategy — and **scans all pages** (the Executive Summary page number drifts
across editions; it is never hard-coded).

| Slug | Aggregate | FY 2022/23 value (npr_million) |
|---|---|---|
| `fcgo-total-revenue-outturn-annual` | Total revenue utilization of 3 tiers, after revenue-sharing settlements | 1,506,321.46 |
| `fcgo-total-expenditure-outturn-annual` | Total expenditure after eliminating intergovernmental transfers (excl. EBUs) | 1,672,128.84 |
| `fcgo-recurrent-expenditure-outturn-annual` | Consolidated recurrent expenditure (Σ across 3 tiers, **gross**) | 1,356,150.86 |
| `fcgo-capital-expenditure-outturn-annual` | Consolidated capital expenditure (Σ across 3 tiers, **gross**) | 527,447.04 |
| `fcgo-provincial-expenditure-consolidated-annual` | Total expenditure of all 7 provinces | 204,678.62 |
| `fcgo-local-level-expenditure-consolidated-annual` | Total expenditure of all 753 local governments | 453,817.73 |

### Basis mismatch (important — stamped in `parser_notes`)

`total-revenue` and `total-expenditure` are **after-elimination** figures, whereas
`recurrent` and `capital` are the **gross** consolidated sums (Σ over the three
tiers, *before* eliminating intergovernmental transfers). Hence
`recurrent + capital + financing` (= NPR 2,079,823.31 million for FY 2022/23)
does **not** equal `total-expenditure` (NPR 1,672,128.84 million). The
recurrent/capital rows carry an explicit "gross … not directly comparable to
total-expenditure" note so downstream consumers do not naively reconcile them.
(Recurrent and capital are captured from groups 1 and 2 of the single page-31
prose sentence that states recurrent, capital, and financing together.)

## Slug and unit conventions

**Slug convention:** `fcgo-<measure>-<scope>-annual`, matching the `SOURCE_ID`
family (`fcgo-consolidated-financial-statements`) — the same pattern the NRB CMEFs
parser uses (`cmefs-…` slugs ↔ `nrb-cmefs-monthly`). The bare slugs in the source
profile (`total-revenue-outturn-annual`, …) are prefixed with `fcgo-`.

**Unit:** all six values are `npr_million`. The source profile originally said
"billion" — that was **wrong** (see the profile's corrected "What we extract"
section). FY 2022/23 total revenue = NPR 1,506,321.46 **million** ≈ NPR 1.5
trillion, the correct order of magnitude for Nepal's 3-tier consolidated revenue.

**Reporting period:** `annual`. The CFS labels its fiscal year by **AD**
("Fiscal Year 2022/23"); Nepal's fiscal year (mid-July → mid-July) maps 1:1 to a
BS fiscal year via the **+57 offset on the lead year** (AD 2022/23 → BS 2079/80,
[ADR-0013](../../docs/decisions/0013-dne-ad-fiscal-year-periods.md)). The AD→BS
conversion uses a **local** helper (`_ad_fy_to_bs_start`); `_common/periods.py` is
not edited. Each row stores `reporting_period_bs` = `FY 2079/80`, `fiscal_year_bs`
= `2079/80`, `fiscal_year_ad_label` = `2022/23`. AD start/end bound the BS fiscal
span (mid-Shrawan … mid-Ashadh) via `_common.periods.mid_month_ad`
(mid-month approximation; the TS validator refines).

**Confidence:** `A` for all rows. The CFS is the audited outturn (the Office of
the Auditor General's opinion is bound into the document) — the highest-confidence
fiscal data the project ingests.

## PARSER_VERSION

`0.1.0` — defined in `parser.py` as `PARSER_VERSION: Final[str] = "0.1.0"`. Bump on
any behavior change (see [CONVENTIONS.md](../../docs/CONVENTIONS.md)).

## Output contract

```python
from fcgo_consolidated import parse, PARSER_VERSION, SOURCE_ID

result = parse(source_document_path: str, source_document_id: str)
# result.status: "success" | "partial" | "failure"
# result.staging_rows: list[StagingRowDraft]
# result.errors: list[ParserError]
```

`parse()` never raises on bad data — a missing prose anchor becomes a typed
`PageLayoutChanged` error (not a crash); an unparseable number becomes
`ValueUnparseable`. If only some anchors match, status is `partial` (found rows
emitted, missing ones reported as errors). The deterministic matching core is
`extract_indicators(text: str) -> ParserResult`, split out from PDF reading so it
can be unit-tested without a PDF-writing dependency.

## CLI invocation (orchestrator contract)

```powershell
# From scrapers/.venv, with PYTHON set:
python scrapers/fcgo_consolidated/parser.py <source_document_path> <source_document_id>
# Writes ParserResult JSON to stdout; exit 0 = ran (status may be failure), 2 = usage error.
```

## Ingest command

```powershell
# Dry-run (no DB writes, no DATABASE_URL needed):
pnpm ingest:fcgo-cfs --dry-run

# Live ingest (source-registry FK + seeded indicator slugs required first):
pnpm ingest:fcgo-cfs --input "Financial Data/fcgo_consolidated/FCGO_CFS_2022-23.pdf"
```

Wired via `ingest:fcgo-cfs` in `package.json`. The 6 FCGO slugs above must be
seeded in `seed-indicators.ts` for rows to promote to `approved_indicator_values`
(Mother adds them at integration; this parser does not edit the seed).

## Tests

No PDF-writing library is available in the venv and the 3.9 MB binary is **not
committed** (ADR-0003 / source profile). Tests therefore exercise the
deterministic core (`extract_indicators`) against **synthesized text fixtures**
reproducing two phrasings plus misses, with two optional integration tests that
run the full `parse` against the real PDF when it is on disk (skipped otherwise,
so CI without the binary stays green).

```powershell
# From the worktree root, with PYTHONPATH set to <worktree>/scrapers:
python -m pytest scrapers/fcgo_consolidated -q
```

| Test group | What it exercises |
|---|---|
| `test_phrasing1_*` | Canonical FY 2022/23 wording — 6 aggregates, exact values, magnitude check, basis notes, period/FY fields, recurrent≠capital |
| `test_phrasing2_*` | Alternation drift ("is"/"stands at"/"amounting to") reads different values — proves the regex is not echoing phrasing #1 |
| `test_miss_*` / `test_partial_*` / `test_empty_*` | Absent anchors → `failure` with typed `PageLayoutChanged`; partial match → `partial`; empty text → clean fail |
| `test_idempotent` | Same input → identical output (parser contract) |
| `test_missing_file_returns_failure` | Non-existent path → `failure` |
| `test_ad_fy_to_bs_roundtrip` | AD FY lead +57 → BS FY lead, round-trips via `fiscal_year_ad_label` (ADR-0013) |
| `test_real_pdf_*` (skip-if-absent) | Full `parse` + CLI JSON on the real 325-page PDF: 6 values, valid ISO datetimes, `npr_million` |

## Known breakage modes

- **Reversed-glyph tables.** The detailed statement tables extract with reversed
  word order; the parser deliberately does **not** read them. If a future edition
  moves a headline figure out of the Executive Summary / Treasury prose into a
  table only, that indicator will emit `PageLayoutChanged` (fail-loud).
- **CDN-token filenames.** Real PDFs are served from `giwmscdnone.gov.np` with
  opaque tokens; the downloader resolves links by scraping the FCGO category page,
  not by constructing URLs (see the source profile).
- **Phrasing drift.** Anchors use alternation for the verbs known to vary
  ("amounts to | stands at | is", "totaling | totalling | amounting to"). A larger
  rewording emits `PageLayoutChanged` for the affected indicator rather than a
  wrong value.

## Cross-reference

- [docs/DATA_PIPELINE.md](../../docs/DATA_PIPELINE.md) — staging → validation → approved flow
- [docs/CALENDAR_AND_PERIODS.md](../../docs/CALENDAR_AND_PERIODS.md) — BS/AD period handling
- [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md) — no LLM in production parsers
- [ADR-0011](../../docs/decisions/0011-fiscal-data-units-and-identity.md) — data-unit verification protocol
- [ADR-0013](../../docs/decisions/0013-dne-ad-fiscal-year-periods.md) — AD fiscal-year → BS (+57)
- `scrapers/README.md` — parser contract, BS↔AD date conventions, venv setup
