/**
 * Typed errors and Result<T> for Nepal Ledger.
 *
 * Functions that can fail return Result<T>; they never throw strings, never
 * return null on failure, never swallow exceptions. The only place throws are
 * caught is at an external boundary (HTTP, DB, file I/O, third-party SDK),
 * where they are translated into AppError variants — see
 * `src/lib/db/safe-query.ts` for the DB-boundary translator and
 * `docs/CONVENTIONS.md` §"Error Handling" for the doctrine.
 */

export type AppError =
  | { kind: 'NotFound'; resource: string; id: string }
  | { kind: 'Validation'; field: string; reason: string }
  | { kind: 'External'; service: string; cause: string }
  | { kind: 'Conflict'; reason: string }
  | { kind: 'DatabaseUnavailable'; detail: string }
  | {
      kind: 'ConstraintViolation';
      constraint: 'unique' | 'foreign_key' | 'not_null' | 'check';
      detail: string;
    }
  | { kind: 'QueryFailed'; detail: string }
  | { kind: 'MigrationMismatch'; detail: string }
  | { kind: 'ParseFailed'; field: string; reason: string };

export type Result<T> = { ok: true; value: T } | { ok: false; error: AppError };

export const ok = <T>(value: T): Result<T> => ({ ok: true, value });

export const err = (error: AppError): Result<never> => ({ ok: false, error });

/**
 * Convert an AppError into a stable string for logs / Sentry breadcrumbs.
 * Never use this for user-facing copy — UI surfaces should render based on
 * `kind` and pick the appropriate translated message.
 */
export function formatAppError(e: AppError): string {
  switch (e.kind) {
    case 'NotFound':
      return `NotFound: ${e.resource} (${e.id})`;
    case 'Validation':
      return `Validation: ${e.field} — ${e.reason}`;
    case 'External':
      return `External(${e.service}): ${e.cause}`;
    case 'Conflict':
      return `Conflict: ${e.reason}`;
    case 'DatabaseUnavailable':
      return `DatabaseUnavailable: ${e.detail}`;
    case 'ConstraintViolation':
      return `ConstraintViolation(${e.constraint}): ${e.detail}`;
    case 'QueryFailed':
      return `QueryFailed: ${e.detail}`;
    case 'MigrationMismatch':
      return `MigrationMismatch: ${e.detail}`;
    case 'ParseFailed':
      return `ParseFailed: ${e.field} — ${e.reason}`;
  }
}
