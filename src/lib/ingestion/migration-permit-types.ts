/**
 * DoFE migration-permit parser-output contract (ADR-0026).
 *
 * The boundary between the (future) deterministic Python DoFE parser's stdout
 * and the typed ingest orchestrator. Mirrors the `migration_permit_facts` row
 * shape in snake_case (the orchestrator maps snake → Drizzle camelCase on
 * insert), and is the typed target the parser PR must satisfy.
 *
 * Dimensional discipline is enforced here, at the boundary, not left to the DB:
 * every row must declare which dimensions are marginal (`null`) vs. specified,
 * and `permits` must be a non-negative integer count (no fractional permits).
 *
 * Foundation only (ADR-0026) — no parser exists yet; this contract is what it
 * will be held to.
 */

import { z } from 'zod';

// ─── Enums (mirror src/lib/db/schema/enums.ts) ──────────────────────────

const MigrationSkillClassSchema = z.enum([
  'unskilled',
  'semi_skilled',
  'skilled',
  'highly_skilled',
  'professional',
]);

const MigrationPermitCategorySchema = z.enum([
  'new_individual',
  'reentry',
  'recruitment_agency',
  'g2g',
]);

const MigrationDestinationRegionSchema = z.enum([
  'india',
  'saarc_other',
  'asean',
  'middle_east',
  'other_asia',
  'europe',
  'africa',
  'americas',
  'other',
]);

const MigrationSexSchema = z.enum(['male', 'female', 'total']);

const ConfidenceGradeSchema = z.enum(['A', 'B', 'C']);

/** Whole, non-negative permit count as a canonical integer string. */
const PermitCountStr = z.string().regex(/^\d+$/, 'permits must be a non-negative integer string');

// ─── migration_permit_facts draft ───────────────────────────────────────

/**
 * One `(period × destination × origin × skill × category × sex)` cell. A
 * `null` in any nullable dimension means "marginal/aggregate over that
 * dimension". `sex` is required — its both-sexes aggregate is the explicit
 * `total` value, never a null.
 */
export const MigrationPermitFactInputSchema = z.object({
  fiscal_year_bs: z.string().min(1),
  month_num: z.number().int().min(1).max(12).nullable(), // null = annual aggregate

  destination_country: z.string().min(1).nullable(), // null = all-countries marginal
  destination_region: MigrationDestinationRegionSchema.nullable(), // null = marginal

  origin_entity_id: z.string().uuid().nullable(), // null = all-Nepal marginal

  skill_class: MigrationSkillClassSchema.nullable(), // null = marginal
  permit_category: MigrationPermitCategorySchema.nullable(), // null = marginal

  sex: MigrationSexSchema, // REQUIRED — 'total' is the both-sexes aggregate

  permits: PermitCountStr,
  unit: z.string().min(1).default('permits'),

  source_document_id: z.string().uuid(),
  confidence_grade: ConfidenceGradeSchema.default('A'), // administrative records
  promoted_by: z.string().min(1),
});

export type MigrationPermitFactInput = z.infer<typeof MigrationPermitFactInputSchema>;
