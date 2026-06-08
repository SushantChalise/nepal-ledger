"""Deterministic post-processing of raw Surya line text.

Observed Surya 0.17.1 failure modes on the intergovernmental Devanagari
tables (task #50 validation run, page 6 of 207980.pdf) that this module
repairs WITHOUT guessing a value:

1. Spurious markup tags. Surya emits ``<br>``, ``<b>``…``</b>``, ``<math>``
   (findings §13 issues #410/#467). We strip them. ``<br>`` between two
   tokens becomes a space.
2. Arabic-Indic (Persian, U+0660–U+0669) digits leaking in where Devanagari
   (U+0966–U+096F) was meant — e.g. ``٩,८८,٩८`` for ``९,८८,९८``. We fold
   Arabic-Indic -> Devanagari (lossless, same digit values).
3. Multiple numbers merged into one line because Surya's detector drew one
   bbox across adjacent columns — e.g. ``'९२,०० ११,५२,२७'`` or
   ``'७,७४,६६ | १०,०६,५१'``. :func:`split_numeric_tokens` splits a line into
   its component number tokens (on whitespace / pipe separators) so the
   reconstruction step can place each under its own column.

This module is numeral-system aware but does NOT normalize Devanagari→Arabic
here — that (and the OCR-substitution dictionary) is applied downstream by
``_common.devanagari_normalization`` so both numeral systems are preserved.
"""

from __future__ import annotations

import re

# Arabic-Indic (Persian) digits -> Devanagari digits (same values). Surya
# occasionally classifies a Devanagari digit as its Arabic-Indic look-alike.
_ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"
_DEVANAGARI = "०१२३४५६७८९"
_ARABIC_INDIC_TO_DEVANAGARI = str.maketrans(_ARABIC_INDIC, _DEVANAGARI)

# Spurious markup Surya can emit. ``<br>`` -> space, the rest -> removed.
_BR_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_TAG_RE = re.compile(r"</?\s*(?:b|i|u|sub|sup|math|span)\s*>", re.IGNORECASE)

# A "number token": runs of digits (either script) with grouping commas/dots,
# optional leading minus. Nepali tables group as ``1,29,46,06`` (lakh system).
_NUMBER_TOKEN_RE = re.compile(r"-?[\d०-९٠-٩][\d०-९٠-٩.,]*")


def strip_markup(text: str) -> str:
    """Remove spurious HTML-ish tags Surya emits; ``<br>`` becomes a space."""
    if not text:
        return text
    return _TAG_RE.sub("", _BR_RE.sub(" ", text))


def fold_arabic_indic_digits(text: str) -> str:
    """Map Arabic-Indic digits to Devanagari (lossless value-preserving)."""
    return text.translate(_ARABIC_INDIC_TO_DEVANAGARI)


def clean_line(text: str) -> str:
    """Full single-line cleanup: strip markup, fold digits, squeeze spaces."""
    text = strip_markup(text)
    text = fold_arabic_indic_digits(text)
    return re.sub(r"\s+", " ", text).strip()


def split_numeric_tokens(text: str) -> list[str]:
    """Return the distinct number tokens in a (cleaned) line, left-to-right.

    Empty when the line has no digits (a label cell). Each token keeps its
    original grouping punctuation; numeral-script conversion happens later.

    >>> split_numeric_tokens("९२,०० ११,५२,२७")
    ['९२,००', '११,५२,२७']
    >>> split_numeric_tokens("७,७४,६६ | १०,०६,५१")
    ['७,७४,६६', '१०,०६,५१']
    >>> split_numeric_tokens("समानीकरण अनुदान")
    []
    """
    cleaned = clean_line(text)
    return [m.group(0) for m in _NUMBER_TOKEN_RE.finditer(cleaned)]


def is_pure_numeric_line(text: str) -> bool:
    """True iff the cleaned line is one-or-more number tokens and nothing else.

    Used to distinguish a value cell from a label cell during reconstruction.
    """
    cleaned = clean_line(text)
    if not cleaned:
        return False
    residue = _NUMBER_TOKEN_RE.sub("", cleaned)
    # Allow only separators between tokens.
    return residue.strip(" |/\t") == ""
