/**
 * CI gate for the source registry contract (ADR-0009).
 *
 * Three checks, no DB, no network:
 *   1. No duplicate `source_id` in the seed.
 *   2. Every non-reference-only row has a corresponding
 *      `docs/sources/<source-id>.md` profile.
 *   3. `docs/sources/_index.md` on disk matches what the generator
 *      would emit (regenerate-and-diff).
 *
 * Exits non-zero with a human-readable error list on failure.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { ROWS } from './seed-source-registry';
import { buildIndex } from './gen-source-index';

function main(): void {
  const errors: string[] = [];

  // 1. Duplicate source_id
  const seen = new Set<string>();
  for (const row of ROWS) {
    if (seen.has(row.sourceId)) {
      errors.push(`duplicate source_id: ${row.sourceId}`);
    }
    seen.add(row.sourceId);
  }

  // 2. Profile file presence
  const sourcesDir = resolve(process.cwd(), 'docs/sources');
  for (const row of ROWS) {
    if (row.ingestionMode === 'reference_only') continue;
    const profile = resolve(sourcesDir, `${row.sourceId}.md`);
    if (!existsSync(profile)) {
      errors.push(`missing profile: docs/sources/${row.sourceId}.md`);
    }
  }

  // 3. Generated index matches disk
  const indexPath = resolve(sourcesDir, '_index.md');
  if (!existsSync(indexPath)) {
    errors.push('missing docs/sources/_index.md — run `pnpm gen:source-index`');
  } else {
    const expected = buildIndex();
    const actual = readFileSync(indexPath, 'utf8');
    if (actual !== expected) {
      errors.push(
        'docs/sources/_index.md is stale — run `pnpm gen:source-index` and commit the result',
      );
    }
  }

  if (errors.length > 0) {
    console.error('[check:source-registry] FAILED:');
    for (const e of errors) console.error('  - ' + e);
    process.exit(1);
  }

  console.log(`[check:source-registry] OK — ${ROWS.length} rows verified`);
}

main();
