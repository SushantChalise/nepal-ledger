/**
 * Approved Indicator Values repository.
 *
 * Production table the Pulse, Money Map, Fact Ledger and stories read.
 * Inserts happen exclusively through the validation job's promote path;
 * features never write here directly.
 */

import { and, desc, eq, gte, sql } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import type { ConfidenceGrade, ReportingPeriodType } from '@/lib/db/schema/enums';
import {
  approvedIndicatorValues,
  type ApprovedIndicatorValueRow,
  type NewApprovedIndicatorValueRow,
} from '@/lib/db/schema/indicator-values';
import type { IndicatorRow } from '@/lib/db/schema/indicators';
import { indicators } from '@/lib/db/schema/indicators';
import type { SourceDocumentRow } from '@/lib/db/schema/source-documents';
import { sourceDocuments } from '@/lib/db/schema/source-documents';
import { sourceRegistry } from '@/lib/db/schema/source-registry';
import { err, ok, type Result } from '@/lib/errors';

export async function insertApprovedIndicatorValue(
  input: NewApprovedIndicatorValueRow,
): Promise<Result<ApprovedIndicatorValueRow>> {
  const inserted = await safeQuery(() =>
    db().insert(approvedIndicatorValues).values(input).returning(),
  );
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertApprovedIndicatorValue: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Find the latest approved row (highest revision_number) for an indicator
 * and a (periodType, periodBs). Returns ok(null) — not NotFound — when no
 * row matches: the validator's DuplicateCheck and RevisionFlowCheck treat
 * "no prior approved row" as a successful negative.
 */
export async function findLatestApprovedByPeriod(
  indicatorId: string,
  periodType: ReportingPeriodType,
  periodBs: string,
): Promise<Result<ApprovedIndicatorValueRow | null>> {
  const queried = await safeQuery(() =>
    db().query.approvedIndicatorValues.findFirst({
      where: and(
        eq(approvedIndicatorValues.indicatorId, indicatorId),
        eq(approvedIndicatorValues.reportingPeriodType, periodType),
        eq(approvedIndicatorValues.reportingPeriodBs, periodBs),
      ),
      orderBy: [desc(approvedIndicatorValues.revisionNumber)],
    }),
  );
  if (!queried.ok) return queried;
  return ok(queried.value ?? null);
}

/**
 * Trailing window of approved values for plausibility-band computation. The
 * validator computes mean/stdev across this window and warns rows that fall
 * outside ±5 stdev. Window is bounded by `since` (ad start) inclusive.
 */
export async function listApprovedTrailingForIndicator(
  indicatorId: string,
  since: Date,
): Promise<Result<ApprovedIndicatorValueRow[]>> {
  return safeQuery(() =>
    db().query.approvedIndicatorValues.findMany({
      where: and(
        eq(approvedIndicatorValues.indicatorId, indicatorId),
        gte(approvedIndicatorValues.reportingPeriodAdEnd, since),
      ),
      orderBy: [desc(approvedIndicatorValues.reportingPeriodAdEnd)],
    }),
  );
}

/**
 * Shape returned by listApprovedWithIndicator — one row per approved value
 * with the joined indicator metadata and source document metadata.
 */
export type ApprovedIndicatorWithMeta = {
  value: ApprovedIndicatorValueRow;
  indicator: IndicatorRow;
  sourceDocument: SourceDocumentRow;
};

/**
 * Read all approved indicator values joined to their indicator and source
 * document. Intended for the Pulse page; ordered by indicator category then
 * indicator slug for stable presentation.
 *
 * Returns ok([]) when the table is empty — callers render an empty state.
 * Only queries approved_indicator_values and indicators; does not touch
 * staging.
 */
export async function listApprovedWithIndicator(): Promise<Result<ApprovedIndicatorWithMeta[]>> {
  const queried = await safeQuery(() =>
    db()
      .select({
        value: approvedIndicatorValues,
        indicator: indicators,
        sourceDocument: sourceDocuments,
      })
      .from(approvedIndicatorValues)
      .innerJoin(indicators, eq(approvedIndicatorValues.indicatorId, indicators.id))
      .innerJoin(sourceDocuments, eq(approvedIndicatorValues.sourceDocumentId, sourceDocuments.id))
      .orderBy(indicators.category, indicators.slug),
  );
  if (!queried.ok) return queried;
  return ok(queried.value);
}

/**
 * Flat, render-ready row for the Fact Ledger index. Unlike
 * `listApprovedWithIndicator` (which returns whole Drizzle row objects and
 * joins only `source_documents`), this projects the exact columns the public
 * ledger table needs AND joins through to `source_registry` so the visible
 * "source" is the dataset's agency + dataset name — the three NRB feeds
 * (`nrb-dne-xlsx`, `nrb-ncpi-table`, `nrb-cmefs-monthly`) are otherwise
 * indistinguishable via `indicators.source_agency` alone (all "Nepal Rastra
 * Bank"). Drizzle types every selected column, so no Zod boundary is needed
 * here (the result is fully typed, not the untyped `db().execute` path).
 */
export type FactLedgerEntry = {
  indicatorSlug: string;
  indicatorNameEn: string;
  category: IndicatorRow['category'];
  unit: string;
  value: string;
  confidence: ConfidenceGrade;
  reportingPeriodBs: string;
  reportingPeriodType: ReportingPeriodType;
  sourceAgency: string;
  sourceAgencyShort: string;
  sourceDataset: string;
  sourceId: string;
};

/**
 * Read every approved indicator value joined to its indicator and the
 * registered source feed, projected to {@link FactLedgerEntry}. Ordered by
 * indicator category then slug for stable, DB-driven presentation (the page
 * groups by category without re-sorting).
 *
 * Returns ok([]) when the table is empty — the page renders an empty state.
 * Reads production only (`approved_indicator_values`); never staging.
 */
export async function listFactLedgerEntries(): Promise<Result<FactLedgerEntry[]>> {
  const queried = await safeQuery(() =>
    db()
      .select({
        indicatorSlug: indicators.slug,
        indicatorNameEn: indicators.nameEn,
        category: indicators.category,
        unit: indicators.unit,
        value: approvedIndicatorValues.value,
        confidence: approvedIndicatorValues.confidenceGrade,
        reportingPeriodBs: approvedIndicatorValues.reportingPeriodBs,
        reportingPeriodType: approvedIndicatorValues.reportingPeriodType,
        sourceAgency: sourceRegistry.agency,
        sourceAgencyShort: sourceRegistry.agencyShort,
        sourceDataset: sourceRegistry.datasetName,
        sourceId: sourceRegistry.sourceId,
      })
      .from(approvedIndicatorValues)
      .innerJoin(indicators, eq(approvedIndicatorValues.indicatorId, indicators.id))
      .innerJoin(sourceDocuments, eq(approvedIndicatorValues.sourceDocumentId, sourceDocuments.id))
      .innerJoin(sourceRegistry, eq(sourceDocuments.sourceId, sourceRegistry.sourceId))
      .orderBy(indicators.category, indicators.slug),
  );
  if (!queried.ok) return queried;
  return ok(queried.value);
}

/**
 * Roll-up row counts of the typed dimensional fact tables, for the Fact
 * Ledger "coverage" summary strip. These tables hold dimensional/granular
 * facts (foreign-trade commodities, bank balance-sheets, fiscal transfers,
 * census) that are NOT in `approved_indicator_values`; the strip makes the
 * full auditable surface tangible without listing every one of the ~578k rows.
 *
 * Counts are read via a single `COUNT(*)` per table (sequential-scan-free on
 * Postgres via the visibility map for these append-mostly tables). Validated
 * with Zod at the boundary because `db().execute` returns an untyped result.
 */
export type FactTableCount = {
  table:
    | 'dne_facts'
    | 'banking_sector_facts'
    | 'local_government_fiscal_transfers'
    | 'census_facts';
  rows: number;
};

export async function getFactTableCounts(): Promise<Result<FactTableCount[]>> {
  const raw = await safeQuery(() =>
    db().execute(
      sql`
        SELECT 'dne_facts' AS t, COUNT(*)::int AS n FROM dne_facts
        UNION ALL SELECT 'banking_sector_facts', COUNT(*)::int FROM banking_sector_facts
        UNION ALL SELECT 'local_government_fiscal_transfers', COUNT(*)::int FROM local_government_fiscal_transfers
        UNION ALL SELECT 'census_facts', COUNT(*)::int FROM census_facts
      `,
    ),
  );
  if (!raw.ok) return raw;

  const out: FactTableCount[] = [];
  for (const row of raw.value) {
    const t = (row as { t?: unknown }).t;
    const n = (row as { n?: unknown }).n;
    if (
      (t === 'dne_facts' ||
        t === 'banking_sector_facts' ||
        t === 'local_government_fiscal_transfers' ||
        t === 'census_facts') &&
      typeof n === 'number'
    ) {
      out.push({ table: t, rows: n });
    }
  }
  return ok(out);
}
