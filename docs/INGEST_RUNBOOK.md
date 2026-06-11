# Ingest Runbook

**Canonical in-repo operational guide for running Nepal Ledger's data pipeline.**

This doc is the authoritative reference for anyone (human or agent) running
an ingest, re-running a failed seed, or bootstrapping a fresh database. It
supersedes any private agent notes that point to external files.

Cross-linked from [DOCUMENTATION_STANDARD.md](DOCUMENTATION_STANDARD.md) §"Ingest CLI doc".

---

## Prerequisites

### 1. Environment file

Every ingest command requires a `.env.local` file in the **worktree root** (not
the project root). It must contain at minimum:

```
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
```

The `--env-file=.env.local` flag in the `node` invocation loads these variables
before any module import. Without it, `@/lib/db/client` throws at import time.

### 2. Python virtual environment and PYTHON env var

The ingest scripts spawn Python parsers as subprocesses. The spawner reads
`process.env['PYTHON']` and falls back to `python` (Windows) or `python3`
(Linux/Mac). On Windows with a venv:

```powershell
# Activate scrapers venv so 'python' resolves to it:
& "C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\.venv\Scripts\Activate.ps1"

# Or set PYTHON explicitly in .env.local:
PYTHON=C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\.venv\Scripts\python.exe
```

The venv must have scrapers installed: from `scrapers/` run `pip install -e ".[dev]"`.

### 3. Directory junction for `Financial Data/`

