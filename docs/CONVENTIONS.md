# Code Conventions

The opinionated rules that every line of code follows. Workers read this before writing.

---

## TypeScript

### Strict mode, hard

`tsconfig.json` enables:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "exactOptionalPropertyTypes": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true
  }
}
```

### Forbidden

- `any` — banned by ESLint
- `@ts-ignore` — banned (use `@ts-expect-error` with a comment if absolutely necessary)
- `as` casts — banned **except in the four sanctioned cases below**
- `as unknown as X` double-cast — banned absolutely, no exceptions
- Non-null assertion `!` — banned except in tests
- Type assertion on object literals — banned (use `satisfies` instead)

### Sanctioned `as` Cast Escape Hatches

In real TypeScript + data-viz + parsed-PDF + third-party-SDK code, some narrowing is unavoidable. Four sanctioned locations:

1. **After Zod validation at external boundaries.** Inside the same function as the `.parse()` call. The cast is the documented bridge between unknown input and validated type.
2. **DOM narrowing.** When TypeScript can't narrow a DOM event target. Local, brief, no `unknown` chain.
3. **Visualization library adapter boundaries** — files under `src/lib/viz/adapters/*`. D3 and Recharts have looser typings than ours; adapters bridge them.
4. **Third-party SDK response adapters** — files under `src/lib/external/*`. Resend, Supabase JS client, Sentry — their response types occasionally need bridging.

**Every cast in cases 3 and 4 lives in an adapter file with a co-located test that asserts the contract.** No casts in feature code; ever. If a worker thinks they need one outside the four cases, they stop and surface to Mother.

### Required

- All exported functions have explicit return types
- All Zod schemas are exported alongside their inferred type
- All discriminated unions use a literal `kind` or `type` field
- All enums are TypeScript const unions, not `enum` keyword

---

## Validation: Zod at Boundaries

Every external input passes through a Zod schema:

```typescript
// src/features/pulse/schemas.ts
import { z } from 'zod';

export const NcpiRowSchema = z.object({
  category: z.string().min(1),
  weight: z.number().min(0).max(100),
  value: z.number().nonnegative(),
  period: z.string().regex(/^\d{4}\/\d{2}-(Mar|Apr|...)/),
  source_document_id: z.string().uuid(),
});

export type NcpiRow = z.infer<typeof NcpiRowSchema>;
```

What counts as a boundary:
- HTTP request body
- HTTP response from a third-party API
- CLI argument
- Environment variable (`env-schema` pattern)
- Parsed file (CSV, JSON, PDF table)
- Database row read into application code (Drizzle handles this, but Zod re-validates if data crossed an untrusted source)

Internal function calls do NOT re-validate. Once inside the application boundary, types are trusted.

---

## Folder Structure

### Feature-domain, not technical layers

```
src/features/
├── verdict/                  # Vertical slice
│   ├── CLAUDE.md             # Feature-local context for agents
│   ├── components/           # UI
│   │   ├── VerdictCard.tsx
│   │   └── VerdictBody.tsx
│   ├── server/               # Server-only: data access, mutations
│   │   ├── get-current-verdict.ts
│   │   └── publish-verdict.ts
│   ├── schemas.ts            # Zod schemas
│   ├── types.ts              # Derived types
│   └── tests/                # Co-located tests
│       ├── verdict.test.ts
│       └── fixtures.ts
├── pulse/
├── fact-ledger/
└── ...
```

**Rule:** A worker working on `verdict` touches only `src/features/verdict/**` (plus shared files explicitly listed in the scope fence).

### Shared code lives in `src/lib/`

```
src/lib/
├── db/
│   ├── client.ts             # Drizzle client singleton
│   ├── schema/               # Drizzle schemas (one file per table)
│   │   ├── indicators.ts
│   │   ├── source-documents.ts
│   │   └── fact-ledger.ts
│   └── repositories/         # Typed data access — only path features use
│       ├── indicators.ts
│       └── fact-ledger.ts
├── r2/
│   └── client.ts             # R2 S3-compatible client
├── resend/
│   └── client.ts
├── env.ts                    # Zod-validated environment variables
├── errors.ts                 # Typed error definitions
└── utils.ts                  # `cn()` and other tiny utilities
```

Features import from `lib/`, never the reverse.

---

## React + Next.js

### Server Components by default

Pages and most components are Server Components. `'use client'` is added ONLY when:

- The component uses `useState`, `useEffect`, `useReducer`, `useContext`
- The component uses browser APIs (`window`, `document`, `localStorage`)
- The component renders interactive third-party widgets (charts that need DOM access — Recharts wrappers go here)

Drop the `'use client'` directive as deep into the tree as possible. The page itself stays a Server Component; only the interactive island is a Client Component.

### File naming

| Type | Naming |
|------|--------|
| Component | `PascalCase.tsx` (one component per file) |
| Hook | `use-kebab-case.ts` |
| Server action | `kebab-case.ts` (function inside is `verbNoun`) |
| Schema / type module | `kebab-case.ts` |
| Test | `<name>.test.ts` (Vitest) or `<name>.spec.ts` (Playwright) |
| Folder | `kebab-case/` |

### Component shape

```typescript
// src/features/pulse/components/KpiCard.tsx
import { cn } from '@/lib/utils';

type Direction = 'up' | 'down' | 'flat';

type KpiCardProps = {
  label: string;
  value: string;
  direction: Direction;
  confidence: 'A' | 'B' | 'C';
  source: string;
  className?: string;
};

export function KpiCard({ label, value, direction, confidence, source, className }: KpiCardProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-4', className)}>
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      <DirectionIndicator direction={direction} />
      <ConfidenceBadge level={confidence} source={source} />
    </div>
  );
}
```

- Props type defined inline as `type <Component>Props`
- No `React.FC` (verbose, doesn't add value)
- No default exports for components (named export, easier refactor)
- `cn()` from `@/lib/utils` for conditional classes

---

## Error Handling

### Typed errors, not thrown strings

```typescript
// src/lib/errors.ts
export type AppError =
  | { kind: 'NotFound'; resource: string; id: string }
  | { kind: 'Validation'; field: string; reason: string }
  | { kind: 'External'; service: string; cause: string }
  | { kind: 'Conflict'; reason: string };

export type Result<T> = { ok: true; value: T } | { ok: false; error: AppError };

export const ok = <T>(value: T): Result<T> => ({ ok: true, value });
export const err = (error: AppError): Result<never> => ({ ok: false, error });
```

Functions that can fail return `Result<T>`. No throwing.

```typescript
export async function getIndicatorBySlug(slug: string): Promise<Result<Indicator>> {
  const row = await db.query.indicators.findFirst({ where: eq(indicators.slug, slug) });
  if (!row) return err({ kind: 'NotFound', resource: 'indicator', id: slug });
  return ok(row);
}
```

### Forbidden patterns

```typescript
// BAD — swallows error, returns nothing useful
try {
  return await fetchData();
} catch {
  return null;
}

// BAD — string thrown
throw 'something went wrong';

// BAD — silent fallback masks broken behavior
return data?.value ?? 0;  // if 0 is meaningful, this is a bug magnet
```

### Allowed patterns

```typescript
// OK — boundary translation: external throws → typed result
try {
  const data = await fetch(url).then(r => r.json());
  return ok(externalSchema.parse(data));
} catch (e) {
  return err({ kind: 'External', service: 'NRB', cause: String(e) });
}
```

The only `try/catch` blocks in the codebase are at external boundaries.

---

## Database (Drizzle)

### Schema is the source of truth

```typescript
// src/lib/db/schema/indicators.ts
import { pgTable, uuid, text, timestamp, numeric, integer } from 'drizzle-orm/pg-core';

export const indicators = pgTable('indicators', {
  id: uuid('id').primaryKey().defaultRandom(),
  slug: text('slug').notNull().unique(),
  nameEn: text('name_en').notNull(),
  nameNe: text('name_ne'),
  category: text('category').notNull(),
  unit: text('unit').notNull(),
  frequency: text('frequency').notNull(),  // 'monthly' | 'quarterly' | 'annual'
  sourceAgency: text('source_agency').notNull(),
  parentIndicatorId: uuid('parent_indicator_id'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type Indicator = typeof indicators.$inferSelect;
export type NewIndicator = typeof indicators.$inferInsert;
```

### Migrations are commit-controlled

```bash
pnpm drizzle-kit generate   # generates SQL migration
pnpm drizzle-kit migrate    # applies to dev DB
```

Migration files in `src/lib/db/migrations/` are committed to git. They never get edited after merge — new changes = new migration.

### Repository pattern

Repositories wrap Drizzle calls in a `safeQuery` boundary that converts Drizzle/Postgres exceptions to typed `AppError` variants. Without this, database errors throw uncaught and break the typed-error doctrine.

```typescript
// src/lib/db/safe-query.ts
import type { AppError, Result } from '@/lib/errors';
import { err, ok } from '@/lib/errors';
import { DrizzleError } from 'drizzle-orm';
import { PostgresError } from 'postgres';

/**
 * Single DB boundary wrapper. Use it in every repository function that
 * touches the database. Converts Drizzle / postgres-js exceptions to
 * typed AppError variants.
 */
