"""Devanagari OCR normalization library.

Ported from ``Financial Data/mof_documents/Cleaned/manual_match_reasoning.py``
(previous-iteration cleanup of MoF Fiscal Transfer OCR output) into a reusable
shape so every future Nepal Ledger OCR parser can apply the same fixes.

Doctrine
--------
The substitution dict (``OCR_SUBSTITUTIONS``) is a **closed registry of
observed OCR errors**, not a speculative list. Each entry was discovered by
diffing the OCR result against the source PDF in the MoF fiscal-transfer
cleanup. NEW entries are added ONLY when:

1. A real OCR mistake is observed in raw parser output, AND
2. The correct Devanagari spelling is verified against the source PDF (or
   another authoritative source — e.g. the canonical 753-row local-level
   table), AND
3. The new entry is added in a PR that cites both the source document and
   the observed misread.

Do NOT add entries from intuition or from generic Devanagari spelling rules.
A wrong substitution silently corrupts downstream entity resolution; an
absent substitution merely surfaces as a low-confidence fuzzy match.

The numeral helpers are lossless and independent of the substitution table.
"""

from __future__ import annotations

from typing import Literal

# ---------------------------------------------------------------------------
# Observed-OCR-error substitutions (ported byte-for-byte from
# manual_match_reasoning.py > normalize_nepali.variations).
# Order matters: ``replace`` is applied sequentially, so longer/more specific
# typos go first.
# ---------------------------------------------------------------------------
OCR_SUBSTITUTIONS: dict[str, str] = {
    "पाललका": "पालिका",
    "पाललिका": "पालिका",
    "गाउँपाललका": "गाउँपालिका",
    "नगरपाललका": "नगरपालिका",
    "ूयोदय": "सूर्योदय",
    "री ": "",  # strip stray leading "री " token observed in MoF OCR
    "अिु ान": "अनुसन्",
    "ल द": "सि",
    "ल री": "सिरी",
    "लम": "मि",
    "फा": "फा",  # noqa: PIE810  -- preserved to match upstream dict byte-for-byte
    "रािगढ": "राजगढ",
    "ुरुङ्गा": "सुरुङ्गा",
    "दुहवी": "दुहबी",
    "न्द्द": "नन्द",
    "चैन": "चैनपुर",
    "अथराई": "आठराई",
    "वब": "बि",
    "वफ": "फि",
    "वह": "हि",
    "कु": "कु",  # noqa: PIE810  -- preserved to match upstream dict byte-for-byte
    "तुव": "तुम्",
    "फाले": "फाले",  # noqa: PIE810  -- preserved to match upstream dict byte-for-byte
    "फाल्गु": "फाल्गुनन्",
    "बबअथी": "बिबाथी",
    "याङवरक": "याङ्वरक",
    "मेरर": "मेरि",
    "कचन": "कञ्चन",
    "न्द्का": "सन्द",
    "पाथी": "पाथि",
    "रोरा": "रोराङ",
}

# ---------------------------------------------------------------------------
# Numeral tables
# ---------------------------------------------------------------------------
_DEVANAGARI_DIGITS = "०१२३४५६७८९"
_ARABIC_DIGITS = "0123456789"

_DEV_TO_ARABIC = str.maketrans(_DEVANAGARI_DIGITS, _ARABIC_DIGITS)
_ARABIC_TO_DEV = str.maketrans(_ARABIC_DIGITS, _DEVANAGARI_DIGITS)

# Devanagari block U+0900..U+097F (excluding the digits, which we treat as a
# numeral system rather than script content).
_DEVANAGARI_LETTER_MIN = 0x0900
_DEVANAGARI_LETTER_MAX = 0x097F
_DEVANAGARI_DOMINANCE_THRESHOLD = 0.5

NumeralScript = Literal["devanagari", "arabic", "mixed", "none"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def normalize_devanagari_text(s: str) -> str:
    """Apply known OCR-error substitutions for Devanagari Nepali.

    Pure string transform. Substitutions come from ``OCR_SUBSTITUTIONS``;
    see the module docstring for the doctrine governing additions.

    Empty/whitespace input is returned unchanged.
    """
    if not s:
        return s
    result = s
    for wrong, right in OCR_SUBSTITUTIONS.items():
        if wrong in result:
            result = result.replace(wrong, right)
    return result


def is_devanagari_dominant(s: str) -> bool:
    """Return True iff more than 50% of non-whitespace chars are Devanagari
    letters (digits excluded — see ``detect_numeral_script``).
    """
    if not s:
        return False
    non_ws = [c for c in s if not c.isspace()]
    if not non_ws:
        return False
    devanagari_count = sum(
        1
        for c in non_ws
        if _DEVANAGARI_LETTER_MIN <= ord(c) <= _DEVANAGARI_LETTER_MAX
        and c not in _DEVANAGARI_DIGITS
    )
    return (devanagari_count / len(non_ws)) > _DEVANAGARI_DOMINANCE_THRESHOLD


def detect_numeral_script(s: str) -> NumeralScript:
    """Return which numeral system this string uses.

    - ``"devanagari"`` — contains only Devanagari digits (no Arabic digits)
    - ``"arabic"``     — contains only Arabic digits (no Devanagari digits)
    - ``"mixed"``      — contains both
    - ``"none"``       — contains no digits at all
    """
    has_dev = any(c in _DEVANAGARI_DIGITS for c in s)
    has_arabic = any(c in _ARABIC_DIGITS for c in s)
    if has_dev and has_arabic:
        return "mixed"
    if has_dev:
        return "devanagari"
    if has_arabic:
        return "arabic"
    return "none"


def to_arabic_numerals(s: str) -> str:
    """Replace ०१२३४५६७८९ with 0123456789 losslessly. All other chars preserved."""
    return s.translate(_DEV_TO_ARABIC)


def to_devanagari_numerals(s: str) -> str:
    """Inverse of :func:`to_arabic_numerals`. All other chars preserved."""
    return s.translate(_ARABIC_TO_DEV)


def normalize_both_numeral_systems(
    s: str,
) -> tuple[str, str | None, str | None]:
    """Split a string into ``(normalized_text, arabic_numerals, devanagari_numerals)``.

    The first element is the input with OCR substitutions applied AND any
    digit run stripped (so callers can match the non-numeric remainder
    against name tables). The second and third elements are the numeric
    portion expressed in each script, or ``None`` if the input contained no
    digits.

    Examples
    --------
    >>> normalize_both_numeral_systems("वडा १२")
    ('वडा', '12', '१२')
    >>> normalize_both_numeral_systems("Ward 7")
    ('Ward', '7', '७')
    >>> normalize_both_numeral_systems("no digits here")
    ('no digits here', None, None)
    """
    normalized_full = normalize_devanagari_text(s)
    script = detect_numeral_script(normalized_full)

    if script == "none":
        return normalized_full.strip(), None, None

    # Extract digits, preserving order. We keep separate runs joined by no
    # delimiter — typical OCR cases are single contiguous numerals.
    arabic_digits = "".join(
        c for c in to_arabic_numerals(normalized_full) if c in _ARABIC_DIGITS
    )
    if not arabic_digits:
        # Defensive: detect said there were digits but extraction was empty.
        return normalized_full.strip(), None, None

    devanagari_digits = arabic_digits.translate(_ARABIC_TO_DEV)

    # Strip all digit chars (both scripts) from the text portion.
    stripped = "".join(
        c
        for c in normalized_full
        if c not in _DEVANAGARI_DIGITS and c not in _ARABIC_DIGITS
    ).strip()

    return stripped, arabic_digits, devanagari_digits
