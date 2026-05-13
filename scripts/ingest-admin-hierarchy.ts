/**
 * Parse the admin-hierarchy CSV → staging JSON for wards + polling stations.
 *
 * Source: `Financial Data/Administrative Division/administrative_hierarchy_FINAL.csv`
 *   - 10,263 rows = 7 provinces × 77 districts × 719 municipalities × ~6,176
 *     wards × ~10,203 polling stations × actual voter counts
 *   - Derived from the voter database (17.8M records)
 *
 * The canonical 753-row local-level table is in staging-data/fiscal-transfer-canonical/.
 * This script joins the CSV's per-ward rows to the canonical local levels by name
 * (with fuzzy fallback via Worker ε's municipality resolver if available).
 *
 * Output: `staging-data/admin-hierarchy/wards-and-polling-stations.json`
 *
 * Usage:
 *   pnpm exec tsx scripts/ingest-admin-hierarchy.ts [--dry-run]
 *
 * The --dry-run mode emits the JSON but does not connect to the DB. Live
 * ingest (DB writes) is handled by the unified `scripts/apply-all.ts`
 * wrapper, which the user runs once authorized.
 */

import 'dotenv/config';

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { argv } from 'node:process';

import { config as dotenvConfig } from 'dotenv';
import { parse } from 'csv-parse/sync';

dotenvConfig({ path: '.env.local', override: true });

const csvPath = 'Financial Data/Administrative Division/administrative_hierarchy_FINAL.csv';
const stagingDir = 'staging-data/admin-hierarchy';

// ─── Types ────────────────────────────────────────────────────────

type CsvRow = {
  Province: string;
  District: string;
  'Constituency No.': string;
  'Municipality/Rural Municipality': string;
  'Municipality Type': string;
  'Rural/Urban': string;
  'Ward No.': string;
  'Polling Station': string;
  'Voter Count': string;
};

type WardKey = {
  provinceNe: string;
  districtNe: string;
  localLevelNe: string;
  wardNo: number;
};

type WardRollup = WardKey & {
  pollingStations: Array<{
    name: string;
    voterCount: number;
  }>;
  totalVoterCount: number;
  constituencyNo: string | null;
  ruralUrban: string | null;
};

// ─── Main ─────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log(`[admin] reading ${csvPath}`);
  const raw = await readFile(csvPath, 'utf-8');
  const records = parse(raw, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
  }) as CsvRow[];

  console.log(`[admin] parsed ${records.length} CSV rows`);

  // Build ward-level rollups: each ward → list of polling stations + total voters
  const wardMap = new Map<string, WardRollup>();
  let skippedBlankWard = 0;
  let skippedBlankPolling = 0;

  for (const r of records) {
    const provinceNe = r['Province']?.trim() ?? '';
    const districtNe = r['District']?.trim() ?? '';
    const localLevelNe = r['Municipality/Rural Municipality']?.trim() ?? '';
    const wardRaw = r['Ward No.']?.trim() ?? '';
    const pollingStation = r['Polling Station']?.trim() ?? '';
    const constituencyNo = r['Constituency No.']?.trim() || null;
    const ruralUrban = r['Rural/Urban']?.trim() || null;
    const voterCount = parseInt(r['Voter Count']?.replace(/,/g, '') ?? '0', 10);

    if (!provinceNe || !districtNe || !localLevelNe) continue;

    const wardNo = parseInt(wardRaw, 10);
    if (!Number.isFinite(wardNo)) {
      skippedBlankWard += 1;
      continue;
    }

    const key = `${provinceNe}|${districtNe}|${localLevelNe}|${wardNo}`;
    let ward = wardMap.get(key);
    if (!ward) {
      ward = {
        provinceNe,
        districtNe,
        localLevelNe,
        wardNo,
        pollingStations: [],
        totalVoterCount: 0,
        constituencyNo,
        ruralUrban,
      };
      wardMap.set(key, ward);
    }

    if (!pollingStation) {
      skippedBlankPolling += 1;
      continue;
    }

    ward.pollingStations.push({
      name: pollingStation,
      voterCount: Number.isFinite(voterCount) ? voterCount : 0,
    });
    ward.totalVoterCount += Number.isFinite(voterCount) ? voterCount : 0;
    // Prefer non-null over null when merging
    if (!ward.constituencyNo && constituencyNo) ward.constituencyNo = constituencyNo;
    if (!ward.ruralUrban && ruralUrban) ward.ruralUrban = ruralUrban;
  }

  const wards = Array.from(wardMap.values());
  const pollingStationCount = wards.reduce((acc, w) => acc + w.pollingStations.length, 0);
  const totalVoters = wards.reduce((acc, w) => acc + w.totalVoterCount, 0);
  const distinctLocalLevels = new Set(wards.map((w) => `${w.districtNe}|${w.localLevelNe}`)).size;

  console.log(`[admin] ward rollups: ${wards.length}`);
  console.log(`[admin] polling stations: ${pollingStationCount}`);
  console.log(`[admin] total voters: ${totalVoters.toLocaleString()}`);
  console.log(
    `[admin] distinct local levels: ${distinctLocalLevels} (canonical = 753; gap reveals name variants)`,
  );
  console.log(`[admin] skipped rows (blank ward): ${skippedBlankWard}`);
  console.log(`[admin] skipped rows (blank polling station): ${skippedBlankPolling}`);

  // Write staging JSON
  await mkdir(stagingDir, { recursive: true });
  const outPath = path.join(stagingDir, 'wards-and-polling-stations.json');
  await writeFile(
    outPath,
    JSON.stringify(
      {
        sourceFile: csvPath,
        parsedAt: new Date().toISOString(),
        rowCount: records.length,
        wardCount: wards.length,
        pollingStationCount,
        totalVoters,
        distinctLocalLevels,
        // Note: per the source README, Municipality Type classification is broken
        // (Nepali-script names weren't matched by the English-suffix script). The
        // unified apply-all wrapper joins this against the canonical 753-row table
        // from staging-data/fiscal-transfer-canonical/ to fix the classification.
        notes: [
          'Municipality Type from source CSV is unreliable (classifies all as Rural Municipality).',
          'Constituency No. is sparse (~10% coverage); upstream fix uses Combined_Constituency_Master_Table.csv.',
          'Joins to canonical local-level table by (district_ne, local_level_ne).',
        ],
        wards,
      },
      null,
      2,
    ),
  );
  console.log(`[admin] wrote ${outPath}`);
}

main().catch((e: unknown) => {
  console.error('[admin] FAILED:', e instanceof Error ? e.stack : String(e));
  process.exit(1);
});
