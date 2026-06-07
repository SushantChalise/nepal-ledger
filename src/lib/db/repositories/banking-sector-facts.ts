/**
 * Banking Sector Facts repository.
 *
 * Targets the `banking_sector_facts` table populated from the NRB BFI
 * monthly XLSX corpus (source id `nrb-bfi-monthly-xlsx`). Each row is one
 * (bank_class, indicator_slug, period) data point — the long-format
 * equivalent of the C-series sheet tables.
 *
 * Separate from `approved_indicator_values` because:
 *   - Bank-class dimension would explode the indicator slug namespace
 *   - Sheet-specific provenance (which C-sheet → which indicator slug)
 *     matters for revision detection across monthly snapshots
 */

import { and, eq } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import type { BankClass, ReportingPeriodType } from '@/lib/db/schema/enums';
import {
  bankingSectorFacts,
  type BankingSectorFactRow,
  type NewBankingSectorFactRow,
} from '@/lib/db/schema/banking-sector-facts';
import { err, ok, type Result } from '@/lib/errors';

export async function insertBankingSectorFact(
  input: NewBankingSectorFactRow,
): Promise<Result<BankingSectorFactRow>> {
  const inserted = await safeQuery(() => db().insert(bankingSectorFacts).values(input).returning());
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertBankingSectorFact: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Bulk insert with idempotency. The natural key is the unique index
 * `banking_facts_unique_idx` on
 *   (bank_class, coalesce(bank_entity_id, <null-sentinel>::uuid),
 *    indicator_slug, reporting_period_bs, reporting_period_type).
 *
 * The COALESCE wrapper is load-bearing: system-aggregate rows carry
 * `bank_entity_id IS NULL`, and Postgres treats NULLs as DISTINCT in a plain
 * unique index — so a repeat ingest would re-insert every aggregate row.
 * Coalescing NULL to BANK_ENTITY_NULL_SENTINEL makes those rows collide.
 *
 * `onConflictDoNothing()` is called WITHOUT an explicit `target`. That is
 * deliberate and required here: Drizzle's `target` only accepts plain columns
 * (it emits a `(col, …)` list and cannot express a `coalesce(…)` expression
 * index). The bare form skips on ANY unique-constraint violation; this table
 * has exactly one unique index (`banking_facts_unique_idx`), so "any conflict"
 * is precisely the natural key. Re-ingesting the same XLSX is thus a no-op
 * (matches the parser contract in DATA_PIPELINE.md).
 *
 * Returns the rows actually inserted (drizzle `returning()` only yields
 * conflict-skipped rows on inserts that produced new rows).
 */
export async function bulkInsertBankingSectorFacts(
  inputs: ReadonlyArray<NewBankingSectorFactRow>,
): Promise<Result<BankingSectorFactRow[]>> {
  if (inputs.length === 0) return ok([]);
  return safeQuery(() =>
    db()
      .insert(bankingSectorFacts)
      .values([...inputs])
      .onConflictDoNothing()
      .returning(),
  );
}

/**
 * Lookup by (bank entity OR class) + period. Used by validation and
 * follow-up parsers checking for revisions of a row. Returns ok([]) for
 * the empty-match case — "no row" is a successful negative.
 */
export async function findBankingFactsByEntityAndPeriod(args: {
  bankClass: BankClass;
  bankEntityId: string | null;
  reportingPeriodType: ReportingPeriodType;
  reportingPeriodBs: string;
}): Promise<Result<BankingSectorFactRow[]>> {
  const conds = [
    eq(bankingSectorFacts.bankClass, args.bankClass),
    eq(bankingSectorFacts.reportingPeriodType, args.reportingPeriodType),
    eq(bankingSectorFacts.reportingPeriodBs, args.reportingPeriodBs),
  ];
  if (args.bankEntityId !== null) {
    conds.push(eq(bankingSectorFacts.bankEntityId, args.bankEntityId));
  }
  return safeQuery(() =>
    db().query.bankingSectorFacts.findMany({
      where: and(...conds),
    }),
  );
}
