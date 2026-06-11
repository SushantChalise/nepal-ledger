/**
 * Pure origin-province → destination-region flow model for the migration Sankey
 * (View C, the Atlas's Figure 6).
 *
 * Plain module — NOT `'use client'` and NOT a server module: it must import no
 * `server-only` code (the DB client is `server-only`), so it can be unit tested
 * and shared by both the Server query and the client Sankey component. The SQL
 * lives in `server/queries.ts`; the roll-up math lives here.
 */

import { DISTRICT_TO_PROVINCE, PROVINCE_ORDER, type ProvinceName } from './district-province';

// Census destination-region code → a consolidated Sankey destination. The 13
// census buckets are collapsed to the 6 the Atlas's flow diagram uses so the
// diagram stays legible (EU + other-Europe → Europe; SAARC + other-Asian →
// Other Asia; the long tail → Other). `id` is the node id; `order` fixes the
// right-column stacking.
const SANKEY_DESTINATIONS: Record<string, { id: string; label: string; order: number }> = {
  'a-india': { id: 'india', label: 'India', order: 0 },
  'd-midleast': { id: 'middle-east', label: 'Middle East', order: 1 },
  'c-asean': { id: 'asean', label: 'ASEAN', order: 2 },
  'f-eucntry': { id: 'europe', label: 'Europe', order: 3 },
  'g-othreuropn': { id: 'europe', label: 'Europe', order: 3 },
  'b-saarc': { id: 'other-asia', label: 'Other Asia', order: 4 },
  'e-othrasian': { id: 'other-asia', label: 'Other Asia', order: 4 },
  'h-northamericn': { id: 'other', label: 'Other', order: 5 },
  'i-southamericn': { id: 'other', label: 'Other', order: 5 },
  'j-african': { id: 'other', label: 'Other', order: 5 },
  'k-pacific': { id: 'other', label: 'Other', order: 5 },
  'l-other': { id: 'other', label: 'Other', order: 5 },
  'm-notstd': { id: 'other', label: 'Other', order: 5 },
};

/** A Sankey node: an origin province (column 0) or destination region (column 1). */
export type FlowNode = {
  /** Stable node id, e.g. `p-Koshi` or `d-india`. */
  id: string;
  label: string;
  /** 0 = origin province (left), 1 = destination region (right). */
  column: 0 | 1;
  /** Absent population flowing through this node (people). */
  people: number;
};

/** A Sankey link: province → destination region, weighted by absent population. */
export type FlowLink = {
  sourceId: string;
  targetId: string;
  people: number;
};

export type MigrationFlowGraph = {
  nodes: FlowNode[];
  links: FlowLink[];
  /** Total absent population across the flow (people). */
  totalPeople: number;
  censusYearAd: string;
};

/** A pre-aggregation flow row: origin district, consolidated region, people. */
export type FlowInputRow = { district: string | null; regionCode: string; people: number };

/**
 * Pure roll-up: district×region rows → an origin-province → destination-region
 * Sankey graph. Province resolution uses the authoritative `DISTRICT_TO_PROVINCE`
 * map; a district that does not resolve, or a region code outside the known
 * buckets, is skipped rather than bucketed wrongly. Returns null when no
 * positive flow remains.
 */
export function buildMigrationFlowGraph(
  rows: ReadonlyArray<FlowInputRow>,
  censusYearAd = '2021',
): MigrationFlowGraph | null {
  const linkPeople = new Map<string, number>(); // `${province}|${destId}` → people
  const provinceTotals = new Map<ProvinceName, number>();
  const destTotals = new Map<string, { label: string; order: number; people: number }>();
  let totalPeople = 0;

  for (const row of rows) {
    const province = row.district !== null ? DISTRICT_TO_PROVINCE[row.district] : undefined;
    const dest = SANKEY_DESTINATIONS[row.regionCode];
    if (
      province === undefined ||
      dest === undefined ||
      !Number.isFinite(row.people) ||
      row.people <= 0
    ) {
      continue;
    }
    const key = `${province}|${dest.id}`;
    linkPeople.set(key, (linkPeople.get(key) ?? 0) + row.people);
    provinceTotals.set(province, (provinceTotals.get(province) ?? 0) + row.people);
    const dt = destTotals.get(dest.id) ?? { label: dest.label, order: dest.order, people: 0 };
    dt.people += row.people;
    destTotals.set(dest.id, dt);
    totalPeople += row.people;
  }

  if (totalPeople <= 0) return null;

  // Nodes: provinces (column 0) in fixed geographic order, then destinations
  // (column 1) in their stacking order. Only nodes with flow are included.
  const provinceNodes: FlowNode[] = PROVINCE_ORDER.filter(
    (p) => (provinceTotals.get(p) ?? 0) > 0,
  ).map((p) => ({ id: `p-${p}`, label: p, column: 0, people: provinceTotals.get(p) ?? 0 }));
  const destNodes: FlowNode[] = [...destTotals.entries()]
    .sort((a, b) => a[1].order - b[1].order)
    .map(([id, d]) => ({ id: `d-${id}`, label: d.label, column: 1, people: d.people }));
  const links: FlowLink[] = [...linkPeople.entries()]
    .map(([key, people]) => {
      const [province, destId] = key.split('|');
      return { sourceId: `p-${province}`, targetId: `d-${destId}`, people };
    })
    .sort((a, b) => b.people - a.people);

  return { nodes: [...provinceNodes, ...destNodes], links, totalPeople, censusYearAd };
}
