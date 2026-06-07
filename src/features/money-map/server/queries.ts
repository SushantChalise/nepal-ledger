/**
 * Money Map server queries.
 *
 * Aggregates local_government_fiscal_transfers into a 3-column Sankey layout:
 *   Column A: "Federal Government" (single source node)
 *   Column B: 5 grant types (conditional_current, conditional_capital,
 *             special_current, special_capital, complementary_capital)
 *   Column C: 4 local-level types (metropolitan_city, sub_metropolitan_city,
 *             municipality, rural_municipality)
 *
 * All amounts are stored in NPR_thousand; the query sums them to a single
 * numeric that we format for display in the component.
 *
 * SCOPE: only the money-map feature. Reads from DB directly; does NOT edit
 * any existing repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { GrantType } from '@/lib/db/schema/enums';

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

/** Human-readable label for each grant type column. */
export const GRANT_TYPE_LABELS: Record<GrantType, string> = {
  equalization_minimum: 'Equalization (Minimum)',
  equalization_formula: 'Equalization (Formula)',
  equalization_performance: 'Equalization (Performance)',
  conditional_current: 'Conditional (Current)',
  conditional_capital: 'Conditional (Capital)',
  special_current: 'Special (Current)',
  special_capital: 'Special (Capital)',
  complementary_capital: 'Complementary (Capital)',
};

export const LOCAL_LEVEL_TYPE_LABELS: Record<string, string> = {
  metropolitan_city: 'Metropolitan City',
  sub_metropolitan_city: 'Sub-metropolitan City',
  municipality: 'Municipality',
  rural_municipality: 'Rural Municipality',
};

export type SankeyNodeData = {
  /** Unique stable identifier used as node key. */
  id: string;
  /** Display label. */
  label: string;
  /** Total amount in NPR thousands. */
  totalNprThousand: number;
  /** Which column (0=Federal, 1=GrantType, 2=LocalLevelType). */
  column: 0 | 1 | 2;
};

export type SankeyLinkData = {
  /** Matches SankeyNodeData.id of the source node. */
  sourceId: string;
  /** Matches SankeyNodeData.id of the target node. */
  targetId: string;
  /** Flow value in NPR thousands. */
  valueNprThousand: number;
};

export type SankeyData = {
  nodes: SankeyNodeData[];
  links: SankeyLinkData[];
  /** Reporting period from the data. */
  fiscalYearBs: string;
  /** Unit label — always 'NPR_thousand' from this table. */
  unit: string;
  /** Grand total across all transfers. */
  grandTotalNprThousand: number;
};

// ---------------------------------------------------------------------------
// Raw DB row shape from the aggregation query
// ---------------------------------------------------------------------------

// The raw aggregation row, validated at the DB boundary with Zod (the
// sanctioned alternative to an `as` cast on the untyped postgres-js result).
const TransferAggRowSchema = z.object({
  grant_type: z.string(),
  local_level_type: z.string().nullable(),
  total_amount: z.string(),
  fiscal_year_bs: z.string(),
  unit: z.string(),
});
type TransferAggRow = z.infer<typeof TransferAggRowSchema>;

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/**
 * Aggregates intergovernmental fiscal transfers for FY 2082/83 into
 * Sankey-ready nodes + links.
 *
 * Uses a single GROUP BY (grant_type, local_level_type) query and derives
 * the Federal→grantType totals by summing over local_level_type within each
 * grant type. amountNpr is a numeric string from Drizzle — coerced with
 * Number() after ruling out NaN.
 */
