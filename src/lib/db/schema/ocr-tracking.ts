/**
 * OCR tile + stitch tracking for Surya-based PDF parsers.
 *
 * Per the user-mandated tile-based architecture (FINANCIAL_DATA_STRATEGY.md
 * §Phase B + the 12-item failure-mode catalogue), every Surya parser run
 * persists:
 *   - The tile manifest (offsets, DPI, model version) so coords are
 *     reproducible
 *   - Per-cell extractions (text raw + normalized, both numeral systems,
 *     confidence, distance-to-nearest-seam)
 *   - Stitch disagreements (when two overlapping tiles produce different
 *     text for the same spatial cell)
 *
 * These tables let an operator (or Claude) post-hoc answer "where did the
 * OCR struggle on this run?" without re-running anything. Wired up when
 * the first Surya-based parser ships (Phase B1: intergovernmental PDFs).
 */

import { index, integer, numeric, pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';

import { stitchResolutionEnum } from './enums';
import { parserRuns } from './parser-runs';
import { sourceDocuments } from './source-documents';

export const ocrTileManifests = pgTable(
  'ocr_tile_manifests',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    parserRunId: uuid('parser_run_id')
      .notNull()
      .references(() => parserRuns.id, { onDelete: 'cascade' }),
    sourceDocumentId: uuid('source_document_id')
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: 'restrict' }),

    pageNumber: integer('page_number').notNull(),
    tileIndex: integer('tile_index').notNull(),

    offsetXPx: integer('offset_x_px').notNull(),
    offsetYPx: integer('offset_y_px').notNull(),
    widthPx: integer('width_px').notNull(),
    heightPx: integer('height_px').notNull(),
    dpi: integer('dpi').notNull(),

    // The OCR model + version that processed this tile.
    modelName: text('model_name').notNull(),
    modelVersion: text('model_version').notNull(),

    renderedAt: timestamp('rendered_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index('ocr_tiles_run_idx').on(table.parserRunId),
    index('ocr_tiles_page_idx').on(table.sourceDocumentId, table.pageNumber),
  ],
);

export type OcrTileManifestRow = typeof ocrTileManifests.$inferSelect;
export type NewOcrTileManifestRow = typeof ocrTileManifests.$inferInsert;

export const ocrCellExtractions = pgTable(
  'ocr_cell_extractions',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    tileId: uuid('tile_id')
      .notNull()
      .references(() => ocrTileManifests.id, { onDelete: 'cascade' }),

    // When Surya layout detection identifies a table region, every cell
    // links back to it for stitch deduplication.
    tableRegionId: text('table_region_id'),

    // Tile-local coords (relative to the tile's top-left)
    tileBboxX: integer('tile_bbox_x').notNull(),
    tileBboxY: integer('tile_bbox_y').notNull(),
    tileBboxW: integer('tile_bbox_w').notNull(),
    tileBboxH: integer('tile_bbox_h').notNull(),

    // Page-global coords (computed: tile offset + tile-local)
    pageBboxX: integer('page_bbox_x').notNull(),
    pageBboxY: integer('page_bbox_y').notNull(),
    pageBboxW: integer('page_bbox_w').notNull(),
    pageBboxH: integer('page_bbox_h').notNull(),

    // Distance from this cell to the nearest tile seam, in pixels.
    // Cells close to seams are at higher risk of clipped diacritics or
    // split numerals — analytical signal for spot-check sampling.
    nearTileSeamPx: integer('near_tile_seam_px'),

    // OCR output before any post-processing
    textRaw: text('text_raw').notNull(),

    // After Devanagari-substitution dictionary (Cleaned/manual_match_reasoning.py
    // ported into scrapers/_common/devanagari_normalization.py)
    textNormalized: text('text_normalized'),

    // Both numeral systems preserved losslessly. Whichever the source had,
    // the other is computed via lookup. Either may be NULL if no numeral.
    numeralArabic: text('numeral_arabic'),
    numeralDevanagari: text('numeral_devanagari'),

    confidence: numeric('confidence', { precision: 6, scale: 4 }),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index('ocr_cells_tile_idx').on(table.tileId),
    index('ocr_cells_region_idx').on(table.tableRegionId),
    index('ocr_cells_seam_idx').on(table.nearTileSeamPx),
  ],
);

export type OcrCellExtractionRow = typeof ocrCellExtractions.$inferSelect;
export type NewOcrCellExtractionRow = typeof ocrCellExtractions.$inferInsert;

export const ocrStitchDisagreements = pgTable(
  'ocr_stitch_disagreements',
  {
    id: uuid('id').primaryKey().defaultRandom(),

    cellAExtractionId: uuid('cell_a_extraction_id')
      .notNull()
      .references(() => ocrCellExtractions.id, { onDelete: 'cascade' }),
    cellBExtractionId: uuid('cell_b_extraction_id')
      .notNull()
      .references(() => ocrCellExtractions.id, { onDelete: 'cascade' }),

    iou: numeric('iou', { precision: 6, scale: 4 }).notNull(),
    resolution: stitchResolutionEnum('resolution').notNull(),
    resolutionReason: text('resolution_reason').notNull(),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index('ocr_disagreements_a_idx').on(table.cellAExtractionId),
    index('ocr_disagreements_b_idx').on(table.cellBExtractionId),
  ],
);

export type OcrStitchDisagreementRow = typeof ocrStitchDisagreements.$inferSelect;
export type NewOcrStitchDisagreementRow = typeof ocrStitchDisagreements.$inferInsert;
