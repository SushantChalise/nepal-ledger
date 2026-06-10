"""Tests for surya_ocr.stitch — overlap dedupe + disagreement recording."""

from __future__ import annotations

from surya_ocr.stitch import stitch_cells
from surya_ocr.types import CellExtraction


def _cell(
    idx_tile: int,
    x: int,
    y: int,
    w: int,
    h: int,
    text: str,
    conf: float,
) -> CellExtraction:
    return CellExtraction(
        page_number=0,
        tile_index=idx_tile,
        table_region_id=None,
        tile_bbox_x=x,
        tile_bbox_y=y,
        tile_bbox_w=w,
        tile_bbox_h=h,
        page_bbox_x=x,
        page_bbox_y=y,
        page_bbox_w=w,
        page_bbox_h=h,
        near_tile_seam_px=None,
        text_raw=text,
        text_normalized=text,
        numeral_arabic=None,
        numeral_devanagari=None,
        confidence=conf,
    )


def test_no_overlap_keeps_all() -> None:
    cells = [
        _cell(0, 0, 0, 100, 20, "a", 0.9),
        _cell(0, 200, 0, 100, 20, "b", 0.9),
    ]
    out = stitch_cells(cells)
    assert out.kept_indices == [0, 1]
    assert out.disagreements == []


def test_same_tile_never_merged() -> None:
    # Identical bbox but SAME tile → not merged (Surya already deduped).
    cells = [
        _cell(0, 0, 0, 100, 20, "a", 0.9),
        _cell(0, 0, 0, 100, 20, "a", 0.9),
    ]
    out = stitch_cells(cells)
    assert out.kept_indices == [0, 1]


def test_overlap_agree_keeps_higher_confidence_silently() -> None:
    cells = [
        _cell(0, 0, 0, 100, 20, "१९,०९,९१", 0.80),
        _cell(1, 5, 0, 100, 20, "१९,०९,९१", 0.95),  # diff tile, high IoU
    ]
    out = stitch_cells(cells)
    assert out.kept_indices == [1]  # higher-confidence survivor
    assert out.disagreements == []  # text agreed → no disagreement


def test_overlap_disagree_records_disagreement() -> None:
    cells = [
        _cell(0, 0, 0, 100, 20, "१९,०९,९१", 0.70),
        _cell(1, 5, 0, 100, 20, "१९,०९,९२", 0.95),  # differs in last digit
    ]
    out = stitch_cells(cells)
    assert out.kept_indices == [1]
    assert len(out.disagreements) == 1
    d = out.disagreements[0]
    assert d.resolution == "kept_higher_confidence"
    assert d.cell_a_index == 1  # kept
    assert d.cell_b_index == 0  # dropped
    assert d.iou > 0.5


def test_overlap_disagree_tie_flags_for_review() -> None:
    cells = [
        _cell(0, 0, 0, 100, 20, "१९,०९,९१", 0.90),
        _cell(1, 5, 0, 100, 20, "१९,०९,९२", 0.91),  # within tie eps
    ]
    out = stitch_cells(cells)
    assert len(out.disagreements) == 1
    assert out.disagreements[0].resolution == "flagged_for_review"


def test_markup_difference_not_a_disagreement() -> None:
    # Same value, one with a stray <br> — cleanup normalizes both → agree.
    cells = [
        _cell(0, 0, 0, 100, 20, "९२,००", 0.80),
        _cell(1, 5, 0, 100, 20, "९२,००<br>", 0.85),
    ]
    out = stitch_cells(cells)
    assert out.disagreements == []
    assert out.kept_indices == [1]
