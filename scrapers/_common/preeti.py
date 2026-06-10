"""Deterministic Preeti / legacy-8-bit-Nepali-font → Unicode transliteration.

ADR-0021 **Tier 1a** (deterministic font transliteration — *not* OCR, *not* AI).

Legacy Nepali fonts (Preeti, Kantipur, Sagarmatha, PCS Nepali, Siddhi, …) are
8-bit TrueType faces whose glyph slots reuse the ASCII / Latin-1 byte range: a
byte like ``0x3B`` (``;``) is painted as the Devanagari letter स, ``0x6A`` (``j``)
as व, and so on. ``pdfplumber`` therefore extracts a *byte soup* (``j}b]lzs`` for
वैदेशिक) that is **deterministically reversible** by the published font byte-map
plus a fixed set of reordering rules — it is a lookup table, never recognition.

Why this is ADR-0003-clean
--------------------------
ADR-0003 forbids a *generative LLM* "reading" a value out of a document
(hallucination risk). This module is the opposite: a closed, reproducible byte
table. Same input → same output, every time. ADR-0021 classifies it as Tier 1a
(ships first, before any OCR).

Provenance of the map (do NOT hand-invent a byte-map)
-----------------------------------------------------
The byte → Devanagari character maps and the post-substitution reordering rules
are ported **verbatim** from the well-established open-source ``npttf2utf``
project (`casualsnek/npttf2utf`, MIT-licensed; its Preeti rules are in turn
derived from `globalpolicy/UnicodeToPreeti`, MIT). Porting the published table is
exactly what ADR-0021 prescribes ("port the standard one; do NOT invent a map").

The reordering rules (the non-obvious part)
-------------------------------------------
A legacy font stores glyphs in *visual* order; Unicode wants *logical* order. The
two transforms that matter for Nepali:

* **Pre-base vowel sign ि (i-matra).** In the font the ि glyph (byte ``l``) is
  typed/stored **before** the consonant it attaches to (``lzs`` = ि श क → visually
  "िशक"); Unicode needs it **after** the consonant cluster (शिक). The post-rule
  ``ि((.्)*[^्]) → \1ि`` performs that move.
* **Reph र् (``{``)** and the full/half-form vowel compositions (ओ/औ/आ/ऐ, ो/ौ
  from ``ा`` + ``े``/``ै``) are likewise reordered/composed by the post-rules.

Public API
----------
* :func:`to_unicode` — transliterate one byte-string from a named legacy font.
* :func:`looks_legacy_font` / :data:`LEGACY_FONT_HINTS` — detect a legacy font
  from a ``pdfplumber`` ``fontname``.
* :func:`legacy_font_for` — map a ``fontname`` to the map name to use, or ``None``.
* :func:`transliterate_page_chars` — run-aware conversion of a ``pdfplumber``
  ``page.chars`` list: only runs in a legacy font are transliterated; clean
  Unicode / Latin text passes through untouched.

Numerals are intentionally **not** touched here when a font already emits ASCII
digits (e.g. Siddhi) — digit handling for value cells stays with the caller and
``_common.devanagari_normalization``. The Preeti/Kantipur maps *do* map the
font's digit-glyph bytes (``)!@#…``) because those faces paint digits there.
"""

from __future__ import annotations

import re
from typing import Final

# ---------------------------------------------------------------------------
# Byte → Devanagari character maps (ported verbatim from npttf2utf map.json).
# Each value is a Unicode *fragment* (it may already contain a halant ्); the
# reordering happens in the shared POST_RULES below.
# ---------------------------------------------------------------------------

