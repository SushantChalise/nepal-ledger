# `surya_ocr` — Tier-2 Surya tile-OCR harness

Reusable optical-recognition pipeline for Nepal Ledger PDF recovery, per
[ADR-0021](../../docs/decisions/0021-pdf-recovery-tiers-and-verification-gate.md)
(recovery tiers) and [ADR-0022](../../docs/decisions/0022-surya-ocr-pipeline.md)
(this harness's design). It implements the Phase B pipeline mandated by
`docs/FINANCIAL_DATA_STRATEGY.md` §Phase B and populates the `ocr_tracking`
schema trio (`ocr_tile_manifests` / `ocr_cell_extractions` /
`ocr_stitch_disagreements`).

**ADR-0003 posture:** Surya does *recognition with confidence*, not generative
extraction. Every value is read optically, normalized deterministically, and
gated by reconciliation + sample verification before it can enter the truth
layer. No LLM ever produces a number here.

## Pipeline

```
PDF + page range
  → render        pymupdf fitz.Matrix(zoom,zoom); RGB PIL    (render.py)
  → preprocess?   OpenCV deskew/denoise/binarize (opt-in)    (render.py)
  → tile          overlapping windows; single-tile fast path (tiling.py)
  → OCR per tile  Surya detection + recognition              (engine.py)
  → to CellExtraction  page-global bbox + seam distance      (harness.py)
  → normalize     _common.devanagari_normalization           (harness.py)
                  (OCR-substitution dict + BOTH numeral systems)
  → stitch        IoU-dedupe overlapping tiles; log disagreements (stitch.py)
  ⇒ OcrPageResult (tiles, cells, disagreements)               (types.py)

then, separately, the domain parser calls:
  → reconstruct_table   bbox-cluster cells → labelled rows × columns (reconstruct.py)
                        (splits merged multi-number cells)
```

`reconstruct.py` is deliberately **not** part of the per-page harness output:
the harness is domain-agnostic (it doesn't know what the columns mean), so
table reconstruction is an importable step the domain parser drives with its
own column semantics.

## Validated parameters (Surya 0.17.1, RTX 4060, task #50)

| Param | Value | Why |
|---|---|---|
| Render zoom | `fitz.Matrix(3,3)` (≈216 DPI) | RECOVERY_PROGRAM pin; high-confidence output on province tables. Findings §5.2 caps useful raster at ~2048 px long-edge; a 3x landscape MoF page (≈2463 px) was still clean in a single tile, so `max_edge_px` has headroom. |
| `max_edge_px` | 2200 | Tile above this; keeps most A4-ish MoF pages single-tile, slices genuinely-wide/tall pages. |
| `overlap_px` | 256 | Wide enough that a table row split by a seam is whole in one tile. |
| Surya call | `rec([img], det_predictor=det)` | Detection-driven line bboxes — the path that behaves best on Devanagari (findings §2). |
| Preprocess | **off** for born-digital | These MoF PDFs render crisp; OpenCV is for scanned legacy pages (Yellow/Red books). |
| Confidence review gate | mean line conf < 0.75 | Findings §5.5 — flag, don't drop. |

## Observed Surya 0.17.1 failure modes (and how the harness handles them)

From the validation run on page 6 of `207980.pdf` (the FY2079/80
intergovernmental province table — 7 provinces × 14 numeric columns):

1. **Labels OCR far better than the PDF text layer.** The embedded text layer
   in these PDFs is *corrupted* (dropped matras: `ववरण` for `विवरण`, stray
   `सु"मा`). Surya read the headers correctly in Unicode Devanagari at
   conf > 0.99 (`समानीकरण अनुदान (२६३३१)`, the budget-head codes `(२६३३२)`
   etc.). **OCR is the better label source here**, not a fallback.
2. **Adjacent-column merging (dominant issue).** Surya's detector frequently
   draws ONE bbox across 2–3 horizontally adjacent numbers, emitting
   `'९२,०० ११,५२,२७'` or `'७,७४,६६ | १०,०६,५१'`. `cleanup.split_numeric_tokens`
   splits the line; `reconstruct._place_tokens_across_span` distributes the
   tokens across the columns the bbox spans. **This is the key fix** that
   makes merged cells recoverable instead of lost.
3. **Arabic-Indic digit leakage.** A Devanagari digit is occasionally
   classified as its Arabic-Indic (Persian, U+0660–U+0669) look-alike:
   `٩,८८,٩८` for `९,८८,९८`. `cleanup.fold_arabic_indic_digits` folds them
   (lossless — same digit values).
4. **Spurious markup.** Surya emits `<br>`, `<b>…</b>`, `<math>` (findings
   issues #410/#467). `cleanup.strip_markup` removes them; `<br>` → space.
5. **Low-confidence cells flag themselves.** Confidence rides on every cell
   (`ocr_cell_extractions.confidence`); low-confidence + near-seam cells are
   the spot-check sampling bias (`near_tile_seam_px`).

## Reconciliation discipline (ADR-0021 gate)

The harness records provenance; it does NOT decide what ships. The domain
parser must reconcile extracted subtotals/totals to the document's PRINTED
grand-total rows before any fact is promoted. The intergovernmental tables
self-reconcile (8 atomic grant components sum to the printed grand total per
row), giving a strong internal check. A FY that doesn't reconcile is deferred,
never shipped.

## Determinism

Surya is neural and sets no global seed; CUDA attention is not bit-exact
(findings §11). We pin `surya-ocr==0.17.1` and record `model_name` +
`model_version` + `dpi` per tile in `ocr_tile_manifests`. A re-run that
diverges is a model-drift event to re-validate — never a silent overwrite.

## Tests

```
cd scrapers
PYTHONPATH=$PWD <base-py312-python> -m pytest surya_ocr/tests -q
```

- `test_cleanup.py` — markup strip, digit fold, merged-number split (cases are
  REAL Surya output strings from page 6 of `207980.pdf`).
- `test_tiling.py` — windowing grid + seam-distance geometry.
- `test_stitch.py` — IoU dedupe + disagreement recording.
- `test_reconstruct.py` — bbox clustering into rows/columns, incl. the
  merged-cell split path.

The GPU path (`engine.py`, the render+OCR in `harness.py`) is exercised by the
domain parser's live validation run, not unit tests — it needs the model
weights and a GPU. The pure-logic modules above are fully unit-tested without
the heavy stack (importing `surya_ocr` does not import torch/surya/cv2).

## Env

Base py312 GPU interpreter (NOT the scrapers venv):
`C:/Users/ACER/AppData/Local/Programs/Python/Python312/python.exe`
(torch cu128, surya-ocr 0.17.1, pymupdf, opencv). Set
`PYTHONPATH=<worktree>/scrapers` for `_common`. First run downloads/caches the
Surya weights to `%LOCALAPPDATA%\datalab\models`.
