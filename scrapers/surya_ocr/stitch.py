"""Stitch per-tile OCR lines into one de-duplicated page-level cell list.

When a page is tiled with overlap, a line in the overlap band is detected by
BOTH neighbouring tiles. We dedupe by spatial IoU on the page-global bbox:

- Two cells from DIFFERENT tiles whose IoU >= ``IOU_MERGE_THRESHOLD`` are the
  "same" physical cell seen twice.
- If their cleaned text AGREES, keep the higher-confidence copy silently.
- If their cleaned text DISAGREES, keep the higher-confidence copy AND record
  an :class:`StitchDisagreement` (resolution ``kept_higher_confidence``), or
  ``flagged_for_review`` when the two confidences are within a hair of each
  other (we can't trust either). Nothing is fabricated; the loser is dropped
  but its disagreement is preserved for inspection.

Cells from the SAME tile are never merged (Surya already deduped within a
tile). A single-tile page therefore produces zero disagreements and zero
merges — the cells pass straight through.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cleanup import clean_line
from .types import CellExtraction, StitchDisagreement, StitchResolution

# IoU at/above which two cells from different tiles are deemed the same cell.
IOU_MERGE_THRESHOLD: float = 0.5
# Confidence delta below which a text disagreement is "too close to call".
_CONFIDENCE_TIE_EPS: float = 0.05


def _iou(a: CellExtraction, b: CellExtraction) -> float:
    ax0, ay0 = a.page_bbox_x, a.page_bbox_y
    ax1, ay1 = a.page_bbox_x + a.page_bbox_w, a.page_bbox_y + a.page_bbox_h
    bx0, by0 = b.page_bbox_x, b.page_bbox_y
    bx1, by1 = b.page_bbox_x + b.page_bbox_w, b.page_bbox_y + b.page_bbox_h

    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


@dataclass
class StitchOutcome:
    """Result of stitching: surviving cells + recorded disagreements.

    ``disagreements`` index into the ORIGINAL pre-stitch cell list (the harness
    keeps every extraction in ``cells`` for full provenance; disagreements
    reference both the kept and dropped cell by their original index).
    """

    kept_indices: list[int]
    disagreements: list[StitchDisagreement]


def _confidence(c: CellExtraction) -> float:
    return c.confidence if c.confidence is not None else 0.0


def stitch_cells(cells: list[CellExtraction]) -> StitchOutcome:
    """Dedupe overlapping cells across tiles; record text disagreements.

    Greedy: iterate cells in order; for each not-yet-consumed cell, find later
    cells from a DIFFERENT tile with IoU >= threshold, resolve each pair, and
    consume the loser. O(n^2) in cells-per-page (hundreds at most) — fine.
    """
    n = len(cells)
    consumed = [False] * n
    kept: list[int] = []
    disagreements: list[StitchDisagreement] = []

    for i in range(n):
        if consumed[i]:
            continue
        winner = i
        for j in range(i + 1, n):
            if consumed[j]:
                continue
            if cells[j].tile_index == cells[winner].tile_index:
                continue  # same tile: Surya already deduped within it
            iou = _iou(cells[winner], cells[j])
            if iou < IOU_MERGE_THRESHOLD:
                continue
            # Overlapping pair from different tiles → resolve.
            text_w = clean_line(cells[winner].text_raw)
            text_j = clean_line(cells[j].text_raw)
            conf_w = _confidence(cells[winner])
            conf_j = _confidence(cells[j])
            if text_w != text_j:
                resolution, reason = _resolve(conf_w, conf_j)
                # Disagreement always references (kept, dropped) by index; we
                # record it regardless of which side wins.
                if conf_j > conf_w:
                    disagreements.append(
                        StitchDisagreement(
                            cell_a_index=j,
                            cell_b_index=winner,
                            iou=round(iou, 4),
                            resolution=resolution,
                            resolution_reason=reason,
                        ),
                    )
                else:
                    disagreements.append(
                        StitchDisagreement(
                            cell_a_index=winner,
                            cell_b_index=j,
                            iou=round(iou, 4),
                            resolution=resolution,
                            resolution_reason=reason,
                        ),
                    )
            # Keep the higher-confidence cell as the winner; consume the other.
            if conf_j > conf_w:
                consumed[winner] = True
                winner = j
            else:
                consumed[j] = True
        consumed[winner] = True
        kept.append(winner)

    kept.sort()
    return StitchOutcome(kept_indices=kept, disagreements=disagreements)


def _resolve(conf_a: float, conf_b: float) -> tuple[StitchResolution, str]:
    """Pick a resolution label + human reason for a text disagreement."""
    if abs(conf_a - conf_b) < _CONFIDENCE_TIE_EPS:
        return (
            "flagged_for_review",
            f"text differs; confidences within {_CONFIDENCE_TIE_EPS} "
            f"({conf_a:.3f} vs {conf_b:.3f}) — too close to auto-resolve",
        )
    hi, lo = max(conf_a, conf_b), min(conf_a, conf_b)
    return (
        "kept_higher_confidence",
        f"text differs; kept higher confidence {hi:.3f} over {lo:.3f}",
    )
