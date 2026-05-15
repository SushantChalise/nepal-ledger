/**
 * CBS NPHC 2021 census ingest — single-CSV invocation.
 *
 * Usage:
 *   pnpm ingest:census-2021 -- --csv "<absolute-path-to.csv>" --dry-run
 *   pnpm ingest:census-2021 -- --csv "<absolute-path-to.csv>" \
 *       --source-document-id <uuid>
 *
 * Flow:
 *   1. Spawn `scrapers/cbs_nphc/parser.py <csv> <source_document_id>`.
 *   2. Parse the JSON ParserResult, validate with Zod.
 *   3. For each emitted CensusFactDraft, resolve `entity_slug` (8-digit
 *      federal code) → `entities.id` (UUID). Skip drafts whose entity is
 *      missing and surface them in the dry-run summary.
 *   4. Bulk-insert via `census-facts` repository with ON CONFLICT DO
 *      NOTHING so re-runs are idempotent.
 *
 * The script reuses `src/lib/ingestion/run-parser.ts`'s subprocess contract
 * (`stdout = JSON result, exit 0/1/2`). For now we parse a custom census
 * shape with a local Zod schema rather than going through ParserOutputSchema
 * which is staging-row-shaped.
 *
 * Lazy imports: `db` is only imported when `--dry-run` is NOT set, so the
 * dry-run path works without DATABASE_URL.
 */

import { resolve } from 'node:path';

import { z } from 'zod';

const CENSUS_FACT_DRAFT_SCHEMA = z.object({
  entity_slug: z.string().min(1),
  source_table_id: z.string().min(1),
  indicator_family: z.enum([
    'household_housing',
    'household_facility',
    'household_economic',
    'household_demographic',
    'individual_demographic',
    'individual_education',
    'individual_economic',
    'individual_migration',
    'individual_fertility',
  ]),
  indicator_slug: z.string().min(1),
  value: z.number(),
  unit: z.string().min(1),
  census_year_ad: z.string().default('2021'),
  census_year_bs: z.string().default('2078'),
  confidence_grade_proposed: z.enum(['A', 'B', 'C']).default('A'),
  parser_notes: z.string().nullable().optional(),
});

const CENSUS_PARSER_RESULT_SCHEMA = z.object({
  status: z.enum(['success', 'partial', 'failure']),
  parser_version: z.string(),
  mode: z.enum(['A', 'B']).nullable(),
  facts: z.array(CENSUS_FACT_DRAFT_SCHEMA).default([]),
  errors: z
    .array(
      z.object({
        error_class: z.string(),
        error_detail: z.string(),
        source_excerpt: z.string().nullable().optional(),
      }),
    )
    .default([]),
});

type Args = {
  csv: string;
  dryRun: boolean;
  sourceDocumentId: string;
};

function parseArgs(argv: readonly string[]): Args {
  let csv: string | undefined;
  let dryRun = false;
  let sourceDocumentId: string | undefined;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--csv') {
      csv = argv[++i];
    } else if (a === '--dry-run') {
      dryRun = true;
    } else if (a === '--source-document-id') {
      sourceDocumentId = argv[++i];
    }
  }
  if (!csv) {
    console.error(
      'usage: ingest-census-2021 --csv <path> [--dry-run] [--source-document-id <uuid>]',
    );
    process.exit(2);
  }
  // For dry-run we accept a placeholder UUID so the script can run without a DB.
  return {
    csv,
    dryRun,
    sourceDocumentId: sourceDocumentId ?? '00000000-0000-0000-0000-000000000000',
  };
}

