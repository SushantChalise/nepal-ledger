/**
 * Seed non-local audit-subject entities (ADR-0024) into the `entities` table,
 * so the OAG audit parsers can attach per-entity rows.
 *
 * SCOPE — provinces only, for now. The 7 provinces are constitutional and
 * definitive, so they are seeded here as inline canonical reference data
 * (kind='province', slug = federal province number 1–7).
 *
 * DEFERRED — federal ministries/departments and public corporations are NOT
 * seeded here. Per the project's seed pattern (local levels were seeded from
 * the MoF XLSX — see scripts/seed-local-level-entities.ts), volatile rosters
 * must be seeded from their authoritative source document so names/spellings
 * match what the parser reconciles against. Those are seeded during the OAG
 * parser PR from the report's own entity roster (Nepali edition) and the DPM
 * "Yellow Book" — not hand-typed here.
 *
 * Usage:
 *   pnpm seed:audit-entities --dry-run
 *   pnpm seed:audit-entities
 *
 * Idempotency: upsert keyed on the unique index `(kind, slug)`. Re-running is
 * a no-op for name/metadata when unchanged; otherwise they are refreshed.
 */

import { type NewEntityRow } from '@/lib/db/schema/entities';

// ─── Canonical province reference data (Constitution of Nepal, Schedule 4) ──

type ProvinceSeed = {
  no: number; // federal province number 1–7 (also the slug)
  nameEn: string;
  nameNe: string;
};

// `name_variants` carry the "Province No. N" forms (Devanagari + Latin) that
// older OAG reports used before the provinces were formally named — fuzzy
// resolution at parse time matches against these too.
const PROVINCES: readonly ProvinceSeed[] = [
  { no: 1, nameEn: 'Koshi Province', nameNe: 'कोशी प्रदेश' },
  { no: 2, nameEn: 'Madhesh Province', nameNe: 'मधेश प्रदेश' },
  { no: 3, nameEn: 'Bagmati Province', nameNe: 'बागमती प्रदेश' },
  { no: 4, nameEn: 'Gandaki Province', nameNe: 'गण्डकी प्रदेश' },
  { no: 5, nameEn: 'Lumbini Province', nameNe: 'लुम्बिनी प्रदेश' },
  { no: 6, nameEn: 'Karnali Province', nameNe: 'कर्णाली प्रदेश' },
  { no: 7, nameEn: 'Sudurpashchim Province', nameNe: 'सुदूरपश्चिम प्रदेश' },
];

const _DEVANAGARI_DIGITS = '०१२३४५६७८९';
const toDevanagari = (n: number): string =>
  String(n)
    .split('')
    .map((d) => _DEVANAGARI_DIGITS[Number(d)] ?? d)
    .join('');

function buildProvinceInserts(): NewEntityRow[] {
  return PROVINCES.map((p) => ({
    kind: 'province' as const,
    slug: String(p.no),
    nameEn: p.nameEn,
    nameNe: p.nameNe,
    metadata: {
      province_no: p.no,
      federal_code: String(p.no),
      name_variants: [`Province No. ${p.no}`, `प्रदेश नं. ${toDevanagari(p.no)}`],
    },
  }));
}

// ─── CLI ────────────────────────────────────────────────────────────────

function log(msg: string): void {
  console.log(`[seed-audit-entities] ${msg}`);
}

async function main(): Promise<void> {
  const dryRun = process.argv.slice(2).includes('--dry-run');
  const inserts = buildProvinceInserts();
  log(`dry_run = ${dryRun}`);
  log(`provinces = ${inserts.length}`);
  for (const row of inserts) {
    log(`  ${row.slug.padEnd(2)} ${row.nameEn} / ${row.nameNe}`);
  }

  if (inserts.length !== PROVINCES.length || inserts.length !== 7) {
    log(`ERROR: expected 7 province rows, built ${inserts.length} — refusing to seed`);
    process.exit(1);
  }

  if (dryRun) {
    log('dry-run mode: no DB writes performed');
    process.exit(0);
  }

  // Lazy import so --dry-run needs no DATABASE_URL.
  const { bulkUpsertEntities } = await import('@/lib/db/repositories/entities');
  const result = await bulkUpsertEntities(inserts);
  if (!result.ok) {
    log(`ERROR: upsert failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }
  log(`upserted = ${result.value.upserted}`);
  log('done.');
  process.exit(0);
}

main().catch((e: unknown) => {
  log(`uncaught error: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`);
  process.exit(1);
});
