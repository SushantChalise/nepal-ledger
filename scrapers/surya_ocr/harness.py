"""Top-level Surya tile-OCR harness: PDF + page range -> OcrPageResult list.

Flow per page (the pipeline mandated by FINANCIAL_DATA_STRATEGY §Phase B and
ADR-0021 Tier 2):

    render  (pymupdf Matrix(zoom,zoom))
      -> preprocess  (optional OpenCV deskew/denoise/binarize)
      -> tile        (overlapping windows, single-tile fast path)
      -> OCR each tile (Surya detection+recognition)
      -> to page-global CellExtraction (compute seam distance)
      -> normalize   (_common.devanagari_normalization: both numeral systems,
                      OCR-substitution dictionary)
      -> stitch      (dedupe overlaps across tiles; record disagreements)

The result mirrors the ``ocr_tracking`` trio so a Node ingest CLI can insert
manifests, cell extractions, and disagreements verbatim. The harness does NOT
reconstruct tables — that is the domain parser's job (it knows the column
semantics). ``reconstruct.py`` is provided for parsers to call.

This module imports the GPU stack (via ``engine``) only when :func:`ocr_pdf`
runs, not at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import fitz  # pymupdf

from _common.devanagari_normalization import (
    normalize_both_numeral_systems,
    normalize_devanagari_text,
)

from . import engine, render, tiling
from .stitch import stitch_cells
from .types import CellExtraction, OcrPageResult, TileManifest

# ``fitz`` (pymupdf) ships no py.typed marker, so ``fitz.Document`` resolves to
# ``Any`` under our strict ``disallow_any_unimported``. We alias it to an
# EXPLICIT ``Any`` so passing a doc across functions doesn't trip that check —
# the runtime type is always ``fitz.Document``.
FitzDocument = Any


@dataclass(frozen=True)
class HarnessConfig:
    """Tunable parameters for an OCR run. Defaults are the validated values."""

    zoom: float = render.DEFAULT_ZOOM
    # Tile only when a page edge exceeds this (px). 2200 keeps a 3x landscape
    # MoF page (≈2463 px) as a single tile when set higher, but defaults below
    # that so wide pages get sliced per findings §5.2 (2048 px guidance, with
    # headroom since the validated single-tile run at 2463 px was clean).
    max_edge_px: int = 2200
    overlap_px: int = 256
    # OpenCV preprocessing — OFF for born-digital pages (passthrough), ON for
    # genuinely-scanned legacy pages.
    preprocess: bool = False
    preprocess_deskew: bool = True
    preprocess_binarize: bool = True
    preprocess_denoise: bool = True


def _to_cell(
    *,
    page_number: int,
    tile: tiling.Tile,
    line: engine.OcrLine,
) -> CellExtraction:
    """Convert a tile-local OCR line into a page-global CellExtraction.

    Applies the Devanagari OCR-substitution dictionary + dual numeral
    extraction from ``_common`` so both numeral systems are preserved (schema
    requirement). ``text_raw`` is the untouched Surya text; ``text_normalized``
    has the substitution pass applied (markup left intact here — cleanup is the
    reconstruction step's concern, but normalization must see raw text).
    """
    lx0, ly0, lx1, ly1 = line.bbox
    tile_bbox_x = int(round(lx0))
    tile_bbox_y = int(round(ly0))
    tile_bbox_w = int(round(lx1 - lx0))
    tile_bbox_h = int(round(ly1 - ly0))

    page_bbox_x = tile.offset_x + tile_bbox_x
    page_bbox_y = tile.offset_y + tile_bbox_y

    seam = tiling.seam_distance_px(
        page_bbox_x, page_bbox_y, tile_bbox_w, tile_bbox_h,
        tile.seam_xs, tile.seam_ys,
    )

    text_normalized = normalize_devanagari_text(line.text)
    _, arabic, devanagari = normalize_both_numeral_systems(line.text)

    return CellExtraction(
        page_number=page_number,
        tile_index=tile.tile_index,
        table_region_id=None,
        tile_bbox_x=tile_bbox_x,
        tile_bbox_y=tile_bbox_y,
        tile_bbox_w=tile_bbox_w,
        tile_bbox_h=tile_bbox_h,
        page_bbox_x=page_bbox_x,
        page_bbox_y=page_bbox_y,
        page_bbox_w=tile_bbox_w,
        page_bbox_h=tile_bbox_h,
        near_tile_seam_px=seam,
        text_raw=line.text,
        text_normalized=text_normalized,
        numeral_arabic=arabic,
        numeral_devanagari=devanagari,
        confidence=line.confidence,
    )


def ocr_page(
    doc: FitzDocument,
    page_number: int,
    config: HarnessConfig,
) -> OcrPageResult:
    """Run the full render→…→stitch pipeline for one page."""
    rendered = render.render_page(doc, page_number, zoom=config.zoom)
    image = rendered.image
    if config.preprocess:
        image = render.preprocess_for_ocr(
            image,
            deskew=config.preprocess_deskew,
            binarize=config.preprocess_binarize,
            denoise=config.preprocess_denoise,
        )

    tiles = tiling.tile_page(
        image, max_edge_px=config.max_edge_px, overlap_px=config.overlap_px,
    )

    manifests: list[TileManifest] = []
    cells: list[CellExtraction] = []
    for tile in tiles:
        manifests.append(
            TileManifest(
                page_number=page_number,
                tile_index=tile.tile_index,
                offset_x_px=tile.offset_x,
                offset_y_px=tile.offset_y,
                width_px=tile.width,
                height_px=tile.height,
                dpi=rendered.dpi,
                model_name=engine.MODEL_NAME,
                model_version=engine.MODEL_VERSION,
            ),
        )
        for line in engine.ocr_image(tile.image):
            cells.append(_to_cell(page_number=page_number, tile=tile, line=line))

    outcome = stitch_cells(cells)
    # Surviving cells are those the stitch kept; we still RETAIN every
    # extraction in ``cells`` so disagreement indices stay valid and so the
    # operator can inspect dropped duplicates. ``kept_cell_indices`` marks the
    # de-duplicated survivors (the reconstruction step filters on it).
    return OcrPageResult(
        page_number=page_number,
        tiles=manifests,
        cells=cells,
        disagreements=outcome.disagreements,
        kept_cell_indices=outcome.kept_indices,
    )


def ocr_pdf(
    pdf_path: str,
    page_numbers: list[int],
    config: HarnessConfig | None = None,
) -> list[OcrPageResult]:
    """OCR a list of (0-based) pages from a PDF. Opens/closes the doc."""
    cfg = config or HarnessConfig()
    doc = fitz.open(pdf_path)
    try:
        return [ocr_page(doc, p, cfg) for p in page_numbers]
    finally:
        doc.close()


def kept_cells(result: OcrPageResult) -> list[int]:
    """Return the post-stitch survivor indices for a page.

    Reads the indices stored on the result (computed once in :func:`ocr_page`);
    falls back to recomputing if absent (e.g. a hand-built result in a test).
    """
    if result.kept_cell_indices:
        return result.kept_cell_indices
    return stitch_cells(result.cells).kept_indices
