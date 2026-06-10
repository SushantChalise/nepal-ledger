"""Intergovernmental fiscal-transfer parser (Phase B1) — per-local-level grants.

Source: MoF/NNRFC ``अन्तरसरकारी वित्तीय हस्तान्तरण`` (intergovernmental fiscal
transfer) annual books, in-repo at
``Financial Data/mof_documents/intergovernmental/<FY>.pdf``. Each book lists,
per local level, the federal grant allocation broken into the 8 atomic
components of Nepal's fiscal-federalism chart of accounts.

Output: rows matching ``local_government_fiscal_transfers``
(``src/lib/db/schema/fiscal-transfers.ts``) — exactly the shape the FY2082/83
XLSX parser (``mof_fiscal_transfers``) emits, so the historical FYs extend the
same time series.

-------------------------------------------------------------------------------
THE DUAL-CHANNEL DESIGN (read this before changing extraction_method)
-------------------------------------------------------------------------------
Investigation of the in-repo PDFs (task #52) found two distinct page types:

  * Text-layer-clean books (FY2078/79, FY2079/80): the embedded text layer
    yields the NUMBERS exactly — every local-level row's 8 atomic components
    sum to its printed grand total, and the 753 grand totals sum to the
    document's printed ``स्थानीय तह`` (local-level) total, TO THE RUPEE. The
    Devanagari LABELS in the text layer are font-corrupted (dropped matras),
    but we don't need names — the 9-digit local-level code is the join key.

  * Scanned books (FY2074/75, 2075/76, 2077/78, 2080/81, 2081/82, 2082/83-pdf):
    no usable numeric text layer → genuine Surya OCR territory. Deferred until
    OCR output reconciles (the harness is ready; per-FY reconciliation is the
    gate). See ``RECONCILABLE_FYS`` / ``SCANNED_FYS``.

For the text-layer-clean FYs we therefore take the NUMERIC VALUES from the text
layer (deterministic, exact, self-reconciling — ADR-0021 Tier 0/1) and use the
Surya harness as an INDEPENDENT CROSS-VALIDATION channel that (a) recovers the
correct Devanagari labels, (b) confirms the values cell-by-cell, and (c)
populates the ``ocr_tracking`` trio for inspectability. ``extraction_method``
is recorded HONESTLY per run: ``textlayer`` when only the deterministic text
layer ran (values are always text-layer-derived), and
``surya-ocr+textlayer-xcheck`` only when the Surya channel actually ran
(``--surya``) — never claim an OCR cross-check that did not happen. Confidence
is B (recovered historical data). This maximizes BOTH completeness (100% of
rows ship, none dropped to OCR digit errors) and accuracy (the text-layer
values self-reconcile to the printed document total), which is the mission
guardrail.

Code crosswalk (verified 753/753, zero misses): the PDF uses a 9-digit code
that is the canonical 8-digit federal code + a trailing ``3``. We strip the
trailing digit to recover ``entities.slug`` for ``kind='local_level'``.

Unit: the books print ``रु. लाखमा`` (NPR lakh). The FY2082/83 XLSX rows are
stored in ``npr_crore``; to keep the series directly comparable we convert
lakh → crore (÷10) and store ``unit='npr_crore'``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Literal

import fitz  # pymupdf

# ``fitz`` lacks a py.typed marker → ``fitz.Document`` resolves to ``Any``
# under ``disallow_any_unimported``. Explicit alias for signatures.
FitzDocument = Any

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "mof-intergovernmental"

# FY filename stem -> BS fiscal-year label.
FY_BY_STEM: Final[dict[str, str]] = {
    "207475": "2074/75",
    "207576": "2075/76",
    "207677": "2076/77",
    "207778": "2077/78",
    "207879": "2078/79",
    "207980": "2079/80",
    "208081": "2080/81",
    "208182": "2081/82",
    "208283": "2082/83",
}

# Books whose text layer reconciles end-to-end with the 14-column detail model
# (8- OR 9-digit leading codes). Each verified 753/753 rows AND the 753 grand
# totals summing to the printed ``स्थानीय तह`` document total to the rupee.
# (FY2082/83 also lives here via the XLSX feed; the PDF is a redundant copy and
# is not re-ingested — running the CLI on it would only skip-dup.)
RECONCILABLE_FYS: Final[frozenset[str]] = frozenset(
    {"2078/79", "2079/80", "2080/81", "2081/82", "2082/83"},
)
# Books with a text layer but a DIFFERENT detail layout (not the 14-column
# model) — recovery pending a per-edition adapter. parse() refuses them rather
# than risk mis-mapping columns (honest failure; never ship mis-parsed data):
#   * 2074/75, 2075/76 — early fiscal-federalism format: 7-digit code + ~5
#     value columns (fewer grant types existed then), larger unit.
#   * 2076/77 — richer text layer with a different code/column geometry.
DEFERRED_LAYOUT_FYS: Final[frozenset[str]] = frozenset(
    {"2074/75", "2075/76", "2076/77"},
)
# Genuinely image-only scans (no usable numeric text layer) — Surya-OCR-only,
# deferred until OCR output reconciles per ADR-0021.
SCANNED_FYS: Final[frozenset[str]] = frozenset({"2077/78"})

# ── Column model ──────────────────────────────────────────────────────────
# The detail tables have 14 numeric columns. Index → meaning:
#   0 eq_minimum   1 eq_formula  2 eq_performance  3 eq_subtotal
#   4 cond_current 5 cond_capital                  6 cond_subtotal
#   7 spec_current 8 spec_capital                  9 spec_subtotal
#  10 complementary_capital
#  11 current_total 12 capital_total 13 GRAND TOTAL
# We store the 8 ATOMIC components (subtotals/totals are derived + excluded).
_GrantType = Literal[
    "equalization_minimum",
    "equalization_formula",
    "equalization_performance",
    "conditional_current",
    "conditional_capital",
    "special_current",
    "special_capital",
    "complementary_capital",
]
_COLUMN_TO_GRANT: Final[dict[int, _GrantType]] = {
    0: "equalization_minimum",
    1: "equalization_formula",
    2: "equalization_performance",
    4: "conditional_current",
    5: "conditional_capital",
    7: "special_current",
    8: "special_capital",
    10: "complementary_capital",
}
_ATOMIC_COLUMNS: Final[tuple[int, ...]] = tuple(_COLUMN_TO_GRANT)
_GRAND_TOTAL_COLUMN: Final[int] = 13
_NUM_COLUMNS: Final[int] = 14

# Detail-page numeric column x-anchors (pt, on the un-scaled PDF). Tolerant
# nearest-match handles the small per-page jitter. Derived from the FY2079/80
# + FY2078/79 detail pages; the same layout holds across both books.
_DETAIL_ANCHORS: Final[tuple[int, ...]] = (
    233, 270, 328, 358, 396, 443, 477, 523, 559, 588, 645, 677, 714, 749,
)
# A row's leading 9-digit local-level code starts in this x-band.
_CODE_MAX_X: Final[float] = 200.0
_Y_BUCKET: Final[int] = 4  # row-grouping tolerance (pt) for text-layer words
# The PDF local-level code is 9 digits = 8-digit federal code + trailing '3'.
_PDF_CODE_LEN: Final[int] = 9
_FEDERAL_CODE_LEN: Final[int] = 8
_MAX_VALUE_DIGITS: Final[int] = 4  # ungrouped value cells are <= 4 digits

_LAKH_PER_CRORE: Final[float] = 10.0
_RECONCILE_TOL_LAKH: Final[float] = 0.5  # rupee-exact in lakh terms
# Surya line-confidence below which a cell is flagged for sample verification
# (findings §5.5 — flag, don't drop).
_LOW_CONF_THRESHOLD: Final[float] = 0.75


@dataclass(frozen=True)
class TransferRow:
    """One (local_level × grant_type) historical fiscal-transfer fact.

    Mirrors ``mof_fiscal_transfers.FiscalTransferRow`` so both feed the same
    ingest path / table. ``municipality_name_*`` are left empty here — the
    entity is resolved from ``federal_code`` (the seeded 8-digit slug); the
    historical text layer's names are font-corrupted and unneeded.
    """

    federal_code: str  # 8-digit; matches entities.slug for kind='local_level'
    municipality_name_en: str
    municipality_name_ne: str
    local_level_type: str
    district_en: str
    fiscal_year_bs: str
    grant_type: str
    amount_npr: float  # in unit below (npr_crore)
    unit: str
    confidence_grade: Literal["A", "B", "C"]
    notes: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationReport:
    """Per-FY reconciliation outcome — the ADR-0021 gate evidence."""

    fiscal_year_bs: str
    local_level_count: int
    rows_reconciled: int
    rows_failed: int
    row_grand_total_sum_lakh: float
    printed_local_total_lakh: float | None
    document_total_reconciles: bool

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(token: str) -> float:
    """Parse a Nepali-grouped Arabic-numeral token (``1,29,46,06``) to float."""
    return float(token.replace(",", ""))


def _is_value_token(token: str) -> bool:
    """A numeric value cell: digits + commas, short enough to not be a code."""
    bare = token.replace(",", "")
    if not bare.isdigit():
        return False
    # Exclude the 9-digit local-level code (and any other long id) — value
    # cells in this table are at most 4 ungrouped digits (e.g. '1,29,46,06').
    return ("," in token) or len(bare) <= _MAX_VALUE_DIGITS


def _nearest_column(x: float) -> int:
    best = 0
    best_d = abs(x - _DETAIL_ANCHORS[0])
    for i in range(1, _NUM_COLUMNS):
        d = abs(x - _DETAIL_ANCHORS[i])
        if d < best_d:
            best_d = d
            best = i
    return best


def _crosswalk_code(code: str) -> str | None:
    """PDF local-level code -> 8-digit federal code (== entities.slug).

    Two edition formats, both verified 753/753 against the seeded slugs:
      * 9-digit (FY2078/79, 2079/80): 8-digit federal code + trailing '3' →
        strip the trailing '3'.
      * 8-digit (FY2080/81, 2081/82, 2082/83): already the federal code →
        identity.
    Returns None when the code fits neither verified pattern.
    """
    if not code.isdigit() or not code.startswith("80"):
        return None
    if len(code) == _PDF_CODE_LEN and code[-1] == "3":
        return code[:-1]
    if len(code) == _FEDERAL_CODE_LEN:
        return code
    return None


@dataclass
class _RawRow:
    code: str  # 8- or 9-digit leading local-level code (edition-dependent)
    col_vals: dict[int, str]
    page_number: int


def _extract_text_layer_rows(doc: FitzDocument) -> list[_RawRow]:
    """Pull every local-level row from the PDF text layer, by x-position.

    The leading row code is 8 digits (FY2080/81+) or 9 digits (FY2078/79,
    2079/80); both start ``80`` and sit in the left ``_CODE_MAX_X`` band.
    """
    rows: list[_RawRow] = []
    for pno in range(doc.page_count):
        by_y: dict[int, list[tuple[float, str]]] = {}
        for w in doc[pno].get_text("words"):
            x0, y0, text = w[0], w[1], w[4]
            by_y.setdefault(round(y0 / _Y_BUCKET) * _Y_BUCKET, []).append((x0, text))
        for y in sorted(by_y):
            items = sorted(by_y[y])
            code: str | None = None
            for x, t in items:
                if (
                    x < _CODE_MAX_X
                    and t.isdigit()
                    and len(t) in (_FEDERAL_CODE_LEN, _PDF_CODE_LEN)
                    and t.startswith("80")
                ):
                    code = t
                    break
            if code is None:
                continue
            col_vals: dict[int, str] = {}
            for x, t in items:
                if t == code:
                    continue
                if _is_value_token(t):
                    col_vals[_nearest_column(x)] = t
            rows.append(_RawRow(code=code, col_vals=col_vals, page_number=pno))
    return rows


def _row_reconciles(col_vals: dict[int, str]) -> bool:
    """A row reconciles iff its 8 atomic components sum to its grand total."""
    if not all(c in col_vals for c in _ATOMIC_COLUMNS):
        return False
    if _GRAND_TOTAL_COLUMN not in col_vals:
        return False
    atomic_sum = sum(_num(col_vals[c]) for c in _ATOMIC_COLUMNS)
    grand = _num(col_vals[_GRAND_TOTAL_COLUMN])
    return abs(atomic_sum - grand) < _RECONCILE_TOL_LAKH


# Stable Devanagari substring of the font-corrupted ``स्थानीय तह`` label
# (text-layer renders it ``1थानीय`` / ``,थानीय`` / ``/थानीय`` — all share this).
_LOCAL_LEVEL_LABEL_SUFFIX: Final[str] = "थानीय"
_LABEL_BAND_MAX_X: Final[float] = 120.0


def _printed_local_total_lakh(doc: FitzDocument) -> float | None:
    """Read the document's printed ``स्थानीय तह`` grand total (kul jamma).

    The summary page (by local-level type) has a ``स्थानीय तह`` row whose last
    column is the system-wide ``कुल जम्मा``. We locate that specific row by its
    label (matched on the stable suffix ``थानीय`` in the label band) and take
    the rightmost value token on the row — the grand-total column. This is the
    ADR-0021 printed grand total the per-row sum must reconcile to.
    """
    for pno in range(min(doc.page_count, 6)):
        page = doc[pno]
        if _LOCAL_LEVEL_LABEL_SUFFIX not in page.get_text():
            continue
        by_y: dict[int, list[tuple[float, str]]] = {}
        for w in page.get_text("words"):
            by_y.setdefault(round(w[1] / _Y_BUCKET) * _Y_BUCKET, []).append((w[0], w[4]))
        for items in by_y.values():
            has_label = any(
                x < _LABEL_BAND_MAX_X and _LOCAL_LEVEL_LABEL_SUFFIX in t
                for x, t in items
            )
            if not has_label:
                continue
            # Grand total = rightmost value token on this row.
            values = [(x, t) for x, t in items if _is_value_token(t)]
            if not values:
                continue
            rightmost = max(values, key=lambda xt: xt[0])
            return _num(rightmost[1])
    return None


def parse(
    source_document_path: str,
    source_document_id: str,
    *,
    require_reconcile: bool = True,
    surya_xcheck: bool = False,
) -> dict[str, Any]:
    """Parse one intergovernmental book → transfer rows + reconciliation.

    Returns the standard parser JSON shape plus a ``reconciliation`` block.
    ``status`` is ``failure`` when the FY is scanned-only (no text layer) or
    when ``require_reconcile`` and the document total does not reconcile.

    ``surya_xcheck`` records provenance HONESTLY: the per-row numeric values
    always come from the deterministic text layer, so the default
    ``extraction_method`` is ``textlayer``. Only when the caller actually runs
    the Surya cross-validation channel (``--surya``) is the method recorded as
    ``surya-ocr+textlayer-xcheck`` — never claim an OCR cross-check that did
    not run (mission guardrail: honest provenance).
    """
    _ = source_document_id  # threaded for symmetry; identity handled Node-side
    path = Path(source_document_path)
    stem = path.stem
    fy = FY_BY_STEM.get(stem)
    errors: list[dict[str, Any]] = []

    if fy is None:
        errors.append({
            "error_class": "Other",
            "error_detail": f"unknown intergovernmental FY for file stem {stem!r}",
            "source_excerpt": None,
        })
        return _result("failure", [], errors, None)

    if fy in SCANNED_FYS:
        errors.append({
            "error_class": "PageLayoutChanged",
            "error_detail": (
                f"FY{fy} has no usable numeric text layer (scanned). Surya-OCR-only; "
                "deferred until OCR output reconciles (ADR-0021). Harness is ready."
            ),
            "source_excerpt": None,
        })
        return _result("failure", [], errors, None)

    if fy in DEFERRED_LAYOUT_FYS:
        errors.append({
            "error_class": "PageLayoutChanged",
            "error_detail": (
                f"FY{fy} has a text layer but a different detail layout (not the 14-column "
                "model) — recovery pending a per-edition adapter. Refusing to mis-map columns."
            ),
            "source_excerpt": None,
        })
        return _result("failure", [], errors, None)

    doc = fitz.open(str(path))
    try:
        raw_rows = _extract_text_layer_rows(doc)
        printed_total = _printed_local_total_lakh(doc)
    finally:
        doc.close()

    rows: list[TransferRow] = []
    reconciled = 0
    failed = 0
    grand_sum_lakh = 0.0
    # Honest provenance: values are text-layer-derived in BOTH modes. Only label
    # the row as Surya-cross-checked when the Surya channel actually runs.
    method = "surya-ocr+textlayer-xcheck" if surya_xcheck else "textlayer"

    for raw in raw_rows:
        code8 = _crosswalk_code(raw.code)
        if code8 is None:
            failed += 1
            errors.append({
                "error_class": "RegexMismatch",
                "error_detail": f"code {raw.code!r} does not fit the 8/9-digit crosswalk",
                "source_excerpt": None,
            })
            continue
        if not _row_reconciles(raw.col_vals):
            failed += 1
            errors.append({
                "error_class": "ValueUnparseable",
                "error_detail": (
                    f"local-level {code8} (FY{fy}) atomic components do not sum to "
                    "printed grand total — row not shipped"
                ),
                "source_excerpt": None,
            })
            continue
        reconciled += 1
        grand_sum_lakh += _num(raw.col_vals[_GRAND_TOTAL_COLUMN])
        for col, grant in _COLUMN_TO_GRANT.items():
            amount_lakh = _num(raw.col_vals[col])
            amount_crore = round(amount_lakh / _LAKH_PER_CRORE, 4)
            rows.append(
                TransferRow(
                    federal_code=code8,
                    municipality_name_en="",
                    municipality_name_ne="",
                    local_level_type="",
                    district_en="",
                    fiscal_year_bs=fy,
                    grant_type=grant,
                    amount_npr=amount_crore,
                    unit="npr_crore",
                    confidence_grade="B",
                    notes=f"extraction_method={method}; source=intergovernmental/{stem}.pdf",
                ),
            )

    document_reconciles = (
        printed_total is not None
        and abs(grand_sum_lakh - printed_total) < _RECONCILE_TOL_LAKH
    )
    report = ReconciliationReport(
        fiscal_year_bs=fy,
        local_level_count=reconciled,
        rows_reconciled=reconciled,
        rows_failed=failed,
        row_grand_total_sum_lakh=round(grand_sum_lakh, 2),
        printed_local_total_lakh=printed_total,
        document_total_reconciles=document_reconciles,
    )

    if not rows:
        return _result("failure", rows, errors or [{
            "error_class": "Other",
            "error_detail": f"FY{fy}: parsed zero reconciled local-level rows",
            "source_excerpt": None,
        }], report)

    if require_reconcile and not document_reconciles:
        errors.append({
            "error_class": "ValueUnparseable",
            "error_detail": (
                f"FY{fy} document total mismatch: sum of {reconciled} local-level "
                f"grand totals = {grand_sum_lakh:.0f} lakh vs printed "
                f"{printed_total} lakh — refusing to ship (ADR-0021)"
            ),
            "source_excerpt": None,
        })
        return _result("failure", rows, errors, report)

    status = "partial" if failed else "success"
    return _result(status, rows, errors, report)


def _result(
    status: str,
    rows: list[TransferRow],
    errors: list[dict[str, Any]],
    report: ReconciliationReport | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "parser_version": PARSER_VERSION,
        "rows": [asdict(r) for r in rows],
        "errors": errors,
        "reconciliation": report.to_json_dict() if report is not None else None,
    }


# ── Surya cross-validation channel (the ocr_tracking trio + value confirm) ──
# This is the GPU path. It is OPTIONAL on the value-extraction (the text layer
# is the value source); its jobs are (1) populate ocr_tracking so the run is
# inspectable, and (2) independently confirm the text-layer values cell-by-cell
# so disagreements surface for sample verification (ADR-0021 gate step 2).

# First detail page (0-based) where per-local-level rows begin. Pages 0–9 are
# cover / by-type / by-province summaries (validated on FY2079/80 + FY2078/79).
_FIRST_DETAIL_PAGE: Final[int] = 10


@dataclass(frozen=True)
class CrossValidationReport:
    """Surya cross-check summary for one FY (ocr_tracking population + matches).

    ``value_cells_compared`` / ``value_cells_agreeing`` measure how often a
    Surya-read numeric token matched the text-layer value at the same grid
    position — the independent-channel confirmation rate. Low-confidence and
    near-seam cells are where mismatches concentrate (and are exactly the
    sample-verification bias the schema's ``near_tile_seam_px`` enables).
    """

    fiscal_year_bs: str
    pages_ocred: int
    tile_count: int
    cell_count: int
    disagreement_count: int
    value_cells_compared: int
    value_cells_agreeing: int
    mean_line_confidence: float

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def cross_validate_with_surya(
    source_document_path: str,
    *,
    max_pages: int | None = None,
    sample_low_confidence: int = 20,
) -> dict[str, Any]:
    """Run the Surya harness over the detail pages → ocr_tracking + match rate.

    Returns a dict with ``ocr_pages`` (list of ``OcrPageResult.to_json_dict()``
    — the tiles/cells/disagreements the Node ingest maps onto the ocr_tracking
    trio) and a ``cross_validation`` report. GPU-bound; the caller decides
    whether to run it (the text-layer ``parse`` already produced shippable
    rows). Imports the harness lazily so non-GPU callers of this module pay
    nothing.
    """
    # This module is invoked BOTH as an importable package member (pytest) and
    # as a bare script by the Node CLI (`python .../intergovernmental.py …`).
    # Under the bare-script entry point there is no parent package, so a
    # relative `from .. import` raises "attempted relative import with no known
    # parent package". Bootstrap the `scrapers/` dir onto sys.path (idempotent)
    # and use absolute imports, which resolve under both entry points.
    import sys

    scrapers_dir = str(Path(__file__).resolve().parents[2])
    if scrapers_dir not in sys.path:
        sys.path.insert(0, scrapers_dir)
    from surya_ocr import HarnessConfig, kept_cells, ocr_page
    from surya_ocr.cleanup import split_numeric_tokens

    path = Path(source_document_path)
    fy = FY_BY_STEM.get(path.stem, path.stem)

    doc = fitz.open(str(path))
    try:
        last = (
            doc.page_count
            if max_pages is None
            else min(doc.page_count, _FIRST_DETAIL_PAGE + max_pages)
        )
        page_range = list(range(_FIRST_DETAIL_PAGE, last))
        config = HarnessConfig()
        ocr_pages = [ocr_page(doc, p, config) for p in page_range]
    finally:
        doc.close()

    tile_count = sum(len(p.tiles) for p in ocr_pages)
    cell_count = sum(len(p.cells) for p in ocr_pages)
    disagreement_count = sum(len(p.disagreements) for p in ocr_pages)

    confs: list[float] = []
    value_cells_compared = 0
    value_cells_agreeing = 0
    low_conf_samples: list[dict[str, Any]] = []
    for page_result in ocr_pages:
        kept = set(kept_cells(page_result))
        for idx, cell in enumerate(page_result.cells):
            if cell.confidence is not None:
                confs.append(cell.confidence)
            if idx not in kept:
                continue
            tokens = split_numeric_tokens(cell.text_raw)
            if not tokens:
                continue
            # Count every numeric token Surya emitted in a surviving cell as a
            # comparison candidate; the actual text-layer agreement is computed
            # by the Node side against the parsed rows. Here we surface the
            # low-confidence + near-seam samples for spot-checking.
            value_cells_compared += len(tokens)
            is_low_conf = cell.confidence is not None and cell.confidence < _LOW_CONF_THRESHOLD
            if is_low_conf and len(low_conf_samples) < sample_low_confidence:
                low_conf_samples.append({
                    "page_number": cell.page_number,
                    "tile_index": cell.tile_index,
                    "page_bbox": [cell.page_bbox_x, cell.page_bbox_y,
                                  cell.page_bbox_w, cell.page_bbox_h],
                    "near_tile_seam_px": cell.near_tile_seam_px,
                    "text_raw": cell.text_raw,
                    "confidence": cell.confidence,
                })

    mean_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
    report = CrossValidationReport(
        fiscal_year_bs=fy,
        pages_ocred=len(ocr_pages),
        tile_count=tile_count,
        cell_count=cell_count,
        disagreement_count=disagreement_count,
        value_cells_compared=value_cells_compared,
        value_cells_agreeing=value_cells_agreeing,  # computed Node-side
        mean_line_confidence=mean_conf,
    )
    return {
        "ocr_pages": [p.to_json_dict() for p in ocr_pages],
        "cross_validation": report.to_json_dict(),
        "low_confidence_samples": low_conf_samples,
    }


def _main() -> None:
    """CLI: ``intergovernmental.py <pdf> <source_document_id> [--surya] [--max-pages N]``.

    Without ``--surya``: text-layer extraction + reconciliation only (fast, no
    GPU). With ``--surya``: also runs the Surya cross-validation channel and
    attaches ``ocr_pages`` + ``cross_validation`` to the JSON (GPU-bound).
    ``--max-pages N`` bounds the Surya channel to the first N detail pages
    (smoke-testing / incremental runs); omit it to OCR every detail page.
    """
    import io
    import json
    import sys

    # The Surya channel emits Devanagari ``text_raw`` in the JSON
    # (``ensure_ascii=False``). On Windows the default stdout codec is cp1252,
    # which cannot encode Devanagari → UnicodeEncodeError mid-dump. Force UTF-8
    # so the JSON contract holds on every platform.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

    run_surya = "--surya" in sys.argv[1:]
    max_pages: int | None = None
    positional: list[str] = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--surya":
            i += 1
        elif arg == "--max-pages":
            if i + 1 >= len(argv):
                sys.stderr.write("--max-pages requires an integer value\n")
                sys.exit(2)
            max_pages = int(argv[i + 1])
            i += 2
        elif arg.startswith("--max-pages="):
            max_pages = int(arg.split("=", 1)[1])
            i += 1
        else:
            positional.append(arg)
            i += 1

    expected_argc = 2
    if len(positional) != expected_argc:
        sys.stderr.write(
            "usage: intergovernmental.py <source_document_path> "
            "<source_document_id> [--surya] [--max-pages N]\n",
        )
        sys.exit(2)
    result = parse(positional[0], positional[1], surya_xcheck=run_surya)
    if run_surya and result["status"] in {"success", "partial"}:
        result["surya"] = cross_validate_with_surya(positional[0], max_pages=max_pages)
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    _main()
