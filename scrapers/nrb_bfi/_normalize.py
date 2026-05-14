"""Cell normalisation helpers for NRB BFI XLSX parsing.

Covers:

- Devanagari -> Arabic numeral digit mapping (delegates to
  ``_common.devanagari_normalization.to_arabic_numerals`` — see ADR-0004
  successor / Worker epsilon's deliverable).
- Float coercion that tolerates whitespace, commas, and stray Devanagari.
- Indicator-slug derivation from raw multi-level Excel labels.

NOTE: ADR-0003 forbids AI-assisted parsing at runtime; this module is pure
deterministic text munging.
"""

from __future__ import annotations

import math
import re
from typing import Final

from _common.devanagari_normalization import (
    detect_numeral_script,
    to_arabic_numerals,
)

# Decimal-point variants seen in published NRB tables.
_DECIMAL_VARIANTS: Final[dict[str, str]] = {
    "·": ".",  # middle dot
    "•": ".",  # bullet
}

_NON_LABEL_CHARS: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")


def has_devanagari_digit(text: str) -> bool:
    """Return True if ``text`` contains any Devanagari digit (U+0966..U+096F)."""
    return detect_numeral_script(text) == "devanagari" or any(
        "०" <= ch <= "९" for ch in text
    )


def normalise_digits(text: str) -> str:
    """Map Devanagari digits to Arabic digits + canonicalise decimal points.

    Leaves all non-digit characters untouched so callers can preserve labels.
    """
    if not text:
        return text
    result = to_arabic_numerals(text)
    for variant, replacement in _DECIMAL_VARIANTS.items():
        if variant in result:
            result = result.replace(variant, replacement)
    return result


_SENTINEL_BLANKS: Final[frozenset[str]] = frozenset({"-", "--", "n/a", "N/A"})


def coerce_float(raw: object) -> float | None:
    """Best-effort coerce a cell value to ``float``; return None for blank/NaN.

    Accepts native int/float, strings with thousands commas, leading/trailing
    whitespace, and Devanagari digits. Returns None on any parse failure
    (caller emits a ``ValueUnparseable`` ParserError if needed).
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, int | float):
        value = float(raw)
        return None if math.isnan(value) else value
    return _coerce_text_to_float(str(raw))


def _coerce_text_to_float(raw_text: str) -> float | None:
    """String-only branch of ``coerce_float``."""
    text = raw_text.strip()
    if not text:
        return None
    text = normalise_digits(text).replace(",", "").replace(" ", "")
    if not text or text in _SENTINEL_BLANKS:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def slugify(label: str) -> str:
    """Turn a raw indicator label into a kebab-case slug fragment.

    - Lower-cases.
    - Strips outline numbering (e.g. ``" 1.1.2.3  Upto 3 Months"`` ->
      ``"upto-3-months"``).
    - Collapses any non-``[a-z0-9]`` to single hyphens.
    """
    cleaned = label.strip().lower()
    # Drop leading numbering ("1.1.2.3  Foo Bar" -> "foo bar"; "a. Paid"
    # -> "paid"; "  1   Interest" -> "interest") while leaving inner
    # numerics alone ("3 Months" -> "3-months").
    cleaned = re.sub(r"^\s*([a-z]\.|[\d\.]+)\s+", "", cleaned)
    cleaned = re.sub(r"^[\s\d\.\)\(]+", "", cleaned)
    return _NON_LABEL_CHARS.sub("-", cleaned).strip("-")


def clean_block_title(raw: str) -> str:
    """Normalise a C-sheet block heading.

    Excel cell values are sometimes truncated to ~60 chars; we accept the
    truncated form and key off a substring match.
    """
    return raw.strip().lower()
