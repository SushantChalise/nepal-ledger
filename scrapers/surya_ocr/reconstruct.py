"""Reconstruct table rows/columns from page-level OCR cells by bbox clustering.

Surya gives a flat list of recognized lines with page-global bboxes. It does
NOT give table structure (the table-rec model is separate and OCRs cell text
from the PDF layer, which is unreliable on these docs — findings §4). So we
rebuild the grid geometrically:

ROWS: cluster cells by vertical position. Two cells belong to the same row if
their bbox y-centres are within ``row_tol_px``. Rows are then ordered top→down.

COLUMNS: a header-anchored model. Numeric data tables here have fixed column
x-positions; we derive column centres from the rows themselves (the modal set
of x-centres across data rows) OR accept caller-supplied column anchors. Each
number token is assigned to the nearest column centre.

MERGED LINES: a single OCR line may contain several numbers spanning multiple
columns (Surya drew one bbox across them — observed on task #50). We split the
line into number tokens (``cleanup.split_numeric_tokens``) and distribute the
tokens across the columns the bbox spans, proportional to bbox width. This is
the key fix that makes merged cells recoverable instead of lost.

The output is a list of :class:`ReconstructedRow` — a label cell (leftmost
non-numeric text) plus a value-by-column-index map. The domain parser
(intergovernmental) maps columns→grant types and the label→entity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cleanup import clean_line, is_pure_numeric_line, split_numeric_tokens
from .types import CellExtraction


@dataclass(frozen=True)
class PlacedValue:
    """A number token placed in a column, with provenance back to its cell."""

    column_index: int
    token: str
    source_cell_index: int
    confidence: float | None
    # True when this token came from a multi-number line we had to split.
    from_split: bool


@dataclass
class ReconstructedRow:
    """One table row: a label + values keyed by column index."""

    row_y: float
    label: str
    label_cell_index: int | None
    values: dict[int, PlacedValue] = field(default_factory=dict)


def _y_centre(c: CellExtraction) -> float:
    return c.page_bbox_y + c.page_bbox_h / 2


def _x_centre(c: CellExtraction) -> float:
    return c.page_bbox_x + c.page_bbox_w / 2


def cluster_rows(
    cells: list[CellExtraction],
    indices: list[int],
    *,
    row_tol_px: int,
) -> list[list[int]]:
    """Group cell indices into rows by y-centre proximity.

    Returns a list of rows (each a list of cell indices), ordered top→down;
    within a row, indices are ordered left→right by x.
    """
    ordered = sorted(indices, key=lambda i: _y_centre(cells[i]))
    rows: list[list[int]] = []
    for i in ordered:
        yc = _y_centre(cells[i])
        if rows and abs(yc - _y_centre(cells[rows[-1][0]])) <= row_tol_px:
            rows[-1].append(i)
        else:
            rows.append([i])
    for row in rows:
        row.sort(key=lambda i: cells[i].page_bbox_x)
    return rows


def derive_column_anchors(
    cells: list[CellExtraction],
    rows: list[list[int]],
    *,
    expected_columns: int,
    cluster_tol_px: int,
) -> list[float]:
    """Infer column x-centres from the SINGLE-token numeric cells across rows.

    Only single-number cells vote (a merged multi-number cell has an x-centre
    that sits between real columns and would pollute the anchors). We collect
    their x-centres, cluster nearby ones, and return the ``expected_columns``
    densest cluster centres, sorted left→right.
    """
    xs: list[float] = []
    for row in rows:
        for i in row:
            text = cells[i].text_raw
            if is_pure_numeric_line(text) and len(split_numeric_tokens(text)) == 1:
                xs.append(_x_centre(cells[i]))
    if not xs:
        return []
    xs.sort()
    # Agglomerate: walk sorted x, start a new cluster when the gap exceeds tol.
    clusters: list[list[float]] = [[xs[0]]]
    for x in xs[1:]:
        if x - clusters[-1][-1] <= cluster_tol_px:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    # Rank clusters by membership; keep the densest ``expected_columns``.
    clusters.sort(key=len, reverse=True)
    chosen = clusters[:expected_columns]
    centres = [sum(c) / len(c) for c in chosen]
    centres.sort()
    return centres


def _nearest_column(x: float, anchors: list[float]) -> int:
    best_idx = 0
    best_dist = abs(x - anchors[0])
    for idx in range(1, len(anchors)):
        d = abs(x - anchors[idx])
        if d < best_dist:
            best_dist = d
            best_idx = idx
    return best_idx


def _place_tokens_across_span(
    tokens: list[str],
    bbox_x: float,
    bbox_w: float,
    anchors: list[float],
) -> list[int]:
    """Assign each token in a multi-number line to a column.

    The line's bbox spans ``[bbox_x, bbox_x+bbox_w]``. We lay the tokens out at
    even sub-positions across that span and snap each to its nearest column
    anchor. This recovers the common ``"a b"`` / ``"a | b"`` merges where two
    or three adjacent columns were captured in one bbox.
    """
    n = len(tokens)
    placed: list[int] = []
    for k in range(n):
        # Token centre = even fraction across the bbox width.
        frac = (k + 0.5) / n
        x = bbox_x + frac * bbox_w
        placed.append(_nearest_column(x, anchors))
    return placed


def reconstruct_table(
    cells: list[CellExtraction],
    indices: list[int],
    *,
    expected_columns: int,
    row_tol_px: int,
    column_tol_px: int,
    column_anchors: list[float] | None = None,
) -> list[ReconstructedRow]:
    """Turn stitched cells into labelled rows with values keyed by column.

    ``column_anchors`` may be supplied (e.g. derived once from a clean page and
    reused); otherwise they are derived from the data rows themselves.
    """
    rows = cluster_rows(cells, indices, row_tol_px=row_tol_px)
    anchors = column_anchors or derive_column_anchors(
        cells, rows, expected_columns=expected_columns, cluster_tol_px=column_tol_px,
    )
    if not anchors:
        return []

    out: list[ReconstructedRow] = []
    for row in rows:
        label_parts: list[tuple[float, str]] = []
        label_cell_index: int | None = None
        values: dict[int, PlacedValue] = {}

        for i in row:
            text = cells[i].text_raw
            if not is_pure_numeric_line(text):
                cleaned = clean_line(text)
                if cleaned:
                    label_parts.append((cells[i].page_bbox_x, cleaned))
                    if label_cell_index is None:
                        label_cell_index = i
                continue
            tokens = split_numeric_tokens(text)
            if not tokens:
                continue
            if len(tokens) == 1:
                col = _nearest_column(_x_centre(cells[i]), anchors)
                _assign(values, col, PlacedValue(
                    column_index=col,
                    token=tokens[0],
                    source_cell_index=i,
                    confidence=cells[i].confidence,
                    from_split=False,
                ))
            else:
                cols = _place_tokens_across_span(
                    tokens, cells[i].page_bbox_x, cells[i].page_bbox_w, anchors,
                )
                for token, col in zip(tokens, cols, strict=True):
                    _assign(values, col, PlacedValue(
                        column_index=col,
                        token=token,
                        source_cell_index=i,
                        confidence=cells[i].confidence,
                        from_split=True,
                    ))

        label = " ".join(text for _, text in sorted(label_parts))
        out.append(
            ReconstructedRow(
                row_y=_y_centre(cells[row[0]]),
                label=label,
                label_cell_index=label_cell_index,
                values=values,
            ),
        )
    return out


def _assign(values: dict[int, PlacedValue], col: int, placed: PlacedValue) -> None:
    """Place a value at a column; on collision keep the higher-confidence one.

    Two tokens snapping to the same column is a placement ambiguity (e.g. a
    split mis-distributed). We keep the more-confident token and leave the
    other dropped — the disagreement is observable because ``from_split``
    flags split provenance and the reconstruction caller can re-derive.
    """
    existing = values.get(col)
    if existing is None:
        values[col] = placed
        return
    ec = existing.confidence if existing.confidence is not None else 0.0
    pc = placed.confidence if placed.confidence is not None else 0.0
    if pc > ec:
        values[col] = placed