export async function safeQuery<T>(op: () => Promise<T>): Promise<Result<T>> {
  try {
    return ok(await op());
  } catch (e) {
    return err(toAppError(e));
  }
}

function toAppError(e: unknown): AppError {
  if (e instanceof PostgresError) {
    // Postgres SQLSTATE classification
    if (e.code === '23505') return { kind: 'ConstraintViolation', constraint: 'unique', detail: e.detail ?? e.message };
    if (e.code === '23503') return { kind: 'ConstraintViolation', constraint: 'foreign_key', detail: e.detail ?? e.message };
    if (e.code === '23502') return { kind: 'ConstraintViolation', constraint: 'not_null', detail: e.detail ?? e.message };
    if (e.code?.startsWith('08')) return { kind: 'DatabaseUnavailable', detail: e.message };
    if (e.code === '57014') return { kind: 'QueryFailed', detail: 'statement timeout' };
    return { kind: 'QueryFailed', detail: e.message };
  }
  if (e instanceof DrizzleError) return { kind: 'QueryFailed', detail: e.message };
  return { kind: 'QueryFailed', detail: e instanceof Error ? e.message : String(e) };
}
```

Add to the `AppError` union in `src/lib/errors.ts`:

```typescript
| { kind: 'DatabaseUnavailable'; detail: string }
| { kind: 'ConstraintViolation'; constraint: 'unique' | 'foreign_key' | 'not_null' | 'check'; detail: string }
| { kind: 'QueryFailed'; detail: string }
| { kind: 'MigrationMismatch'; detail: string }
```

Then repository functions:

```typescript
// src/lib/db/repositories/indicators.ts
import { db } from '@/lib/db/client';
import { indicators } from '@/lib/db/schema/indicators';
import { eq } from 'drizzle-orm';
import { ok, err, type Result } from '@/lib/errors';
import { safeQuery } from '@/lib/db/safe-query';
import type { Indicator } from '@/lib/db/schema/indicators';

