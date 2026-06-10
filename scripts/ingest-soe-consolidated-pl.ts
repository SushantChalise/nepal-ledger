/**
 * Ingest CLI: consolidated SOE profit/loss (Yellow Book 2081, p79, ५.५ एकीकृत नाफा/नोक्सान)
 * → `dne_facts`. Source values: `scrapers/surya_ocr/_ai_pass/soe_2081_p79_pl/verified_soe_pl_2078-80.json`,
 * Mother render-verified (Matrix 8–20) + reconciled (income exact FY2078/79; profit identity exact
 * FY2079/80; worst residual +701 lakh source-rounding in FY2079/80 income breakdown — documented).
 *
 * Model: one measure `soe-consolidated-pl`, dimension_kind `pl-line-item`, dimension_value = line slug
 * (e.g. `net-profit`, `total-income`, `direct-trading-expense`). Stored in npr_crore (source is lakh ÷10).
 * Consistent with the existing budget-allocation × budget-head dne_facts pattern. Idempotent via
 * dne_facts_unique_idx; re-run guard refuses a second ingest (would duplicate under a new source_document).
 *
 * Usage: node --env-file=.env.local --conditions=react-server --import tsx scripts/ingest-soe-consolidated-pl.ts [--dry-run] [--force]
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
  'scrapers/surya_ocr/_ai_pass/soe_2081_p79_pl/verified_soe_pl_2078-80.json',
);
const PDF_PATH = path.join(
  REPO_ROOT,
  'Financial Data/mof_documents/yellowbook/सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१_ksi3tbe.pdf',
);
const SOURCE_ID = 'dpm-public-enterprises-annual';
const BASE_SLUG = 'soe-consolidated-pl';
const BASE_NAME = 'Public enterprises — consolidated profit/loss (income statement)';

// FY BS → AD (mid-July fiscal year). FY2078/79 = AD2021/22; FY2079/80 = AD2022/23.
const PERIODS: Record<'2078/79' | '2079/80', { adStart: Date; adEnd: Date; adLabel: string }> = {
  '2078/79': {
    adStart: new Date('2021-07-16T00:00:00Z'),
    adEnd: new Date('2022-07-15T00:00:00Z'),
    adLabel: '2021/22',
  },
  '2079/80': {
    adStart: new Date('2022-07-16T00:00:00Z'),
    adEnd: new Date('2023-07-16T00:00:00Z'),
    adLabel: '2022/23',
  },
};

const MatrixSchema = z.object({
  unit_source: z.literal('npr_lakh'),
  years: z.array(z.string()),
  rows: z.array(
    z.object({
      slug: z.string().min(1),
      label_ne: z.string(),
      kind: z.string(),
      fy_2078_79_crore: z.number(),
      fy_2079_80_crore: z.number(),
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
  console.log(`[ingest-soe-pl] ${m}`);
}

function buildRows(m: z.infer<typeof MatrixSchema>, sourceDocumentId: string): FactRow[] {
  const rows: FactRow[] = [];
  for (const r of m.rows) {
    for (const [bs, crore] of [
      ['2078/79', r.fy_2078_79_crore],
      ['2079/80', r.fy_2079_80_crore],
    ] as const) {
      const p = PERIODS[bs];
      rows.push({
        sourceDocumentId,
        baseIndicatorSlug: BASE_SLUG,
        baseIndicatorName: BASE_NAME,
        dimensionKind: 'pl-line-item',
        dimensionValue: r.slug,
        dimensionLabel: `${r.label_ne} [${r.kind}]`,
        value: crore.toString(),
        unit: 'npr_crore',
        reportingPeriodType: 'annual',
        reportingPeriodBs: bs,
        reportingPeriodAdStart: p.adStart,
        reportingPeriodAdEnd: p.adEnd,
        fiscalYearBs: bs,
        fiscalYearAdLabel: p.adLabel,
        confidenceGrade: 'B',
      });
    }
  }
  return rows;
}

async function main(): Promise<void> {
  const dryRun = process.argv.includes('--dry-run');
  if (!existsSync(MATRIX_PATH)) {
    console.error(`[ingest-soe-pl] matrix not found: ${MATRIX_PATH}`);
    process.exit(2);
  }
  const m = MatrixSchema.parse(JSON.parse(readFileSync(MATRIX_PATH, 'utf8')));

  // Sanity: net profit FY2079/80 = total income − total expense (the reconciling headline).
  const ti = m.rows.find((r) => r.slug === 'total_income')!.fy_2079_80_crore;
  const te = m.rows.find((r) => r.slug === 'total_expense')!.fy_2079_80_crore;
  const np = m.rows.find((r) => r.slug === 'net_profit')!.fy_2079_80_crore;
  log(
    `rows: ${m.rows.length} × ${m.years.length} years = ${m.rows.length * 2} facts. FY2079/80 check: ${ti} − ${te} = ${ti - te} vs net_profit ${np}`,
  );
  if (Math.abs(ti - te - np) > 1) {
    console.error(`[ingest-soe-pl] profit identity broken — aborting (not clean)`);
    process.exit(1);
  }

  if (dryRun) {
    log('dry-run — no archive, no DB writes. Sample:');
    for (const r of m.rows.filter((x) =>
      ['net_profit', 'total_income', 'revenue_contract_sales_interest'].includes(x.slug),
    ))
      log(
        `  ${BASE_SLUG} / pl-line-item / ${r.slug} = ${r.fy_2078_79_crore} → ${r.fy_2079_80_crore} npr_crore`,
      );
    log('dry-run complete.');
    return;
  }

  if (!existsSync(PDF_PATH)) {
    console.error(`[ingest-soe-pl] source PDF not found: ${PDF_PATH}`);
    process.exit(2);
  }
  const { archiveAndInsertSourceDocument } = await import('./_lib/archive-source-document');
  const { bulkInsertDneFacts, countByBaseIndicator } =
    await import('@/lib/db/repositories/dne-facts');

  const existing = await countByBaseIndicator(BASE_SLUG);
  if (existing.ok && existing.value > 0 && !process.argv.includes('--force')) {
    console.error(
      `[ingest-soe-pl] ${existing.value} '${BASE_SLUG}' facts already exist — refusing (re-run would duplicate under a new source_document). Use --force to add another edition.`,
    );
    process.exit(1);
  }

  const sourceDocumentId = await archiveAndInsertSourceDocument({
    filePath: PDF_PATH,
    sourceId: SOURCE_ID,
    contentType: 'application/pdf',
    reportingPeriodLabel: 'FY2078/79-2079/80 (Yellow Book 2081 p79 - consolidated SOE profit/loss)',
    notes:
      'Tier-2 Surya-OCR, Mother render-verified + reconciled (profit identity exact; +701 lakh source-rounding in FY2079/80 income breakdown documented).',
  });
  log(`source_documents.id = ${sourceDocumentId}`);

  const rows = buildRows(m, sourceDocumentId);
  const result = await bulkInsertDneFacts(rows);
  if (!result.ok) {
    console.error(`[ingest-soe-pl] bulkInsertDneFacts failed: ${JSON.stringify(result.error)}`);
    process.exit(1);
  }
  log(
    `dne_facts inserted = ${result.value.length} (of ${rows.length}). Re-run audit to confirm no new mismatch.`,
  );
}

main()
  .then(() => process.exit(0))
  .catch((e) => {
    console.error(e);
    process.exit(1);
  });
