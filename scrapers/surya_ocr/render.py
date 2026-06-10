"""PDF page rendering + OpenCV preprocessing for the Surya OCR harness.

Render: pymupdf (``fitz``) rasterizes each page at a fixed zoom matrix. The
validated default is ``fitz.Matrix(3, 3)`` (3x = ~216 DPI on a 72-DPI base),
which the RECOVERY_PROGRAM pinned and which produced high-confidence Surya
output on the intergovernmental province tables (task #50).

Preprocess: Surya does NO deskew/denoise/binarize itself (surya-ocr-findings
§5.3). For born-digital pages with a crisp raster (the intergovernmental
corpus) preprocessing is a no-op passthrough and is left OFF by default. For
genuinely-scanned legacy pages (Yellow/Red books) the caller opts in to a
conservative OpenCV pass: grayscale -> deskew (minimum-area-rect angle) ->
adaptive Gaussian threshold -> light denoise. cv2 is a pinned Surya transitive
dep (opencv 4.x).

Both functions return ``PIL.Image`` in RGB (Surya's required input form).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import fitz  # pymupdf
import numpy as np
from PIL import Image

# Validated render zoom (RECOVERY_PROGRAM §Environments: ``fitz.Matrix(3,3)``).
DEFAULT_ZOOM: float = 3.0
# fitz base userspace is 72 DPI; effective DPI = 72 * zoom.
_BASE_DPI: int = 72

# ``fitz`` lacks a py.typed marker → ``fitz.Document`` is ``Any`` under
# ``disallow_any_unimported``. Alias to an explicit ``Any`` for signatures.
FitzDocument = Any


@dataclass(frozen=True)
class RenderedPage:
    """A rasterized page plus the metadata the tile manifest needs."""

    page_number: int
    image: Image.Image
    dpi: int
    width_px: int
    height_px: int


def effective_dpi(zoom: float = DEFAULT_ZOOM) -> int:
    """Effective DPI for a given zoom on the 72-DPI fitz base."""
    return round(_BASE_DPI * zoom)


def render_page(
    doc: FitzDocument,
    page_number: int,
    zoom: float = DEFAULT_ZOOM,
) -> RenderedPage:
    """Rasterize one page to an RGB PIL image at ``zoom``.

    ``page_number`` is 0-based (matches pymupdf indexing and the
    ``ocr_tile_manifests.page_number`` convention used across the harness).
    """
    page = doc[page_number]
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return RenderedPage(
        page_number=page_number,
        image=img,
        dpi=effective_dpi(zoom),
        width_px=pix.width,
        height_px=pix.height,
    )


def _deskew_angle(gray: np.ndarray[Any, Any]) -> float:
    """Estimate a small skew angle (degrees) from foreground pixel geometry.

    Returns 0.0 when there is too little signal or the estimate is large
    enough to be a false positive (we only correct gentle scanner skew, never
    rotate a page 90deg). Positive angle = rotate counter-clockwise to level.
    """
    # Foreground = dark ink on light paper after inversion.
    inverted = cv2.bitwise_not(gray)
    _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is None or len(coords) < 50:  # noqa: PLR2004 — too little ink to trust
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    # OpenCV reports the angle in (-90, 0]; normalize to a small signed tilt.
    if angle < -45:  # noqa: PLR2004
        angle = 90 + angle
    # Only correct gentle skew; a large value is a misdetection on table rules.
    max_correct = 10.0
    if abs(angle) > max_correct:
        return 0.0
    return -angle


def preprocess_for_ocr(
    image: Image.Image,
    *,
    deskew: bool = True,
    binarize: bool = True,
    denoise: bool = True,
) -> Image.Image:
    """Conservative OpenCV cleanup for scanned pages.

    Off the hot path for born-digital pages — the caller decides via
    ``HarnessConfig.preprocess``. Each step is independently toggleable so a
    page that only needs deskew (not binarization) can opt out. Returns an RGB
    PIL image so the result drops straight back into the Surya input list.

    For a crisp born-digital raster this is close to identity, but adaptive
    thresholding can still help faint Devanagari diacritics (findings §5.3).
    """
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    if deskew:
        angle = _deskew_angle(gray)
        if angle != 0.0:
            h, w = gray.shape
            center = (w // 2, h // 2)
            rot = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(
                gray, rot, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

    if denoise:
        # Edge-preserving; gentle so thin diacritic strokes survive.
        gray = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)

    if binarize:
        # Gaussian adaptive threshold works well on Devanagari scans where
        # diacritic strokes are faint (findings §5.3 recommendation).
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=31,
            C=15,
        )

    return Image.fromarray(gray).convert("RGB")
