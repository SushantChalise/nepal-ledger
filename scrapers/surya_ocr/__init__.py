"""Reusable Surya tile-OCR harness for Nepal Ledger PDF recovery (Tier 2).

See ADR-0021 (recovery tiers) + ADR-0022 (this harness's design) +
``scrapers/surya_ocr/README.md``. The harness renders PDF pages, optionally
preprocesses with OpenCV, tiles large pages with overlap, runs Surya
detection+recognition per tile, stitches overlapping tiles (recording
disagreements), normalizes Devanagari (both numeral systems), and emits
records mirroring the ``ocr_tracking`` schema trio. Table reconstruction is a
separate, importable step so domain parsers supply the column semantics.

Public surface:
    HarnessConfig, ocr_pdf, ocr_page          — run the pipeline
    OcrPageResult, TileManifest, CellExtraction, StitchDisagreement — records
    reconstruct_table, ReconstructedRow        — geometric table rebuild
    cleanup helpers                            — markup strip + numeral fold

Importing this package does NOT import torch/surya/cv2 — only calling the
harness functions does (the heavy imports live inside ``engine`` / ``render``).
"""

from __future__ import annotations

from .harness import HarnessConfig, kept_cells, ocr_page, ocr_pdf
from .reconstruct import PlacedValue, ReconstructedRow, reconstruct_table
from .types import (
    CellExtraction,
    OcrPageResult,
    StitchDisagreement,
    TileManifest,
)

__all__ = [
    "CellExtraction",
    "HarnessConfig",
    "OcrPageResult",
    "PlacedValue",
    "ReconstructedRow",
    "StitchDisagreement",
    "TileManifest",
    "kept_cells",
    "ocr_page",
    "ocr_pdf",
    "reconstruct_table",
]
