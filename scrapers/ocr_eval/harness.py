"""
OCR evaluation harness — 4 pipelines x 5 pages.

Pipelines:
  A: Surya OCR @ 192 DPI flat (default baseline)
  B: Surya OCR @ 384 DPI, 2x2 tiled with 80 px overlap
  C: Surya OCR @ 576 DPI, 3x3 tiled with 100 px overlap
  D: PaddleOCR @ 300 DPI flat

For each (page, pipeline) we emit:
  docs/research/ocr-eval/<page>/pipeline-<X>.json
  docs/research/ocr-eval/<page>/source-crop.png   (rendered once at 192 DPI)
  docs/research/ocr-eval/<page>/judge-rubric.md   (template)

Per-cell record: {page, pipeline, cell_index, bbox_page, text, confidence, language_detected}
bbox_page is in the coordinate space of the source-crop.png (192 DPI).

Preprocessing for Surya: OpenCV deskew + denoise + adaptive-threshold pre-bin
(per surya-ocr-findings.md §5.3). PaddleOCR receives the raw rendered RGB
because its own preprocessing pipeline is built-in.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image

# Surya env overrides — set BEFORE importing surya.
os.environ.setdefault("TABLE_REC_MAX_BOXES", "500")
os.environ.setdefault("DISABLE_TQDM", "true")
os.environ.setdefault("TORCH_DEVICE", "cpu")
os.environ.setdefault("RECOGNITION_BATCH_SIZE", "8")
os.environ.setdefault("DETECTOR_BATCH_SIZE", "2")

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "Financial Data"
OUT_ROOT = ROOT / "docs" / "research" / "ocr-eval"

# Final page selections (locked).
PAGES: dict[str, dict[str, Any]] = {
    "P1": {
        "name": "P1_yellowbook_p016",
        "pdf": CORPUS / "mof_documents/yellowbook/1685280975_Yellow Book BIG 2080 Final_6jh3p9r.pdf",
        "page_index": 16,
        "description": "Yellow Book PE-financial table — Devanagari labels + numeric columns; medium density.",
    },
    "P2": {
        "name": "P2_redbook_p025",
        "pdf": CORPUS / "mof_documents/redbook/Redbook (Final)_2079_80_uryb8ga.pdf",
        "page_index": 25,
        "description": "Red Book budget line-item — densest Devanagari + 8-digit codes; small font.",
    },
    "P3": {
        "name": "P3_intergov_p026",
        "pdf": CORPUS / "mof_documents/intergovernmental/208283.pdf",
        "page_index": 26,
        "description": "Intergovernmental fiscal transfer table — 4 grant types x 20+ local levels.",
    },
    "P4": {
        "name": "P4_nrb_bfi_p001",
        "pdf": CORPUS / "nrb_monthly_statistics/bfi_niyamabali.pdf",
        "page_index": 1,
        "description": "NRB BFI regulation — text-dense Devanagari prose.",
    },
    "P5": {
        "name": "P5_old_redbook_p007",
        "pdf": CORPUS / "mof_documents/redbook/Budget Details - Red Book 2062 - 2063_20130717120229_cbmey2a.pdf",
        "page_index": 7,
        "description": "Worst scan — old (2062 BS) Red Book; low contrast, pixelated, slight rotation.",
    },
}

# ---------------------------------------------------------------------------
# Devanagari helpers
# ---------------------------------------------------------------------------
DEVANAGARI_DIGITS = set("०१२३४५६७८९")
DEVANAGARI_BLOCK = re.compile(r"[ऀ-ॿ]")
ARABIC_DIGITS = set("0123456789")


def detect_language(text: str) -> str:
    """Cheap script detector: returns 'devanagari', 'latin', 'mixed', or 'empty'."""
    if not text or not text.strip():
        return "empty"
    has_deva = bool(DEVANAGARI_BLOCK.search(text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if has_deva and has_latin:
        return "mixed"
    if has_deva:
        return "devanagari"
    if has_latin:
        return "latin"
    return "numeric_or_punct"


def has_devanagari_digits(text: str) -> bool:
    return any(c in DEVANAGARI_DIGITS for c in text)


def has_arabic_digits(text: str) -> bool:
    return any(c in ARABIC_DIGITS for c in text)


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------
def deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Estimate skew via min-area rect of dark pixels and rotate."""
    inv = 255 - gray
    coords = np.column_stack(np.where(inv > 50))
    if len(coords) < 100:
        return gray, 0.0
    angle = cv2.minAreaRect(coords)[-1]
    # normalize to [-45, 45]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    # only correct meaningful skew (>0.2 deg)
    if abs(angle) < 0.2:
        return gray, 0.0
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, float(angle)


