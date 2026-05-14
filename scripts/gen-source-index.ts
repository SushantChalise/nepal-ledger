/**
 * Generate `docs/sources/_index.md` from the canonical seed.
 *
 * Per ADR-0009, `scripts/seed-source-registry.ts` is the declarative source
 * of truth. This generator reads its `ROWS` export, sorts deterministically,
 * and writes a Markdown index. The output is committed for PR-diff visibility
 * and CI-gated by `scripts/check-source-registry.ts`.
 *
 * Usage:
 *   pnpm gen:source-index          # write docs/sources/_index.md
 *   pnpm gen:source-index --check  # print to stdout (no write)
 *
 * No DB, no network. Pure function of the seed.
 */

import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { ROWS } from './seed-source-registry';

const HEADER = '<!-- GENERATED — do not edit. Run: pnpm gen:source-index -->';

function tierLabel(tier: number | null | undefined): string {
  if (tier === null || tier === undefined) return 'Reference';
  return `Tier ${tier}`;
}

export function buildIndex(): string {
  const sorted = [...ROWS].sort((a, b) => {
    // Sort: tier (null last) → source_id
    const ta = a.tier ?? 99;
    const tb = b.tier ?? 99;
    if (ta !== tb) return ta - tb;
    return a.sourceId.localeCompare(b.sourceId);
  });

  const lines: string[] = [
    HEADER,
    '',
    '# Source Registry — Index',
    '',
    'Generated from `scripts/seed-source-registry.ts` (the canonical seed).',
    'For schema + workflow, see [`../SOURCE_REGISTRY.md`](../SOURCE_REGISTRY.md).',
    'For the lifetime contract, see [ADR-0009](../decisions/0009-source-registry-single-source-of-truth.md).',
    '',
    `Total registered sources: ${ROWS.length}`,
    '',
    '| Tier | Source ID | Agency | Dataset | Frequency | Mode | Status |',
    '|---|---|---|---|---|---|---|',
  ];

  for (const row of sorted) {
    const profileLink =
      row.ingestionMode === 'reference_only'
        ? row.sourceId
        : `[${row.sourceId}](${row.sourceId}.md)`;
    lines.push(
      `| ${tierLabel(row.tier)} | ${profileLink} | ${row.agencyShort} | ${row.datasetName} | ${row.publicationFrequency} | ${row.ingestionMode} | ${row.status ?? 'active'} |`,
    );
  }

  lines.push('');
  return lines.join('\n');
}

function isDirectInvocation(): boolean {
  if (typeof process === 'undefined' || !process.argv[1]) return false;
  return process.argv[1].replace(/\\/g, '/').endsWith('gen-source-index.ts');
}

function main(): void {
  const args = process.argv.slice(2);
  const checkOnly = args.includes('--check');
  const content = buildIndex();

  if (checkOnly) {
    process.stdout.write(content);
    return;
  }

  const target = resolve(process.cwd(), 'docs/sources/_index.md');
  writeFileSync(target, content, 'utf8');
  console.log(`[gen:source-index] wrote ${target} (${ROWS.length} rows)`);
}

if (isDirectInvocation()) {
  main();
}
