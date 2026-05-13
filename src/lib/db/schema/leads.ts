/**
 * Newsletter / signup leads.
 *
 * Captured by the (future) landing-page Server Action. Lightweight schema;
 * we expand to full subscriber management when Resend wires up in Phase 2.
 */

import { index, pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';

export const leads = pgTable(
  'leads',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    email: text('email').notNull(),
    source: text('source'),

    // Coarse-grained UTM bucket. NULL until we wire UTM capture.
    referrer: text('referrer'),

    // 'subscribed' | 'unsubscribed' | 'bounced'
    status: text('status').notNull().default('subscribed'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    confirmedAt: timestamp('confirmed_at', { withTimezone: true }),
    unsubscribedAt: timestamp('unsubscribed_at', { withTimezone: true }),
  },
  (table) => [index('leads_email_idx').on(table.email), index('leads_status_idx').on(table.status)],
);

export type LeadRow = typeof leads.$inferSelect;
export type NewLeadRow = typeof leads.$inferInsert;
