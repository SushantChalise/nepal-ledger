"""Tests for _common.preeti — deterministic Preeti/legacy-font transliteration.

ADR-0021 Tier 1a. The correctness anchors are real byte-strings extracted by
pdfplumber from the MoF White Book Preeti/Siddhi editions (FY2062/63–2067/68):
``j}b]lzs`` → वैदेशिक, ``;xfotf`` → सहायता, ``g]kfn`` → नेपाल, ``cg'bfg`` →
अनुदान (grant), ``C)f`` → ऋण (loan). These are the contract: if they decode, the
byte-map + reordering are wired correctly.

The byte-map itself is a verbatim port of the published npttf2utf table; these
tests pin the behaviour the White-Book parser relies on (the shared letter layout
+ the Siddhi divergences for the table bodies + font detection), not the entire
1000-entry table.
"""

from __future__ import annotations

import pytest

from _common.preeti import (
    legacy_font_for,
    looks_legacy_font,
    to_unicode,
    transliterate_page_chars,
)

# ---------------------------------------------------------------------------
# Correctness anchors (task-mandated). The consonant/vowel layout is shared by
# Preeti and Siddhi, so these decode identically under either map.
# ---------------------------------------------------------------------------

_ANCHORS: dict[str, str] = {
    "j}b]lzs": "वैदेशिक",   # the i-matra reorder: ि moves after श
    ";xfotf": "सहायता",
    "g]kfn": "नेपाल",
    "cg'bfg": "अनुदान",     # grant
}


@pytest.mark.parametrize(("src", "want"), list(_ANCHORS.items()))
def test_anchor_words_preeti(src: str, want: str) -> None:
    assert to_unicode(src, "preeti") == want


@pytest.mark.parametrize(("src", "want"), list(_ANCHORS.items()))
def test_anchor_words_siddhi(src: str, want: str) -> None:
    # Siddhi shares Preeti's letter layout → the shared anchors decode the same.
    assert to_unicode(src, "siddhi") == want


def test_loan_word_is_siddhi_specific() -> None:
    """``C)f`` = ऋण ONLY under the Siddhi map (Siddhi ``)`` = half-ण; Preeti ``)``
    is the digit ०, so the Preeti decode is deliberately different). The White
    Book table bodies are Siddhi, so this is the path the parser uses."""
    assert to_unicode("C)f", "siddhi") == "ऋण"
    assert to_unicode("C)f", "preeti") != "ऋण"


# ---------------------------------------------------------------------------
# The pre-base i-matra (ि) reordering rule — the non-trivial transform.
# ---------------------------------------------------------------------------


def test_i_matra_is_reordered_after_consonant() -> None:
    """In the font ``l`` (ि) precedes its consonant (``lzs`` = ि-श-क); Unicode
    needs शिक. The post-rule must move the matra after the cluster."""
    assert to_unicode("lzs", "preeti") == "शिक"
    # And it must NOT leave a leading ि.
    assert not to_unicode("lzs", "preeti").startswith("ि")


# ---------------------------------------------------------------------------
# Numerals.
# ---------------------------------------------------------------------------


def test_preeti_numeral_glyphs_decode_to_devanagari_digits() -> None:
    """On a genuine Preeti run the digit row paints Devanagari numerals: the
    cover prints the year as ``@)^%`` = २०६५ and ``÷`` = the / separator."""
    assert to_unicode("@)^%", "preeti") == "२०६५"
    assert to_unicode("@)^%÷^^", "preeti") == "२०६५/६६"


def test_siddhi_passes_ascii_digits_through() -> None:
    """The Siddhi table bodies paint Arabic digits on the ASCII digit row, so a
    value cell's digits must survive verbatim (value-correctness, ADR-0021)."""
    assert to_unicode("47093225", "siddhi") == "47093225"
    assert to_unicode("1,78,60,33", "siddhi") == "1,78,60,33"


# ---------------------------------------------------------------------------
# Real decoded labels / headers from the in-corpus editions.
# ---------------------------------------------------------------------------


def test_unit_header_decodes_to_thousand_marker() -> None:
    """The legacy unit annotation ``?.xhf<df`` decodes to रु।हजारमा (Rs in
    thousand) — the parser keys ``npr_thousand`` off the हजार marker."""
    decoded = to_unicode("?.xhf<df", "siddhi")
    assert "हजार" in decoded