export async function findIndicatorBySlug(slug: string): Promise<Result<Indicator>> {
  const queried = await safeQuery(() =>
    db.query.indicators.findFirst({ where: eq(indicators.slug, slug) })
  );
  if (!queried.ok) return queried;
  if (!queried.value) return err({ kind: 'NotFound', resource: 'indicator', id: slug });
  return ok(queried.value);
}
```

- Repositories are the ONLY place that imports from `@/lib/db/schema`
- Every database call goes through `safeQuery`
- Features import from `@/lib/db/repositories`, never direct Drizzle calls
- Every repository function returns `Result<T>` or `Result<T[]>`

---

## Server Actions

Mutations are Server Actions. They are typed end-to-end:

```typescript
// src/features/fact-ledger/server/submit-challenge.ts
'use server';

import { z } from 'zod';
import { ok, err, type Result } from '@/lib/errors';
import { db } from '@/lib/db/client';
import { factLedgerChallenges } from '@/lib/db/schema/fact-ledger';

const SubmitChallengeInput = z.object({
  claimId: z.string().uuid(),
  email: z.string().email(),
  source: z.string().url().optional(),
  message: z.string().min(20).max(2000),
});

export async function submitChallenge(input: z.infer<typeof SubmitChallengeInput>): Promise<Result<{ id: string }>> {
  const parsed = SubmitChallengeInput.safeParse(input);
  if (!parsed.success) {
    return err({ kind: 'Validation', field: parsed.error.issues[0].path.join('.'), reason: parsed.error.issues[0].message });
  }
  const [row] = await db.insert(factLedgerChallenges).values({ ...parsed.data, status: 'pending' }).returning({ id: factLedgerChallenges.id });
  return ok({ id: row.id });
}
```

Client components call server actions directly; types flow.

---

## Testing

### What gets tested

1. **Pure logic** — utility functions, schema validators, formula computations (e.g., basket inflation calculation): Vitest, mocked nothing.
2. **Repositories** — every repository function: Vitest + integration DB (Supabase local).
3. **Server actions** — every mutation: Vitest.
4. **Critical E2E flows** — Pulse loads, Money Map renders, calculator computes correctly: Playwright.

### What does NOT get tested

- Tailwind classes
- One-line JSX components
- Trivial getters
- Third-party library behavior

### Test file shape

```typescript
// src/features/pulse/tests/compute-basket.test.ts
import { describe, it, expect } from 'vitest';
import { computeBasket } from '../server/compute-basket';

