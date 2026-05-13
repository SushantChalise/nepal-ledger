# Worker D — Repositories (typed data-access for source registry, source documents, indicators)

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** 300 lines (non-test source lines preferred metric — see ADR follow-up after Worker A)

---

## Goal

Build `src/lib/db/repositories/` — the typed data-access layer. Every repository function composes `safeQuery` from `src/lib/db/safe-query.ts` and returns `Result<T>` (per CONVENTIONS.md §"Repository pattern"). Feature code imports from this folder only; raw `db.*` calls in features are rejected at review.

Done = `pnpm typecheck`, `pnpm lint`, `pnpm test --run` green; the three repository modules exist with the API contract below; Vitest cases mock `db()` to verify the Result-wrapping happy and unhappy paths.

## Why

Day 11–28 milestone preparation. The parser pipeline writes through repositories, not raw Drizzle. The (future) admin page reads through repositories. The Pulse page reads through repositories. Without this layer the typed-error doctrine has a giant hole at the most error-prone surface (the DB).

## Scope Fence (files this worker MAY touch)

Create:
- `src/lib/db/repositories/source-registry.ts` — typed accessors for `source_registry`
- `src/lib/db/repositories/source-documents.ts` — typed accessors for `source_documents`
- `src/lib/db/repositories/indicators.ts` — typed accessors for `indicators` + `indicator_source_map`
- `src/lib/db/repositories/source-registry.test.ts`
- `src/lib/db/repositories/source-documents.test.ts`
- `src/lib/db/repositories/indicators.test.ts`
- `src/lib/db/repositories/index.ts` — barrel re-export

Edit:
- None outside `src/lib/db/repositories/`

**Out of scope:**
- `package.json` / lockfile
- Schemas (locked in PR #3)
- Anything else

## Context to Read First (in order)

1. `docs/CONVENTIONS.md` §"Repository pattern" — the canonical shape.
2. `docs/CONTEXT_RULES.md` Six Rules — especially Type-Driven and Scope-Fence.
3. `src/lib/errors.ts` — Result<T>, AppError variants. Pay particular attention to `NotFound`.
4. `src/lib/db/safe-query.ts` — every repository function composes this.
5. `src/lib/db/client.ts` — `db()` returns the singleton; only repositories call it.
6. `src/lib/db/schema/source-registry.ts` + `source-documents.ts` + `indicators.ts` — the tables you access.
7. `docs/DATA_PIPELINE.md` §"What Feature Code Sees" — the feature-side example you're delivering on.

## API Contract (target shape)

```typescript
// src/lib/db/repositories/source-registry.ts
export async function findSourceById(sourceId: string): Promise<Result<SourceRegistryRow>>;
export async function listActiveSources(): Promise<Result<SourceRegistryRow[]>>;
export async function upsertSource(input: NewSourceRegistryRow): Promise<Result<SourceRegistryRow>>;
export async function markVerified(sourceId: string, atIso: string): Promise<Result<SourceRegistryRow>>;

// src/lib/db/repositories/source-documents.ts
export async function insertSourceDocument(input: NewSourceDocumentRow): Promise<Result<SourceDocumentRow>>;
export async function findSourceDocumentById(id: string): Promise<Result<SourceDocumentRow>>;
export async function findSourceDocumentByHash(sha256: string): Promise<Result<SourceDocumentRow | null>>; // hash-based lookups expect null-as-success when not found
export async function listSourceDocumentsForSource(sourceId: string, limit: number): Promise<Result<SourceDocumentRow[]>>;

// src/lib/db/repositories/indicators.ts
export async function findIndicatorBySlug(slug: string): Promise<Result<IndicatorRow>>;
export async function listIndicatorsByCategory(category: IndicatorCategory): Promise<Result<IndicatorRow[]>>;
export async function linkIndicatorToSource(indicatorId: string, sourceId: string, notes?: string): Promise<Result<IndicatorSourceMapRow>>;
```

Where `findX` distinguishes "row not found = error" (return `NotFound`) from "hash-existence check" (return `Result<T | null>` — null is a successful negative answer, not an error). This nuance is critical for content-addressed dedup in the storage layer.

## Test pattern (mocking db())

Use `vi.mock('@/lib/db/client', ...)` to replace `db()` with a stub Drizzle-like object. Each test asserts:

1. Happy path: stub returns rows; repo returns `ok(value)`
2. Empty path for `findX`: stub returns undefined/empty; repo returns `err({ kind: 'NotFound', resource, id })`
3. DB throws: stub rejects; repo returns the appropriate `err(...)` per `safeQuery`'s translation
4. `findSourceDocumentByHash` returns `ok(null)` when no row matches (not an error)
5. `upsertSource` happy path returns the row with the input merged

You don't need real Postgres. The point is the `Result<T>` shape and the error mapping.

## Acceptance Criteria

- [ ] Files in scope only
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` — new repository tests pass; existing tests still pass
- [ ] No new dependencies
- [ ] No `as` casts outside the sanctioned locations
- [ ] No raw `db().*` calls visible to feature-layer imports
- [ ] Every public function returns `Result<T>` or `Result<T[]>` or `Result<T | null>`
- [ ] Diff under 300 non-test lines (tests in addition)
- [ ] `findX` returns `NotFound` with the literal resource name and the queried id

## What to Return

1. Summary of changes (≤10 bullets)
2. Acceptance-criteria checklist with checkmarks
3. `git diff --stat main`
4. Any deviations + rationale
5. Open questions
6. Conventional-commit suggestion