async function spawnAndCaptureJson(
  csvPath: string,
  sourceDocumentId: string,
): Promise<z.infer<typeof CENSUS_PARSER_RESULT_SCHEMA>> {
  const { spawn } = await import('node:child_process');
  const parserPath = resolve(process.cwd(), 'scrapers/cbs_nphc/parser.py');
  const python = process.env['PYTHON'] ?? (process.platform === 'win32' ? 'python' : 'python3');
  return new Promise((resolveP, rejectP) => {
    const child = spawn(python, [parserPath, csvPath, sourceDocumentId], {
      cwd: resolve(process.cwd(), 'scrapers'),
      shell: false,
    });
    const out: Buffer[] = [];
    const errBufs: Buffer[] = [];
    child.stdout.on('data', (c: Buffer) => out.push(c));
    child.stderr.on('data', (c: Buffer) => errBufs.push(c));
    child.on('close', (code) => {
      if (code !== 0) {
        rejectP(new Error(`python exit ${code}: ${Buffer.concat(errBufs).toString()}`));
        return;
      }
      try {
        const json: unknown = JSON.parse(Buffer.concat(out).toString('utf8'));
        resolveP(CENSUS_PARSER_RESULT_SCHEMA.parse(json));
      } catch (e) {
        rejectP(e instanceof Error ? e : new Error(String(e)));
      }
    });
    child.on('error', rejectP);
  });
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  console.log(`[ingest] parsing ${args.csv} ...`);
  const result = await spawnAndCaptureJson(args.csv, args.sourceDocumentId);

  console.log(
    `[ingest] parser: status=${result.status} mode=${result.mode} ` +
      `facts=${result.facts.length} errors=${result.errors.length}`,
  );
  if (result.errors.length > 0) {
    const sample = result.errors.slice(0, 5);
    for (const e of sample) {
      console.log(`  [error/${e.error_class}] ${e.error_detail}`);
    }
    if (result.errors.length > 5) {
      console.log(`  ... ${result.errors.length - 5} more errors`);
    }
  }

  if (args.dryRun) {
    console.log(`[ingest] --dry-run: ${result.facts.length} facts NOT written`);
    const sample = result.facts.slice(0, 3);
    for (const f of sample) {
      console.log(
        `  ${f.entity_slug} | ${f.indicator_slug} | ${f.value} ${f.unit} | ${f.indicator_family}`,
      );
    }
    process.exit(result.status === 'failure' ? 1 : 0);
  }

  // ─── DB write path ─────────────────────────────────────────────────
  const { db } = await import('@/lib/db/client');
  const { entities } = await import('@/lib/db/schema/entities');
  const { eq } = await import('drizzle-orm');
  const { bulkInsert } = await import('@/lib/db/repositories/census-facts');

  // Resolve entity_slug → entity_id for every distinct slug in the batch.
  const distinctSlugs = Array.from(new Set(result.facts.map((f) => f.entity_slug)));
  const slugToId = new Map<string, string>();
  for (const slug of distinctSlugs) {
    const found = await db().query.entities.findFirst({
      where: eq(entities.slug, slug),
    });
    if (found) slugToId.set(slug, found.id);
  }
  const missing = distinctSlugs.filter((s) => !slugToId.has(s));
  if (missing.length > 0) {
    console.warn(
      `[ingest] WARNING: ${missing.length} entity slug(s) missing from entities table:`,
      missing.slice(0, 5).join(', '),
      missing.length > 5 ? `(+${missing.length - 5} more)` : '',
    );
  }

  const rows = result.facts
    .filter((f) => slugToId.has(f.entity_slug))
    .map((f) => ({
      entityId: slugToId.get(f.entity_slug) as string,
      indicatorFamily: f.indicator_family,
      sourceTableId: f.source_table_id,
      indicatorSlug: f.indicator_slug,
      value: f.value.toString(),
      unit: f.unit,
      censusYearAd: f.census_year_ad,
      censusYearBs: f.census_year_bs,
      sourceDocumentId: args.sourceDocumentId,
      confidenceGrade: f.confidence_grade_proposed,
      promotedBy: 'cbs-nphc-2021-ingest-script',
    }));

  const written = await bulkInsert(rows);
  if (!written.ok) {
    console.error('[ingest] bulkInsert failed:', written.error);
    process.exit(1);
  }
  const inserted = written.value.length;
  const deduped = rows.length - inserted;
  console.log(
    `[ingest] inserted=${inserted} deduped=${deduped} skipped-missing-entity=${result.facts.length - rows.length}`,
  );
}

main().catch((e: unknown) => {
  console.error('[ingest] fatal:', e);
  process.exit(1);
});
