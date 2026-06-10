/**
 * Money Flow server queries — the national money-flow Sankey.
 *
 * This is the capstone view: it ties the now-live macro flows into ONE picture of
 * money entering Nepal, circulating, and leaving. The defining insight it must
 * surface: **remittance is the dominant inflow and roughly funds the merchandise
 * trade deficit** — Nepal's structural macro story.
 *
 * THREE SOURCES, THREE UNITS, ONE DISPLAY UNIT (ADR-0011 — critical):
 *   - Remittance inflow  — `approved_indicator_values` slug `dne-remittance-inflow`,
 *                          unit `npr_million`     → ÷ 1,000     → NPR bn
 *   - Foreign aid        — `foreign_aid_facts` latest edition, unit `npr_lakh`
 *                          (grant + loan)         → ÷ 10,000    → NPR bn
 *   - Merchandise trade  — `dne_facts` customs imports/exports, unit `npr_thousand`
 *                          (commodity dimension)  → ÷ 1,000,000 → NPR bn
 * Every magnitude is converted to **NPR billion** (via `../format`) BEFORE it
 * enters a node or link. A Sankey with mixed units is meaningless.
 *
 * NODE MODEL — a Money-In → Nepal Economy → Money-Out flow (3 columns):
 *   Column 0 (sources):  Remittance, Foreign Aid (grant+loan), Merchandise Exports
 *   Column 1 (hub):      Nepal Economy
 *   Column 2 (sinks):    Merchandise Imports, Retained in the economy
 * Inflows rarely equal merchandise imports, so the gap is shown HONESTLY as an
 * explicitly-labelled "Retained in the economy" residual node (inflows − imports),
 * NOT folded silently into another flow. If imports were ever to exceed inflows,
 * the residual is clamped to 0 and the imbalance is reported via `outflowsExceedInflows`.
 *
 * FISCAL-YEAR MISMATCH (stated honestly on the page): remittance + trade are
 * FY 2081/82; the foreign-aid edition is FY 2077/78. The flows are NOT all the
 * same year — `aidFiscalYearBs` is carried separately so the page can caveat it.
 *
 * Each source is fetched independently and may be absent: a missing aid table
 * yields `aid: null` rather than failing the whole page. The query returns a
 * top-level error only when BOTH headline inflows (remittance) AND merchandise
 * trade are unavailable — i.e. there is no story to tell.
 *
 * SCOPE: only the money-flow feature. Reads from the DB directly (read-only); does
 * NOT edit any existing repository in src/lib/db/repositories/*.
 */

import { sql } from 'drizzle-orm';
import { z } from 'zod';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import { err, ok, type Result } from '@/lib/errors';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';

import { lakhToBillion, millionToBillion, thousandToBillion } from '../format';

// ---------------------------------------------------------------------------
// Source identifiers (the exact slugs / measures probed)
// ---------------------------------------------------------------------------

/** Remittance inflow — approved indicator (npr_million). */
export const REMITTANCE_SLUG = 'dne-remittance-inflow';
/** Customs merchandise imports — dne_facts base measure (npr_thousand). */
export const IMPORTS_SLUG = 'customs-merchandise-imports';
/** Customs merchandise exports — dne_facts base measure (npr_thousand). */
export const EXPORTS_SLUG = 'customs-merchandise-exports';
/** Commodity dimension — the canonical aggregate for a trade period. */
export const COMMODITY_DIMENSION_KIND = 'commodity';
/** Foreign-aid grant measure — foreign_aid_facts (npr_lakh / npr_thousand by edition). */
export const AID_GRANT_SLUG = 'foreign-aid-grant';
/** Foreign-aid loan measure — foreign_aid_facts. */
export const AID_LOAN_SLUG = 'foreign-aid-loan';
/**
 * Foreign-aid dimension to sum over. The `donor` and `sector` cuts of the same
 * (measure, period) are the SAME aggregate (each partitions the same total), so
 * we MUST pick exactly one to avoid double-counting. `donor` is canonical here.
 */
