/**
 * One row per parser execution + granular error rows for failed parses.
 * Per docs/DATA_PIPELINE.md.
 */

import { index, integer, pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';

import { parserErrorClassEnum, parserStatusEnum } from './enums';
import { sourceDocuments } from './source-documents';

export const parserRuns = pgTable(
  'parser_runs',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    parserPath: text('parser_path').notNull(),
    parserVersion: text('parser_version').notNull(),

    startedAt: timestamp('started_at', { withTimezone: true }).notNull().defaultNow(),
    endedAt: timestamp('ended_at', { withTimezone: true }),

    status: parserStatusEnum('status').notNull(),
    stagingRowsWritten: integer('staging_rows_written').notNull().default(0),

    errorSummary: text('error_summary'),
    stdoutTail: text('stdout_tail'),
  },
  (table) => [
    index('parser_runs_source_doc_idx').on(table.sourceDocumentId),
    index('parser_runs_status_idx').on(table.status),
  ],
);

export type ParserRunRow = typeof parserRuns.$inferSelect;
export type NewParserRunRow = typeof parserRuns.$inferInsert;

export const parserErrors = pgTable(
  'parser_errors',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    parserRunId: uuid('parser_run_id')
      .notNull()
      .references(() => parserRuns.id, { onDelete: 'cascade' }),

    errorClass: parserErrorClassEnum('error_class').notNull(),
    errorDetail: text('error_detail').notNull(),
    sourceExcerpt: text('source_excerpt'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index('parser_errors_run_idx').on(table.parserRunId)],
);

export type ParserErrorRow = typeof parserErrors.$inferSelect;
export type NewParserErrorRow = typeof parserErrors.$inferInsert;
