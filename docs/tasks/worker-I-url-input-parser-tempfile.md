# Worker I — URL-input parser temp-file lifecycle

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** soft 300 / hard 500 code-only non-test source lines (per ADR-0007 + 2026-05-14 amendment)
**Status:** Filed; not yet dispatched. Low priority — Year 1 ingests are all `{filePath}` inputs.

---

## Goal

Close the URL-input gap in `src/lib/ingestion/` (Worker H output, PR #29). Today when `ingestSource({ url })` is called:

1. Bytes are fetched and archived to Supabase Storage via `uploadSourceDocument`
2. A `source_documents` row is written
3. The Python parser is invoked with the **original URL** as `source_file_path`
4. The parser fails-fast because it reads local files only

This works for `{ filePath }` inputs (the path is local; archive happens but the parser also reads from the original path). It breaks for `{ url }` inputs.

The proper fix: when the input is `{ url }`, after archiving, **download the archived storage object to a temp file**, pass that path to the parser, then clean up the temp file.

Done = `ingestSource({ url })` runs end-to-end against a fixture URL (mocked via the existing `globalThis.fetch` seam + a mocked storage `downloadSourceDocument`) and produces the same `IngestionSummary` shape as the `{ filePath }` path. The temp file is deleted on every exit (success, parser failure, validation error).

## Why this is its own brief

The fix touches subprocess invocation timing, temp-file lifecycle (Windows + POSIX cleanup quirks), and a new storage download path. Bundling it into Worker H would have pushed that diff over the cap. Year 1 ingests are all `{filePath}` so non-blocking.

## Scope Fence

Edit:
- `src/lib/ingestion/index.ts` — branch on input shape before calling `run-parser`; manage temp-file lifecycle
- `src/lib/ingestion/run-parser.ts` — accept a `localPath` that may be a temp file; no other change
- `src/lib/ingestion/types.ts` — extend `IngestionInput` if needed (likely a no-op; the union already covers it)
- `src/lib/ingestion/index.test.ts` — add 4+ tests covering URL path

Create:
- `src/lib/storage/download-to-temp.ts` (or extend `src/lib/storage/index.ts`) — `downloadSourceDocumentToTemp(sourceDocId): Promise<Result<{ path: string; cleanup: () => Promise<void> }>>`

**Out of scope:**
- The Python parser (unchanged)
- The storage wrapper's public surface beyond the new function
- Validation job (unchanged)

## Behavior Specifications

**Temp file lifecycle:**
- Use `os.tmpdir()` + `crypto.randomUUID()` for the path. Suffix `.bin` (parser doesn't care about extension; it reads bytes).
- On Windows, hold the file handle open during parser invocation only if necessary; otherwise close immediately after write (avoids EBUSY on cleanup).
- Cleanup runs in a `finally` block that swallows ENOENT (file already gone) but logs anything else to `console.error` and surfaces in the `IngestionSummary.warnings[]`.
- On parser timeout or kill, cleanup still runs.

**Failure modes to test:**
1. URL input, archive succeeds, download-to-temp fails → return `Result.err`, no parser invoked, no temp file leaked
2. URL input, archive succeeds, download succeeds, parser fails → return parser error, temp file cleaned
3. URL input, archive succeeds, download succeeds, parser succeeds, validation fails → return validation error, temp file cleaned
4. URL input, archive succeeds, download succeeds, parser succeeds, validation succeeds → return full `IngestionSummary`, temp file cleaned

## Acceptance Criteria

- [ ] Files in scope only
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test --run` clean
- [ ] At least 4 new tests covering the failure modes above
- [ ] No temp file leaks across any test run (use `afterEach` cleanup assertion)
- [ ] Windows-safe (no file-locking issues; explicit close before unlink)
- [ ] Under 500 code-only non-test source lines

## What to Return

Standard 6-section report (summary, checklist, diff stat, deviations, open questions, commit message).

Do NOT commit, push, or open a PR — Mother integrates.