export const AID_DIMENSION_KIND = 'donor';
/** Default trade / remittance reporting period — the FY 2081/82 annual figures. */
export const DEFAULT_PERIOD_BS = '2081/82';

// ---------------------------------------------------------------------------
// Output types — all magnitudes are NPR BILLION (already normalized)
// ---------------------------------------------------------------------------

/** Column index in the Sankey: 0 = inflow source, 1 = economy hub, 2 = outflow sink. */
export type FlowColumn = 0 | 1 | 2;

export type FlowNode = {
  /** Stable identifier used as the node key + link endpoint. */
  id: string;
  /** Display label. */
  label: string;
  /** Total magnitude in NPR billion (already unit-normalized). */
  valueBillion: number;
  /** Which column the node sits in. */
  column: FlowColumn;
};

export type FlowLink = {
  /** Matches a FlowNode.id. */
  sourceId: string;
  /** Matches a FlowNode.id. */
  targetId: string;
  /** Flow magnitude in NPR billion (already unit-normalized). */
  valueBillion: number;
};

/** One inflow source's headline figure (for the KPI strip + prose). */
export type InflowFigure = {
  /** NPR billion (normalized). */
  valueBillion: number;
  /** Confidence grade of the underlying source. */
  confidence: ConfidenceGrade;
  /** BS reporting-period label for this figure. */
  fiscalYearBs: string;
};

export type MoneyFlowData = {
  /** Sankey nodes (3 columns). */
  nodes: FlowNode[];
  /** Sankey links. */
  links: FlowLink[];

  // --- Headline figures (NPR billion), for the KPI strip + prose ---
  /** Remittance inflow. Null when the indicator has no approved row. */
  remittance: InflowFigure | null;
  /** Foreign aid = grant + loan, summed. Null when the table is empty. */
  aid: InflowFigure | null;
  /** Merchandise exports. */
  exportsBillion: number;
  /** Merchandise imports. */
  importsBillion: number;
  /** Merchandise trade deficit = imports − exports (positive = deficit), NPR bn. */
  tradeDeficitBillion: number;
  /** Sum of all available inflows (remittance + aid + exports), NPR bn. */
  totalInflowsBillion: number;
  /** Residual retained in the economy = inflows − imports (clamped ≥ 0), NPR bn. */
  retainedBillion: number;
  /**
   * True when merchandise imports exceed total inflows (residual clamped to 0).
   * The page surfaces this honestly rather than drawing a negative band.
   */
  outflowsExceedInflows: boolean;
  /** Remittance as a share of total inflows (0–100), or null when no remittance. */
  remittanceSharePct: number | null;

  // --- Provenance ---
  /** BS reporting period for the trade + remittance figures (e.g. "2081/82"). */
  periodBs: string;
  /** BS fiscal year of the foreign-aid edition (differs — e.g. "2077/78"). Null when no aid. */
  aidFiscalYearBs: string | null;
  /** Confidence grade for the merchandise-trade figures (customs → 'A'). */
  tradeConfidence: ConfidenceGrade;
};

// ---------------------------------------------------------------------------
// DB boundary schemas (Zod — sanctioned alternative to an `as` cast on the
// untyped postgres-js result; CONTEXT_RULES §"Cast Escape Hatches" (a)).
// ---------------------------------------------------------------------------

const RemittanceRowSchema = z.object({
  value: z.string(),
  unit: z.string(),
  fiscal_year_bs: z.string().nullable(),
  reporting_period_bs: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});

const TradeTotalsRowSchema = z.object({
  slug: z.string(),
  total: z.string().nullable(),
  unit: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});

