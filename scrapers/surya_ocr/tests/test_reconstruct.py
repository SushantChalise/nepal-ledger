"""Tests for surya_ocr.reconstruct — bbox clustering into table rows/cols.

The synthetic fixture mirrors the REAL geometry of page 6 of 207980.pdf: a
label column on the left and 14 numeric columns. Crucially it includes a
MERGED multi-number cell (one bbox spanning two columns) to prove the split +
placement path, since that was the dominant failure mode on the real page.
"""

from __future__ import annotations

from surya_ocr.reconstruct import cluster_rows, derive_column_anchors, reconstruct_table
from surya_ocr.types import CellExtraction


def _cell(x: int, y: int, w: int, text: str, conf: float = 0.95) -> CellExtraction:
    h = 28
    return CellExtraction(
        page_number=0,
        tile_index=0,
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


# Column x-centres roughly matching the real page (3 numeric cols for brevity).
_COL_A, _COL_B, _COL_C = 600, 720, 900


def _province_rows() -> list[CellExtraction]:
    """Two province rows + one with a merged (A,B) cell."""
    cells: list[CellExtraction] = []
    # Row 1: clean, three separate numbers.
    cells.append(_cell(160, 642, 230, "७०१०००११ प्रदेश नं. १"))
    cells.append(_cell(_COL_A - 40, 643, 80, "२,८१,८३"))
    cells.append(_cell(_COL_B - 40, 643, 80, "५,८९,१३"))
    cells.append(_cell(_COL_C - 40, 643, 80, "२९,८६"))
    # Row 2: A and B MERGED into one bbox spanning [560, 760].
    cells.append(_cell(160, 686, 230, "७०१०००१२ मधेश प्रदेश"))
    cells.append(_cell(560, 687, 200, "१,८६,४६ ५,६८,२५"))  # merged A+B
    cells.append(_cell(_COL_C - 40, 688, 80, "२६,८७"))
    return cells


def test_cluster_rows_groups_by_y() -> None:
    cells = _province_rows()
    rows = cluster_rows(cells, list(range(len(cells))), row_tol_px=15)
    assert len(rows) == 2
    # within-row ordering is left→right
    assert cells[rows[0][0]].page_bbox_x < cells[rows[0][1]].page_bbox_x


def test_derive_anchors_from_single_token_cells() -> None:
    cells = _province_rows()
    rows = cluster_rows(cells, list(range(len(cells))), row_tol_px=15)
    anchors = derive_column_anchors(
        cells, rows, expected_columns=3, cluster_tol_px=40,
    )
    # Three columns recovered, sorted left→right, near the real centres.
    assert len(anchors) == 3
    assert anchors[0] < anchors[1] < anchors[2]


def test_reconstruct_places_clean_row() -> None:
    cells = _province_rows()
    rows_out = reconstruct_table(
        cells,
        list(range(len(cells))),
        expected_columns=3,
        row_tol_px=15,
        column_tol_px=40,
        column_anchors=[_COL_A, _COL_B, _COL_C],
    )
    r0 = rows_out[0]
    assert "७०१०००११" in r0.label
    assert r0.values[0].token == "२,८१,८३"
    assert r0.values[1].token == "५,८९,१३"
    assert r0.values[2].token == "२९,८६"
    assert all(not v.from_split for v in r0.values.values())


def test_reconstruct_splits_merged_cell_into_columns() -> None:
    cells = _province_rows()
    rows_out = reconstruct_table(
        cells,
        list(range(len(cells))),
        expected_columns=3,
        row_tol_px=15,
        column_tol_px=40,
        column_anchors=[_COL_A, _COL_B, _COL_C],
    )
    r1 = rows_out[1]
    assert "मधेश" in r1.label
    # The merged "१,८६,४६ ५,६८,२५" must land in columns 0 and 1.
    assert r1.values[0].token == "१,८६,४६"
    assert r1.values[1].token == "५,६८,२५"
    assert r1.values[0].from_split is True
    assert r1.values[1].from_split is True
    # The standalone third number lands in column 2.
    assert r1.values[2].token == "२६,८७"
    assert r1.values[2].from_split is False


def test_reconstruct_empty_when_no_anchors() -> None:
    # Only label cells, no numerics → no anchors derivable → empty.
    cells = [_cell(160, 642, 230, "केवल लेबल")]
    out = reconstruct_table(
        cells, [0], expected_columns=3, row_tol_px=15, column_tol_px=40,
    )
    assert out == []
