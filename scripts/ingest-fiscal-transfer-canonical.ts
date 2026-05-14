/**
 * Ingest the canonical 753-row local-level table from
 * `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx` into
 * the `entities` + `administrative_units` + `local_government_fiscal_transfers`
 * tables.
 *
 * This is the FIRST live ingest of real data. It produces:
 *   - 7 province entities
 *   - 77 district entities (each linked to its province)
 *   - 753 local-level entities (each linked to its district)
 *   - 753 administrative_units rows (with federal codes + local-level types)
 *   - ~6000 local_government_fiscal_transfers rows (one per local_level x grant_type)
 *
 * Idempotent: re-runs upsert on (kind, slug) for entities and on
 * (local_level, fiscal_year, grant_type) for transfers.
 *
 * Usage:
 *   pnpm exec tsx scripts/ingest-fiscal-transfer-canonical.ts \
 *     --xlsx="Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx" \
 *     --fiscal-year=2082/83 \
 *     [--dry-run]
 *
 * Source-document handling: the script also inserts a `source_documents`
 * row referencing the XLSX file with its SHA-256 hash. The fiscal_transfer
 * rows FK into that. No Supabase Storage upload here — done separately by
 * Mother once the storage wrapper is wired up. The source_documents row
 * carries an `original_url` of "local-file:..." until then.
 */

import 'dotenv/config';

import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { argv } from 'node:process';

import { config as dotenvConfig } from 'dotenv';
import { drizzle } from 'drizzle-orm/postgres-js';
import { eq, and } from 'drizzle-orm';
import ExcelJS from 'exceljs';
import postgres from 'postgres';

import {
  administrativeUnits,
  entities,
  localGovernmentFiscalTransfers,
  sourceDocuments,
  sourceRegistry,
} from '@/lib/db/schema';
import type { GrantType, LocalLevelType } from '@/lib/db/schema';

dotenvConfig({ path: '.env.local', override: true });

const url = process.env['DIRECT_URL'] ?? process.env['DATABASE_URL'];
if (!url) {
  console.error('No DIRECT_URL / DATABASE_URL in .env.local.');
  process.exit(1);
}

// ─── Args ─────────────────────────────────────────────────────────

function getArg(flag: string): string | undefined {
  const eq = argv.find((a) => a.startsWith(`${flag}=`));
  if (eq) return eq.slice(flag.length + 1);
  const idx = argv.indexOf(flag);
  if (idx >= 0 && idx + 1 < argv.length) return argv[idx + 1];
  return undefined;
}

const xlsxPath =
  getArg('--xlsx') ?? 'Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx';
const fiscalYear = getArg('--fiscal-year') ?? '2082/83';
const dryRun = argv.includes('--dry-run');

// ─── Column mapping ───────────────────────────────────────────────

const COL = {
  code: 1,
  districtNe: 2,
  localLevelNe: 3,
  districtEn: 4,
  localLevelEn: 5,
  localLevelType: 6,
  // Grant columns (1-indexed Excel cells; column 7 onward)
  minimumGrant: 7,
  formulaGrant: 8,
  performanceGrant: 9,
  // 10: Total Equalization (computed; we ingest the 3 components)
  conditionalCurrent: 11,
  conditionalCapital: 12,
  // 13: Total Conditional
  specialCurrent: 14,
  specialCapital: 15,
  // 16: Total Special
  complementaryCapital: 17,
  // 18, 19, 20: Total Current / Capital / Grand Total (computed; skip)
};

// Maps the type column to our enum
function mapLocalLevelType(s: string | null | undefined): LocalLevelType | null {
  if (!s) return null;
  const t = s.trim();
  if (t === 'Metropolitan City') return 'metropolitan_city';
  if (t === 'Sub-Metropolitan City') return 'sub_metropolitan_city';
  if (t === 'Municipality') return 'municipality';
  if (t === 'Rural Municipality') return 'rural_municipality';
  return null; // 'District Total' / aggregate rows
}

// 7-province lookup. The CSV is district-level so we need a separate
// district -> province mapping. Federal codes encode it: 1xxxxxxx = Koshi,
// 2 = Madhesh, 3 = Bagmati, 4 = Gandaki, 5 = Lumbini, 6 = Karnali, 7 = Sudurpaschim.
const PROVINCE_BY_DIGIT: Record<string, { slug: string; nameEn: string; nameNe: string }> = {
  '1': { slug: '1', nameEn: 'Koshi Province', nameNe: 'कोशी प्रदेश' },
  '2': { slug: '2', nameEn: 'Madhesh Province', nameNe: 'मधेश प्रदेश' },
  '3': { slug: '3', nameEn: 'Bagmati Province', nameNe: 'बागमती प्रदेश' },
  '4': { slug: '4', nameEn: 'Gandaki Province', nameNe: 'गण्डकी प्रदेश' },
  '5': { slug: '5', nameEn: 'Lumbini Province', nameNe: 'लुम्बिनी प्रदेश' },
  '6': { slug: '6', nameEn: 'Karnali Province', nameNe: 'कर्णाली प्रदेश' },
  '7': { slug: '7', nameEn: 'Sudurpaschim Province', nameNe: 'सुदूरपश्चिम प्रदेश' },
};

