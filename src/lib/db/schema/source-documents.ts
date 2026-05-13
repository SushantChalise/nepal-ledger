/**
 * Append-only archive of every downloaded source file.
 *
 * Per docs/DATA_PIPELINE.md: rows are never updated or deleted. Re-download
 * of the same source produces a new row, even if the content is unchanged
 * (the hash equality is checked at read time, not by suppressing inserts).
 */

import { bigint, index, pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';

import { storageProviderEnum } from './enums';
import { sourceRegistry } from './source-registry';

export const sourceDocuments = pgTable(
  'source_documents',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    sourceId: text('source_id')
      .notNull()
      .references(() => sourceRegistry.sourceId, { onDelete: 'restrict', onUpdate: 'cascade' }),

    originalUrl: text('original_url').notNull(),
    storageProvider: storageProviderEnum('storage_provider').notNull().default('supabase'),
    // Key inside the storage bucket. Format: <source-id>/<yyyy-mm-dd>/<filename>.
    storageKey: text('storage_key').notNull(),

    fileHashSha256: text('file_hash_sha256').notNull(),
    fileSizeBytes: bigint('file_size_bytes', { mode: 'number' }).notNull(),
    contentType: text('content_type').notNull(),

    downloadedAt: timestamp('downloaded_at', { withTimezone: true }).notNull().defaultNow(),

    // Best-guess label set at download time; the parser refines this.
    reportingPeriodLabel: text('reporting_period_label'),
    notes: text('notes'),
  },
  (table) => [
    index('source_documents_source_id_idx').on(table.sourceId),
    index('source_documents_hash_idx').on(table.fileHashSha256),
  ],
);

export type SourceDocumentRow = typeof sourceDocuments.$inferSelect;
export type NewSourceDocumentRow = typeof sourceDocuments.$inferInsert;