The `Financial Data/` directory lives only in the **parent repo root**
(`C:\Users\ACER\Projects\Economy\`). It is gitignored and is NOT copied into
worktrees. Ingest CLIs for fiscal-transfers and census resolve paths relative to
the worktree root, so they need a junction:

```powershell
# Run once per worktree. Replace the worktree path as needed.
New-Item -ItemType Junction `
    -Path "C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\Financial Data" `
    -Target "C:\Users\ACER\Projects\Economy\Financial Data"
```

Without this junction, `ingest:fiscal-transfers` and `ingest:census-2021` will
fail with "file not found" on the default input paths.

### 4. Node invocation pattern

All ingest and seed scripts use this invocation (via `pnpm run <script>`):

```
node --env-file=.env.local --conditions=react-server --import tsx scripts/<name>.ts
```

- `--env-file=.env.local` — loads the env file before any module is evaluated.
  Must come before `--conditions`.
- `--conditions=react-server` — activates Next.js server-only module conditions
  so `server-only` package imports do not throw at the top of `@/lib/db/client`.
- `--import tsx` — registers the tsx ESM loader so TypeScript source files can
  be imported directly without a separate compile step.

Running scripts with plain `tsx scripts/foo.ts` (without the Node flags) will
fail on `import 'server-only'` inside the DB client.

---

## Fresh-DB Bootstrap Order

Run these commands in sequence. Each step depends on the previous.

```powershell
# 0. Run Drizzle migrations (creates all tables)
pnpm exec drizzle-kit migrate

# 1. Seed the source registry (required FK for source_documents)
pnpm exec tsx scripts/seed-source-registry.ts

# 2. Seed indicators (required FK for staging_indicator_values)
node --env-file=.env.local --conditions=react-server --import tsx scripts/seed-indicators.ts

# 3. Seed local-level entities (required FK for fiscal-transfers + census)
#    Requires Financial Data junction (see Prerequisites §3).
node --env-file=.env.local --conditions=react-server --import tsx scripts/seed-local-level-entities.ts `
    --input "C:\Users\ACER\Projects\Economy\Financial Data\mof_documents\Cleaned\Fiscal Transfer_2082_82.xlsx"

# 4. Run ingests (see Per-Source Ingest Commands below)
```

---

## Per-Source Ingest Commands

All commands are run from the **worktree root**. Replace `<worktree>` with the
full absolute path.

### CMEFs (NRB narrative PDF)

Source ID: `nrb-cmefs-monthly` | Parser: `scrapers/nrb_cmefs/parser.py` v0.1.0

```powershell
# Dry-run (no DB writes):
pnpm ingest:cmefs --dry-run

# Live ingest:
pnpm ingest:cmefs --input "C:\Users\ACER\Projects\Economy\Stastical Information\CMEFs_Eng_Nine-Months_2082.83.pdf"
```

### NCPI Table 2(B) CSV

Source ID: `nrb-ncpi-table` | Parser: `scrapers/nrb_ncpi/parser.py`

```powershell
# Dry-run:
pnpm ingest:ncpi --dry-run

# Live ingest:
pnpm ingest:ncpi --input "C:\Users\ACER\Projects\Economy\NRB Current\CMEFs_Table_Nine-Months_2082.83(2(B).csv"
```

### BFI Monthly XLSX

Source ID: `nrb-bfi-monthly-xlsx` | Parser: `scrapers/nrb_bfi/parser.py`

```powershell
# Dry-run (uses default canonical-month fixture):
pnpm ingest:bfi-monthly --dry-run

# Live ingest:
pnpm ingest:bfi-monthly --input "C:\Users\ACER\Projects\Economy\Financial Data\nrb_monthly_statistics\Bhadau_2082_Publish.xlsx"
```

Note: the BFI CLI self-archives its file bytes to Supabase Storage and creates
its own `source_documents` row via `scripts/_lib/archive-source-document.ts`.
It does NOT go through the general `ingestSource()` orchestrator. The parser is
spawned as a module (`python -m scrapers.nrb_bfi.parser`) so relative imports resolve.

### Fiscal Transfers

Source ID: `local-fiscal-transfers-cleaned` | Parser: `scrapers/mof_fiscal_transfers/parser.py`

```powershell
# Dry-run:
pnpm ingest:fiscal-transfers --dry-run

# Live ingest:
pnpm ingest:fiscal-transfers --input "C:\Users\ACER\Projects\Economy\Financial Data\mof_documents\Cleaned\Fiscal Transfer_2082_82.xlsx"
```

Requires `Financial Data/` junction and local-level entities seed. The parser
writes directly to `local_government_fiscal_transfers` (no staging step).
Self-creates `source_documents` row.

### Census 2021 (CBS NPHC)

Source ID: `cbs-nphc-2021` | Parser: `scrapers/cbs_nphc/parser.py`

```powershell
# Dry-run (single CSV):
pnpm ingest:census-2021 -- --csv "C:\Users\ACER\Projects\Economy\Financial Data\Census\Hhld01_OwnershipOfHouse.csv" --dry-run

# Live ingest:
pnpm ingest:census-2021 -- --csv "C:\Users\ACER\Projects\Economy\Financial Data\Census\Hhld01_OwnershipOfHouse.csv"
```

Requires `Financial Data/` junction and local-level entities seed. The census
CLI accepts one CSV per invocation; loop externally for batch ingestion.
Self-archives bytes to Supabase Storage and inserts `source_documents` row via
`scripts/_lib/archive-source-document.ts` (mirrors BFI pattern). Parser is
spawned as a module (`python -m scrapers.cbs_nphc.parser`) for relative imports.

### FCGO Consolidated Financial Statements

Source ID: `fcgo-consolidated-financial-statements` | Parser: `scrapers/fcgo_consolidated/parser.py` v0.2.0

Audited all-of-government outturn (revenue + expenditure, 6 headline aggregates). Annual.
English CFS available FY 2018/19 → 2023/24 (6 editions). Parser auto-detects the fiscal year
from "FY YYYY/YY" in Executive Summary prose — no `--period` flag needed.

Requires a `Financial Data/` junction (§"Directory junction" above). Download the PDF from
https://fcgo.gov.np/category/consolidated-us and place it under
`Financial Data/fcgo_consolidated/` before running.

```powershell
# Dry-run (validates parser output shape — no DB writes):
$env:PYTHON = "C:\Users\ACER\Projects\Economy\scrapers\.venv\Scripts\python.exe"
pnpm ingest:fcgo-cfs --dry-run --input "C:\Users\ACER\Projects\Economy\Financial Data\fcgo_consolidated\FCGO_CFS_2022-23.pdf"

# Live ingest for FY 2022/23 (BS 2079/80):
pnpm ingest:fcgo-cfs --input "C:\Users\ACER\Projects\Economy\Financial Data\fcgo_consolidated\FCGO_CFS_2022-23.pdf"

# Live ingest for FY 2023/24 (BS 2080/81) — newest edition as of 2026-06-11:
pnpm ingest:fcgo-cfs --input "C:\Users\ACER\Projects\Economy\Financial Data\fcgo_consolidated\FCGO_CFS_2023-24.pdf"
```

Expected output: 6 staging rows, status `success`, all 6 promote to `approved_indicator_values`
(requires indicator slugs seeded via `pnpm seed:indicators`). Confidence grade A (audited outturn).

Cross-validate: total revenue for FY 2022/23 ≈ NPR 1,506,321.46 million; total expenditure ≈ NPR 1,672,128.84 million.
Compare against NRB CMEFs Table 9 "Government Finance" — should align within 1% (NRB sources from FCGO/MoF).

### DNE XLSX (NRB Database on Nepalese Economy)

Source ID: `nrb-dne-xlsx` (umbrella; see source-registry reconciliation note in
`scrapers/nrb_dne/README.md`) | Parser: `scrapers/nrb_dne/parser.py` v0.1.0

```powershell
# Dry-run (uses test fixture — always safe, no DB writes):
pnpm ingest:dne --dry-run

# Dry-run against a real DNE XLSX:
pnpm ingest:dne --dry-run --input "C:\Users\ACER\Projects\Economy\Financial Data\nrb_dne\external_sector_YYYY-MM-DD.xlsx"

# Live ingest (source-registry FK must exist first — see README):
pnpm ingest:dne --input "<path>" --source-id nrb-db-external-sector
```

Source-id to registry reconciliation is pending. Dry-run only until Mother
resolves the FK question.

### World Bank WDI (World Development Indicators)

Source ID: `wb-wdi` | Parser: `scrapers/wb_wdi/parser.py` v0.1.0 | 15 indicators

```powershell
# Dry-run against saved fixture (no DB, no network):
pnpm ingest:wdi --dry-run

# Live ingest from pre-downloaded combined JSON (recommended for reproducibility):
pnpm ingest:wdi --input "C:\path\to\wdi_npl_2025-06-11.json"

# Download fresh snapshot from WB API then ingest (requires network):
pnpm ingest:wdi --download

# Download and save to a specific directory without ingesting:
pnpm ingest:wdi --download --output-dir "C:\Users\ACER\Projects\Economy\Financial Data\wb_wdi"
```

Notes:
- Parser reads a single combined JSON blob assembled by the CLI (one `source_documents` row per run).
- WB year Y = Nepal FY Jul Y – Jul Y+1 = BS FY (Y+57)/(Y+58%100).
- Poverty headcount and Gini are sparse (1 non-null every 3–5 years); null values are silently skipped.
- After live ingest, `checkWdiDneDivergence()` auto-runs and writes `ValueOutOfPlausibleRange` warning
  flags if WDI–DNE divergence exceeds 3 pp (GDP growth, CPI) or 20% relative (GDP per capita).
- Cross-source divergence flags are warnings only; they never block ingest.
- No `Financial Data/` junction required — the WB API is network-only or via a local JSON file.

### IMF WEO (World Economic Outlook)

Source ID: `imf-weo` | Parser: `scrapers/imf_weo/parser.py` v0.1.0 | 13 indicators (actuals + projections)

```powershell
# Dry-run against saved fixture (no DB, no network):
pnpm ingest:imf-weo --dry-run

# Download fresh from the IMF DataMapper API, marking forecast years, then ingest:
pnpm ingest:imf-weo --download --projection-from-year 2025

# Download/save without ingesting (inspect first):
pnpm ingest:imf-weo --download --projection-from-year 2025 --output-dir "C:\WEO"

# Live ingest from a pre-downloaded combined JSON:
pnpm ingest:imf-weo --input "C:\WEO\weo_npl_2026-06-11.json"
```

Notes:
- Parser reads a single combined JSON blob assembled by the CLI (one `source_documents` row per run).
- API: `https://www.imf.org/external/datamapper/api/v1/<code>/NPL` — no auth, one GET per code.
- WEO year Y = Nepal FY Jul Y – Jul Y+1 = BS FY (Y+57)/(Y+58%100) — same convention as WDI.
- **Projections (ADR-0025):** the DataMapper API does not flag forecast years. Supply
  `--projection-from-year <YEAR>` (the vintage's first forecast year, e.g. 2025 for the Apr-2026 WEO).
  Years ≥ that become `observation_type='projection'`; omit the flag and every row is `'actual'`.
  Re-confirm the boundary each April/October vintage.
- USD/PPP levels are published in billions; the parser scales ×1000 → `usd_million` / `intl_dollar_million`
  (matches `wb-wdi` so the two benchmark in one unit).
- No `Financial Data/` junction required.

### WB PIP (Poverty and Inequality Platform)

Source ID: `wb-pip` | Parser: `scrapers/wb_pip/parser.py` v0.1.0 | 10 indicators (survey anchors + filled trend)

```powershell
# Dry-run against saved fixture (no DB, no network):
pnpm ingest:pip --dry-run

# Download fresh from the PIP API (4 queries, merged), then ingest:
pnpm ingest:pip --download

# Download/save without ingesting:
pnpm ingest:pip --download --output-dir "C:\PIP"

# Live ingest from a pre-downloaded combined JSON:
pnpm ingest:pip --input "C:\PIP\pip_npl_2026-06-11.json"
```

Notes:
- The CLI runs **4 PIP queries** (survey anchors at $2.15/$3.65/$6.85 + the $3.65 fill_gaps trend) and merges
  them into one combined JSON; the parser is deterministic file-in.
- PIP API is **intermittently flaky** (transient empty / HTTP 000) — the CLI retries each query up to 4×.
- `reporting_year` is a **calendar** year; the parser maps it onto Nepal's FY via the WDI convention
  (Y → BS Y+57) so `pip-*` aligns with `wdi-*` for the same survey.
- **observation_type (ADR-0025):** survey rounds → `actual`/conf-A; the filled $3.65 trend →
  `interpolated`/`projection`/`estimate` per PIP's `estimation_type`, conf-B. Survey years come only from
  the anchor block (the filled series is deduped against them).
- `pip-gini` is stored ×100 (`index_points`) to match `wdi-gini-index`.
- No `Financial Data/` junction required.

### UNDP HDR Composite Indices

Source ID: `hdr-composite` | Parser: `scrapers/hdr_composite/parser.py` v0.1.0 | 18 indicators

```powershell
# Dry-run against saved fixture (no DB, no network):
pnpm ingest:hdr --dry-run

# Download the HDR 2025 CSV, then ingest:
pnpm ingest:hdr --download

# Download/save without ingesting:
pnpm ingest:hdr --download --output-dir "C:\HDR"

# Live ingest from a pre-downloaded CSV:
pnpm ingest:hdr --input "C:\HDR\HDR25_Composite_indices_complete_time_series.csv"
```

Notes:
- The parser reads the UNDP "complete time series" **CSV directly** (one wide row per country); the CLI just
  downloads it and passes the path — no JSON assembly.
- **The CSV is Latin-1 (cp1252)**, not UTF-8 — the parser reads it as Latin-1; the CLI streams bytes verbatim.
- Wide format: ~1,112 `<metric>_<year>` columns; exact-prefix matching means `hdi` ignores `hdi_rank`/`hdi_f`.
- HDR year is calendar; mapped onto Nepal FY via the WDI convention (Y → BS Y+57). Nepal HDI 2023 = 0.622.
- All rows `observation_type='actual'`, confidence A. Publication date is pinned to the HDR vintage in the parser.
- **The UNDP CSV URL path changes each vintage** (`2025_HDR/HDR25_…`) — update the CLI constant + registry URL when bumping.
- No `Financial Data/` junction required.

### WB IDS (International Debt Statistics — debt by creditor)

Source ID: `wb-ids` | Parser: `scrapers/wb_ids/parser.py` v0.1.0 | 12 indicators

```powershell
# Dry-run against saved fixture (no DB, no network):
pnpm ingest:ids --dry-run

# Download fresh from the IDS API (6 series, creditor extraction), then ingest:
pnpm ingest:ids --download

# Download/save without ingesting:
pnpm ingest:ids --download --output-dir "C:\IDS"

# Live ingest from a pre-downloaded combined JSON:
pnpm ingest:ids --input "C:\IDS\ids_npl_2026-06-11.json"
```

Notes:
- **IDS uses the `sources/6` counterpart-area route**, NOT `/indicator/?source=6` (the latter 404s for IDS series):
  `api.worldbank.org/v2/sources/6/country/NPL/series/<CODE>/counterpart-area/all/time/all`.
- The CLI runs 6 series queries (DECT.CD, DECT.GN.ZS, TDS.DECT.CD, DSTC.CD, BLAT.CD, MLAT.CD), extracts the
  World aggregate (`WLD`) + named counterparts (Japan 701, India 646, China 730, Korea 742, IDA 905, ADB 915)
  into pre-resolved `ids-*` slugs. Keys on counterpart **id** (names carry trailing nbsp garbage).
- Creditors are **slug-encoded** (`ids-debt-bilateral-china-usd`) — no partner-dimension schema/ADR for this set.
- USD stocks ÷1e6 → `usd_million` (matches wb-wdi); debt-to-GNI in `percent`. All `observation_type='actual'`, conf A.
- Year mapped onto Nepal FY via the shared `nepal_wb_year_period` helper (Y → BS Y+57).
- No `Financial Data/` junction required.

---

## Operational Gotchas

### Source must be in the seed (not just docs/sources/)

The `source_documents` table has a FK on `source_registry.source_id`. If a
source has a profile under `docs/sources/` but has NOT been seeded via
`seed-source-registry.ts`, any ingest attempt will fail at the DB insert
with a foreign-key violation. Seed first, then ingest.

### BFI, census, and fiscal-transfers CLIs self-archive to Supabase Storage

The BFI, census, and fiscal-transfers ingest CLIs create their own
`source_documents` row via the shared `scripts/_lib/archive-source-document.ts`
helper. They do NOT use the `ingestSource()` orchestrator. They upload file bytes
to Supabase Storage first (content-addressed; idempotent), then insert the
`source_documents` row using the real `storageKey`/`fileHashSha256`/`fileSizeBytes`
returned by the upload — no synthetic keys.

### Subprocess module flag for BFI and census parsers

The BFI and census parsers use relative imports within the `scrapers/` package.
They must be spawned with `python -m scrapers.nrb_bfi.parser` (or
`python -m scrapers.cbs_nphc.parser`), NOT as a direct script path, otherwise
Python cannot resolve the `_common` package. The ingest CLIs handle this
automatically — do not change the spawn invocation.

### FK errors surface as generic QueryFailed under tsx

When a foreign-key constraint fires (e.g. source not in registry, entity not
seeded), the Drizzle/postgres.js error surfaces as a generic `QueryFailed` with
the original message buried in the `cause`. To diagnose:

```sql
-- Run a direct insert in a Postgres client to see the SQLSTATE:
INSERT INTO source_documents (source_id, ...) VALUES ('unknown-id', ...);
-- => ERROR 23503: insert or update on table "source_documents" violates foreign key constraint
```

Then check that the `source_id` is in `source_registry` and the seed has been run.

### tsx path resolution and @/ alias

The `@/` alias resolves to `src/` in the worktree. Scripts that import
`@/lib/db/client` require the `--conditions=react-server` flag AND `server-only`
in the dependency graph. If you get `Cannot import 'server-only' in a client
component`, you are missing `--conditions=react-server`.

---

## Render Verification

After a successful ingest, verify the output appears in the UI:

```powershell
pnpm dev
```

Navigate to:
- `/pulse` — checks `approved_indicator_values` (CMEFs, NCPI, BFI indicators)
- `/money-map` — checks `local_government_fiscal_transfers` (fiscal-transfers ingest)

---

## See Also

- [DATA_PIPELINE.md](DATA_PIPELINE.md) — staging → validation → approved flow
- [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) — source registration workflow
- [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md) — BS/AD period handling
- [WINDOWS_DEV.md](WINDOWS_DEV.md) — Windows + WSL2 environment notes
- [docs/decisions/0003-ai-assisted-parsing-policy.md](decisions/0003-ai-assisted-parsing-policy.md) — no LLM in parsers
- [docs/decisions/0004-supabase-storage-instead-of-r2.md](decisions/0004-supabase-storage-instead-of-r2.md) — storage backend
- [docs/decisions/0009-source-registry-single-source-of-truth.md](decisions/0009-source-registry-single-source-of-truth.md) — seed-first rule
