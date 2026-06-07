# mof_yellowbook — MoF / DPM-Office Yellow Book parser

Deterministic Python parser (ADR-0003) for the **Annual Performance Review of
Public Enterprises** (the *Yellow Book* / सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा),
published by the Office of the Prime Minister & Council of Ministers (DPM
Office).

- **Source id:** `dpm-public-enterprises-annual`
- **Corpus:** `Financial Data/mof_documents/yellowbook/` (6 PDFs)
- **Output:** ADR-0015 **dimensional facts** → `dne_facts` (dimension = public
  enterprise). Emits a `dimensional_rows` JSON array; no single-series
  `staging_rows`.
- **Ingest CLI:** `scripts/ingest-dne-yellowbook.ts`
  (`pnpm ingest:dne-yellowbook` — script line pending Mother, see below).

## What it extracts

The target is **Annex-1** ("ऋण लगानी तथा साँवा असूली" — government loan-investment
and principal-recovery by enterprise) of the **FY 2080/81** edition
(`Webiste Uploaded Yellow_sdwyi9v.pdf`), a clean-Unicode, stable 10-column table
spanning two pages and grouped by sector. Two base measures per enterprise:

| base_indicator_slug    | source column | meaning                                  |
|------------------------|---------------|------------------------------------------|
| `soe-government-share` | शेयर          | paid-in government equity/share capital  |
| `soe-loan-principal`   | ऋण            | outstanding government-loan principal    |

- `dimension_kind` = `public_enterprise`
- `dimension_value` = kebab slug of the enterprise name (Devanagari preserved)
- `dimension_label` = raw Devanagari enterprise name
- `unit` = `npr_thousand` — verbatim from the annex header "(रु. हजारमा)" (हजार =
  thousand; **NOT** million, **NOT** lakh — ADR-0011 magnitude verified: NEA
  share = 181,330,245 thousand = NPR 181.33 billion ✓)
- `reporting_period_type` = `annual`; BS fiscal year read from the annex header
  ("आ.व.२०८०/८१"); AD label via the +57 offset (ADR-0013): BS 2080/81 → AD 2023/24
- `confidence_grade` = `B`

Real-PDF dry-run (FY 2080/81): **84 rows** = 42 enterprises × 2 measures,
`status=success`, 0 errors.

## Why only Annex-1 (known breakage modes)

Encoding quality varies **page-to-page and edition-to-edition**:

- The older FY2079 edition's body prose is **CID-broken** (`(cid:N)` glyphs, no
  ToUnicode) — unusable.
- The **per-sector financial summary tables** (revenue सञ्चालन आय / net-profit
  खुद नाफा / admin-cost) ARE Unicode but render with **ragged, merged-cell
  geometry** whose column count differs every sector (12 / 13 / 21 / 15 / 9
  cols), and one sector renders in a **legacy Preeti byte-mapping**. Parsing
  those deterministically inside the 300-line diff budget is not feasible — so
  the brief's intended `soe-revenue` / `soe-net-profit-loss` /
  `soe-paid-up-capital` measures are **deferred** (they live there).
- **Annex-2 / Annex-3** are Preeti-encoded gibberish under text extraction
  (e.g. `g]kfn b"Uw ljsf; ;+:yfg` = "नेपाल दुग्ध विकास संस्थान"). We do **not**
  transliterate Preeti (that is reverse-engineering a font byte-map — fragile,
  out of scope, and effectively the OCR ADR-0003 forbids).
- The FY2081 edition (402 pp, 133 MB) does not surface a clean Annex-1 in the
  same place; layout differs. The parser scans every page for the annex markers
  and emits a typed `PageLayoutChanged` if the annex is absent (never a crash).

## Tests

`tests/test_parser.py` exercises the deterministic core
(`extract_dimensional_rows`) against a **synthesized** tiny Annex-1 table (sector
sub-headers, serial-led rows, total rows, Devanagari numerals, a preserved zero,
a dropped dash). The real multi-MB PDF is **not committed** (ADR-0003 / source
profile); two optional integration tests run against it when present and are
skipped otherwise.

```
cd scrapers
PYTHONPATH=<worktree>/scrapers <venv>/python -m pytest mof_yellowbook -q
```

## Pending Mother (RETURN items — not edited here per scope fence)

- `scrapers/pyproject.toml`: add `"mof_yellowbook*"` to
  `[tool.setuptools.packages.find].include` and `"mof_yellowbook/tests"` to
  `[tool.pytest.ini_options].testpaths`.
- `package.json` scripts: `"ingest:dne-yellowbook": "tsx scripts/ingest-dne-yellowbook.ts"`.
- `seed-source-registry.ts`: flip `dpm-public-enterprises-annual`
  `status: 'paused'` → `'active'` once the first live ingest lands.
