/**
 * Ingest CLI: Economic Survey annex 13.1 — provincial + national GVA by industry
 * → `dne_facts` (ADR-0023, composite dimension per ADR-0018).
 *
 * Source of values: `scrapers/surya_ocr/_ai_pass/es2081_annex13_1/verified_matrix_2081_82.json`,
 * a Tier-2 Surya-OCR table render-verified by Mother and dual-reconciled (Σsectors=GVA per
 * province; Σprovinces=national per sector; national GDP = dne-gdp-nominal to the rupee — see
 * MOTHER_VERIFICATION.md). FY2080/81 is excluded (a +799 source-internal defect).
 *
 * Two dimension kinds under one measure `economic-survey-gva-current`:
 *   - `industry`           → national sectoral GVA (18 rows), dimension_value = sector slug
 *   - `province-industry`  → provincial disaggregation (7×18=126), dimension_value = `<prov>__<sector>`
 * Idempotent via dne_facts_unique_idx (ON CONFLICT DO NOTHING). Unit npr_crore, confidence B.
 *
 * Usage:
 *   pnpm tsx scripts/ingest-economic-survey-gva.ts --dry-run
 *   pnpm tsx scripts/ingest-economic-survey-gva.ts
 */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const MATRIX_PATH = path.join(
  REPO_ROOT,
  'scrapers/surya_ocr/_ai_pass/es2081_annex13_1/verified_matrix_2081_82.json',
);
const PDF_PATH = path.join(
  REPO_ROOT,
  'Financial Data/mof_documents/economic_survey/Economic_Survey_2081-82.pdf',
);
const SOURCE_ID = 'mof-economic-survey-annual';
const BASE_SLUG = 'economic-survey-gva-current';
const BASE_NAME = 'Gross Value Added at basic prices (current prices)';

// FY2081/82 BS = AD 2024/25 — match the existing dne-provincial-gdp 2081/82 convention.
const PERIOD = {
  reportingPeriodType: 'annual' as const,
  reportingPeriodBs: '2081/82',
  reportingPeriodAdStart: new Date('2024-07-15T00:00:00Z'),
  reportingPeriodAdEnd: new Date('2025-07-15T00:00:00Z'),
  fiscalYearBs: '2081/82',
  fiscalYearAdLabel: '2024/25',
  confidenceGrade: 'B' as const,
};

const SECTOR_EN: Record<string, string> = {
  'agriculture-forestry-fishing': 'Agriculture, forestry & fishing',
  'mining-quarrying': 'Mining & quarrying',
  manufacturing: 'Manufacturing',
  'electricity-gas-steam-ac': 'Electricity, gas, steam & air conditioning',
  'water-supply-sewerage-waste': 'Water supply, sewerage & waste management',
  construction: 'Construction',
  'wholesale-retail-trade-vehicle-repair': 'Wholesale & retail trade; vehicle repair',
  'transport-storage': 'Transport & storage',
  'accommodation-food-service': 'Accommodation & food service',
  'information-communication': 'Information & communication',
  'financial-insurance': 'Financial & insurance',
  'real-estate': 'Real estate',
  'professional-scientific-technical': 'Professional, scientific & technical',
  'administrative-support-service': 'Administrative & support service',
  'public-administration-defence': 'Public administration & defence',
  education: 'Education',
  'human-health-social-work': 'Human health & social work',
  'other-service': 'Other service activities',
};
const PROVINCE_EN: Record<string, string> = {
  koshi: 'Koshi',
  madhes: 'Madhes',
  bagamati: 'Bagamati',
  gandaki: 'Gandaki',
  lumbini: 'Lumbini',
  karnali: 'Karnali',
  'sudur-pashchim': 'Sudur Pashchim',
};

const MatrixSchema = z.object({
  unit: z.literal('npr_crore'),
  fiscal_year_bs: z.literal('2081/82'),
  cells: z.array(
    z.object({
      province: z.string().min(1),
      sector_idx: z.number().int(),
      sector_slug: z.string().min(1),
      value: z.number(),
    }),
  ),
});

type FactRow = {
  sourceDocumentId: string;
  baseIndicatorSlug: string;
  baseIndicatorName: string;
  dimensionKind: string;
  dimensionValue: string;
  dimensionLabel: string;
  value: string;
  unit: string;
  reportingPeriodType: 'annual';
  reportingPeriodBs: string;
  reportingPeriodAdStart: Date;
  reportingPeriodAdEnd: Date;
  fiscalYearBs: string;
  fiscalYearAdLabel: string;
  confidenceGrade: 'B';
};

function log(m: string): void {
  console.log(`[ingest-es-gva] ${m}`);
}

