"""Tests for the intergovernmental parser's deterministic core.

The text-layer extraction + reconciliation + code crosswalk are pure (no GPU).
A synthetic single-page PDF built with fitz exercises the end-to-end text-layer
path; helper-level tests pin the crosswalk + column model. The Surya
cross-validation channel (GPU) is exercised by the live ingest run, not here.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from surya_ocr.parsers import intergovernmental as ig

# ── Crosswalk + helpers ─────────────────────────────────────────────────────

def test_crosswalk_strips_trailing_three() -> None:
    # 9-digit editions (FY2078/79, 2079/80): strip the trailing '3'.
    assert ig._crosswalk_code("801011013") == "80101101"
    assert ig._crosswalk_code("801013093") == "80101309"


def test_crosswalk_8_digit_is_identity() -> None:
    # 8-digit editions (FY2080/81, 2081/82, 2082/83): already the federal code.
    assert ig._crosswalk_code("80101101") == "80101101"
    assert ig._crosswalk_code("80101309") == "80101309"


def test_crosswalk_rejects_9_digit_wrong_trailing() -> None:
    # 9 digits not ending in '3' fits neither pattern.
    assert ig._crosswalk_code("801011011") is None


def test_crosswalk_rejects_wrong_prefix() -> None:
    assert ig._crosswalk_code("701000113") is None
    assert ig._crosswalk_code("70100011") is None  # 8-digit, wrong prefix


def test_crosswalk_rejects_bad_length() -> None:
    assert ig._crosswalk_code("8010110") is None  # 7 digits
    assert ig._crosswalk_code("8010110133") is None  # 10 digits


def test_num_parses_nepali_grouping() -> None:
    assert ig._num("1,29,46,06") == 1294606.0
    assert ig._num("33,00") == 3300.0


def test_is_value_token_accepts_grouped() -> None:
    assert ig._is_value_token("1,29,46,06") is True
    assert ig._is_value_token("63") is True


def test_is_value_token_rejects_nine_digit_code() -> None:
    assert ig._is_value_token("801011013") is False


def test_atomic_columns_are_eight() -> None:
    assert len(ig._ATOMIC_COLUMNS) == 8
    assert set(ig._COLUMN_TO_GRANT.values()) == {
        "equalization_minimum",
        "equalization_formula",
        "equalization_performance",
        "conditional_current",
        "conditional_capital",
        "special_current",
        "special_capital",
        "complementary_capital",
    }


def test_row_reconciles_true_when_atomic_sums_to_grand() -> None:
    # 8 atomic components summing to the grand-total column (idx 13).
    cv = {
        0: "3,25", 1: "13,41", 2: "63", 3: "17,29",   # eq (3 = subtotal)
        4: "26,07", 5: "2,82", 6: "28,89",            # cond
        7: "2,00", 8: "1,00", 9: "3,00",              # spec
        10: "1,70", 11: "45,36", 12: "5,52", 13: "50,88",
    }
    assert ig._row_reconciles(cv) is True


def test_row_reconciles_false_on_mismatch() -> None:
    cv = {0: "3,25", 1: "13,41", 2: "63", 4: "26,07", 5: "2,82",
          7: "2,00", 8: "1,00", 10: "1,70", 13: "99,99"}
    assert ig._row_reconciles(cv) is False


def test_row_reconciles_false_when_incomplete() -> None:
    cv = {0: "3,25", 13: "50,88"}  # missing most atomic columns
    assert ig._row_reconciles(cv) is False


def test_scanned_fy_returns_failure() -> None:
    # Stem maps to a scanned FY → failure without touching the file.
    res = ig.parse("nonexistent/207475.pdf", "x")
    assert res["status"] == "failure"
    assert res["errors"][0]["error_class"] == "PageLayoutChanged"


def test_unknown_stem_returns_failure() -> None:
    res = ig.parse("nonexistent/999999.pdf", "x")
    assert res["status"] == "failure"
    assert "unknown intergovernmental FY" in res["errors"][0]["error_detail"]


# ── Synthetic-PDF integration (text-layer path) ─────────────────────────────

def _build_synthetic_pdf(path: str) -> None:
    """Two local-level detail rows laid out at the real detail-page x-anchors.

    NOTE: fitz's built-in fonts cannot render Devanagari, so this fixture
    cannot reproduce the ``स्थानीय तह`` summary label the document-total check
    matches on. The synthetic test therefore exercises the per-row
    reconciliation + crosswalk + column model with ``require_reconcile=False``;
    the document-total reconciliation is validated against the REAL in-repo
    PDFs in ``test_real_pdf_*`` (skipped when the corpus is absent).
    """
    doc = fitz.open()
    # Pad to the first detail page (index 10).
    for _ in range(ig._FIRST_DETAIL_PAGE):
        doc.new_page(width=821, height=576)
    detail = doc.new_page(width=821, height=576)
    anchors = ig._DETAIL_ANCHORS

    def row(y: int, code9: str, vals: list[str]) -> None:
        detail.insert_text((56, y), code9, fontsize=8)
        for ax, v in zip(anchors, vals, strict=True):
            detail.insert_text((float(ax), float(y)), v, fontsize=8)

    # Row 1: reconciles (atomic 0,1,2,4,5,7,8,10 sum to col 13 = 50,88).
    row(160, "801011013",
        ["3,25", "13,41", "63", "17,29", "26,07", "2,82", "28,89",
         "2,00", "1,00", "3,00", "1,70", "45,36", "5,52", "50,88"])
    # Row 2: reconciles to 32,61.
    row(180, "801013013",
        ["3,00", "8,35", "42", "11,77", "16,87", "1,17", "18,04",
         "0", "1,00", "1,00", "1,80", "28,64", "3,97", "32,61"])
    doc.save(path)
    doc.close()


@pytest.fixture()
def synthetic_pdf(tmp_path: object) -> str:
    # Stem must be a RECONCILABLE FY so the text-layer path runs.
    p = tmp_path / "207980.pdf"  # type: ignore[operator]
    _build_synthetic_pdf(str(p))
    return str(p)


def test_synthetic_per_row_reconciliation(synthetic_pdf: str) -> None:
    # require_reconcile=False: the synthetic fixture can't carry the Devanagari
    # summary label, so we assert the per-row gate only here.
    res = ig.parse(synthetic_pdf, "syn-doc", require_reconcile=False)
    assert res["status"] == "success", res["errors"]
    rec = res["reconciliation"]
    assert rec["rows_reconciled"] == 2
    assert rec["rows_failed"] == 0
    assert rec["row_grand_total_sum_lakh"] == 8349.0


def test_synthetic_rows_have_expected_shape(synthetic_pdf: str) -> None:
    res = ig.parse(synthetic_pdf, "syn-doc", require_reconcile=False)
    rows = res["rows"]
    # 2 local levels × 8 grant types
    assert len(rows) == 16
    codes = {r["federal_code"] for r in rows}
    assert codes == {"80101101", "80101301"}
    for r in rows:
        assert r["fiscal_year_bs"] == "2079/80"
        assert r["unit"] == "npr_crore"
        assert r["confidence_grade"] == "B"
        # Honest provenance: default (no --surya) is text-layer-only.
        assert "extraction_method=textlayer" in r["notes"]
        assert "surya-ocr" not in r["notes"]
        assert len(r["federal_code"]) == 8


def test_surya_xcheck_flag_changes_extraction_method(synthetic_pdf: str) -> None:
    # When the caller plans to run the Surya cross-check, the row provenance is
    # labelled accordingly; otherwise it must NOT claim an OCR cross-check.
    res = ig.parse(synthetic_pdf, "syn-doc", require_reconcile=False, surya_xcheck=True)
    for r in res["rows"]:
        assert "extraction_method=surya-ocr+textlayer-xcheck" in r["notes"]


def test_synthetic_value_lakh_to_crore_conversion(synthetic_pdf: str) -> None:
    res = ig.parse(synthetic_pdf, "syn-doc", require_reconcile=False)
    # 801011013 eq_minimum = 3,25 lakh = 325 lakh → 32.5 crore.
    eq_min = next(
        r for r in res["rows"]
        if r["federal_code"] == "80101101" and r["grant_type"] == "equalization_minimum"
    )
    assert eq_min["amount_npr"] == pytest.approx(32.5)


def test_idempotent(synthetic_pdf: str) -> None:
    first = ig.parse(synthetic_pdf, "x", require_reconcile=False)
    second = ig.parse(synthetic_pdf, "x", require_reconcile=False)
    assert first == second


# ── Real-PDF reconciliation (skipped when the gitignored corpus is absent) ──

_CORPUS = Path(
    "C:/Users/ACER/Projects/Economy/Financial Data/mof_documents/intergovernmental",
)


@pytest.mark.parametrize(
    ("stem", "fy", "expected_total_lakh"),
    [
        # 9-digit-code editions.
        ("207879", "2078/79", 2830147.0),
        ("207980", "2079/80", 3003716.0),
        # 8-digit-code editions (same 14-column model; verified 753/753).
        ("208081", "2080/81", 2950202.0),
        ("208182", "2081/82", 3124261.0),
    ],
)
def test_real_pdf_document_total_reconciles(
    stem: str, fy: str, expected_total_lakh: float,
) -> None:
    pdf = _CORPUS / f"{stem}.pdf"
    if not pdf.exists():
        pytest.skip(f"corpus PDF absent: {pdf}")
    res = ig.parse(str(pdf), "real-doc")
    assert res["status"] == "success", res["errors"]
    rec = res["reconciliation"]
    assert rec["fiscal_year_bs"] == fy
    assert rec["rows_reconciled"] == 753
    assert rec["rows_failed"] == 0
    assert rec["document_total_reconciles"] is True
    assert rec["printed_local_total_lakh"] == expected_total_lakh
    assert rec["row_grand_total_sum_lakh"] == expected_total_lakh
    # 753 local levels × 8 grant types.
    assert len(res["rows"]) == 753 * 8


@pytest.mark.parametrize(
    "stem",
    [
        "207475",  # deferred layout (early 7-digit / ~5-col format)
        "207576",  # deferred layout
        "207677",  # deferred layout (different code/column geometry)
        "207778",  # genuinely scanned (no numeric text layer)
    ],
)
def test_real_pdf_unsupported_fy_refused(stem: str) -> None:
    """Both genuinely-scanned and different-layout text-layer FYs are refused
    (status=failure, no rows) — the parser never mis-maps columns."""
    pdf = _CORPUS / f"{stem}.pdf"
    if not pdf.exists():
        pytest.skip(f"corpus PDF absent: {pdf}")
    res = ig.parse(str(pdf), "real-doc")
    assert res["status"] == "failure"
    assert res["errors"][0]["error_class"] == "PageLayoutChanged"
    assert res["rows"] == []
