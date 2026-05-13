/**
 * Fact Ledger — the visible claims database.
 *
 * Every claim is clickable, every claim cites a source document, every claim
 * has a confidence grade and a last-verified-at timestamp. This is what
 * makes Nepal Ledger an *auditable* publication rather than another opinion
 * blog. See docs/STRATEGY.md §"The Visible Fact Ledger".
 *
 * A claim's `text` is the prose assertion (one sentence, citable). The
 * `indicatorValueId` ties it to a specific approved value when applicable;
 * the `sourceDocumentId` is mandatory regardless.
 */

import { index, pgTable, text, timestamp, uniqueIndex, uuid } from 'drizzle-orm/pg-core';

import { confidenceGradeEnum } from './enums';
import { approvedIndicatorValues } from './indicator-values';
import { indicators } from './indicators';
import { sourceDocuments } from './source-documents';

export const factLedgerClaims = pgTable(
  'fact_ledger_claims',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    // Human-readable stable slug for citation URLs (e.g. /facts/<slug>).
    slug: text('slug').notNull(),

    textEn: text('text_en').notNull(),
    textNe: text('text_ne'),

    // Optional: link to a specific approved value (for "inflation was X" claims).
    indicatorValueId: uuid('indicator_value_id').references(() => approvedIndicatorValues.id, {
      onDelete: 'set null',
    }),

    // Optional: link to the indicator concept (for "we track X" claims).
    indicatorId: uuid('indicator_id').references(() => indicators.id, {
      onDelete: 'set null',
    }),

    // Mandatory: every claim cites at least one source document.
    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    confidenceGrade: confidenceGradeEnum('confidence_grade').notNull(),

    // When a human last verified the claim still holds against the source.
    lastVerifiedAt: timestamp('last_verified_at', { withTimezone: true }).notNull().defaultNow(),
    verifiedBy: text('verified_by').notNull(),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),

    // If a claim is retired (e.g. superseded by a revision), set retiredAt
    // rather than delete. Citations may still link to retired claims.
    retiredAt: timestamp('retired_at', { withTimezone: true }),
    retiredReason: text('retired_reason'),
  },
  (table) => [
    uniqueIndex('fact_ledger_slug_idx').on(table.slug),
    index('fact_ledger_indicator_idx').on(table.indicatorId),
    index('fact_ledger_source_doc_idx').on(table.sourceDocumentId),
  ],
);

export type FactLedgerClaimRow = typeof factLedgerClaims.$inferSelect;
export type NewFactLedgerClaimRow = typeof factLedgerClaims.$inferInsert;

/**
 * User-submitted challenges to a claim. Logged for transparency.
 * The submitter's email is captured; replies happen by email out-of-band.
 */
export const factLedgerChallenges = pgTable(
  'fact_ledger_challenges',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    claimId: uuid('claim_id')
      .notNull()
      .references(() => factLedgerClaims.id, { onDelete: 'cascade' }),

    email: text('email').notNull(),
    sourceUrl: text('source_url'),
    message: text('message').notNull(),

    // 'pending' | 'reviewing' | 'resolved-upheld' | 'resolved-overturned' | 'rejected'
    status: text('status').notNull().default('pending'),
    resolutionNote: text('resolution_note'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    resolvedAt: timestamp('resolved_at', { withTimezone: true }),
  },
  (table) => [index('fact_ledger_challenges_claim_idx').on(table.claimId)],
);

export type FactLedgerChallengeRow = typeof factLedgerChallenges.$inferSelect;
export type NewFactLedgerChallengeRow = typeof factLedgerChallenges.$inferInsert;
