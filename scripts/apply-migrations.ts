/**
 * Apply Drizzle migrations to the Supabase database.
 *
 * Reads DATABASE_URL / DIRECT_URL from .env.local (gitignored) and runs
 * `drizzle-kit`'s migrator against `src/lib/db/migrations/`. This is the
 * sole place migration application happens — Mother runs this once per
 * milestone with explicit user authorization.
 *
 * Usage: pnpm exec tsx scripts/apply-migrations.ts
 *
 * Rollback: pnpm exec drizzle-kit drop (interactive; drops the latest
 * migration). For fully resetting the DB during prototype phase, drop
 * the schema in Supabase dashboard and re-run this.
 */

import 'dotenv/config';

import { config as dotenvConfig } from 'dotenv';
import { drizzle } from 'drizzle-orm/postgres-js';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import postgres from 'postgres';

// dotenv/config auto-loads .env; explicitly load .env.local for our setup.
dotenvConfig({ path: '.env.local', override: true });

const url = process.env['DIRECT_URL'] ?? process.env['DATABASE_URL'];

if (!url) {
  console.error('No DIRECT_URL / DATABASE_URL found in .env.local. Add them and re-run.');
  process.exit(1);
}

async function main(): Promise<void> {
  console.log('[migrate] Connecting to Postgres...');
  // Migrator needs a single dedicated connection.
  const sql = postgres(url!, { max: 1, prepare: false });
  const db = drizzle(sql);

  console.log('[migrate] Applying migrations from src/lib/db/migrations/...');
  await migrate(db, { migrationsFolder: 'src/lib/db/migrations' });

  console.log('[migrate] Done. Listing applied migrations...');
  const applied = await sql`
    SELECT id, hash, created_at
    FROM drizzle.__drizzle_migrations
    ORDER BY id ASC
  `;
  for (const row of applied) {
    console.log(`  - id=${row['id']} created_at=${row['created_at']}`);
  }

  console.log('[migrate] Listing user tables in public schema...');
  const tables = await sql<{ tablename: string }[]>`
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
  `;
  for (const row of tables) {
    console.log(`  - ${row.tablename}`);
  }

  await sql.end();
  console.log('[migrate] Closed connection. OK.');
}

main().catch((e: unknown) => {
  console.error('[migrate] FAILED:', e instanceof Error ? e.message : String(e));
  process.exit(1);
});
