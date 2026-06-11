/**
 * Migration permit facts repository (ADR-0026).
 *
 * Targets the `migration_permit_facts` table — the DoFE labour-permit corpus
 * (source id `dofe-labour-migration`). Each row is one
 * `(period × destination × origin × skill × category × sex)` cell; NULLs mark
 * marginal/aggregate dimensions.
 *
 * Mirrors `banking-sector-facts.ts`: every call goes through `safeQuery` and
 * returns a typed `Result` — these functions never throw. Foundation only —
 * no parser writes here yet (ADR-0026).
 */

import { and, eq, isNull, type SQL } from 'drizzle-orm';

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import type {
  MigrationDestinationRegion,
  MigrationPermitCategory,
  MigrationSex,
  MigrationSkillClass,
} from '@/lib/db/schema/enums';
import {
  migrationPermitFacts,
  type MigrationPermitFactRow,
  type NewMigrationPermitFactRow,
} from '@/lib/db/schema/migration-permit-facts';
import { err, ok, type Result } from '@/lib/errors';

export async function insertMigrationPermitFact(
  input: NewMigrationPermitFactRow,
): Promise<Result<MigrationPermitFactRow>> {
  const inserted = await safeQuery(() =>
    db().insert(migrationPermitFacts).values(input).returning(),
  );
  if (!inserted.ok) return inserted;
  const row = inserted.value[0];
  if (!row) {
    return err({
      kind: 'QueryFailed',
      detail: 'insertMigrationPermitFact: insert...returning produced no row',
    });
  }
  return ok(row);
}

/**
 * Bulk insert with idempotency. The natural key is the unique constraint
 * `migration_permit_facts_unique` over the full dimension tuple
 *   (fiscal_year_bs, month_num, destination_country, destination_region,
 *    origin_entity_id, skill_class, permit_category, sex),
 * declared with NULLS NOT DISTINCT so marginal rows (carrying NULLs) collide
 * on conflict instead of duplicating.
 *
 * `onConflictDoNothing()` is called WITHOUT an explicit `target`. The table has
 * exactly one unique constraint, so "any conflict" is precisely the natural
 * key; re-ingesting the same DoFE release is thus a no-op. (Passing a `target`
 * column list is unnecessary here and the bare form is the established pattern
 * for these fact tables.)
 *
 * Returns only the rows actually inserted (drizzle `returning()` yields nothing
 * for conflict-skipped rows).
 */
export async function bulkInsertMigrationPermitFacts(
  inputs: ReadonlyArray<NewMigrationPermitFactRow>,
): Promise<Result<MigrationPermitFactRow[]>> {
  if (inputs.length === 0) return ok([]);
  return safeQuery(() =>
    db()
      .insert(migrationPermitFacts)
      .values([...inputs])
      .onConflictDoNothing()
      .returning(),
  );
}

/**
 * Reader over the migration-permit facts. Every dimension filter is optional;
 * passing `null` for a nullable dimension matches the marginal (NULL) rows,
 * while omitting a filter (`undefined`) leaves that dimension unconstrained.
 * Used by validation and follow-up parsers checking for existing/revised rows.
 * Returns ok([]) for the empty-match case — "no row" is a successful negative.
 */
export async function findMigrationPermitFacts(args: {
  fiscalYearBs?: string;
  monthNum?: number | null;
  destinationCountry?: string | null;
  destinationRegion?: MigrationDestinationRegion | null;
  originEntityId?: string | null;
  skillClass?: MigrationSkillClass | null;
  permitCategory?: MigrationPermitCategory | null;
  sex?: MigrationSex;
}): Promise<Result<MigrationPermitFactRow[]>> {
  const conds: SQL[] = [];

  if (args.fiscalYearBs !== undefined) {
    conds.push(eq(migrationPermitFacts.fiscalYearBs, args.fiscalYearBs));
  }
  if (args.monthNum !== undefined) {
    conds.push(
      args.monthNum === null
        ? isNull(migrationPermitFacts.monthNum)
        : eq(migrationPermitFacts.monthNum, args.monthNum),
    );
  }
  if (args.destinationCountry !== undefined) {
    conds.push(
      args.destinationCountry === null
        ? isNull(migrationPermitFacts.destinationCountry)
        : eq(migrationPermitFacts.destinationCountry, args.destinationCountry),
    );
  }
  if (args.destinationRegion !== undefined) {
    conds.push(
      args.destinationRegion === null
        ? isNull(migrationPermitFacts.destinationRegion)
        : eq(migrationPermitFacts.destinationRegion, args.destinationRegion),
    );
  }
  if (args.originEntityId !== undefined) {
    conds.push(
      args.originEntityId === null
        ? isNull(migrationPermitFacts.originEntityId)
        : eq(migrationPermitFacts.originEntityId, args.originEntityId),
    );
  }
  if (args.skillClass !== undefined) {
    conds.push(
      args.skillClass === null
        ? isNull(migrationPermitFacts.skillClass)
        : eq(migrationPermitFacts.skillClass, args.skillClass),
    );
  }
  if (args.permitCategory !== undefined) {
    conds.push(
      args.permitCategory === null
        ? isNull(migrationPermitFacts.permitCategory)
        : eq(migrationPermitFacts.permitCategory, args.permitCategory),
    );
  }
  if (args.sex !== undefined) {
    conds.push(eq(migrationPermitFacts.sex, args.sex));
  }

  return safeQuery(() =>
    db().query.migrationPermitFacts.findMany({
      where: conds.length > 0 ? and(...conds) : undefined,
    }),
  );
}
