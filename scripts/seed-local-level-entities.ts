/**
 * Seed the canonical 753 local-level (municipality / rural municipality /
 * metro / sub-metro) rows into the `entities` table.
 *
 * Without this seed, the entity resolver in
 * `findLocalLevelEntityBySlug(<federal_code>)` always returns NULL, so
 * every domain-fact parser that joins on entities (Worker P1 fiscal
 * transfers, Worker P3 census, future MoF book parsers) silently drops
 * rows. This script ships the seed so those parsers can actually persist.
 *
 * Source of truth:
 *   Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx — Sheet2
 *   (the MoF-published, manually-validated 753-row table). The Python
 *   helper `scripts/_seed-helpers/extract_local_levels.py` reads + filters
 *   it; this TS file owns the DB write path via safeQuery.
 *
 * Usage:
 *   pnpm seed:local-levels --dry-run
 *   pnpm seed:local-levels --input "Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx"
 *   pnpm seed:local-levels                      # uses default input path
 *
 * Idempotency: upsert keyed by the unique index `(kind, slug)`. Re-running
 * after a successful seed is a no-op for the `nameEn / nameNe / metadata`
 * fields if they match; otherwise they are refreshed.
 */

import { spawn as nodeSpawn } from 'node:child_process';
import { stat } from 'node:fs/promises';
import { resolve } from 'node:path';

import { sql } from 'drizzle-orm';
import { z } from 'zod';

const DEFAULT_INPUT = 'Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx';
const HELPER_PATH = 'scripts/_seed-helpers/extract_local_levels.py';
const EXTRACT_TIMEOUT_MS = 60_000;
const EXPECTED_ROW_COUNT = 753;

// ─── Helper output schema ───────────────────────────────────────────────

const ExtractRowSchema = z.object({
  federal_code: z.string().regex(/^\d{8}$/),
  name_en: z.string().min(1),
  name_ne: z.string().min(1),
  local_level_type: z.enum([
    'metropolitan_city',
    'sub_metropolitan_city',
    'municipality',
    'rural_municipality',
  ]),
  district_en: z.string().min(1),
});

type ExtractRow = z.infer<typeof ExtractRowSchema>;

const ExtractOutputSchema = z.array(ExtractRowSchema);

// ─── CLI ────────────────────────────────────────────────────────────────

type CliArgs = {
  inputPath: string;
  dryRun: boolean;
};

function parseArgs(argv: readonly string[]): CliArgs {
  let inputPath = DEFAULT_INPUT;
  let dryRun = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') {
      dryRun = true;
    } else if (arg === '--input') {
      const next = argv[i + 1];
      if (!next) throw new Error('--input requires a value');
      inputPath = next;
      i += 1;
    } else if (arg?.startsWith('--input=')) {
      inputPath = arg.slice('--input='.length);
    }
  }
  return { inputPath, dryRun };
}

function log(msg: string): void {
  console.log(`[seed-local-levels] ${msg}`);
}

function logErr(msg: string): void {
  console.error(`[seed-local-levels] ${msg}`);
}

// ─── Python helper subprocess ───────────────────────────────────────────

async function extractRows(inputPath: string): Promise<readonly ExtractRow[]> {
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolvePromise, reject) => {
    const child = nodeSpawn(python, [HELPER_PATH, inputPath], {
      cwd: process.cwd(),
      shell: false,
    });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`python helper timeout after ${EXTRACT_TIMEOUT_MS}ms`));
    }, EXTRACT_TIMEOUT_MS);
    child.stdout.on('data', (c: Buffer) => stdoutChunks.push(c));
    child.stderr.on('data', (c: Buffer) => stderrChunks.push(c));
    child.on('error', (e) => {
      clearTimeout(timer);
      reject(e);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      const stdout = Buffer.concat(stdoutChunks).toString('utf8');
      const stderr = Buffer.concat(stderrChunks).toString('utf8');
      if (code !== 0) {
        reject(new Error(`python helper exit ${code}: ${stderr.trim() || '<no stderr>'}`));
        return;
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(stdout);
      } catch (e) {
        reject(new Error(`helper stdout was not JSON: ${e instanceof Error ? e.message : e}`));
        return;
      }
      const validated = ExtractOutputSchema.safeParse(parsed);
      if (!validated.success) {
        reject(new Error(`helper output failed schema: ${validated.error.message}`));
        return;
      }
      resolvePromise(validated.data);
    });
  });
}

// ─── DB write path ──────────────────────────────────────────────────────

async function persist(rows: readonly ExtractRow[]): Promise<{ upserted: number }> {
  // Lazy imports so --dry-run doesn't require DATABASE_URL.
  const { db } = await import('@/lib/db/client');
  const { entities } = await import('@/lib/db/schema/entities');
  const { safeQuery } = await import('@/lib/db/safe-query');

  type NewEntityInsert = {
    kind: 'local_level';
    slug: string;
    nameEn: string;
    nameNe: string;
    metadata: {
      local_level_type: ExtractRow['local_level_type'];
      federal_code: string;
      district_en: string;
    };
  };

  const inserts: NewEntityInsert[] = rows.map((r) => ({
    kind: 'local_level',
    slug: r.federal_code,
    nameEn: r.name_en,
    nameNe: r.name_ne,
    metadata: {
      local_level_type: r.local_level_type,
      federal_code: r.federal_code,
      district_en: r.district_en,
    },
  }));

  // Postgres caps parameter count at 65535. With 4 mutable columns per row
  // plus the slug+kind for conflict targeting we have ~6 params/row; 753
  // rows = ~4.5k params, well under the limit, so a single batch is safe.
  const result = await safeQuery(() =>
    db()
      .insert(entities)
      .values(inserts)
      .onConflictDoUpdate({
        target: [entities.kind, entities.slug],
        set: {
          nameEn: sql`excluded.name_en`,
          nameNe: sql`excluded.name_ne`,
          metadata: sql`excluded.metadata`,
          updatedAt: new Date(),
        },
      })
      .returning({ id: entities.id }),
  );
  if (!result.ok) {
    throw new Error(`entities upsert failed: ${JSON.stringify(result.error)}`);
  }
  return { upserted: result.value.length };
}

// ─── Main ───────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const absoluteInput = resolve(args.inputPath);
  log(`input    = ${absoluteInput}`);
  log(`dry_run  = ${args.dryRun}`);

  try {
    await stat(absoluteInput);
  } catch {
    logErr(`input file not found: ${absoluteInput}`);
    process.exit(2);
  }

  const rows = await extractRows(absoluteInput);
  log(`extracted_rows = ${rows.length}`);
  if (rows.length !== EXPECTED_ROW_COUNT) {
    logErr(
      `expected ${EXPECTED_ROW_COUNT} local-level rows, got ${rows.length} — refusing to seed`,
    );
    process.exit(1);
  }

  // Type breakdown for visibility.
  const byType: Record<string, number> = {};
  for (const r of rows) {
    byType[r.local_level_type] = (byType[r.local_level_type] ?? 0) + 1;
  }
  log('by_local_level_type:');
  for (const [k, v] of Object.entries(byType).sort()) {
    log(`  ${k.padEnd(24)} ${v}`);
  }

  if (args.dryRun) {
    log('dry-run mode: no DB writes performed');
    log(`would upsert ${rows.length} rows into entities (kind=local_level)`);
    process.exit(0);
  }

  const { upserted } = await persist(rows);
  log(`upserted = ${upserted}`);
  log('done.');
  process.exit(0);
}

main().catch((e: unknown) => {
  logErr(`uncaught error: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
