/**
 * OCR-tracking repository — persists the Surya harness provenance trio.
 *
 * The three tables form an FK chain that the harness emits by INDEX (it has no
 * UUIDs): a page's tiles, the cells per tile, and the stitch disagreements
 * between cells. This repository inserts them in dependency order, threading
 * the generated UUIDs:
 *
 *   1. ocr_tile_manifests   — keyed (per run) by (page_number, tile_index)
 *   2. ocr_cell_extractions — each cell names its (page_number, tile_index);
 *                             we resolve that to the inserted manifest UUID
 *   3. ocr_stitch_disagreements — each names two cells by their ORIGINAL index
 *                             in the page's cell list; we resolve to cell UUIDs
 *
 * One call = one parser_run's worth of OCR provenance. All inserts go through
 * safeQuery; partial failure returns the typed error (the caller decides
 * whether the fact rows still ship — the trio is provenance, not the truth
 * layer).
 */

import { db } from '@/lib/db/client';
import { safeQuery } from '@/lib/db/safe-query';
import {
  ocrCellExtractions,
  ocrStitchDisagreements,
  ocrTileManifests,
} from '@/lib/db/schema/ocr-tracking';
import { err, ok, type Result } from '@/lib/errors';
import type { StitchResolution } from '@/lib/db/schema/enums';

/** A page's OCR result, mirroring the Python harness `OcrPageResult` JSON. */
export type OcrPagePayload = {
  pageNumber: number;
  tiles: ReadonlyArray<{
    pageNumber: number;
    tileIndex: number;
    offsetXPx: number;
    offsetYPx: number;
    widthPx: number;
    heightPx: number;
    dpi: number;
    modelName: string;
    modelVersion: string;
  }>;
  cells: ReadonlyArray<{
    pageNumber: number;
    tileIndex: number;
    tableRegionId: string | null;
    tileBboxX: number;
    tileBboxY: number;
    tileBboxW: number;
    tileBboxH: number;
    pageBboxX: number;
    pageBboxY: number;
    pageBboxW: number;
    pageBboxH: number;
    nearTileSeamPx: number | null;
    textRaw: string;
    textNormalized: string | null;
    numeralArabic: string | null;
    numeralDevanagari: string | null;
    confidence: number | null;
  }>;
  disagreements: ReadonlyArray<{
    cellAIndex: number;
    cellBIndex: number;
    iou: number;
    resolution: StitchResolution;
    resolutionReason: string;
  }>;
};

export type OcrPersistSummary = {
  tilesInserted: number;
  cellsInserted: number;
  disagreementsInserted: number;
};

function tileKey(pageNumber: number, tileIndex: number): string {
  return `${pageNumber}:${tileIndex}`;
}

/**
 * Persist all OCR-tracking rows for one parser run, across all its pages.
 *
 * `parserRunId` + `sourceDocumentId` anchor every manifest (the schema
 * requires both). Cells/disagreements derive their FKs from the inserted
 * UUIDs — nothing is fabricated.
 */
export async function persistOcrTracking(
  parserRunId: string,
  sourceDocumentId: string,
  pages: readonly OcrPagePayload[],
): Promise<Result<OcrPersistSummary>> {
  // ─── 1. Tile manifests ────────────────────────────────────────────────
  const manifestInserts = pages.flatMap((page) =>
    page.tiles.map((t) => ({
      parserRunId,
      sourceDocumentId,
      pageNumber: t.pageNumber,
      tileIndex: t.tileIndex,
      offsetXPx: t.offsetXPx,
      offsetYPx: t.offsetYPx,
      widthPx: t.widthPx,
      heightPx: t.heightPx,
      dpi: t.dpi,
      modelName: t.modelName,
      modelVersion: t.modelVersion,
    })),
  );
  if (manifestInserts.length === 0) {
    return ok({ tilesInserted: 0, cellsInserted: 0, disagreementsInserted: 0 });
  }
  const manifests = await safeQuery(() =>
    db().insert(ocrTileManifests).values(manifestInserts).returning({
      id: ocrTileManifests.id,
      pageNumber: ocrTileManifests.pageNumber,
      tileIndex: ocrTileManifests.tileIndex,
    }),
  );
  if (!manifests.ok) return manifests;
  const tileIdByKey = new Map<string, string>(
    manifests.value.map((m) => [tileKey(m.pageNumber, m.tileIndex), m.id]),
  );

  // ─── 2. Cell extractions (per page, so disagreement indices stay local) ─
  let cellsInserted = 0;
  let disagreementsInserted = 0;
  for (const page of pages) {
    if (page.cells.length === 0) continue;
    const cellInserts = page.cells.map((c) => {
      const tileId = tileIdByKey.get(tileKey(c.pageNumber, c.tileIndex));
      if (tileId === undefined) {
        throw new Error(
          `persistOcrTracking: no tile manifest for ${tileKey(c.pageNumber, c.tileIndex)}`,
        );
      }
      return {
        tileId,
        tableRegionId: c.tableRegionId,
        tileBboxX: c.tileBboxX,
        tileBboxY: c.tileBboxY,
        tileBboxW: c.tileBboxW,
        tileBboxH: c.tileBboxH,
        pageBboxX: c.pageBboxX,
        pageBboxY: c.pageBboxY,
        pageBboxW: c.pageBboxW,
        pageBboxH: c.pageBboxH,
        nearTileSeamPx: c.nearTileSeamPx,
        textRaw: c.textRaw,
        textNormalized: c.textNormalized,
        numeralArabic: c.numeralArabic,
        numeralDevanagari: c.numeralDevanagari,
        // numeric(6,4) — Drizzle wants a string for numeric columns.
        confidence: c.confidence === null ? null : c.confidence.toFixed(4),
      };
    });
    const inserted = await safeQuery(() =>
      db().insert(ocrCellExtractions).values(cellInserts).returning({
        id: ocrCellExtractions.id,
      }),
    );
    if (!inserted.ok) return inserted;
    // `returning()` preserves insert order → index i ↔ page.cells[i].
    const cellIdByIndex = inserted.value.map((r) => r.id);
    cellsInserted += cellIdByIndex.length;

    if (page.disagreements.length === 0) continue;
    const disInserts = page.disagreements.map((d) => {
      const a = cellIdByIndex[d.cellAIndex];
      const b = cellIdByIndex[d.cellBIndex];
      if (a === undefined || b === undefined) {
        throw new Error(
          `persistOcrTracking: disagreement references out-of-range cell index ` +
            `(${d.cellAIndex}, ${d.cellBIndex}) on page ${page.pageNumber}`,
        );
      }
      return {
        cellAExtractionId: a,
        cellBExtractionId: b,
        // numeric(6,4) — string per Drizzle convention.
        iou: d.iou.toFixed(4),
        resolution: d.resolution,
        resolutionReason: d.resolutionReason,
      };
    });
    const disInserted = await safeQuery(() =>
      db().insert(ocrStitchDisagreements).values(disInserts).returning({
        id: ocrStitchDisagreements.id,
      }),
    );
    if (!disInserted.ok) return disInserted;
    disagreementsInserted += disInserted.value.length;
  }

  if (cellsInserted === 0 && manifestInserts.length > 0) {
    // Tiles but no cells is legal (a blank page); not an error.
    return ok({
      tilesInserted: manifestInserts.length,
      cellsInserted: 0,
      disagreementsInserted: 0,
    });
  }
  void err; // reserved for future typed-error branches; quiets the linter
  return ok({
    tilesInserted: manifestInserts.length,
    cellsInserted,
    disagreementsInserted,
  });
}