function buildRows(
  cells: z.infer<typeof MatrixSchema>['cells'],
  sourceDocumentId: string,
): FactRow[] {
  return cells.map((c) => {
    const isNational = c.province === 'nepal';
    const sectorEn = SECTOR_EN[c.sector_slug];
    if (!sectorEn) throw new Error(`unknown sector slug: ${c.sector_slug}`);
    let dimensionKind: string;
    let dimensionValue: string;
    let dimensionLabel: string;
    if (isNational) {
      dimensionKind = 'industry';
      dimensionValue = c.sector_slug;
      dimensionLabel = sectorEn;
    } else {
      const provEn = PROVINCE_EN[c.province];
      if (!provEn) throw new Error(`unknown province slug: ${c.province}`);
      dimensionKind = 'province-industry';
      dimensionValue = `${c.province}__${c.sector_slug}`;
      dimensionLabel = `${provEn} → ${sectorEn}`;
    }
    return {
      sourceDocumentId,
      baseIndicatorSlug: BASE_SLUG,
      baseIndicatorName: BASE_NAME,
      dimensionKind,
      dimensionValue,
      dimensionLabel,
      value: c.value.toString(),
      unit: 'npr_crore',
      ...PERIOD,
    };
  });
}

async function main(): Promise<void> {
  const dryRun = process.argv.includes('--dry-run');
  if (!existsSync(MATRIX_PATH)) {
    console.error(`[ingest-es-gva] matrix not found: ${MATRIX_PATH}`);
    process.exit(2);
  }
  const matrix = MatrixSchema.parse(JSON.parse(readFileSync(MATRIX_PATH, 'utf8')));
  const national = matrix.cells.filter((c) => c.province === 'nepal');
  const provincial = matrix.cells.filter((c) => c.province !== 'nepal');
  log(
    `matrix cells: ${matrix.cells.length} (national industry=${national.length}, province-industry=${provincial.length})`,
  );

  // Sanity: national sectors must sum to the known GVA-basic total (537959) within rounding.
  const natSum = national.reduce((s, c) => s + c.value, 0);
  log(`national Σ(sectors) = ${natSum} npr_crore (expected ≈ 537959 GVA-basic; ±rounding)`);
  if (Math.abs(natSum - 537959) > 9) {
    console.error(
      `[ingest-es-gva] national sector sum ${natSum} deviates >9 from 537959 — aborting (not clean)`,
    );
    process.exit(1);
  }

  if (dryRun) {
    log('dry-run — no archive, no DB writes. Sample rows:');
    for (const r of [national[0], provincial[0], provincial[provincial.length - 1]]) {
      if (r) {
        const isNat = r.province === 'nepal';
        log(
          `  ${BASE_SLUG} / ${isNat ? 'industry' : 'province-industry'} / ${isNat ? r.sector_slug : `${r.province}__${r.sector_slug}`} = ${r.value} npr_crore`,
        );
      }
    }
    log('dry-run complete.');
    return;
  }

  if (!existsSync(PDF_PATH)) {
    console.error(`[ingest-es-gva] source PDF not found: ${PDF_PATH}`);
    process.exit(2);
  }
  const { archiveAndInsertSourceDocument } = await import('./_lib/archive-source-document');
  const { bulkInsertDneFacts, countByBaseIndicator } =
    await import('@/lib/db/repositories/dne-facts');

  // Re-run guard: each run appends a fresh source_documents row, so the unique
  // index (which includes source_document_id) would NOT dedupe a second run —
  // it would duplicate all 144 facts. Refuse if the measure is already present.
  const force = process.argv.includes('--force');
  const existing = await countByBaseIndicator(BASE_SLUG);
  if (existing.ok && existing.value > 0 && !force) {
    console.error(
      `[ingest-es-gva] ${existing.value} '${BASE_SLUG}' facts already exist — refusing (a re-run would duplicate under a new source_document). Pass --force only if you intend to add another edition.`,
    );
    process.exit(1);
  }

  const sourceDocumentId = await archiveAndInsertSourceDocument({
    filePath: PDF_PATH,
    sourceId: SOURCE_ID,
    contentType: 'application/pdf',
    reportingPeriodLabel: 'FY 2081/82 (Economic Survey annex 13.1 — GVA by industry)',
    notes: 'Tier-2 Surya-OCR, Mother render-verified + dual-reconciled (ADR-0023).',
  });
  log(`source_documents.id = ${sourceDocumentId}`);

  const rows = buildRows(matrix.cells, sourceDocumentId);
  const result = await bulkInsertDneFacts(rows);
  if (!result.ok) {
    console.error(`[ingest-es-gva] bulkInsertDneFacts failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }
  log(`dne_facts inserted = ${result.value.length} (of ${rows.length}; dupes skipped on conflict)`);
  log('done. Re-run `pnpm audit:data` to confirm no new reconciliation mismatch.');
}

main().catch((e: unknown) => {
  console.error(
    `[ingest-es-gva] uncaught: ${e instanceof Error ? (e.stack ?? e.message) : String(e)}`,
  );
  process.exit(1);
});