def preprocess_for_surya(pil_img: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """Deskew + denoise + adaptive threshold per surya-ocr-findings.md §5.3."""
    arr = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gray, skew_deg = deskew(gray)
    # mild denoise — fastNlMeans is too slow on big pages; bilateral is faster
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=40, sigmaSpace=10)
    # adaptive threshold (Gaussian, block 31, C 12) recommended for Devanagari diacritics
    binar = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12
    )
    # convert back to RGB PIL — Surya needs PIL RGB
    rgb = cv2.cvtColor(binar, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(rgb), {"skew_deg": skew_deg}


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render_pdf_page(pdf_path: Path, page_index: int, dpi: int) -> Image.Image:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[page_index]
        img = page.render(scale=dpi / 72).to_pil().convert("RGB")
        page.close()
        return img
    finally:
        pdf.close()


# ---------------------------------------------------------------------------
# Tile / untile
# ---------------------------------------------------------------------------
@dataclass
class Tile:
    row: int
    col: int
    x0: int
    y0: int
    x1: int
    y1: int


def tile_image(img: Image.Image, rows: int, cols: int, overlap_px: int) -> list[tuple[Tile, Image.Image]]:
    w, h = img.size
    tile_w = (w + overlap_px * (cols - 1)) // cols
    tile_h = (h + overlap_px * (rows - 1)) // rows
    step_w = tile_w - overlap_px
    step_h = tile_h - overlap_px
    tiles: list[tuple[Tile, Image.Image]] = []
    for r in range(rows):
        for c in range(cols):
            x0 = c * step_w
            y0 = r * step_h
            x1 = min(x0 + tile_w, w)
            y1 = min(y0 + tile_h, h)
            if c == cols - 1:
                x1 = w
            if r == rows - 1:
                y1 = h
            crop = img.crop((x0, y0, x1, y1))
            tiles.append((Tile(r, c, x0, y0, x1, y1), crop))
    return tiles


# ---------------------------------------------------------------------------
# Coordinate mapping back to the 192-DPI source-crop coordinate frame
# ---------------------------------------------------------------------------
def map_bbox_to_source(
    bbox: list[float],
    source_dpi: int,
    rendered_dpi: int,
    tile_x0: int = 0,
    tile_y0: int = 0,
) -> list[float]:
    """Map a bbox produced at `rendered_dpi` (possibly inside a tile offset by
    tile_x0/tile_y0 in the rendered-image frame) back to the source-crop frame
    rendered at `source_dpi`.
    """
    scale = source_dpi / rendered_dpi
    x1, y1, x2, y2 = bbox
    return [
        round((x1 + tile_x0) * scale, 2),
        round((y1 + tile_y0) * scale, 2),
        round((x2 + tile_x0) * scale, 2),
        round((y2 + tile_y0) * scale, 2),
    ]


# ---------------------------------------------------------------------------
# Surya runner
# ---------------------------------------------------------------------------
_SURYA_PREDICTORS: dict[str, Any] = {}


def _get_surya_predictors() -> tuple[Any, Any]:
    """Lazy global init — Surya predictors take 30-60s to load."""
    if "rec" not in _SURYA_PREDICTORS:
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor

        t0 = time.time()
        fp = FoundationPredictor()
        _SURYA_PREDICTORS["rec"] = RecognitionPredictor(fp)
        _SURYA_PREDICTORS["det"] = DetectionPredictor()
        print(f"  [surya init] {time.time() - t0:.1f}s", flush=True)
    return _SURYA_PREDICTORS["rec"], _SURYA_PREDICTORS["det"]


def run_surya(images: list[Image.Image]) -> list[Any]:
    rec, det = _get_surya_predictors()
    return rec(images, det_predictor=det)


def surya_lines_to_records(
    ocr_result: Any,
    pipeline: str,
    page_label: str,
    *,
    source_dpi: int,
    rendered_dpi: int,
    tile_x0: int = 0,
    tile_y0: int = 0,
    start_cell_index: int = 0,
) -> tuple[list[dict], int]:
    records: list[dict] = []
    idx = start_cell_index
    for line in ocr_result.text_lines:
        bbox_src = map_bbox_to_source(
            list(line.bbox), source_dpi, rendered_dpi, tile_x0, tile_y0
        )
        text = line.text or ""
        records.append(
            {
                "page": page_label,
                "pipeline": pipeline,
                "cell_index": idx,
                "bbox_page": bbox_src,
                "text": text,
                "confidence": round(float(line.confidence or 0.0), 4),
                "language_detected": detect_language(text),
            }
        )
        idx += 1
    return records, idx


# ---------------------------------------------------------------------------
# PaddleOCR runner — lazy init so we don't pay the cost when only testing Surya
# ---------------------------------------------------------------------------
_PADDLE: Any | None = None


def _get_paddle() -> Any:
    global _PADDLE
    if _PADDLE is None:
        from paddleocr import PaddleOCR

        t0 = time.time()
        # Devanagari recognition. PaddleOCR 3.x: lang='devanagari' supports nepali/hindi.
        # use_doc_orientation_classify=False keeps it deterministic. CPU only.
        _PADDLE = PaddleOCR(
            lang="devanagari",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="cpu",
        )
        print(f"  [paddle init] {time.time() - t0:.1f}s", flush=True)
    return _PADDLE


def run_paddle(image_rgb_np: np.ndarray) -> Any:
    ocr = _get_paddle()
    # PaddleOCR 3.x: .predict returns a list of dict-like results per image
    # API: ocr.predict(input=ndarray) or ocr.ocr(image_path)
    try:
        out = ocr.predict(input=image_rgb_np)
    except AttributeError:
        # fallback to legacy API
        out = ocr.ocr(image_rgb_np)
    return out


def paddle_to_records(
    paddle_out: Any,
    pipeline: str,
    page_label: str,
    *,
    source_dpi: int,
    rendered_dpi: int,
) -> list[dict]:
    records: list[dict] = []
    scale = source_dpi / rendered_dpi

    # Two possible result shapes:
    # 1) PaddleOCR 3.x predict: list of OCRResult-like with .json['res']['rec_texts'] etc.
    # 2) Legacy .ocr() — list[list[[ box, (text, conf) ]]] per image.
    def _bbox_from_poly(poly: Any) -> list[float]:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return [
            round(min(xs) * scale, 2),
            round(min(ys) * scale, 2),
            round(max(xs) * scale, 2),
            round(max(ys) * scale, 2),
        ]

    idx = 0
    items: list[tuple[Any, str, float]] = []  # (poly, text, conf)

    # Try 3.x dict access first
    for item in paddle_out:
        if hasattr(item, "json"):
            try:
                d = item.json
                res = d.get("res", d)
                polys = res.get("rec_polys") or res.get("dt_polys") or []
                texts = res.get("rec_texts") or []
                scores = res.get("rec_scores") or []
                for p, t, s in zip(polys, texts, scores, strict=False):
                    items.append((p, t, float(s)))
                continue
            except Exception:
                pass
        # Legacy shape: a list of [poly, (text, conf)]
        if isinstance(item, list):
            for entry in item:
                if entry is None:
                    continue
                if len(entry) >= 2:
                    poly = entry[0]
                    tc = entry[1]
                    if isinstance(tc, (list, tuple)) and len(tc) >= 2:
                        items.append((poly, tc[0], float(tc[1])))

    for poly, text, conf in items:
        bbox_src = _bbox_from_poly(poly)
        text = text or ""
        records.append(
            {
                "page": page_label,
                "pipeline": pipeline,
                "cell_index": idx,
                "bbox_page": bbox_src,
                "text": text,
                "confidence": round(float(conf), 4),
                "language_detected": detect_language(text),
            }
        )
        idx += 1
    return records


# ---------------------------------------------------------------------------
# Summary stats per pipeline run
# ---------------------------------------------------------------------------
def summarize(records: list[dict]) -> dict:
    if not records:
        return {
            "cell_count": 0,
            "empty_text_count": 0,
            "mean_confidence": 0.0,
            "devanagari_lines": 0,
            "latin_lines": 0,
            "mixed_lines": 0,
            "empty_lines": 0,
            "lines_with_devanagari_digits": 0,
            "lines_with_arabic_digits": 0,
            "lines_with_both_digit_scripts": 0,
        }
    confs = [r["confidence"] for r in records if r["confidence"] > 0]
    deva = sum(1 for r in records if r["language_detected"] == "devanagari")
    latin = sum(1 for r in records if r["language_detected"] == "latin")
    mixed = sum(1 for r in records if r["language_detected"] == "mixed")
    empty = sum(1 for r in records if r["language_detected"] == "empty")
    with_deva_dig = sum(1 for r in records if has_devanagari_digits(r["text"]))
    with_ar_dig = sum(1 for r in records if has_arabic_digits(r["text"]))
    with_both = sum(
        1 for r in records if has_devanagari_digits(r["text"]) and has_arabic_digits(r["text"])
    )
    return {
        "cell_count": len(records),
        "empty_text_count": sum(1 for r in records if not r["text"].strip()),
        "mean_confidence": round(float(np.mean(confs)) if confs else 0.0, 4),
        "devanagari_lines": deva,
        "latin_lines": latin,
        "mixed_lines": mixed,
        "empty_lines": empty,
        "lines_with_devanagari_digits": with_deva_dig,
        "lines_with_arabic_digits": with_ar_dig,
        "lines_with_both_digit_scripts": with_both,
    }


# ---------------------------------------------------------------------------
# Pipeline drivers
# ---------------------------------------------------------------------------
SOURCE_DPI = 192  # source-crop.png is always rendered at this DPI


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def pipeline_A_surya_flat(pdf_path: Path, page_index: int, page_label: str) -> dict:
    t0 = time.time()
    img = render_pdf_page(pdf_path, page_index, dpi=192)
    pre, pp_meta = preprocess_for_surya(img)
    [result] = run_surya([pre])
    records, _ = surya_lines_to_records(
        result, "A", page_label, source_dpi=SOURCE_DPI, rendered_dpi=192
    )
    return {
        "pipeline": "A",
        "engine": "surya-ocr",
        "engine_version": "0.17.1",
        "dpi": 192,
        "tile": "flat",
        "preprocess": "deskew+bilateral+adaptive_threshold",
        "preprocess_meta": pp_meta,
        "elapsed_sec": round(time.time() - t0, 2),
        "records": records,
        "summary": summarize(records),
    }


def pipeline_surya_tiled(
    pdf_path: Path,
    page_index: int,
    page_label: str,
    *,
    pipeline: str,
    dpi: int,
    rows: int,
    cols: int,
    overlap: int,
) -> dict:
    t0 = time.time()
    img = render_pdf_page(pdf_path, page_index, dpi=dpi)
    pre, pp_meta = preprocess_for_surya(img)
    tiles = tile_image(pre, rows=rows, cols=cols, overlap_px=overlap)
    # Run tiles in a single batch where memory allows; on CPU just sequential.
    tile_images = [crop for _, crop in tiles]
    results = run_surya(tile_images)
    all_records: list[dict] = []
    idx = 0
    for (tile, _crop), result in zip(tiles, results, strict=True):
        recs, idx = surya_lines_to_records(
            result,
            pipeline,
            page_label,
            source_dpi=SOURCE_DPI,
            rendered_dpi=dpi,
            tile_x0=tile.x0,
            tile_y0=tile.y0,
            start_cell_index=idx,
        )
        # attach tile membership for downstream seam analysis
        for r in recs:
            r["_tile"] = f"r{tile.row}c{tile.col}"
        all_records.extend(recs)
    return {
        "pipeline": pipeline,
        "engine": "surya-ocr",
        "engine_version": "0.17.1",
        "dpi": dpi,
        "tile": f"{rows}x{cols}",
        "overlap_px": overlap,
        "preprocess": "deskew+bilateral+adaptive_threshold",
        "preprocess_meta": pp_meta,
        "elapsed_sec": round(time.time() - t0, 2),
        "records": all_records,
        "summary": summarize(all_records),
    }


def pipeline_D_paddle(pdf_path: Path, page_index: int, page_label: str) -> dict:
    t0 = time.time()
    img = render_pdf_page(pdf_path, page_index, dpi=300)
    # PaddleOCR runs on the *raw* render (its own pipeline does binarization).
    arr = np.array(img)
    out = run_paddle(arr)
    records = paddle_to_records(
        out, "D", page_label, source_dpi=SOURCE_DPI, rendered_dpi=300
    )
    return {
        "pipeline": "D",
        "engine": "paddleocr",
        "dpi": 300,
        "tile": "flat",
        "preprocess": "paddle-builtin",
        "elapsed_sec": round(time.time() - t0, 2),
        "records": records,
        "summary": summarize(records),
    }


# ---------------------------------------------------------------------------
# Source-crop renderer + judge-rubric template
# ---------------------------------------------------------------------------
def write_source_crop(pdf_path: Path, page_index: int, out_path: Path) -> dict:
    img = render_pdf_page(pdf_path, page_index, dpi=SOURCE_DPI)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return {"width": img.size[0], "height": img.size[1], "dpi": SOURCE_DPI}


JUDGE_TEMPLATE = """# Judge rubric — {page_label}

**Source PDF:** `{pdf_rel}`
**Page index (0-based):** {page_index}
**Description:** {description}

**Source crop:** [`source-crop.png`](./source-crop.png) (192 DPI)

---

## Per-pipeline scorecard

Scores 0-5 (5 = excellent). Fill in after eyeballing source-crop.png against each pipeline's JSON.

| Metric | A (Surya 192 flat) | B (Surya 384 2x2) | C (Surya 576 3x3) | D (PaddleOCR 300) |
|---|---:|---:|---:|---:|
| Cell recall (did it find the rows/cells that exist?) | | | | |
| Cell precision (any phantom cells / duplicates?) | | | | |
| Character error rate (subjective inverse: 5=clean, 0=garbled) | | | | |
| Numeral correctness | | | | |
| Devanagari diacritic preservation | | | | |
| Table structure preservation (row/column alignment) | | | | |

## Devanagari-numeral handling

| | A | B | C | D |
|---|---|---|---|---|
| Preserved Devanagari digits (०१२...)? | | | | |
| Normalized to Arabic digits (012...)? | | | | |
| Mixed? | | | | |

## Tile-seam artefacts (B, C only)

- B: ...
- C: ...

## Notes / surprises

- ...

## Winner (per-page rank 1-4)

1.
2.
3.
4.
"""


def write_judge_rubric(page_label: str, info: dict, out_path: Path) -> None:
    pdf_rel = Path(info["pdf"]).relative_to(ROOT) if Path(info["pdf"]).is_relative_to(ROOT) else info["pdf"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        JUDGE_TEMPLATE.format(
            page_label=page_label,
            pdf_rel=str(pdf_rel).replace("\\", "/"),
            page_index=info["page_index"],
            description=info["description"],
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_all(
    page_keys: list[str],
    pipelines: list[str],
) -> None:
    for key in page_keys:
        info = PAGES[key]
        page_label = info["name"]
        out_dir = OUT_ROOT / f"page-{key}"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {page_label} ===", flush=True)

        # Always (re)render source-crop and rubric
        crop_path = out_dir / "source-crop.png"
        if not crop_path.exists():
            meta = write_source_crop(info["pdf"], info["page_index"], crop_path)
            print(f"  wrote source-crop.png {meta['width']}x{meta['height']} @ {meta['dpi']} DPI", flush=True)
        rubric_path = out_dir / "judge-rubric.md"
        if not rubric_path.exists():
            write_judge_rubric(page_label, info, rubric_path)
            print("  wrote judge-rubric.md (template)", flush=True)

        for pipeline in pipelines:
            target = out_dir / f"pipeline-{pipeline}.json"
            if target.exists():
                print(f"  pipeline {pipeline}: SKIP (exists)", flush=True)
                continue
            print(f"  pipeline {pipeline}: running ...", flush=True)
            try:
                if pipeline == "A":
                    result = pipeline_A_surya_flat(info["pdf"], info["page_index"], page_label)
                elif pipeline == "B":
                    result = pipeline_surya_tiled(
                        info["pdf"], info["page_index"], page_label,
                        pipeline="B", dpi=384, rows=2, cols=2, overlap=80,
                    )
                elif pipeline == "C":
                    result = pipeline_surya_tiled(
                        info["pdf"], info["page_index"], page_label,
                        pipeline="C", dpi=576, rows=3, cols=3, overlap=100,
                    )
                elif pipeline == "D":
                    result = pipeline_D_paddle(info["pdf"], info["page_index"], page_label)
                else:
                    raise ValueError(f"unknown pipeline: {pipeline}")
                write_json(target, result)
                s = result["summary"]
                print(
                    f"    -> {s['cell_count']} cells, mean_conf={s['mean_confidence']}, "
                    f"deva={s['devanagari_lines']} latin={s['latin_lines']} mixed={s['mixed_lines']} empty={s['empty_lines']} "
                    f"[{result['elapsed_sec']}s]",
                    flush=True,
                )
            except Exception as e:
                err = {
                    "pipeline": pipeline,
                    "page": page_label,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
                write_json(target.with_suffix(".error.json"), err)
                print(f"    ERROR: {e}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="P1,P2,P3,P4,P5")
    ap.add_argument("--pipelines", default="A,B,C,D")
    args = ap.parse_args(argv)
    page_keys = [k.strip() for k in args.pages.split(",") if k.strip()]
    pipelines = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    run_all(page_keys, pipelines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
