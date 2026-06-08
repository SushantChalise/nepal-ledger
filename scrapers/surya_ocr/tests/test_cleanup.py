"""Tests for surya_ocr.cleanup — markup strip, digit folding, token split.

Cases are drawn from REAL Surya 0.17.1 output on page 6 of 207980.pdf (the
intergovernmental province table, task #50 validation run). Each merged /
mangled string below was actually emitted by Surya.
"""

from __future__ import annotations

from surya_ocr.cleanup import (
    clean_line,
    fold_arabic_indic_digits,
    is_pure_numeric_line,
    split_numeric_tokens,
    strip_markup,
)


def test_strip_br_becomes_space() -> None:
    assert strip_markup("सुत्रमा<br>आधारित") == "सुत्रमा आधारित"


def test_strip_bold_tags() -> None:
    assert strip_markup("<b>५</b>ξ,००").replace("ξ", "") == "५,००"


def test_strip_math_tag() -> None:
    assert strip_markup("<math>x</math>") == "x"


def test_fold_arabic_indic_to_devanagari() -> None:
    # Surya emitted ٩,८८,٩८ (Arabic-Indic ٩) for ९,८८,९८.
    assert fold_arabic_indic_digits("٩,८८,٩८") == "९,८८,९८"


def test_fold_preserves_devanagari() -> None:
    assert fold_arabic_indic_digits("२,८१,८३") == "२,८१,८३"


def test_split_two_merged_numbers_space() -> None:
    # Real merge: '७,७४,६६ १०,०६,५१'
    assert split_numeric_tokens("७,७४,६६ १०,०६,५१") == ["७,७४,६६", "१०,०६,५१"]


def test_split_three_merged_numbers_pipe() -> None:
    # Real merge with pipes: '९२,०० | ११,५२,२७ |'
    assert split_numeric_tokens("९२,०० | ११,५२,२७ |") == ["९२,००", "११,५२,२७"]


def test_split_total_row_merge() -> None:
    # Real total-row merge: '२,३०,३८ | ६१,४३,२१ | १४,७२,३० |'
    assert split_numeric_tokens("२,३०,३८ | ६१,४३,२१ | १४,७२,३० |") == [
        "२,३०,३८",
        "६१,४३,२१",
        "१४,७२,३०",
    ]


def test_split_arabic_indic_merge_folds_first() -> None:
    # '9,0४,00 99,9४,२२' → fold then split (mixed Arabic/Devanagari).
    out = split_numeric_tokens("9,0४,00 99,9४,२२")
    assert len(out) == 2


def test_label_line_has_no_numeric_tokens() -> None:
    assert split_numeric_tokens("समानीकरण अनुदान") == []


def test_is_pure_numeric_true_for_value() -> None:
    assert is_pure_numeric_line("१९,०९,९१") is True


def test_is_pure_numeric_true_for_merged_values() -> None:
    assert is_pure_numeric_line("७,७४,६६ | १०,०६,५१") is True


def test_is_pure_numeric_false_for_label() -> None:
    assert is_pure_numeric_line("७०१०००११ प्रदेश नं. १") is False


def test_is_pure_numeric_false_for_empty() -> None:
    assert is_pure_numeric_line("") is False


def test_clean_line_squeezes_and_folds() -> None:
    assert clean_line("  ९२,००   <br> ११,५२,२७  ") == "९२,०० ११,५२,२७"