const AidTotalsRowSchema = z.object({
  slug: z.string(),
  total: z.string().nullable(),
  unit: z.string(),
  fiscal_year_bs: z.string().nullable(),
  reporting_period_bs: z.string(),
  confidence_grade: z.enum(['A', 'B', 'C']),
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Coerce a postgres numeric string to a finite number, else 0. */
function toFinite(s: string | null | undefined): number {
  if (s === null || s === undefined) return 0;
  const n = Number(s);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Convert an at-rest value to NPR billion using the converter that matches the
 * row's declared unit. Returns null for an unrecognised unit so the caller can
 * skip the flow rather than silently mis-scale it (ADR-0011 — never guess units).
 */
function normalizeToBillion(value: number, unit: string): number | null {
  switch (unit) {
    case 'npr_million':
      return millionToBillion(value);
    case 'npr_lakh':
      return lakhToBillion(value);
    case 'npr_thousand':
      return thousandToBillion(value);
    case 'npr_billion':
      return Number.isFinite(value) ? value : 0;
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Per-source fetchers (each returns a typed Result; absence ≠ error)
// ---------------------------------------------------------------------------

/**
 * Latest remittance inflow for `periodBs`. Returns ok(null) when the indicator
 * has no approved row for that period — a missing source is not an error.
 */
async function fetchRemittance(periodBs: string): Promise<Result<InflowFigure | null>> {
  const raw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          v.value::text             AS value,
          v.unit                    AS unit,
          v.fiscal_year_bs          AS fiscal_year_bs,
          v.reporting_period_bs     AS reporting_period_bs,
          v.confidence_grade        AS confidence_grade
        FROM approved_indicator_values v
        JOIN indicators i ON i.id = v.indicator_id
        WHERE i.slug = ${REMITTANCE_SLUG}
          AND v.reporting_period_bs = ${periodBs}
        ORDER BY v.revision_number DESC
        LIMIT 1
      `,
    ),
  );
  if (!raw.ok) return raw;

  const parsed = z.array(RemittanceRowSchema).safeParse(raw.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `money-flow remittance query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  const row = parsed.data[0];
  if (!row) return ok(null);

  const billion = normalizeToBillion(toFinite(row.value), row.unit);
  if (billion === null) {
    return err({
      kind: 'QueryFailed',
      detail: `money-flow remittance has unrecognised unit '${row.unit}' (expected npr_million)`,
    });
  }
  return ok({
    valueBillion: billion,
    confidence: row.confidence_grade,
    fiscalYearBs: row.fiscal_year_bs ?? row.reporting_period_bs,
  });
}

/**
 * Merchandise import + export totals for `periodBs`, summed over the commodity
 * dimension (the canonical aggregate — it equals the country-dimension sum).
 * Returns ok(null) when neither measure has any row for the period.
 */
async function fetchTrade(periodBs: string): Promise<
  Result<{
    importsBillion: number;
    exportsBillion: number;
    confidence: ConfidenceGrade;
  } | null>
> {
  const raw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          base_indicator_slug    AS slug,
          SUM(value)::text       AS total,
          MIN(unit)              AS unit,
          MIN(confidence_grade)  AS confidence_grade
        FROM dne_facts
        WHERE base_indicator_slug IN (${IMPORTS_SLUG}, ${EXPORTS_SLUG})
          AND dimension_kind = ${COMMODITY_DIMENSION_KIND}
          AND reporting_period_bs = ${periodBs}
        GROUP BY base_indicator_slug
      `,
    ),
  );
  if (!raw.ok) return raw;

  const parsed = z.array(TradeTotalsRowSchema).safeParse(raw.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `money-flow trade totals query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  if (parsed.data.length === 0) return ok(null);

  const importsRow = parsed.data.find((r) => r.slug === IMPORTS_SLUG);
  const exportsRow = parsed.data.find((r) => r.slug === EXPORTS_SLUG);

  const importsBillion =
    normalizeToBillion(toFinite(importsRow?.total ?? null), 'npr_thousand') ?? 0;
  const exportsBillion =
    normalizeToBillion(toFinite(exportsRow?.total ?? null), 'npr_thousand') ?? 0;

  return ok({
    importsBillion,
    exportsBillion,
    confidence: importsRow?.confidence_grade ?? exportsRow?.confidence_grade ?? 'A',
  });
}

/**
 * Foreign aid = grant + loan for the LATEST edition, summed over the `donor`
 * dimension only (the donor and sector cuts are the same aggregate). Each
 * edition is unit-homogeneous, but to be ADR-0011-safe each measure row is
 * normalized via its own declared `unit`. Returns ok(null) when the table is
 * empty.
 *
 * "Latest edition" = the row group with the greatest reporting_period_bs. We
 * read every grant/loan/donor row, pick the max period, and sum within it.
 */
async function fetchAid(): Promise<
  Result<{ aidBillion: number; fiscalYearBs: string; confidence: ConfidenceGrade } | null>
> {
  const raw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT
          base_indicator_slug    AS slug,
          SUM(value)::text       AS total,
          MIN(unit)              AS unit,
          MIN(fiscal_year_bs)    AS fiscal_year_bs,
          reporting_period_bs    AS reporting_period_bs,
          MIN(confidence_grade)  AS confidence_grade
        FROM foreign_aid_facts
        WHERE base_indicator_slug IN (${AID_GRANT_SLUG}, ${AID_LOAN_SLUG})
          AND dimension_kind = ${AID_DIMENSION_KIND}
        GROUP BY base_indicator_slug, reporting_period_bs
        ORDER BY reporting_period_bs DESC
      `,
    ),
  );
  if (!raw.ok) return raw;

  const parsed = z.array(AidTotalsRowSchema).safeParse(raw.value);
  if (!parsed.success) {
    return err({
      kind: 'QueryFailed',
      detail: `money-flow aid totals query returned unexpected row shape: ${parsed.error.message}`,
    });
  }
  if (parsed.data.length === 0) return ok(null);

  // Rows are ordered by reporting_period_bs DESC; the first row's period is the
  // latest edition. Sum only rows in that edition (grant + loan).
  const latestPeriod = parsed.data[0]?.reporting_period_bs;
  if (latestPeriod === undefined) return ok(null);

  const editionRows = parsed.data.filter((r) => r.reporting_period_bs === latestPeriod);

  let aidBillion = 0;
  let fiscalYearBs = latestPeriod;
  let confidence: ConfidenceGrade = 'B';
  for (const row of editionRows) {
    const billion = normalizeToBillion(toFinite(row.total), row.unit);
    if (billion === null) {
      return err({
        kind: 'QueryFailed',
        detail: `money-flow aid has unrecognised unit '${row.unit}' (expected npr_lakh / npr_thousand)`,
      });
    }
    aidBillion += billion;
    if (row.fiscal_year_bs) fiscalYearBs = row.fiscal_year_bs;
    confidence = row.confidence_grade;
  }

  return ok({ aidBillion, fiscalYearBs, confidence });
}

// ---------------------------------------------------------------------------
// Public query
// ---------------------------------------------------------------------------

/**
 * Assemble the national money-flow picture for `periodBs` (default FY 2081/82):
 * remittance + aid + exports inflows, the merchandise imports outflow, the
 * residual retained in the economy, and a 3-column Sankey graph of the whole.
 *
 * Every magnitude is NPR billion (unit-normalized at the boundary). Returns
 * NotFound only when BOTH remittance AND merchandise trade are unavailable
 * (no story); a missing aid edition degrades to `aid: null`. Never throws —
 * callers render typed states.
 */
export async function getMoneyFlowData(
  periodBs: string = DEFAULT_PERIOD_BS,
): Promise<Result<MoneyFlowData>> {
  const [remResult, tradeResult, aidResult] = await Promise.all([
    fetchRemittance(periodBs),
    fetchTrade(periodBs),
    fetchAid(),
  ]);
  if (!remResult.ok) return remResult;
  if (!tradeResult.ok) return tradeResult;
  if (!aidResult.ok) return aidResult;

  const remittance = remResult.value;
  const trade = tradeResult.value;
  const aidRaw = aidResult.value;

  // No story to tell when neither the dominant inflow nor merchandise trade exists.
  if (remittance === null && trade === null) {
    return err({
      kind: 'NotFound',
      resource: 'money-flow sources',
      id: `remittance + customs trade, reporting_period_bs=${periodBs}`,
    });
  }

  const exportsBillion = trade?.exportsBillion ?? 0;
  const importsBillion = trade?.importsBillion ?? 0;
  const tradeConfidence = trade?.confidence ?? 'A';
  const tradeDeficitBillion = importsBillion - exportsBillion;

  const aid: InflowFigure | null =
    aidRaw === null
      ? null
      : {
          valueBillion: aidRaw.aidBillion,
          confidence: aidRaw.confidence,
          fiscalYearBs: aidRaw.fiscalYearBs,
        };

  // Total inflows = remittance + aid + exports (only the parts that exist).
  const totalInflowsBillion =
    (remittance?.valueBillion ?? 0) + (aid?.valueBillion ?? 0) + exportsBillion;

  // Residual retained in the economy = inflows − merchandise imports. Clamped to
  // 0 and flagged when imports exceed inflows (we never draw a negative band).
  const residual = totalInflowsBillion - importsBillion;
  const outflowsExceedInflows = residual < 0;
  const retainedBillion = outflowsExceedInflows ? 0 : residual;

  const remittanceSharePct =
    remittance !== null && totalInflowsBillion > 0
      ? (remittance.valueBillion / totalInflowsBillion) * 100
      : null;

  // --- Build the 3-column Sankey graph ---
  const ECONOMY_ID = 'economy';
  const nodes: FlowNode[] = [];
  const links: FlowLink[] = [];

  // Column 0 — inflow sources → economy hub.
  if (remittance !== null && remittance.valueBillion > 0) {
    nodes.push({
      id: 'remittance',
      label: 'Remittance',
      valueBillion: remittance.valueBillion,
      column: 0,
    });
    links.push({
      sourceId: 'remittance',
      targetId: ECONOMY_ID,
      valueBillion: remittance.valueBillion,
    });
  }
  if (aid !== null && aid.valueBillion > 0) {
    nodes.push({
      id: 'aid',
      label: 'Foreign aid (grants + loans)',
      valueBillion: aid.valueBillion,
      column: 0,
    });
    links.push({ sourceId: 'aid', targetId: ECONOMY_ID, valueBillion: aid.valueBillion });
  }
  if (exportsBillion > 0) {
    nodes.push({
      id: 'exports',
      label: 'Merchandise exports',
      valueBillion: exportsBillion,
      column: 0,
    });
    links.push({ sourceId: 'exports', targetId: ECONOMY_ID, valueBillion: exportsBillion });
  }

  // Column 1 — the economy hub. Its through-value equals total inflows.
  nodes.push({
    id: ECONOMY_ID,
    label: 'Nepal economy',
    valueBillion: totalInflowsBillion,
    column: 1,
  });

  // Column 2 — outflow / retained sinks.
  if (importsBillion > 0) {
    nodes.push({
      id: 'imports',
      label: 'Merchandise imports',
      valueBillion: importsBillion,
      column: 2,
    });
    links.push({ sourceId: ECONOMY_ID, targetId: 'imports', valueBillion: importsBillion });
  }
  if (retainedBillion > 0) {
    nodes.push({
      id: 'retained',
      label: 'Retained in the economy',
      valueBillion: retainedBillion,
      column: 2,
    });
    links.push({ sourceId: ECONOMY_ID, targetId: 'retained', valueBillion: retainedBillion });
  }

  return ok({
    nodes,
    links,
    remittance,
    aid,
    exportsBillion,
    importsBillion,
    tradeDeficitBillion,
    totalInflowsBillion,
    retainedBillion,
    outflowsExceedInflows,
    remittanceSharePct,
    periodBs,
    aidFiscalYearBs: aid?.fiscalYearBs ?? null,
    tradeConfidence,
  });
}