# The canonical Preeti face.
_PREETI_CHAR_MAP: Final[dict[str, str]] = {
    "0": "ण्", "1": "ज्ञ", "2": "द्द", "3": "घ", "4": "द्ध", "5": "छ",
    "6": "ट", "7": "ठ", "8": "ड", "9": "ढ", "~": "ञ्",
    "!": "१", "@": "२", "#": "३", "$": "४", "%": "५", "^": "६", "&": "७",
    "*": "८", "(": "९", ")": "०", "_": ")", "+": "ं", " ": " ", "`": "ञ",
    "-": "(", "=": ".", "Q": "त्त", "W": "ध्", "E": "भ्", "R": "च्", "T": "त्",
    "Y": "थ्", "U": "ग्", "I": "क्ष्", "O": "इ", "P": "ए", "}": "ै", "|": "्र",
    "q": "त्र", "w": "ध", "e": "भ", "r": "च", "t": "त", "y": "थ", "u": "ग",
    "i": "ष्", "o": "य", "p": "उ", "[": "ृ", "]": "े", "\\": "्", "A": "ब्",
    "S": "क्", "D": "म्", "F": "ँ", "G": "न्", "H": "ज्", "J": "व्", "K": "प्",
    "L": "ी", ":": "स्", '"': "ू", "a": "ब", "s": "क", "d": "म", "f": "ा",
    "g": "न", "h": "ज", "j": "व", "k": "प", "l": "ि", ";": "स", "'": "ु",
    "Z": "श्", "X": "ह्", "C": "ऋ", "V": "ख्", "B": "द्य", "N": "ल्", "M": "ः",
    "<": "?", ">": "श्र", "?": "रु", "z": "श", "x": "ह", "c": "अ", "v": "ख",
    "b": "द", "n": "ल", ",": ",", ".": "।", "/": "र",
    "„": "ध्र", "…": "‘", "ˆ": "फ्", "‰": "झ्", "‹": "ङ्घ", "‘": "ॅ", "•": "ड्ड",
    "˜": "ऽ", "›": "द्र", "¡": "ज्ञ्", "¢": "द्घ", "£": "घ्", "¤": "झ्",
    "¥": "्र", "§": "ट्ट", "©": "र", "ª": "ङ", "«": "्र", "°": "ङ्ढ",
    "±": "+", "´": "झ", "¶": "ठ्ठ", "¿": "रू", "Å": "हृ", "Æ": "”", "Ë": "ङ्ग",
    "Ì": "न्न", "Í": "ङ्क", "Î": "ङ्ख", "Ò": "¨", "Ö": "=", "×": "×",
    "Ø": "्य", "Ù": ";", "Ú": "’", "Û": "!", "Ü": "%", "Ý": "ट्ठ", "ß": "द्म",
    "å": "द्व", "æ": "“", "ç": "ॐ", "÷": "/",
}

# Kantipur — same letter layout as Preeti, ASCII digits, a few different specials.
_KANTIPUR_CHAR_MAP: Final[dict[str, str]] = {
    "~": "ञ्", "!": "१", "@": "२", "#": "३", "$": "४", "%": "५", "^": "६",
    "&": "७", "*": "८", "(": "९", ")": "०", "_": ")", "+": "ं", "`": "ञ",
    "1": "ज्ञ", "2": "द्द", "3": "घ", "4": "द्ध", "5": "छ", "6": "ट", "7": "ठ",
    "8": "ड", "9": "ढ", "0": "ण्", "-": "(", "=": ".", "Q": "त्त", "W": "ध्",
    "E": "भ्", "R": "च्", "T": "त्", "Y": "थ्", "U": "ग्", "I": "क्ष्", "O": "इ",
    "P": "ए", "}": "ै", "|": "्र", "q": "त्र", "w": "ध", "e": "भ", "r": "च",
    "t": "त", "y": "थ", "u": "ग", "i": "ष्", "o": "य", "p": "उ", "[": "ृ",
    "]": "े", "\\": "्", "A": "ब्", "S": "क्", "D": "म्", "F": "ा", "G": "न्",
    "H": "ज्", "J": "व्", "K": "प्", "L": "ी", ":": "स्", '"': "ू", "a": "ब",
    "s": "क", "d": "म", "f": "ा", "g": "न", "h": "ज", "j": "व", "k": "प",
    "l": "ि", ";": "स", "'": "ु", "Z": "श्", "X": "हृ", "C": "ऋ", "V": "ख्",
    "B": "द्य", "N": "ल्", "M": "ः", "<": "?", ">": "श्र", "?": "रु", "z": "श",
    "x": "ह", "c": "अ", "v": "ख", "b": "द", "n": "ल", ",": ",", ".": "।",
    "/": "र", "„": "ध्र", "…": "‘", "†": "!", "‰": "झ्", "‹": "ङ्ग",
    "Œ": "त्त्", "‘": "ॅ", "“": "ँ", "•": "ड्ड", "˜": "ऽ", "™": "र", "›": "ऽ",
    "œ": "त्र्", "¡": "ज्ञ्", "¢": "द्घ", "£": "घ्", "¤": "झ्", "¥": "र्‍",
    "§": "ट्ट", "¨": "ङ्ग", "©": "र", "ª": "ङ", "«": "्र", "¬": "…", "­": "(",
    "®": "र", "¯": "¯", "°": "ङ्ढ", "±": "+", "´": "झ", "µ": "र", "¶": "ठ्ठ",
    "º": "फ्", "¿": "रू", "Â": "र", "Æ": "”", "È": "ष", "Ë": "ङ्ग", "Ì": "न्न",
    "Í": "ङ्क", "Î": "फ्", "Ï": "फ्", "Ò": "¨", "Ô": "क्ष", "Ø": "्य",
    "Ú": "’", "ß": "द्म", "å": "द्व", "æ": "“", "ç": "ॐ", "÷": "/", "ø": "य्",
}

