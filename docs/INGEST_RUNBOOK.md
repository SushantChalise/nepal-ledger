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
