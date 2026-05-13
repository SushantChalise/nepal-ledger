"""
Inspect candidate PDFs to pick representative pages for OCR evaluation.

Renders a small thumbnail of each page and computes:
  - page count
  - rendered dimensions
  - estimated text-density via dark-pixel ratio after Otsu binarize
  - estimated contrast (stddev of grayscale)
  - estimated skew via Hough lines on edge map

Writes JSON to scrapers/ocr_eval/page_picks.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "Financial Data"

# (label, relative_path, scan_pages_first_n) — only scan first N pages for speed
CANDIDATES = [
    ("P1_yellowbook", "mof_documents/yellowbook/1685280975_Yellow Book BIG 2080 Final_6jh3p9r.pdf", 80),
    ("P2_redbook", "mof_documents/redbook/Redbook (Final)_2079_80_uryb8ga.pdf", 80),
    ("P3_intergov", "mof_documents/intergovernmental/208283.pdf", 30),
    ("P4_nrb_bfi", "nrb_monthly_statistics/bfi_niyamabali.pdf", 40),
    # P5 -> worst scan candidates; we probe across older redbook + older intergov scans
    ("P5_old_redbook", "mof_documents/redbook/Budget Details - Red Book 2062 - 2063_20130717120229_cbmey2a.pdf", 40),
    ("P5_old_intergov", "mof_documents/intergovernmental/207475.pdf", 30),
]


def estimate_skew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=200, minLineLength=200, maxLineGap=20)
    if lines is None:
        return 0.0
    angles = []
    for x1, y1, x2, y2 in lines[:, 0]:
        if x2 == x1:
            continue
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # only consider near-horizontal lines (within +/-15 deg)
        if -15 < ang < 15:
            angles.append(ang)
    if not angles:
        return 0.0
    return float(np.median(angles))


def score_page(pil_img) -> dict:
    arr = np.array(pil_img.convert("L"))
    h, w = arr.shape
    _, binar = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dark_ratio = float(binar.mean() / 255.0)
    contrast = float(arr.std())
    mean_lum = float(arr.mean())
    skew = estimate_skew(arr)
    return {
        "width": w,
        "height": h,
        "dark_ratio": round(dark_ratio, 4),
        "contrast": round(contrast, 2),
        "mean_lum": round(mean_lum, 2),
        "skew_deg": round(skew, 2),
    }


def main() -> int:
    out = {}
    for label, rel, scan_n in CANDIDATES:
        path = CORPUS / rel
        if not path.exists():
            out[label] = {"error": f"missing: {path}"}
            print(f"MISS {label}: {path}", file=sys.stderr)
            continue
        pdf = pdfium.PdfDocument(str(path))
        n = len(pdf)
        pages_to_scan = min(scan_n, n)
        page_stats = []
        for i in range(pages_to_scan):
            try:
                page = pdf[i]
                # render at modest DPI (100) just for inspection
                img = page.render(scale=100 / 72).to_pil()
                stats = score_page(img)
                stats["page"] = i
                page_stats.append(stats)
                page.close()
            except Exception as e:  # noqa: BLE001
                page_stats.append({"page": i, "error": str(e)})
        pdf.close()
        out[label] = {
            "path": str(path),
            "total_pages": n,
            "scanned": pages_to_scan,
            "pages": page_stats,
        }
        print(f"OK   {label}: {n} pages, scanned {pages_to_scan}")
    out_path = Path(__file__).parent / "page_picks.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
