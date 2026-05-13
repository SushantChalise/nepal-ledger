# Worker B — Supabase Storage Client (with R2 migration seam)

**Spawn type:** `general-purpose`
**Plan mode:** required (touches >3 files)
**Diff cap:** 300 lines

---

## Goal

Build `src/lib/storage/` — the typed wrapper around Supabase Storage that the scraper pipeline uses to archive source documents. Per ADR-0004, Supabase Storage is Year 1; the wrapper exposes an interface that lets us swap to R2 in Phase 2 with a one-line client change.

Done = `pnpm typecheck/lint/test` green; the module exposes `uploadSourceDocument`, `downloadSourceDocument`, `getPublicUrl`, `sha256OfBuffer`; all return `Result<T>`; tests exercise the SHA-256 path and the error-translation cases against a mocked client.

## Why

Day 11–28 milestone preparation. The first ingestion pipeline (NRB-NCPI parser) writes source files to Supabase Storage with a content-addressed key. Without this wrapper the parser would either reach for the raw Supabase SDK (defeating the typed-error doctrine) or invent its own. The wrapper is also what the Fact Ledger uses to mint public URLs for claim citations.

## Scope Fence (files this worker MAY touch)

Create:
- `src/lib/storage/index.ts` — public surface
- `src/lib/storage/supabase-client.ts` — Supabase JS client singleton (server-only)
- `src/lib/storage/upload.ts` — `uploadSourceDocument({ sourceId, downloadedAtIso, fileName, body, contentType })`
- `src/lib/storage/download.ts` — `downloadSourceDocument(storageKey)`
- `src/lib/storage/url.ts` — `getPublicUrl(storageKey)` and `getSignedUrl(storageKey, expiresSec)`
- `src/lib/storage/hash.ts` — `sha256OfBuffer(buf)` and `sha256OfStream` if needed
- `src/lib/storage/types.ts` — `StorageObject`, `UploadResult`, `DownloadResult`
- `src/lib/storage/index.test.ts` — Vitest with mocked supabase-js client

Edit:
- None outside `src/lib/storage/`

**Out of scope (must NOT touch):**
- `package.json` / `pnpm-lock.yaml` — Mother has already installed `@supabase/supabase-js` and `crypto` is a Node built-in
- Schema files (locked in PR #3)
- `next.config.ts`, CI workflows, anything else

## Context to Read First (in order)

1. `docs/decisions/0004-supabase-storage-instead-of-r2.md` — the constraint and the migration trigger.
2. `docs/CLOUD_STACK.md` §"Supabase Storage" — quota + key format.
3. `docs/DATA_PIPELINE.md` §"source_documents" — the row shape the wrapper must produce (key format `<source-id>/<yyyy-mm-dd>/<filename>`, hash, size, content type).
4. `docs/SOURCE_REGISTRY.md` §"Archive policy".
5. `docs/CONVENTIONS.md` §"Error Handling" — every wrapper function returns `Result<T>`.
6. `src/lib/errors.ts` and `src/lib/env.ts` — the AppError union (External variant fits Supabase Storage failures) and the validated env.
7. `src/lib/db/schema/source-documents.ts` — confirm the field names you'll feed.

## API Contract (target shape)

```typescript
// src/lib/storage/types.ts
export type StorageObject = {
  storageKey: string;
  fileHashSha256: string;
  fileSizeBytes: number;
  contentType: string;
  storageProvider: 'supabase';
};

export type UploadInput = {
  sourceId: string;
  downloadedAtIso: string;   // ISO 8601; the wrapper extracts yyyy-mm-dd for the key prefix
  fileName: string;
  body: Buffer | Uint8Array;
  contentType: string;
};

// src/lib/storage/index.ts
export async function uploadSourceDocument(input: UploadInput): Promise<Result<StorageObject>>;
export async function downloadSourceDocument(storageKey: string): Promise<Result<{ body: Buffer; contentType: string; sizeBytes: number }>>;
export function getPublicUrl(storageKey: string): string;          // sync; just composes URL
export async function getSignedUrl(storageKey: string, expiresSec: number): Promise<Result<string>>;
export function sha256OfBuffer(buf: Buffer | Uint8Array): string;  // hex, lowercase
```

## Key-format rules (enforce in `upload.ts`)

- `storageKey` = `${sourceId}/${yyyy-mm-dd}/${fileName}`
- `fileName` is sanitized: replace any char outside `[A-Za-z0-9._-]` with `_`
- If a file already exists at the same key with the same hash, treat that as success (idempotent re-upload) and still return `Result.ok` with the existing object's metadata. If the same key exists with a *different* hash, return `Result.err({ kind: 'Conflict', reason: 'storage key collision with different content' })`.
- `sourceId` is validated to match `/^[a-z0-9][a-z0-9-]{2,}$/`; reject `Validation` if not.

## Error translation

- Supabase upload error → `{ kind: 'External', service: 'supabase-storage', cause: <message> }`
- Network/timeout → same as above (Supabase JS surfaces these as `Error` instances)
- Invalid input (bad sourceId, empty body) → `{ kind: 'Validation', field: <field>, reason: <reason> }`

NEVER throw. NEVER return null. Always `Result<T>`.

## Required Test Cases

Mock the Supabase JS client (don't call the network). Tests run in Node Vitest, no live Supabase needed.

- Happy-path upload: returns ok with the expected `StorageObject` shape; hash matches input
- Key-collision-same-hash: idempotent ok
- Key-collision-different-hash: returns `Conflict`
- Validation: invalid `sourceId` → `Validation` error
- Validation: empty body → `Validation` error
- Sanitization: filename with spaces / unicode → underscored in the storage key
- `sha256OfBuffer` is deterministic and matches a known hex fixture

## Acceptance Criteria

- [ ] Files in scope only
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` — new tests pass, existing 20 still pass
- [ ] No new dependencies (the Supabase JS client + Node `crypto` are enough)
- [ ] No `as` casts outside `src/lib/external/*` — but this file IS under `src/lib/storage/` not `src/lib/external/`. If you need a Supabase response cast, surface to Mother before adding it; otherwise lean on `z.infer` types from a small Zod schema validating the Supabase response shape.
- [ ] No `any`, no `@ts-ignore`
- [ ] Diff under 300 lines
- [ ] Module is server-only (`import 'server-only'` in `supabase-client.ts`)

## What to Return

1. Summary of changes (≤10 bullets)
2. Acceptance-criteria checklist with checkmarks
3. `git diff --stat main` output
4. Any deviations from this brief and why
5. Open questions
6. Conventional-commit suggestion