def test_summary_captions_decode() -> None:
    # मन्त्रालयगत = Ministrywise (sector); दातृ = donor.
    assert "मन्त्रालयगत" in to_unicode("dGqfnout ljefhg ;f<f_z", "siddhi")
    assert "दातृ" in to_unicode("bft[ut ;f<f_z", "siddhi")
    # grant / loan column headers.
    assert to_unicode("j}b]lzs cg'bfg", "siddhi") == "वैदेशिक अनुदान"
    assert to_unicode("j}b]lzs C)f", "siddhi") == "वैदेशिक ऋण"


def test_total_row_marker_decodes() -> None:
    """The grand-total row marker ``s'n`` → कुल (caught by the parser's total
    filter so the printed total is never emitted as a member)."""
    assert to_unicode("s'n", "siddhi") == "कुल"
    assert to_unicode("s'n hDdf", "siddhi") == "कुल जम्मा"


@pytest.mark.parametrize(
    ("src", "want"),
    [
        ("ef<t", "भारत"),         # India — Siddhi < = र
        ("rLg", "चीन"),           # China
        ("Š]gdfs{", "डेनमार्क"),   # Denmark — Siddhi Š = ड
        ("cy{ dGqfno", "अर्थ मन्त्रालय"),  # Ministry of Finance
        (";_:yf", "संस्था"),       # institution — Siddhi _ = anusvara ं
    ],
)
def test_siddhi_donor_and_ministry_labels(src: str, want: str) -> None:
    assert to_unicode(src, "siddhi") == want


# ---------------------------------------------------------------------------
# Font detection.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fontname", "want"),
    [
        ("LEDHHH+Preeti", "preeti"),
        ("BGNOGF+SiddhiNormal", "siddhi"),
        ("Siddhi,Bold", "siddhi"),
        ("ABCDEF+Kantipur", "kantipur"),
        ("Sagarmatha", "sagarmatha"),
        ("PCS NEPALI", "pcs"),
    ],
)
def test_legacy_font_for_detects_subset_prefixed_names(fontname: str, want: str) -> None:
    assert legacy_font_for(fontname) == want
    assert looks_legacy_font(fontname)


@pytest.mark.parametrize(
    "fontname",
    ["TimesNewRomanPS-BoldItalicMT", "ArialMT", "Arial-BoldMT", "Helvetica", None, ""],
)
def test_legacy_font_for_passes_clean_fonts_through(fontname: str | None) -> None:
    assert legacy_font_for(fontname) is None
    assert not looks_legacy_font(fontname)


# ---------------------------------------------------------------------------
# Contract / robustness.
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty() -> None:
    assert to_unicode("", "preeti") == ""
    assert to_unicode("", "siddhi") == ""


def test_unknown_font_falls_back_to_preeti() -> None:
    assert to_unicode("g]kfn", "no-such-font") == to_unicode("g]kfn", "preeti")


def test_idempotent_on_clean_unicode() -> None:
    """Already-Unicode Devanagari that contains none of the mapped Latin bytes is
    returned unchanged (the converter is safe to run on mixed text)."""
    clean = "नेपाल सरकार"
    assert to_unicode(clean, "preeti") == clean


def test_to_unicode_is_deterministic() -> None:
    src = "dGqfnout ljefhg ;f<f_z"
    assert to_unicode(src, "siddhi") == to_unicode(src, "siddhi")


# ---------------------------------------------------------------------------
# Run-aware page transliteration (mixed legacy + Latin).
# ---------------------------------------------------------------------------


def test_transliterate_page_chars_mixes_legacy_and_latin() -> None:
    """A run in a legacy font is transliterated; a Latin run (and ASCII digits a
    Latin face emits) passes through untouched."""
    chars = [
        {"text": "g", "fontname": "AB: +Preeti"},
        {"text": "]", "fontname": "ABC+Preeti"},
        {"text": "k", "fontname": "ABC+Preeti"},
        {"text": "f", "fontname": "ABC+Preeti"},
        {"text": "n", "fontname": "ABC+Preeti"},
        {"text": " ", "fontname": "ArialMT"},
        {"text": "2", "fontname": "ArialMT"},
        {"text": "0", "fontname": "ArialMT"},
    ]
    assert transliterate_page_chars(chars) == "नेपाल 20"


def test_transliterate_page_chars_empty() -> None:
    assert transliterate_page_chars([]) == ""
