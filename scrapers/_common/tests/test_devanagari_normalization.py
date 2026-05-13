"""Tests for _common.devanagari_normalization.

Covers the four public API functions and round-trip identities for the
numeral helpers.
"""

from __future__ import annotations

import pytest

from _common.devanagari_normalization import (
    OCR_SUBSTITUTIONS,
    detect_numeral_script,
    is_devanagari_dominant,
    normalize_both_numeral_systems,
    normalize_devanagari_text,
    to_arabic_numerals,
    to_devanagari_numerals,
)

# ---------------------------------------------------------------------------
# normalize_devanagari_text
# ---------------------------------------------------------------------------


def test_normalize_empty_returns_empty() -> None:
    assert normalize_devanagari_text("") == ""


def test_normalize_unaffected_string_returns_input() -> None:
    # A clean Nepali municipality name has no known typos.
    assert normalize_devanagari_text("काठमाडौँ") == "काठमाडौँ"


@pytest.mark.parametrize(
    ("wrong", "right"),
    list(OCR_SUBSTITUTIONS.items()),
)
def test_each_substitution_applies(wrong: str, right: str) -> None:
    """Every entry in OCR_SUBSTITUTIONS rewrites its input to its target."""
    assert normalize_devanagari_text(wrong) == right


def test_substitution_inside_longer_string() -> None:
    # The typo can appear embedded; substitution should still fire.
    assert normalize_devanagari_text("नगरपाललका") == "नगरपालिका"


# ---------------------------------------------------------------------------
# is_devanagari_dominant
# ---------------------------------------------------------------------------


def test_dominant_pure_nepali() -> None:
    assert is_devanagari_dominant("काठमाडौँ महानगरपालिका") is True


def test_dominant_pure_english() -> None:
    assert is_devanagari_dominant("Kathmandu Metropolitan City") is False


def test_dominant_mixed_light_devanagari() -> None:
    # Mostly English with one Devanagari word -> not dominant.
    assert is_devanagari_dominant("Kathmandu (काठमाडौँ) area") is False


def test_dominant_mixed_heavy_devanagari() -> None:
    # Mostly Devanagari with parenthetical English -> dominant.
    assert is_devanagari_dominant("काठमाडौँ महानगरपालिका (KMC)") is True


def test_dominant_empty_string() -> None:
    assert is_devanagari_dominant("") is False


def test_dominant_whitespace_only() -> None:
    assert is_devanagari_dominant("    ") is False


# ---------------------------------------------------------------------------
# detect_numeral_script
# ---------------------------------------------------------------------------


def test_detect_devanagari_only() -> None:
    assert detect_numeral_script("वडा १२") == "devanagari"


def test_detect_arabic_only() -> None:
    assert detect_numeral_script("Ward 12") == "arabic"


def test_detect_mixed() -> None:
    assert detect_numeral_script("Ward १2") == "mixed"


def test_detect_no_numerals() -> None:
    assert detect_numeral_script("काठमाडौँ") == "none"


def test_detect_empty() -> None:
    assert detect_numeral_script("") == "none"


# ---------------------------------------------------------------------------
# to_arabic_numerals / to_devanagari_numerals — round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dev", "arabic"),
    [
        ("०", "0"),
        ("०१२३४५६७८९", "0123456789"),
        ("वडा १२३", "वडा 123"),
        ("२०८२", "2082"),
    ],
)
def test_devanagari_to_arabic(dev: str, arabic: str) -> None:
    assert to_arabic_numerals(dev) == arabic


@pytest.mark.parametrize(
    ("dev", "arabic"),
    [
        ("०", "0"),
        ("०१२३४५६७८९", "0123456789"),
        ("वडा १२३", "वडा 123"),
        ("२०८२", "2082"),
    ],
)
def test_round_trip_arabic_devanagari(dev: str, arabic: str) -> None:
    assert to_devanagari_numerals(to_arabic_numerals(dev)) == dev
    assert to_arabic_numerals(to_devanagari_numerals(arabic)) == arabic


def test_to_arabic_preserves_non_digits() -> None:
    # Letters, punctuation, whitespace untouched.
    assert to_arabic_numerals("Ward १२, २०८२!") == "Ward 12, 2082!"


# ---------------------------------------------------------------------------
# normalize_both_numeral_systems
# ---------------------------------------------------------------------------


def test_normalize_both_no_digits() -> None:
    text, arabic, devanagari = normalize_both_numeral_systems("काठमाडौँ")
    assert text == "काठमाडौँ"
    assert arabic is None
    assert devanagari is None


def test_normalize_both_devanagari_digits() -> None:
    text, arabic, devanagari = normalize_both_numeral_systems("वडा १२")
    assert text == "वडा"
    assert arabic == "12"
    assert devanagari == "१२"


def test_normalize_both_arabic_digits() -> None:
    text, arabic, devanagari = normalize_both_numeral_systems("Ward 7")
    assert text == "Ward"
    assert arabic == "7"
    assert devanagari == "७"


def test_normalize_both_applies_ocr_substitution() -> None:
    text, arabic, devanagari = normalize_both_numeral_systems("नगरपाललका १")
    # OCR fix पाललका -> पालिका applied before the digit is stripped.
    assert text == "नगरपालिका"
    assert arabic == "1"
    assert devanagari == "१"