# Sagarmatha — Preeti-family letter layout, ASCII digits, its own high-byte set.
_SAGARMATHA_CHAR_MAP: Final[dict[str, str]] = {
    "~": "ञ्", "!": "१", "@": "२", "#": "३", "$": "४", "%": "५", "^": "६",
    "&": "७", "*": "८", "(": "९", ")": "०", "_": ")", "+": "ं", "`": "ञ",
    "1": "ज्ञ", "2": "द्द", "3": "घ", "4": "द्ध", "5": "छ", "6": "ट", "7": "ठ",
    "8": "ड", "9": "ढ", "0": "ण्", "-": "(", "=": ".", "Q": "त्त", "W": "ध्",
    "E": "भ्", "R": "च्", "T": "त्", "Y": "थ्", "U": "ग्", "I": "क्ष्", "O": "इ",
    "P": "ए", "}": "ै", "|": "्र", "q": "त्र", "w": "ध", "e": "भ", "r": "च",
    "t": "त", "y": "थ", "u": "ग", "i": "ष्", "o": "य", "p": "उ", "[": "ृ",
    "]": "े", "\\": "्", "A": "ब्", "S": "क्", "D": "म्", "F": "ँ", "G": "न्",
    "H": "ज्", "J": "व्", "K": "प्", "L": "ी", ":": "स्", '"': "ू", "a": "ब",
    "s": "क", "d": "म", "f": "ा", "g": "न", "h": "ज", "j": "व", "k": "प",
    "l": "ि", ";": "स", "'": "ु", "Z": "श्", "X": "ह्", "C": "ऋ", "V": "ख्",
    "B": "द्य", "N": "ल्", "M": "ः", "<": "?", ">": "श्र", "?": "रु", "z": "श",
    "x": "ह", "c": "अ", "v": "ख", "b": "द", "n": "ल", ",": ",", ".": "।",
    "/": "र", "‚": ")", "ƒ": "द्र", "„": "्", "†": ";", "‡": "े", "ˆ": "ृ",
    "‰": "झ्", "Š": "र्", "‹": "ै", "Œ": "त्त्", "“": "ँ", "œ": "त्र्",
    "¡": "ज्ञ्", "¢": "द्घ", "£": "घ्", "¤": "!", "¥": "र्‍", "§": "ट्ट",
    "ª": "ङ", "«": "्र", "¬": "ु", "­": "(", "®": "र", "°": "ङ्क", "±": "+",
    "´": "झ", "µ": "झ", "¶": "ठ्ठ", "·": "ङ्ग", "¸": "ड्ड", "¿": "रू",
    "Å": "फ", "Æ": "”", "Ç": "फ्", "È": "ष", "É": "स", "Ò": "ू", "Ô": "क्ष",
    "Ø": "्य", "Ù": "ह", "Ü": "%", "Þ": "ह्", "ß": "द्म", "å": "द्व", "æ": "“",
    "ç": "ॐ", "è": "द्भ", "÷": "/", "ø": "य्",
}

