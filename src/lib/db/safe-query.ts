/**
 * Database boundary wrapper.
 *
 * Every repository function in `src/lib/db/repositories/*` runs its Drizzle
 * call through `safeQuery`. This converts Drizzle / postgres-js exceptions
 * into typed AppError variants — never letting a raw DB exception bubble up
 * into feature code where it would force ad-hoc try/catch and defeat the
 * typed-error doctrine.
 *
 * Reference: docs/CONVENTIONS.md §"Repository pattern".
 */

import { DrizzleError } from 'drizzle-orm';
import postgres from 'postgres';

// `postgres` (v3) attaches its error class to the default export rather than
// exposing a named `PostgresError` export. The named-import form happens to
// work under Vitest's CJS interop but Turbopack's strict ESM analysis rejects
// it ("export PostgresError doesn't exist"), which 500s every RSC page that
// touches a repository. Destructure the value from the default; derive the
// instance type from it (no separate named type export exists either).
const { PostgresError } = postgres;
type PostgresError = InstanceType<typeof PostgresError>;

import { err, ok, type AppError, type Result } from '@/lib/errors';

/**
 * Wrap a database operation. Returns ok(value) on success, err(AppError) on
 * any DB exception. Repository callers compose with their own NotFound /
 * Validation logic on top of the Result.
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
    // Postgres SQLSTATE classification — codes are stable across Postgres
    // versions. Reference: https://www.postgresql.org/docs/current/errcodes-appendix.html
    if (e.code === '23505') {
      return { kind: 'ConstraintViolation', constraint: 'unique', detail: detailOf(e) };
    }
    if (e.code === '23503') {
      return { kind: 'ConstraintViolation', constraint: 'foreign_key', detail: detailOf(e) };
    }
    if (e.code === '23502') {
      return { kind: 'ConstraintViolation', constraint: 'not_null', detail: detailOf(e) };
    }
    if (e.code === '23514') {
      return { kind: 'ConstraintViolation', constraint: 'check', detail: detailOf(e) };
    }
    if (e.code?.startsWith('08')) {
      // 08000–08P01: connection exceptions.
      return { kind: 'DatabaseUnavailable', detail: e.message };
    }
    if (e.code === '57014') {
      return { kind: 'QueryFailed', detail: 'statement timeout' };
    }
    return { kind: 'QueryFailed', detail: e.message };
  }
  if (e instanceof DrizzleError) {
    // DrizzleError.cause holds the underlying postgres-js exception — recurse
    // so SQLSTATE classification still happens, and so connection failures
    // (e.g. EAI_AGAIN, ECONNREFUSED) surface as DatabaseUnavailable instead of
    // being lost in a `Failed query: …` wrapper.
    const cause = (e as DrizzleError & { cause?: unknown }).cause;
    if (cause !== undefined && cause !== e) return toAppError(cause);
    return { kind: 'QueryFailed', detail: e.message };
  }
  if (e instanceof Error) {
    const code = (e as Error & { code?: string }).code;
    if (isConnectionErrorCode(code)) {
      return { kind: 'DatabaseUnavailable', detail: `${code}: ${e.message}` };
    }
    // postgres-js / drizzle wrap the underlying socket failure: the thrown
    // error's message is "Failed query: …" and the real connection code
    // (ECONNRESET, EPIPE, …) lives on `.cause`, NOT the top level. That wrapper
    // is not always a DrizzleError instance, so the cause-recursion in the
    // DrizzleError branch above can miss it and the error lands here. Inspect
    // `.cause` so a mid-pipeline connection reset surfaces as the (retryable)
    // DatabaseUnavailable rather than an opaque QueryFailed. Observed live: a
    // ~0.1%/query ECONNRESET over Supabase's pooler, which over a multi-hundred
    // round-trip ingest reliably aborted the whole run.
    const cause = (e as Error & { cause?: unknown }).cause;
    if (cause !== undefined && cause !== e) {
      const causeCode = (cause as { code?: string }).code;
      if (isConnectionErrorCode(causeCode)) {
        return { kind: 'DatabaseUnavailable', detail: `${causeCode}: ${e.message}` };
      }
    }
    return { kind: 'QueryFailed', detail: e.message };
  }
  return { kind: 'QueryFailed', detail: String(e) };
}

/**
 * Node/libuv socket-level error codes that mean "the connection failed", as
 * opposed to "the query was rejected". These map to `DatabaseUnavailable`
 * (transient, safe to retry) rather than `QueryFailed` (the SQL itself is at
 * fault). 08xxx SQLSTATEs are handled separately on `PostgresError`.
 */
const CONNECTION_ERROR_CODES: ReadonlySet<string> = new Set([
  'EAI_AGAIN',
  'ENOTFOUND',
  'ECONNREFUSED',
  'ETIMEDOUT',
  'ECONNRESET',
  'EPIPE',
]);

function isConnectionErrorCode(code: string | undefined): boolean {
  return code !== undefined && CONNECTION_ERROR_CODES.has(code);
}

function detailOf(e: PostgresError): string {
  // `detail` is the rich Postgres diagnostic; fall back to `message`.
  // Cast is a sanctioned post-Zod / DB-boundary narrowing per CONVENTIONS.md.
  const withDetail = e as PostgresError & { detail?: string };
  return withDetail.detail ?? e.message;
}
