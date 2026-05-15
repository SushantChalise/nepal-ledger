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
 * Bulk insert with idempotency. The unique index on
 * (bank_class, bank_entity_id, indicator_slug, reporting_period_bs,
 * reporting_period_type) is the natural key — `onConflictDoNothing` means
 * a repeat ingestion of the same XLSX is a no-op (matches the parser
 * contract in DATA_PIPELINE.md).
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
