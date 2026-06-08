"""Tests for surya_ocr.tiling — windowing + seam-distance geometry.

Uses tiny PIL images (no GPU) to validate the tiling grid and the
distance-to-seam metric the ``ocr_cell_extractions`` schema expects.
"""

from __future__ import annotations

from PIL import Image

from surya_ocr.tiling import _spans, seam_distance_px, tile_page


def _img(w: int, h: int) -> Image.Image:
    return Image.new("RGB", (w, h), "white")


def test_spans_single_when_under_max() -> None:
    assert _spans(1000, 2200, 256) == [(0, 1000)]


def test_spans_multiple_with_overlap() -> None:
    spans = _spans(5000, 2200, 200)
    # step = 2000; starts 0, 2000, 4000 → last clamped to end at 5000.
    starts = [s for s, _ in spans]
    assert starts == [0, 2000, 4000]
    # every window <= 2200, last ends exactly at total
    assert all(length <= 2200 for _, length in spans)
    assert spans[-1][0] + spans[-1][1] == 5000


def test_spans_raises_when_overlap_ge_max() -> None:
    import pytest

    with pytest.raises(ValueError, match="no progress"):
        _spans(5000, 1000, 1000)


def test_single_tile_fast_path() -> None:
    tiles = tile_page(_img(2000, 1500), max_edge_px=2200, overlap_px=256)
    assert len(tiles) == 1
    t = tiles[0]
    assert (t.offset_x, t.offset_y, t.width, t.height) == (0, 0, 2000, 1500)
    assert t.seam_xs == ()
    assert t.seam_ys == ()


def test_wide_page_tiles_horizontally() -> None:
    tiles = tile_page(_img(5000, 1500), max_edge_px=2200, overlap_px=200)
    # 3 horizontal windows × 1 vertical = 3 tiles
    assert len(tiles) == 3
    assert [t.offset_x for t in tiles] == [0, 2000, 4000]
    # interior seams recorded at the window ends (2200, 4200)
    assert tiles[0].seam_xs == (2200, 4200)


def test_tile_indices_row_major() -> None:
    tiles = tile_page(_img(5000, 5000), max_edge_px=2200, overlap_px=200)
    assert [t.tile_index for t in tiles] == list(range(len(tiles)))


def test_seam_distance_none_when_no_seams() -> None:
    assert seam_distance_px(10, 10, 50, 20, (), ()) is None


def test_seam_distance_zero_when_straddling() -> None:
    # bbox x [100,200] straddles seam at 150 → distance 0
    assert seam_distance_px(100, 10, 100, 20, (150,), ()) == 0


def test_seam_distance_positive_gap() -> None:
    # bbox x [100,200], seam at 260 → nearest edge (200) is 60 away
    assert seam_distance_px(100, 10, 100, 20, (260,), ()) == 60


def test_seam_distance_takes_min_across_axes() -> None:
    # x-seam 60 away, y-seam 5 away → min 5
    d = seam_distance_px(100, 100, 100, 20, (260,), (125,))
    assert d == 5