# PCS Nepali — Preeti-family letters, ASCII digits, different ण/ऋ/reph slots.
_PCS_NEPALI_CHAR_MAP: Final[dict[str, str]] = {
    "~": "ङ", "!": "ज्ञ", "@": "द्द", "#": "घ", "$": "द्ध", "%": "छ", "^": "ट",
    "&": "ठ", "*": "ड", "(": "ढ", ")": "ण्", "_": ")", "+": "ं", "`": "ञ्",
    "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७",
    "8": "८", "9": "९", "0": "०", "-": "(", "=": ".", "Q": "त्त", "W": "ध्",
    "E": "भ्", "R": "च्", "T": "त्", "Y": "थ्", "U": "ग्", "I": "क्ष्", "O": "इ",
    "P": "ए", "}": "ै", "|": "्र", "q": "त्र", "w": "ध", "e": "भ", "r": "च",
    "t": "त", "y": "थ", "u": "ग", "i": "ष्", "o": "य", "p": "उ", "[": "ृ",
    "]": "े", "\\": "्", "A": "ब्", "S": "क्", "D": "म्", "F": "ा", "G": "न्",
    "H": "ज्", "J": "व्", "K": "प्", "L": "ी", ":": "स्", '"': "ू", "a": "ब",
    "s": "क", "d": "म", "f": "ा", "g": "न", "h": "ज", "j": "व", "k": "प",
    "l": "ि", ";": "स", "'": "ु", "Z": "श्", "X": "ह्", "C": "र्‍", "V": "ख्",
    "B": "द्य", "N": "ल्", "M": "ः", "<": "्र", ">": "श्र", "?": "रू", "z": "श",
    "x": "ह", "c": "अ", "v": "ख", "b": "द", "n": "ल", ",": ",", ".": "।",
    "/": "र", "¡": "ज्ञ्", "¢": "द्घ", "£": "घ्", "¤": "ँ", "¥": "ऋ",
    "§": "ट्ट", "©": "?", "ª": "ञ", "®": "+", "°": "ङ्क", "´": "झ", "·": "ट्ठ",
    "¿": "रु", "Æ": "”", "Ò": "ू", "Ô": "क्ष", "Ø": "्य", "Ù": "ह", "ß": "द्म",
    "å": "द्व", "æ": "“", "ç": "ॐ", "é": "ङ्ग", "í": "ष", "ñ": "ङ", "÷": "/",
    "ø": "य्", "ú": "ू",
}

# Siddhi (SiddhiNormal) — the font the White-Book *table bodies* are typeset in.
# Empirically (verified against the in-corpus FY2065/66 summary tables) Siddhi
# shares Preeti's CONSONANT / VOWEL letter layout but diverges in three slots:
#   * digits 0x30..0x39 are real ASCII digits (the face paints Arabic numerals
#     there), so they pass through unchanged — NOT Preeti's ण्/ज्ञ/घ/… glyphs;
#   * ``)`` (0x29) is ण (not ० — Siddhi puts the digit glyphs on the ASCII row);
#   * ``<`` (0x3C) is द (a Siddhi long-form द variant), where Preeti uses it for
#     the ``?`` placeholder.
# Built as Preeti + these overrides so the (large) shared letter table is not
# duplicated. Each override is anchored by a decoded word in the unit tests.
_SIDDHI_OVERRIDES: Final[dict[str, str]] = {
    # Siddhi shifts the retroflT / digit glyphs OFF the ASCII digit row (it paints
    # real Arabic numerals 0-9 there) onto punctuation / high-byte slots. Each
    # override below is anchored by a decoded word in test_preeti.py.
    # --- ASCII digit row: real Arabic numerals, pass through verbatim. ---
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
    # --- relocated letters ---
    ")": "ण्",  # 0x29 — half-ण (as Preeti's 0); )f→ण, e.g. C)f = ऋण (loan)
    "(": "(",   # 0x28 — plain paren in Siddhi (Preeti uses it for ९)
    "<": "र",   # 0x3C — र; e.g. ;<sf< = सरकार, ef<t = भारत, lgb< = निदर
    "_": "ं",   # 0x5F — anusvara; e.g. ;_:yf = संस्था, ;f<f_z = सारांश
    "^": "ट",   # 0x5E — ट; e.g. ah]^ = बजेट, <fi^ = राष्ट, x]lj^ = हेविट
    "&": "ठ",   # 0x26 — ठ; e.g. ;_u&g = संगठन
    "Š": "ड",  # 0x0160 (Š) — ड; e.g. Š]gdfs{ = डेनमार्क, फण्ड, IDA
    # --- parenthetical brackets (paired wrappers in donor labels) ---
    "œ": "(",  # 0x0153 (œ) — opening bracket; e.g. hfkfg œs]=cf<= = जापान (के.आर.
    "": ")",  # 0x009D — closing bracket, pairs with œ
}
_SIDDHI_CHAR_MAP: Final[dict[str, str]] = {**_PREETI_CHAR_MAP, **_SIDDHI_OVERRIDES}


