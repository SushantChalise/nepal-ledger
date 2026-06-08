"""Surya predictor wrapper — the one place that imports the GPU stack.

Surya 0.17.1 validated API (RECOVERY_PROGRAM §Environments, task #50):

    from surya.foundation import FoundationPredictor
    from surya.recognition import RecognitionPredictor
    from surya.detection import DetectionPredictor
    rec = RecognitionPredictor(FoundationPredictor())
    det = DetectionPredictor()
    results = rec([pil_img], det_predictor=det)
    results[0].text_lines[].{text, confidence, bbox, polygon}

Why a wrapper:
    - The predictors are heavy (≈0.7B foundation model). We build them ONCE
      per process (module singleton) and reuse across pages/tiles.
    - Every other harness module (tiling, stitch, reconstruct) can then be
      imported and unit-tested WITHOUT importing torch/surya — they depend
      only on the lightweight :class:`OcrLine` dataclass defined here.
    - We pin the model identity (name + version) so it lands in the tile
      manifest for reproducibility (ADR-0003 / findings §11).

Determinism note (findings §11): Surya sets no global seed and CUDA attention
is not bit-deterministic. We record device + model version per run; a re-run
that diverges is a model-drift event to re-validate, not a silent overwrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

# Pinned in scrapers/pyproject.toml + RECOVERY_PROGRAM. Recorded per tile.
MODEL_NAME: str = "surya-ocr"
MODEL_VERSION: str = "0.17.1"


@dataclass(frozen=True)
class OcrLine:
    """One recognized text line. Lightweight mirror of Surya's ``TextLine``.

    ``bbox`` is axis-aligned ``[x0, y0, x1, y1]`` in the INPUT image's pixel
    space (i.e. tile-local when we feed a tile). Confidence is 0-1; Surya
    coerces NaN to 0.
    """

    text: str
    confidence: float
    bbox: tuple[float, float, float, float]


@dataclass
class _Predictors:
    recognition: object
    detection: object


@lru_cache(maxsize=1)
def _load_predictors() -> _Predictors:
    """Build (once) and cache the Surya recognition + detection predictors.

    Imported lazily inside the function so merely importing this module does
    not pull in torch/surya (keeps the non-GPU harness modules importable in
    CI without the heavy stack).
    """
    from surya.detection import DetectionPredictor
    from surya.foundation import FoundationPredictor
    from surya.recognition import RecognitionPredictor

    foundation = FoundationPredictor()
    recognition = RecognitionPredictor(foundation)
    detection = DetectionPredictor()
    return _Predictors(recognition=recognition, detection=detection)


def warm_up() -> None:
    """Eagerly construct predictors (download/load weights). Optional."""
    _load_predictors()


def ocr_image(image: Image.Image) -> list[OcrLine]:
    """Run detection+recognition on a single image; return recognized lines.

    Uses the detection predictor so Surya finds line bboxes itself (the path
    that behaves best on Devanagari, per findings §2 recommendation #3 — we
    pass ``det_predictor`` rather than relying on a pre-crop).
    """
    preds = _load_predictors()
    # ``rec(images, det_predictor=det)`` -> List[OCRResult]; one per image.
    results = preds.recognition([image], det_predictor=preds.detection)  # type: ignore[operator]
    result = results[0]
    lines: list[OcrLine] = []
    for tl in result.text_lines:
        bbox = tl.bbox
        conf = tl.confidence if tl.confidence is not None else 0.0
        lines.append(
            OcrLine(
                text=tl.text,
                confidence=float(conf),
                bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
            ),
        )
    return lines
