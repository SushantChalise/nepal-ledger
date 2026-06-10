"""Tile a rendered page into overlapping windows for Surya OCR.

Why tile at all: surya-ocr-findings §5.2 caps the useful raster at ~2048 px on
the long edge (segfaults / quality loss above), and the recognition model
resizes very large inputs. A page rendered at 3x (≈2463 px wide for an 821 pt
landscape MoF page) exceeds that, and tall multi-table pages lose detail. We
slice into windows that each stay under a max edge, with overlap so a table
row split by a seam is captured whole in at least one tile. The stitch step
then dedupes the overlap.

Coordinate model: each tile carries its ``(offset_x, offset_y)`` in the page
raster. A detected line's page-global bbox = tile offset + tile-local bbox.
"Distance to nearest seam" is the min pixel gap from a tile-local bbox edge to
the overlap band shared with a neighbouring tile — cells near a seam are the
spot-check sampling bias (schema comment on ``near_tile_seam_px``).

Single-tile fast path: when a page already fits under ``max_edge_px`` the page
is emitted as ONE tile (index 0, offset 0,0). The provenance trail stays
uniform — every page has >=1 manifest row.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class Tile:
    """One window into a page raster."""

    tile_index: int
    offset_x: int
    offset_y: int
    width: int
    height: int
    image: Image.Image
    # Page-raster x of each interior seam this tile borders (the START of an
    # overlap band on its right edge / bottom edge). Used for seam-distance.
    seam_xs: tuple[int, ...]
    seam_ys: tuple[int, ...]


def _spans(total: int, max_edge: int, overlap: int) -> list[tuple[int, int]]:
    """Return ``(start, length)`` windows covering ``[0, total)``.

    Windows are ``max_edge`` long and step by ``max_edge - overlap``; the last
    window is clamped to end exactly at ``total`` (so it may be shorter).
    """
    if total <= max_edge:
        return [(0, total)]
    step = max_edge - overlap
    if step <= 0:
        raise ValueError(f"overlap {overlap} >= max_edge {max_edge} — no progress")
    spans: list[tuple[int, int]] = []
    start = 0
    while start < total:
        end = min(start + max_edge, total)
        spans.append((start, end - start))
        if end >= total:
            break
        start += step
    return spans


def tile_page(
    image: Image.Image,
    *,
    max_edge_px: int,
    overlap_px: int,
) -> list[Tile]:
    """Split ``image`` into overlapping tiles, each <= ``max_edge_px`` per side.

    Tiles are produced in row-major order (top-to-bottom, then left-to-right
    within a row). ``tile_index`` is assigned in that order.
    """
    w, h = image.size
    x_spans = _spans(w, max_edge_px, overlap_px)
    y_spans = _spans(h, max_edge_px, overlap_px)

    # Interior seam coordinates (where one window's right/bottom overlaps the
    # next). A seam at x means columns near x risk being split.
    seam_x_coords = tuple(start + length for (start, length) in x_spans[:-1])
    seam_y_coords = tuple(start + length for (start, length) in y_spans[:-1])

    tiles: list[Tile] = []
    idx = 0
    for oy, th in y_spans:
        for ox, tw in x_spans:
            crop = image.crop((ox, oy, ox + tw, oy + th))
            tiles.append(
                Tile(
                    tile_index=idx,
                    offset_x=ox,
                    offset_y=oy,
                    width=tw,
                    height=th,
                    image=crop,
                    seam_xs=seam_x_coords,
                    seam_ys=seam_y_coords,
                ),
            )
            idx += 1
    return tiles


def seam_distance_px(
    page_bbox_x: int,
    page_bbox_y: int,
    page_bbox_w: int,
    page_bbox_h: int,
    seam_xs: tuple[int, ...],
    seam_ys: tuple[int, ...],
) -> int | None:
    """Min pixel distance from a page-global bbox to any interior seam.

    Returns ``None`` when there are no seams (single-tile page) — distinct
    from 0 (a cell sitting exactly on a seam). Distance is measured from the
    nearest bbox edge to the seam line; a bbox straddling a seam returns 0.
    """
    if not seam_xs and not seam_ys:
        return None
    x0, y0 = page_bbox_x, page_bbox_y
    x1, y1 = page_bbox_x + page_bbox_w, page_bbox_y + page_bbox_h
    candidates: list[int] = []
    for sx in seam_xs:
        if x0 <= sx <= x1:
            candidates.append(0)
        else:
            candidates.append(min(abs(sx - x0), abs(sx - x1)))
    for sy in seam_ys:
        if y0 <= sy <= y1:
            candidates.append(0)
        else:
            candidates.append(min(abs(sy - y0), abs(sy - y1)))
    return min(candidates) if candidates else None