export async function getFiscalTransferSankeyData(): Promise<Result<SankeyData>> {
  const rawResult = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          t.grant_type,
          e.metadata->>'local_level_type' AS local_level_type,
          SUM(t.amount_npr)::text          AS total_amount,
          t.fiscal_year_bs,
          t.unit
        FROM local_government_fiscal_transfers t
        JOIN entities e
          ON e.id = t.local_level_entity_id
         AND e.kind = 'local_level'
        GROUP BY t.grant_type, e.metadata->>'local_level_type', t.fiscal_year_bs, t.unit
        ORDER BY t.grant_type, local_level_type
      `,
    ),
  );

  if (!rawResult.ok) return rawResult;

  // Validate the untyped postgres-js result at the boundary (post-Zod is the
  // sanctioned pattern — no `as` cast). The SQL column list above defines the
  // shape; Zod enforces it at runtime.
  const parsed = z.array(TransferAggRowSchema).safeParse(rawResult.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `money-map aggregation returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const rows: TransferAggRow[] = parsed.data;

  if (rows.length === 0) {
    return err({
      kind: 'NotFound',
      resource: 'local_government_fiscal_transfers',
      id: 'any row',
    });
  }

  // Pick fiscal year + unit from first row (homogeneous across the table).
  const firstRow = rows[0];
  if (!firstRow) {
    return err({
      kind: 'QueryFailed',
      detail: 'getFiscalTransferSankeyData: query returned empty rows array',
    });
  }
  const fiscalYearBs = firstRow.fiscal_year_bs;
  const unit = firstRow.unit;

  // Accumulate grant_type→total and grant_type→localLevelType→amount maps.
  const grantTotals = new Map<string, number>();
  const pairMap = new Map<string, Map<string, number>>();

  for (const row of rows) {
    const amount = Number(row.total_amount);
    if (!isFinite(amount)) continue;

    const localType = row.local_level_type ?? 'unknown';

    // Grant-type total (sum over all local-level types).
    const existing = grantTotals.get(row.grant_type) ?? 0;
    grantTotals.set(row.grant_type, existing + amount);

    // Per-pair map for grantType→localLevelType links.
    if (!pairMap.has(row.grant_type)) {
      pairMap.set(row.grant_type, new Map<string, number>());
    }
    const inner = pairMap.get(row.grant_type);
    if (inner !== undefined) {
      const pairExisting = inner.get(localType) ?? 0;
      inner.set(localType, pairExisting + amount);
    }
  }

  // Compute grand total.
  let grandTotal = 0;
  for (const v of grantTotals.values()) {
    grandTotal += v;
  }

  // --- Build nodes ---

  const federalNode: SankeyNodeData = {
    id: 'federal',
    label: 'Federal Government',
    totalNprThousand: grandTotal,
    column: 0,
  };

  const grantNodes: SankeyNodeData[] = [];
  for (const [grantType, total] of grantTotals.entries()) {
    grantNodes.push({
      id: `grant:${grantType}`,
      label: GRANT_TYPE_LABELS[grantType as GrantType] ?? grantType,
      totalNprThousand: total,
      column: 1,
    });
  }

  // Collect local-level types across all pairs.
  const localTypeTotals = new Map<string, number>();
  for (const innerMap of pairMap.values()) {
    for (const [localType, amount] of innerMap.entries()) {
      const ex = localTypeTotals.get(localType) ?? 0;
      localTypeTotals.set(localType, ex + amount);
    }
  }

  const localNodes: SankeyNodeData[] = [];
  for (const [localType, total] of localTypeTotals.entries()) {
    localNodes.push({
      id: `local:${localType}`,
      label: LOCAL_LEVEL_TYPE_LABELS[localType] ?? localType,
      totalNprThousand: total,
      column: 2,
    });
  }

  // --- Build links ---

  const links: SankeyLinkData[] = [];

  // Federal → each grant type.
  for (const grantNode of grantNodes) {
    links.push({
      sourceId: federalNode.id,
      targetId: grantNode.id,
      valueNprThousand: grantNode.totalNprThousand,
    });
  }

  // Each grant type → each local-level type.
  for (const [grantType, innerMap] of pairMap.entries()) {
    for (const [localType, amount] of innerMap.entries()) {
      links.push({
        sourceId: `grant:${grantType}`,
        targetId: `local:${localType}`,
        valueNprThousand: amount,
      });
    }
  }

  const nodes: SankeyNodeData[] = [federalNode, ...grantNodes, ...localNodes];

  return ok({
    nodes,
    links,
    fiscalYearBs,
    unit,
    grandTotalNprThousand: grandTotal,
  });
}