# Registry of supported maps, keyed by a normalized map name.
_CHAR_MAPS: Final[dict[str, dict[str, str]]] = {
    "preeti": _PREETI_CHAR_MAP,
    "kantipur": _KANTIPUR_CHAR_MAP,
    "sagarmatha": _SAGARMATHA_CHAR_MAP,
    "pcs": _PCS_NEPALI_CHAR_MAP,
    "siddhi": _SIDDHI_CHAR_MAP,
}

# ---------------------------------------------------------------------------
# Reordering / composition rules (ported verbatim from npttf2utf post-rules;
# they are identical across all the faces above). Applied in order, after the
# character-map substitution. ``m`` is the transient placeholder npttf2utf uses
# for the half/pre-base फ-family forms; it is fully consumed by these rules.
# ---------------------------------------------------------------------------
_POST_RULES: Final[tuple[tuple[str, str], ...]] = (
    ("्ा", ""),
    (r"(त्र|त्त)([^उभप]+?)m", r"\1m\2"),
    ("त्रm", "क्र"),
    ("त्तm", "क्त"),
    (r"([^उभप]+?)m", r"m\1"),
    ("उm", "ऊ"),
    ("भm", "झ"),
    ("पm", "फ"),
    ("इ{", "ई"),
    # The pre-base i-matra reorder: move ि AFTER its consonant cluster.
    (r"ि((.्)*[^्])", r"\1ि"),
    (r"(.[ािीुूृेैोौंःँ]*?){", r"{\1"),
    (r"((.्)*){", r"{\1"),
    ("{", "र्"),  # reph
    (r"([ािीुूृेैोौंःँ]+?)(्(.्)*[^्])", r"\2\1"),
    (r"्([ािीुूृेैोौंःँ]+?)((.्)*[^्])", r"्\2\1"),
    (r"([ंँ])([ािीुूृेैोौः]*)", r"\2\1"),
    ("ँँ", "ँ"),
    ("ंं", "ं"),
    ("ेे", "े"),
    ("ैै", "ै"),
    ("ुु", "ु"),
    ("ूू", "ू"),
    ("^ः", ":"),
    ("टृ", "ट्ट"),
    ("ेा", "ाे"),
    ("ैा", "ाै"),
    ("अाे", "ओ"),
    ("अाै", "औ"),
    ("अा", "आ"),
    ("एे", "ऐ"),
    ("ाे", "ो"),
    ("ाै", "ौ"),
)

_COMPILED_POST_RULES: Final[tuple[tuple[re.Pattern[str], str], ...]] = tuple(
    (re.compile(pattern), repl) for pattern, repl in _POST_RULES
)


# ---------------------------------------------------------------------------
# Font detection.
# ---------------------------------------------------------------------------

