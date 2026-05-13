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
import { PostgresError } from 'postgres';

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
    return { kind: 'QueryFailed', detail: e.message };
  }
  if (e instanceof Error) {
    return { kind: 'QueryFailed', detail: e.message };
  }
  return { kind: 'QueryFailed', detail: String(e) };
}

function detailOf(e: PostgresError): string {
  // `detail` is the rich Postgres diagnostic; fall back to `message`.
  // Cast is a sanctioned post-Zod / DB-boundary narrowing per CONVENTIONS.md.
  const withDetail = e as PostgresError & { detail?: string };
  return withDetail.detail ?? e.message;
}
