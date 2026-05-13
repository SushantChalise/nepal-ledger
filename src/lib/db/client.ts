/**
 * Drizzle client singleton (server-only).
 *
 * NEVER import this from a client component. Server Components, Server
 * Actions, Route Handlers, and scripts only. The repositories in
 * `src/lib/db/repositories/*` are the canonical access layer; do not call
 * `db.*` directly from feature code.
 */

import 'server-only';

import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';

import { serverEnv } from '@/lib/env';

import * as schema from './schema';

type DatabaseClient = ReturnType<typeof drizzle<typeof schema>>;

let cachedClient: DatabaseClient | undefined;

export function db(): DatabaseClient {
  if (cachedClient) return cachedClient;
  const env = serverEnv();
  // postgres-js supports the Supabase pooler URL directly. `prepare: false`
  // is required when running on Supabase's transaction-pooler (port 6543),
  // which doesn't support named prepared statements.
  const queryClient = postgres(env.DATABASE_URL, {
    max: 10,
    idle_timeout: 30,
    connect_timeout: 30,
    prepare: false,
  });
  cachedClient = drizzle(queryClient, { schema, casing: 'snake_case' });
  return cachedClient;
}