# Substrings (lower-cased) that flag a legacy 8-bit Nepali font in a pdfplumber
# ``fontname`` (which is often subset-prefixed, e.g. ``LEDHHH+Preeti``,
# ``BGNOGF+SiddhiNormal``). Mapped to the char-map key to use.
LEGACY_FONT_HINTS: Final[dict[str, str]] = {
    "preeti": "preeti",
    "kantipur": "kantipur",
    "sagarmatha": "sagarmatha",
    "pcs": "pcs",
    "siddhi": "siddhi",
}


def legacy_font_for(fontname: str | None) -> str | None:
    """Return the char-map name for a ``pdfplumber`` fontname, or ``None``.

    Matching is case-insensitive and substring-based to tolerate the subset
    prefix pdfplumber prepends (``ABCDEF+Preeti`` → ``preeti``). Returns ``None``
    for clean-Unicode / Latin faces (TimesNewRoman, Arial, …) so the caller knows
    to pass that run through untouched.
    """
    if not fontname:
        return None
    low = fontname.lower()
    for hint, map_name in LEGACY_FONT_HINTS.items():
        if hint in low:
            return map_name
    return None


def looks_legacy_font(fontname: str | None) -> bool:
    """True if ``fontname`` names a supported legacy 8-bit Nepali font."""
    return legacy_font_for(fontname) is not None


# ---------------------------------------------------------------------------
# Core transliteration.
# ---------------------------------------------------------------------------


def _apply_char_map(text: str, char_map: dict[str, str]) -> str:
    """Substitute each byte via the font char-map; unmapped chars pass through."""
    return "".join(char_map.get(ch, ch) for ch in text)


def _apply_post_rules(text: str) -> str:
    """Apply the ordered reordering / composition regexes (npttf2utf parity)."""
    out = text
    for pattern, repl in _COMPILED_POST_RULES:
        out = pattern.sub(repl, out)
    return out


def to_unicode(text: str, font: str = "preeti") -> str:
    """Transliterate one legacy-font byte-string to Unicode Devanagari.

    ``font`` is a map name (``"preeti"`` | ``"kantipur"`` | ``"sagarmatha"`` |
    ``"pcs"`` | ``"siddhi"``) or any ``pdfplumber`` fontname (the subset prefix is
    tolerated — ``"BGNOGF+SiddhiNormal"`` resolves to ``siddhi``). An unknown font
    falls back to the Preeti map (the de-facto standard layout).

    Pure function: deterministic, no I/O, idempotent on already-Unicode input
    that contains none of the mapped Latin bytes. Empty input returns ``""``.
    """
    if not text:
        return text
    map_name = font if font in _CHAR_MAPS else (legacy_font_for(font) or "preeti")
    char_map = _CHAR_MAPS[map_name]
    return _apply_post_rules(_apply_char_map(text, char_map))


def transliterate_page_chars(chars: list[dict[str, object]]) -> str:
    """Transliterate a ``pdfplumber`` ``page.chars`` list, run-aware.

    Walks the chars in order, grouping maximal runs by font *class* (the legacy
    map name, or ``None`` for clean-Unicode/Latin). Legacy runs are converted with
    their font's map; non-legacy runs (and the per-char ``text``, e.g. spaces and
    Arabic digits emitted by a Latin face) are emitted verbatim. This lets a mixed
    page — Latin headings + Preeti body, or Siddhi labels + ASCII digits — decode
    correctly without transliterating the parts that are already Unicode.

    Note: this reconstructs text in ``page.chars`` order, which is the order
    pdfplumber lays glyphs out; it is intended for *cell / line* level strings
    (where reading order is reliable), not whole-page multi-column reflow.
    """
    out: list[str] = []
    run_chars: list[str] = []
    run_map: str | None = None

    def flush() -> None:
        if not run_chars:
            return
        segment = "".join(run_chars)
        out.append(to_unicode(segment, run_map) if run_map else segment)
        run_chars.clear()

    for ch in chars:
        text = str(ch.get("text", ""))
        font = ch.get("fontname")
        this_map = legacy_font_for(font if isinstance(font, str) else None)
        if this_map != run_map:
            flush()
            run_map = this_map
        run_chars.append(text)
    flush()
    return "".join(out)
