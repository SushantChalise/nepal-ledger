import { defineConfig } from 'drizzle-kit';

// Drizzle Kit config. DATABASE_URL is read from .env.local (gitignored).
// DIRECT_URL is preferred for migrations because it bypasses the pgbouncer
// pooler which doesn't speak the full Postgres wire protocol for DDL.
const url = process.env['DIRECT_URL'] ?? process.env['DATABASE_URL'];

if (!url) {
  // drizzle-kit is invoked in CI for `check` (no DB call) and locally for
  // `generate` / `migrate`. The `check` command only needs the schema files,
  // so we fall back to a placeholder when DATABASE_URL is absent.
  console.warn(
    '[drizzle.config] No DATABASE_URL / DIRECT_URL found — using placeholder. OK for `drizzle-kit check`; required for `generate` / `migrate`.',
  );
}

export default defineConfig({
  schema: './src/lib/db/schema/index.ts',
  out: './src/lib/db/migrations',
  dialect: 'postgresql',
  dbCredentials: {
    url: url ?? 'postgresql://placeholder:placeholder@localhost:5432/placeholder',
  },
  casing: 'snake_case',
  strict: true,
  verbose: true,
});
