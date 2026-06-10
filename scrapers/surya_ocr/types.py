"""Typed records emitted by the Surya tile-OCR harness.

These dataclasses mirror, field-for-field, the three OCR-tracking tables in
``src/lib/db/schema/ocr-tracking.ts`` (``ocr_tile_manifests`` /
``ocr_cell_extractions`` / ``ocr_stitch_disagreements``). The harness produces
them; a Node-side ingest CLI maps them onto ``NewOcr*Row`` inserts.

Coordinate conventions (locked, matches the schema comments):
    - ``tile_bbox_*``  — tile-local pixel coords (relative to the tile's
      top-left corner in the rendered page raster).
    - ``page_bbox_*``  — page-global pixel coords (tile offset + tile-local).
    - All coords are in the rendered raster's pixel space at ``dpi``.

Nothing here imports torch/surya/cv2 — keep this module cheap so consumers
(tests, the Node bridge schema) can import it without the GPU stack.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# Mirror of ``stitchResolutionEnum`` in src/lib/db/schema/enums.ts.
StitchResolution = Literal[
    "kept_higher_confidence",
    "kept_left_tile",
    "kept_right_tile",
    "flagged_for_review",
]


@dataclass(frozen=True)
class TileManifest:
    """One rendered tile. Mirrors ``ocr_tile_manifests``.

    ``tile_index`` is 0-based within a page. A page rendered without tiling
    still produces exactly one manifest (tile_index=0 spanning the whole
    page) so the provenance trail is uniform.
    """

    page_number: int
    tile_index: int
    offset_x_px: int
    offset_y_px: int
    width_px: int
    height_px: int
    dpi: int
    model_name: str
    model_version: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CellExtraction:
    """One Surya text line, post-normalization. Mirrors ``ocr_cell_extractions``.

    ``tile_index`` links back to the owning :class:`TileManifest` within the
    same page (the Node side resolves it to ``tile_id`` after the manifest
    rows are inserted). ``table_region_id`` is a stable per-page region label
    when layout detection is used; ``None`` when the whole page is one region.
    """

    page_number: int
    tile_index: int
    table_region_id: str | None

    tile_bbox_x: int
    tile_bbox_y: int
    tile_bbox_w: int
    tile_bbox_h: int

    page_bbox_x: int
    page_bbox_y: int
    page_bbox_w: int
    page_bbox_h: int

    near_tile_seam_px: int | None

    text_raw: str
    text_normalized: str | None
    numeral_arabic: str | None
    numeral_devanagari: str | None
    confidence: float | None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StitchDisagreement:
    """Two overlapping tiles produced different text for ~the same cell.

    Mirrors ``ocr_stitch_disagreements``. The harness emits these by INDEX
    into the run's ``cells`` list (``cell_a_index`` / ``cell_b_index``);
    the Node side translates indices to inserted-row UUIDs.
    """

    cell_a_index: int
    cell_b_index: int
    iou: float
    resolution: StitchResolution
    resolution_reason: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OcrPageResult:
    """Everything the harness produced for one page.

    ``cells`` retains EVERY extraction (including overlap duplicates dropped by
    stitching) for full provenance; ``kept_cell_indices`` marks the post-stitch
    survivors (the de-duplicated set the reconstruction step consumes).
    ``disagreements`` index into ``cells`` by original position.
    """

    page_number: int
    tiles: list[TileManifest] = field(default_factory=list)
    cells: list[CellExtraction] = field(default_factory=list)
    disagreements: list[StitchDisagreement] = field(default_factory=list)
    kept_cell_indices: list[int] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "tiles": [t.to_json_dict() for t in self.tiles],
            "cells": [c.to_json_dict() for c in self.cells],
            "disagreements": [d.to_json_dict() for d in self.disagreements],
            "kept_cell_indices": self.kept_cell_indices,
        }