describe('computeBasket', () => {
  it('returns total cost for an urban family-of-four archetype', () => {
    const result = computeBasket({
      archetype: 'urban-family-4',
      ncpiPeriod: '2082-83-chait',
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.totalNpr).toBeGreaterThan(0);
      expect(result.value.totalNpr).toBeLessThan(50000);
    }
  });
});
```

- `describe` per function
- `it` per scenario
- Use the `Result` discriminant correctly in assertions
- No global mocks; fixtures co-located

---

## Comments

### Default: no comments

Identifiers do the WHAT. Code does the HOW. Comments are for the WHY that the code cannot express.

### When a comment IS warranted

- A constraint that's not obvious from local code: `// per ADR-0007: source documents are immutable`
- A workaround for a known bug: `// workaround for Next.js issue #12345 (App Router cache key collision)`
- A subtle invariant: `// this MUST run after fact-ledger schema is loaded`
- A performance note that affects how someone might change it: `// kept O(n^2) intentionally — n is always < 50 and clarity wins`

### Comments that get rejected in review

- Restating the code: `// loop through items`
- Status: `// TODO: refactor later`
- Authorship: `// Daisy added this on 2026-03-05`
- Issue references that rot: `// see ticket NEPAL-1234`
- The current task: `// added for the inflation calculator story`

---

## Imports

```typescript
// 1. Standard library / external libraries
import { useEffect, useState } from 'react';
import { z } from 'zod';

// 2. Absolute project imports (alias)
import { db } from '@/lib/db/client';
import { Indicator } from '@/lib/db/schema/indicators';

// 3. Relative project imports
import { KpiCard } from './KpiCard';
import type { PulseSummary } from './types';
```

Three groups, separated by blank line. `import type` for type-only imports.

Path alias: `@/*` → `src/*` (configured in `tsconfig.json` and `next.config.ts`).

---

## Naming

| Thing | Casing | Example |
|-------|--------|---------|
| Type | PascalCase | `Indicator`, `KpiCardProps` |
| Component | PascalCase | `KpiCard`, `VerdictBody` |
| Function | camelCase | `findIndicatorBySlug` |
| Variable | camelCase | `currentMonth`, `factLedgerClaim` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_BASKET_ITEMS`, `DEFAULT_LOCALE` |
| Hook | `use` prefix, camelCase | `useDebouncedValue` |
| Boolean | `is`, `has`, `can`, `should` prefix | `isLoading`, `hasNextPage` |
| Folder | kebab-case | `src/features/fact-ledger` |
| File (code) | kebab-case | `submit-challenge.ts` |
| File (component) | PascalCase matching component | `KpiCard.tsx` |
| Database table | snake_case plural | `indicator_values` |
| Database column | snake_case | `created_at` |
| Drizzle TS field | camelCase | `createdAt` |

---

## Forbidden Dependencies (Without ADR)

These are commonly-reached-for libraries that an ADR must justify before adding:

- `lodash` — most of it is in native JS now; we don't add 70KB for `debounce`
- `moment` — use `date-fns` if dates need anything beyond `Intl.DateTimeFormat`
- `axios` — `fetch` is fine; if streaming needed, ADR
- `redux`, `zustand`, `jotai`, `valtio` — server-first; client state is rare and small
- `formik` — React Hook Form is the choice (already approved)
- A second charting library — Recharts and Tremor are it
- A second component library — shadcn primitives only
- A second CSS framework — Tailwind only

If a worker thinks they need one of these → stop and surface to Mother.

---

## ESLint + Prettier

ESLint enforces the typed-error rules, the no-`any` rule, the no-default-export-for-components rule, and the conventional-commits-pr-title rule.

Prettier formats — single source of truth, no debate. Settings:
- Single quotes
- Trailing commas (all)
- 100-char width
- Tabs: no (2 spaces)
- Semicolons: yes

Both run on pre-commit via `lint-staged`.