// ─── Helpers ──────────────────────────────────────────────────────

function strFromCell(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string') return v.trim() || null;
  if (typeof v === 'number') return String(v);
  if (typeof v === 'object' && v !== null && 'result' in v) {
    const r = (v as { result?: unknown }).result;
    return typeof r === 'string' ? r.trim() : typeof r === 'number' ? String(r) : null;
  }
  return String(v).trim() || null;
}

function numFromCell(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const n = Number(v.replace(/,/g, ''));
    return Number.isFinite(n) ? n : null;
  }
  if (typeof v === 'object' && v !== null && 'result' in v) {
    const r = (v as { result?: unknown }).result;
    return typeof r === 'number' ? r : null;
  }
  return null;
}

async function sha256OfFile(p: string): Promise<{ hash: string; bytes: number }> {
  const buf = await readFile(p);
  return {
    hash: createHash('sha256').update(buf).digest('hex'),
    bytes: buf.length,
  };
}

// ─── Main ─────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log(`[ingest-ft] xlsx=${xlsxPath} fy=${fiscalYear} dry=${dryRun}`);

  const absPath = path.resolve(xlsxPath);
  const { hash, bytes } = await sha256OfFile(absPath);
  console.log(`[ingest-ft] file size=${bytes} sha256=${hash.slice(0, 12)}...`);

  const wb = new ExcelJS.Workbook();
  await wb.xlsx.readFile(absPath);
  const ws = wb.worksheets[0];
  if (!ws) throw new Error('No sheet 0 in XLSX');
  console.log(`[ingest-ft] sheet=${ws.name} rows=${ws.rowCount}`);

  // Collect leaf-level rows (skip aggregate rows)
  type Row = {
    code: string;
    districtEn: string;
    districtNe: string;
    localLevelEn: string;
    localLevelNe: string;
    localLevelType: LocalLevelType;
    grants: Map<GrantType, number>;
  };
  const rows: Row[] = [];
  const districtsSeen = new Map<string, { en: string; ne: string }>();

  for (let r = 2; r <= ws.rowCount; r++) {
    const row = ws.getRow(r);
    const code = strFromCell(row.getCell(COL.code).value);
    const districtNe = strFromCell(row.getCell(COL.districtNe).value);
    const localLevelNe = strFromCell(row.getCell(COL.localLevelNe).value);
    const districtEn = strFromCell(row.getCell(COL.districtEn).value);
    const localLevelEn = strFromCell(row.getCell(COL.localLevelEn).value);
    const llType = mapLocalLevelType(strFromCell(row.getCell(COL.localLevelType).value));

    if (!code || !llType || !districtEn || !localLevelEn || !districtNe || !localLevelNe) {
      continue; // aggregate or sparse row
    }

    // Build the grants map from the 8 grant columns
    const grants = new Map<GrantType, number>();
    const candidate: [GrantType, number][] = [
      ['equalization_minimum', numFromCell(row.getCell(COL.minimumGrant).value) ?? 0],
      ['equalization_formula', numFromCell(row.getCell(COL.formulaGrant).value) ?? 0],
      ['equalization_performance', numFromCell(row.getCell(COL.performanceGrant).value) ?? 0],
      ['conditional_current', numFromCell(row.getCell(COL.conditionalCurrent).value) ?? 0],
      ['conditional_capital', numFromCell(row.getCell(COL.conditionalCapital).value) ?? 0],
      ['special_current', numFromCell(row.getCell(COL.specialCurrent).value) ?? 0],
      ['special_capital', numFromCell(row.getCell(COL.specialCapital).value) ?? 0],
      ['complementary_capital', numFromCell(row.getCell(COL.complementaryCapital).value) ?? 0],
    ];
    for (const [k, v] of candidate) grants.set(k, v);

    rows.push({
      code,
      districtEn: districtEn.trim(),
      districtNe: districtNe.trim(),
      localLevelEn: localLevelEn.trim(),
      localLevelNe: localLevelNe.trim(),
      localLevelType: llType,
      grants,
    });

    if (!districtsSeen.has(districtEn.trim())) {
      districtsSeen.set(districtEn.trim(), { en: districtEn.trim(), ne: districtNe.trim() });
    }
  }

  console.log(`[ingest-ft] parsed ${rows.length} local-level rows`);
  console.log(`[ingest-ft] distinct districts: ${districtsSeen.size}`);

  if (dryRun) {
    console.log('[ingest-ft] --dry-run: not connecting to DB');
    // Write staging JSON for the user's one-command ingest later.
    const stagingDir = 'staging-data/fiscal-transfer-canonical';
    await mkdir(stagingDir, { recursive: true });
    const serialized = rows.map((r) => ({
      code: r.code,
      districtEn: r.districtEn,
      districtNe: r.districtNe,
      localLevelEn: r.localLevelEn,
      localLevelNe: r.localLevelNe,
      localLevelType: r.localLevelType,
      grants: Object.fromEntries(r.grants),
    }));
    await writeFile(
      path.join(stagingDir, `fy-${fiscalYear.replace('/', '-')}.json`),
      JSON.stringify(
        {
          fiscalYear,
          sourceFile: xlsxPath,
          sourceHash: hash,
          sourceBytes: bytes,
          rowCount: rows.length,
          rows: serialized,
        },
        null,
        2,
      ),
    );
    console.log(
      `[ingest-ft] wrote staging JSON: ${stagingDir}/fy-${fiscalYear.replace('/', '-')}.json`,
    );
    console.log(
      `[ingest-ft] ${rows.length} local-level rows + ${districtsSeen.size} districts staged`,
    );
    return;
  }

  console.log('[ingest-ft] Connecting to Postgres...');
  const sql = postgres(url!, { max: 1, prepare: false });
  const db = drizzle(sql);

  // ─── 1. Source-document row for the XLSX ─────────────────────────
  console.log(
    '[ingest-ft] Ensuring source_registry row for `mof-intergovernmental-fiscal-transfer`...',
  );
  await db
    .insert(sourceRegistry)
    .values({
      sourceId: 'mof-intergovernmental-fiscal-transfer',
      agency: 'Ministry of Finance',
      agencyShort: 'MoF',
      datasetName: 'Intergovernmental Fiscal Transfer (NNRFC allocations)',
      sourceUrl: 'https://mof.gov.np/intergovernmental',
      publicationFrequency: 'annual',
      reportingPeriodType: 'annual',
      fileFormat: 'xlsx',
      requiresTableExtraction: false,
      licenseStatus: 'gov_open',
      ingestionMode: 'manual_upload',
      confidenceDefault: 'A',
      status: 'active',
      knownBreakageModes: [],
      notes:
        'Pre-cleaned XLSX in Financial Data/mof_documents/Cleaned/; prior FYs in intergovernmental/*.pdf require Surya OCR (Phase B1).',
    })
    .onConflictDoNothing();

  console.log('[ingest-ft] Inserting source_documents row...');
  const [doc] = await db
    .insert(sourceDocuments)
    .values({
      sourceId: 'mof-intergovernmental-fiscal-transfer',
      originalUrl: `local-file:${xlsxPath}`,
      storageProvider: 'supabase',
      storageKey: `mof-intergovernmental-fiscal-transfer/${new Date().toISOString().slice(0, 10)}/Fiscal-Transfer-${fiscalYear.replace('/', '-')}.xlsx`,
      fileHashSha256: hash,
      fileSizeBytes: bytes,
      contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      reportingPeriodLabel: `FY ${fiscalYear}`,
      notes:
        'Pre-cleaned canonical 753-row dataset from Cleaned/. Has not yet been uploaded to Supabase Storage.',
    })
    .returning();
  if (!doc) throw new Error('source_documents insert returned nothing');
  console.log(`[ingest-ft] source_document_id=${doc.id}`);

  // ─── 2. Provinces (7) ────────────────────────────────────────────
  const provinceIds = new Map<string, string>();
  for (const digit of Object.keys(PROVINCE_BY_DIGIT)) {
    const p = PROVINCE_BY_DIGIT[digit]!;
    const upsertedProvince = await db
      .insert(entities)
      .values({
        kind: 'province',
        slug: p.slug,
        nameEn: p.nameEn,
        nameNe: p.nameNe,
        metadata: { province_digit: digit },
      })
      .onConflictDoUpdate({
        target: [entities.kind, entities.slug],
        set: { nameEn: p.nameEn, nameNe: p.nameNe, updatedAt: new Date() },
      })
      .returning({ id: entities.id });
    const province = upsertedProvince[0];
    if (!province) throw new Error(`Failed to upsert province ${digit}`);
    provinceIds.set(digit, province.id);
  }
  console.log(`[ingest-ft] Upserted ${provinceIds.size} provinces.`);

  // ─── 3. Districts ────────────────────────────────────────────────
  const districtIds = new Map<string, string>();
  for (const [districtEn, names] of districtsSeen) {
    // Find first row with this district to extract its 3-digit code prefix
    const sampleRow = rows.find((r) => r.districtEn === districtEn);
    if (!sampleRow) continue;
    const provinceDigit = sampleRow.code[0];
    if (!provinceDigit) continue;
    const districtCode = sampleRow.code.slice(0, 3);
    const provinceId = provinceIds.get(provinceDigit);
    if (!provinceId) continue;

    const districtSlug = districtCode;
    const upsertedDistrict = await db
      .insert(entities)
      .values({
        kind: 'district',
        slug: districtSlug,
        nameEn: names.en,
        nameNe: names.ne,
        parentEntityId: provinceId,
        metadata: { federal_code: districtCode },
      })
      .onConflictDoUpdate({
        target: [entities.kind, entities.slug],
        set: {
          nameEn: names.en,
          nameNe: names.ne,
          parentEntityId: provinceId,
          updatedAt: new Date(),
        },
      })
      .returning({ id: entities.id });
    const district = upsertedDistrict[0];
    if (!district) throw new Error(`Failed to upsert district ${districtEn}`);
    districtIds.set(districtEn, district.id);
  }
  console.log(`[ingest-ft] Upserted ${districtIds.size} districts.`);

  // ─── 4. Local levels + administrative_units + fiscal_transfers ──
  let localCount = 0;
  let transferCount = 0;
  for (const r of rows) {
    const districtId = districtIds.get(r.districtEn);
    if (!districtId) {
      console.warn(`[ingest-ft] Skipping ${r.localLevelEn}: district ${r.districtEn} not found`);
      continue;
    }

    const upsertedLocalLevel = await db
      .insert(entities)
      .values({
        kind: 'local_level',
        slug: r.code,
        nameEn: r.localLevelEn,
        nameNe: r.localLevelNe,
        parentEntityId: districtId,
        metadata: {
          federal_code: r.code,
          local_level_type: r.localLevelType,
          district_en: r.districtEn,
        },
      })
      .onConflictDoUpdate({
        target: [entities.kind, entities.slug],
        set: {
          nameEn: r.localLevelEn,
          nameNe: r.localLevelNe,
          parentEntityId: districtId,
          updatedAt: new Date(),
        },
      })
      .returning({ id: entities.id });
    const localLevel = upsertedLocalLevel[0];
    if (!localLevel) continue;
    localCount += 1;

    // administrative_units row (1:1 with entity)
    await db
      .insert(administrativeUnits)
      .values({
        entityId: localLevel.id,
        federalCode: r.code,
        localLevelType: r.localLevelType,
      })
      .onConflictDoUpdate({
        target: administrativeUnits.entityId,
        set: { federalCode: r.code, localLevelType: r.localLevelType, updatedAt: new Date() },
      });

    // fiscal_transfers — one row per grant_type that's non-zero
    for (const [grantType, amount] of r.grants) {
      if (amount === 0) continue;
      await db
        .insert(localGovernmentFiscalTransfers)
        .values({
          localLevelEntityId: localLevel.id,
          fiscalYearBs: fiscalYear,
          grantType,
          amountNpr: String(amount),
          unit: 'NPR_lakh', // Source uses Rs lakh as default unit; documented in source profile
          sourceDocumentId: doc.id,
          confidenceGrade: 'A',
          promotedBy: 'mother:ingest-fiscal-transfer-canonical',
        })
        .onConflictDoUpdate({
          target: [
            localGovernmentFiscalTransfers.localLevelEntityId,
            localGovernmentFiscalTransfers.fiscalYearBs,
            localGovernmentFiscalTransfers.grantType,
          ],
          set: { amountNpr: String(amount), promotedAt: new Date() },
        });
      transferCount += 1;
    }
  }

  console.log(`[ingest-ft] Upserted ${localCount} local levels + administrative_units rows.`);
  console.log(`[ingest-ft] Upserted ${transferCount} fiscal_transfer rows.`);

  // ─── Summary by grant type ─────────────────────────────────────
  console.log('[ingest-ft] Summary:');
  const totals = await sql<{ grant_type: string; row_count: number; total_npr: number }[]>`
    SELECT grant_type, COUNT(*) AS row_count, SUM(amount_npr::numeric) AS total_npr
    FROM local_government_fiscal_transfers
    WHERE fiscal_year_bs = ${fiscalYear}
    GROUP BY grant_type
    ORDER BY grant_type
  `;
  for (const t of totals) {
    console.log(`  - ${t.grant_type}: ${t.row_count} rows, Σ ${t.total_npr} NPR lakh`);
  }

  await sql.end();
  console.log('[ingest-ft] OK.');
}

main().catch((e: unknown) => {
  console.error('[ingest-ft] FAILED:', e instanceof Error ? e.stack : String(e));
  process.exit(1);
});
