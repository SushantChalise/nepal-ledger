# Worker H — Ingestion Orchestrator (Node ↔ Python parser)

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** soft 300 / hard 500 non-test source lines

---

## Goal

Build `src/lib/ingestion/` — the Node-side orchestrator that drives one full ingestion of a source document end-to-end:

```
file on disk OR URL → archive to Supabase Storage → write source_documents row
→ spawn Python parser via child_process → write parser_runs + staging_indicator_values
→ (calls Worker G's validateParserRun) → returns IngestionSummary
```

Done = `pnpm typecheck/lint/test` green; `ingestSource({ sourceId, ... })` returns `Result<IngestionSummary>`; tests mock the storage wrapper, the child_process call, and `db()` repositories.

## Why

We have:
- Schema + repositories (Workers 3, 10)
- Storage wrapper (Worker 7)
- Python parser (Worker 9)
- Validation job (Worker G)

What's missing: the glue. Without an orchestrator, each piece works in isolation but nothing drives end-to-end. This is the last code piece before the first live ingestion attempt.

## Scope Fence

Create:
- `src/lib/ingestion/index.ts` — public surface: `ingestSource(input): Promise<Result<IngestionSummary>>`
- `src/lib/ingestion/types.ts` — `IngestionInput`, `IngestionSummary`, `ParserOutput` (mirrors Python's `ParserResult`)
- `src/lib/ingestion/download-or-read.ts` — accept either `{ filePath: string }` (already-on-disk) or `{ url: string }` (fetch via `globalThis.fetch` — single retry). Returns `Result<Buffer>`.
- `src/lib/ingestion/run-parser.ts` — spawn the Python parser via `child_process.spawn`, pass `source_document_path` + `source_document_id` as args, parse JSON output from stdout. Returns `Result<ParserOutput>`.
- `src/lib/ingestion/persist-staging.ts` — given a `ParserOutput`, write a `parser_runs` row then bulk-insert `staging_indicator_values` rows. Composes Worker D's repositories.
- `src/lib/ingestion/index.test.ts` — integration tests with mocked pieces

Edit:
- `scrapers/nrb_ncpi/parser.py` — add a `__main__` entrypoint that takes argv, calls `parse()`, prints `ParserResult` as JSON to stdout (so Node can subprocess it). DO NOT change the `parse()` function itself.
- `scrapers/_common/types.py` — add a `to_json` method or a serializer helper on `ParserResult` so the `__main__` can dump it cleanly.

**Out of scope:**
- Schemas (locked)
- `package.json` (no Node deps to add — Node `child_process` is built-in)
- The validation job (Worker G — already done; we just call it)

## Context to Read First

1. `docs/DATA_PIPELINE.md` §"The Flow" — confirm the table-write order
2. `docs/PARSING_WORKFLOW.md` §"Subprocess contract" — if absent (it is), follow this brief
3. `src/lib/db/repositories/*` (Worker D output) — what to compose
4. `src/lib/storage/index.ts` (Worker B output) — `uploadSourceDocument` is your archive entry point
5. `src/lib/validation/index.ts` (Worker G output) — `validateParserRun` is your final step
6. `scrapers/nrb_ncpi/parser.py` (Worker C) — the function shape you're invoking
7. `scrapers/_common/types.py` — the dataclasses you're decoding

## Python __main__ shape

```python
# scrapers/nrb_ncpi/parser.py (append at bottom)
def _main() -> None:
    import sys, json
    if len(sys.argv) != 3:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)
    result = parse(sys.argv[1], sys.argv[2])
    json.dump(result.to_json_dict(), sys.stdout, default=str)

if __name__ == "__main__":
    _main()
```

Add `to_json_dict(self) -> dict` to `ParserResult` and `StagingRowDraft` in `_common/types.py`. Datetimes → ISO 8601 strings.

## Node ↔ Python subprocess contract

- Node spawns `python` (or `python3` on POSIX). For Windows, use `python` with shell:false.
- Pass two positional args: source-file path, source-document UUID.
- Parser writes ParserResult JSON to stdout, errors to stderr.
- Exit code 0 = success/partial parse (consumer reads stdout); exit code 2 = usage error; exit code 1 = catastrophic crash.
- Node parses stdout via `JSON.parse` then Zod-validates the shape into `ParserOutput`.

Zod schema on the Node side mirrors the Python dataclass exactly:

```typescript
const ParserOutputSchema = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string(),
  staging_rows: z.array(StagingRowDraftSchema),
  errors: z.array(ParserErrorSchema),
});
```

Where `StagingRowDraftSchema` parses the strings back into Dates.

## Orchestrator flow

```typescript
export async function ingestSource(input: IngestionInput): Promise<Result<IngestionSummary>> {
  // 1. Read or download file
  const fileBuf = await downloadOrRead(input);
  if (!fileBuf.ok) return fileBuf;

  // 2. Upload to Supabase Storage (idempotent)
  const stored = await uploadSourceDocument({ ... });
  if (!stored.ok) return stored;

  // 3. Insert source_documents row
  const sourceDoc = await insertSourceDocument({ ... });
  if (!sourceDoc.ok) return sourceDoc;

  // 4. Run Python parser
  const parserOutput = await runParser({ filePath, sourceDocumentId: sourceDoc.value.id });
  if (!parserOutput.ok) return parserOutput;

  // 5. Persist parser_runs + staging_indicator_values
  const parserRunId = await persistStaging({ parserOutput, sourceDocumentId: sourceDoc.value.id });
  if (!parserRunId.ok) return parserRunId;

  // 6. Validate (delegates to Worker G)
  const validation = await validateParserRun(parserRunId.value);
  if (!validation.ok) return validation;

  return ok({ sourceDocumentId, parserRunId, validation: validation.value });
}
```

Each step returns `Result<T>`; the orchestrator short-circuits on the first `err`. No `try/catch` blocks anywhere except boundaries (per CONVENTIONS.md).

## Test Cases

In `index.test.ts` (mocking storage, child_process, db, validation):
- Happy path with `filePath` input: file read → uploaded → row inserted → parser invoked → staging persisted → validation called once → returns ok with the summary
- Happy path with `url` input: fetch is called once; on 200 the body is uploaded
- Fetch fails with non-2xx: returns `err({ kind: 'External', service: 'http', ... })`
- Storage upload Conflict: returns the Conflict error
- Parser exit code 2: returns `err({ kind: 'External', service: 'python-parser', cause: 'usage error' })`
- Parser stdout JSON malformed: returns `err({ kind: 'ParseFailed', field: 'parser stdout', ... })`
- Validation returns block: orchestrator still returns ok (validation surfaced via summary); summary.validation.blocked > 0
- Same-document re-run: hash matches existing object → idempotent path; insertSourceDocument creates a new row pointing at the same storage object (per DATA_PIPELINE.md "rows are never updated")

## Acceptance Criteria

- [ ] Files in scope only (`src/lib/ingestion/*` + small `scrapers/` additions for `__main__`)
- [ ] `pnpm typecheck/lint/test` clean; existing tests still pass
- [ ] `pnpm exec tsx --eval 'console.log("ok")'` works as a smoke that subprocess works on this machine (optional sanity)
- [ ] No new Node dependencies
- [ ] `cd scrapers && python -m nrb_ncpi.parser <path> <id>` (or equivalent) emits valid JSON on stdout
- [ ] All DB ops composed via `safeQuery` (via repositories)
- [ ] No `as` casts outside `src/lib/external/*` (which doesn't exist yet — feel free to create it for the Zod-narrowed JSON parse if it makes sense)
- [ ] Diff under 500 non-test source lines

## What to Return

Standard 6-section report.
