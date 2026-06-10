# ADR-0010: Ingest CLI Conventions

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, scripts, ingestion

## Context

The project now has five `scripts/ingest-*.ts` CLIs:
`ingest-cmefs`, `ingest-ncpi`, `ingest-bfi-monthly`, `ingest-fiscal-transfers`, `ingest-census-2021`.
Each was built in a separate worker session. Without a written convention, the next CLI author would have to reverse-engineer the shared patterns from the existing files, risking drift. The conventions listed here are already present in the existing scripts; this ADR makes them canonical.

Four areas needed explicit decisions:

1. **Node invocation flags** — how TypeScript ingest scripts are run without a build step.
2. **Source-document provenance** — when and how `source_documents` rows are created.
3. **Python subprocess spawning** — when to use `python path/to/parser.py` vs. `python -m pkg.parser`.
4. **Entity resolution batching** — per-row FK lookups vs. one batched query.

## Decision

### 1. Node invocation pattern

Every `ingest:*` entry in `package.json` uses:

```
node --env-file=.env.local --conditions=react-server --import tsx scripts/ingest-*.ts
```

Rationale for each flag:

- `--env-file=.env.local` — loads `DATABASE_URL` and `SUPABASE_*` without requiring the caller to `source` or `export` environment variables. The file is gitignored; CI provides secrets via the environment directly.
- `--conditions=react-server` — the `server-only` package (pinned by Next.js) includes a condition export that throws at import time in non-server environments. Without this flag, `tsx` compiles the import successfully but Node resolves the `default` export, which throws. The `react-server` condition activates the no-op export path, allowing `src/lib/db/client.ts` (which has a `server-only` guard) to be imported in a plain Node process.
- `--import tsx` — registers the `tsx` loader so `.ts` files are transpiled on-the-fly. No pre-compilation step needed; the scripts are dev-only tooling, not production code.

### 2. Source-document provenance

Every CLI self-creates its `source_documents` row when `--source-document-id` is omitted. The row is created with:

- `file_hash_sha256` computed from the file buffer (SHA-256, hex).
- `storage_key` formed deterministically: `<source-id>/<YYYY-MM-DD>/<basename>`.
- The file bytes are NOT uploaded to Supabase Storage at ingest time. Storage upload is a follow-up for all CLIs (noted in each script's docstring). The row is written; the blob is deferred.

In `--dry-run` mode a placeholder UUID (`00000000-0000-0000-0000-000000000000`) is used. This UUID is never written to the database; it exists only so the Python parser receives a syntactically valid UUID argument.

**Consequence:** a `source_id` passed to `insertSourceDocument` MUST already exist in `scripts/seed-source-registry.ts`. The `source_documents.source_id` column is a FK into `source_registry`. If the source is not seeded, the insert fails with a constraint violation. This is intentional — it enforces the Source Registry as the gate for all data feeds.

### 3. Python parser subprocess spawning

Parsers that use only stdlib or file-level imports can be spawned as a direct script:

```
python path/to/parser.py <source_document_path> <source_document_id>
```

Parsers that use **relative imports** (i.e., `from _common.types import …`) MUST be spawned as a module:

```
python -m <pkg>.parser <source_document_path> <source_document_id>
# with: cwd=scrapers/, PYTHONPATH=scrapers/
```

Reason: Python resolves relative imports relative to the package root. When the script is run directly (`python scrapers/nrb_bfi/parser.py`), Python adds the script's directory to `sys.path` but the `_common` sibling package is not visible. Running as `-m nrb_bfi.parser` with `cwd=scrapers` and `PYTHONPATH=scrapers` makes the entire `scrapers/` directory a package root, allowing `from _common.types import …` to resolve.

The `PYTHON` environment variable selects the interpreter (defaults to `python` on Windows, `python3` elsewhere), which allows the caller to point at the virtual environment created under `scrapers/.venv`.

### 4. Batched entity resolution

FK entities (e.g., `local_level_entity_id` resolved from `federal_code`) MUST be resolved in a **single `inArray` query** before the insert loop, not inside the loop:

```typescript
// Good — one round trip
const entityMapResult = await findLocalLevelEntitiesBySlugs(rows.map(r => r.federal_code));
const entityBySlug = entityMapResult.value;

// Bad — N+1 round trips
for (const row of rows) {
  const entity = await findEntityBySlug(row.federal_code); // N queries
}
```

The N+1 pattern was the original implementation of `ingest-fiscal-transfers.ts` for 4,400+ rows. Over a remote Supabase connection it took 10+ minutes; the batched form completes in seconds. Any future ingest CLI with FK resolution must use the batched pattern.

## Alternatives Considered

- **`ts-node` instead of `tsx` + `--import`:** `ts-node` requires `tsconfig` alignment and does not support the `--conditions` flag cleanly in ESM mode. `tsx` is already a devDep (used by `gen:source-index` and `check:source-registry`) and works without configuration changes. No reason to add a second transpiler.

- **Pre-compile scripts to JS:** Adds a build step and a compiled artifact that diverges from source. Ingest scripts are run by developers, not deployed. The on-the-fly approach is correct for tooling.

- **Upload file bytes at ingest time:** Supabase Storage writes add latency and a failure mode that would block the ingest. The metadata row (hash, key, size) is written immediately; blob upload can be done asynchronously as a separate pass. Both existing and future CLIs defer blob upload until a dedicated archival job is built.

- **Per-row entity resolution inside the insert loop (N+1):** Simpler to write; catastrophic at scale. Rejected after the fiscal-transfers performance regression.

## Consequences

### Positive

- All five existing ingest CLIs already conform; this ADR makes the pattern explicit and checkable in review.
- New CLI authors have a clear template: copy an existing script, update the source ID and parser path, follow the four rules.
- The `--dry-run` / lazy-import pattern means `DATABASE_URL` is not required for parser-output inspection.

### Negative

- Parsers with relative imports require the `cwd` + `PYTHONPATH` spawn pattern, which is not obvious. The INGEST_RUNBOOK.md §"Python relative imports" note documents this; a future author must read it.
- File bytes not being uploaded means the `storage_key` column in `source_documents` references a key that does not yet exist in Storage. Any code that tries to download a source document via its `storage_key` will 404 until the archival pass runs.

### Neutral / unknown

- The `--conditions=react-server` flag is specific to `server-only` v0.0.1. If `server-only` changes its condition export in a future version, this flag may need updating.

## References

- [`scripts/ingest-cmefs.ts`](../../scripts/ingest-cmefs.ts)
- [`scripts/ingest-bfi-monthly.ts`](../../scripts/ingest-bfi-monthly.ts)
- [`scripts/ingest-fiscal-transfers.ts`](../../scripts/ingest-fiscal-transfers.ts)
- [`scripts/ingest-census-2021.ts`](../../scripts/ingest-census-2021.ts)
- [`scripts/ingest-ncpi.ts`](../../scripts/ingest-ncpi.ts)
- [`docs/INGEST_RUNBOOK.md`](../INGEST_RUNBOOK.md) — §"Python relative imports"
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — production parsers are deterministic Python
- [ADR-0009](0009-source-registry-single-source-of-truth.md) — source_id must exist in seed before ingest
