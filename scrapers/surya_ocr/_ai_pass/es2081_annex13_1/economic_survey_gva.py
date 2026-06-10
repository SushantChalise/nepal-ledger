"""Parser for Economic Survey 2081-82 (Nepali) — अनुसूची १३.१.

Table: प्रदेशगत कुल मूल्य अभिवृद्धि (औद्योगिक वर्गीकरण अनुसार)
       Provincial Gross Value Added by industrial classification
Unit:  रू. करोडमा (Rs. crore, current prices / प्रचलित मूल्यमा)
Source page: 475 of Economic_Survey_2081-82.pdf (Surya OCR at render_scale 3.0)

Scope fence (ADR-0003 / ADR-0021):
  - Reads only the pre-existing Surya OCR JSON; never calls the PDF or any API.
  - All values come from OCR text_lines; arithmetic is deterministic Python.
  - Suspects are FLAGGED, not corrected. Single-cell repair proposals are noted
    in the reconciliation report for Mother to confirm against the rendered page.
  - Zero filling, interpolation, and guessing are FORBIDDEN.

Output artifacts (written by __main__):
  scrapers/surya_ocr/_ai_pass/es2081_annex13_1/cells.json
  scrapers/surya_ocr/_ai_pass/es2081_annex13_1/reconciliation_report.md
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants derived from page geometry (render_scale 3.0, landscape 2052×1512)
# ---------------------------------------------------------------------------

PARSER_VERSION = "0.1.0"
SOURCE_PAGE = 475
# Path relative to scrapers/ directory (parents[2] of __file__)
OCR_PATH = (
    "surya_ocr/_ocr_output"
    "/P2__Economic_Survey_2081-82_309ffe7c/page_0475.json"
)

# Fiscal years (extracted from high-confidence header tokens)
YEAR_A = "2080/81"   # २०८०/८१  — actual
YEAR_B = "2081/82"   # २०८१/८२• — provisional/estimated (• / *)

# 8 provinces × 2 years = 16 value columns.
# Column anchors are the x-centre of each sub-column in px (render_scale 3.0).
# Derived from the province header centres plus year-label offsets observed in
# the header band (y≈368-382).  Each province spans ~170 px; YearA is the left
# sub-column, YearB is the right.
#
# Province centres (from header bboxes):
#   कोशी      ≈ 607     → YearA x≈ 561,  YearB x≈ 657
#   मधेस      ≈ 781     → YearA x≈ 733,  YearB x≈ 831
#   वागमती    ≈ 961     → YearA x≈ 916,  YearB x≈ 1012
#   गण्डकी    ≈ 1136    → YearA x≈ 1090, YearB x≈ 1185
#   लुम्बिनी  ≈ 1299   → YearA x≈ 1262, YearB x≈ 1343
#   कर्णाली   ≈ 1458   → YearA x≈ 1418, YearB x≈ 1501
#   सुदूरपश्चिम ≈ 1616  → YearA x≈ 1577, YearB x≈ 1663
#   नेपाल     ≈ 1784   → YearA x≈ 1735, YearB x≈ 1835

# (col_index, province_ne, year) – col_index 0..15
COLUMN_DEFS: list[tuple[int, str, str]] = [
    (0,  "कोशी",          YEAR_A),
    (1,  "कोशी",          YEAR_B),
    (2,  "मधेस",          YEAR_A),
    (3,  "मधेस",          YEAR_B),
    (4,  "वागमती",        YEAR_A),
    (5,  "वागमती",        YEAR_B),
    (6,  "गण्डकी",        YEAR_A),
    (7,  "गण्डकी",        YEAR_B),
    (8,  "लुम्बिनी",     YEAR_A),
    (9,  "लुम्बिनी",     YEAR_B),
    (10, "कर्णाली",       YEAR_A),
    (11, "कर्णाली",       YEAR_B),
    (12, "सुदूरपश्चिम",   YEAR_A),
    (13, "सुदूरपश्चिम",   YEAR_B),
    (14, "नेपाल",         YEAR_A),
    (15, "नेपाल",         YEAR_B),
]

# x-anchors for columns 0..15 (px at render_scale 3.0).
# Derived empirically as the mean x-centre across all 16 complete data rows (sectors
# 0-2, 5-13, 16-20), confirming consistent column positions across the page.
# Year header labels confirm the assignment: YearA at xc≈560 (col 0, Koshi),
# YearB at xc≈657 (col 1, Koshi), YearA at xc≈916 (col 4, Bagmati),
# YearA at xc≈1736 (col 14, Nepal), YearB at xc≈1826 (col 15, Nepal).
COL_X_ANCHORS: list[float] = [
    582, 672,    # कोशी   YA YB
    756, 843,    # मधेस   YA YB
    935, 1024,   # वागमती YA YB
    1113, 1191,  # गण्डकी YA YB
    1277, 1352,  # लुम्बिनी YA YB
    1435, 1514,  # कर्णाली  YA YB
    1592, 1670,  # सुदूरपश्चिम YA YB
    1750, 1840,  # नेपाल   YA YB
]

# Row y-bands: (sector_idx, label_ne, y_min, y_max)
# Derived from label line bboxes + data row bboxes.  Multi-line labels have
# their lines merged; the sector's data rows fall in the y-band below the label.
SECTOR_DEFS: list[tuple[int, str, float, float]] = [
    (0,  "कृषि, वन र मत्स्यपालन",                            400, 432),
    (1,  "खानी तथा उत्खनन्",                                  432, 460),
    (2,  "उत्पादनमूलक उद्योग",                                460, 490),
    # "विद्युत, ग्यास, वाष्प, तथा वातानुकलित आपूर्ति सेवा" spans two label lines
    (3,  "विद्युत, ग्यास, वाष्प, तथा वातानुकलित आपूर्ति सेवा", 491, 542),
    # "पानी आपूर्ति, ढल फोहोर व्यवस्थापन तथा पुनःउत्पादनका क्रियाकलापहरू" spans two label lines
    (4,  "पानी आपूर्ति, ढल फोहोर व्यवस्थापन तथा पुनःउत्पादनका क्रियाकलापहरू", 542, 600),
    (5,  "निर्माण",                                            599, 624),
    # "थोक तथा खुद्रा व्यापार, गाडि तथा मोटरसाइकल मर्मत सेवा" spans two label lines
    (6,  "थोक तथा खुद्रा व्यापार, गाडि तथा मोटरसाइकल मर्मत सेवा", 624, 680),
    (7,  "यातायात तथा भण्डारण",                               685, 712),
    (8,  "आवास तथा भोजन सेवा",                                712, 740),
    (9,  "सुचना तथा सञ्चार",                                  740, 765),
    (10, "वित्तीय तथा बीमा क्रियाकलापहरु",                    765, 793),
    (11, "घरजग्गा कारोवारको सेवा",                             793, 820),
    # "पेशागत वैज्ञानीक तथा प्राविधिक क्रियाकलापहरू" spans two label lines
    (12, "पेशागत वैज्ञानीक तथा प्राविधिक क्रियाकलापहरू",      820, 875),
    # "प्रशासनिक तथा सहयोगी सेवाका क्रियाकलापहरू"
    (13, "प्रशासनिक तथा सहयोगी सेवाका क्रियाकलापहरू",         875, 904),
    # "सार्वजनिक प्रशासन, रक्षा र अत्यावश्यक सामाजिक सुरक्षा" spans two lines
    (14, "सार्वजनिक प्रशासन, रक्षा र अत्यावश्यक सामाजिक सुरक्षा", 904, 958),
    (15, "शिक्षा",                                             958, 985),
    (16, "मानव स्वास्थ्य तथा सामाजिक कार्य",                  985, 1012),
    (17, "अन्य सेवाका क्रियाकलापहरु",                         1012, 1040),
]

# Aggregate rows (appear AFTER the 18 sectors)
AGG_SECTOR_IDX_GVA_BASIC = 18   # कुल मूल्य अभिवृद्धि (आधारभूत मूल्यमा)
AGG_SECTOR_IDX_NET_TAX   = 19   # उत्पादित वस्तुमा खुद कर
AGG_SECTOR_IDX_GDP       = 20   # कुल गार्हस्थ्य उत्पादन (उत्पादकको मूल्यमा)

AGG_DEFS: list[tuple[int, str, float, float]] = [
    (AGG_SECTOR_IDX_GVA_BASIC, "कुल मूल्य अभिवृद्धि (आधारभूत मूल्यमा)",      1041, 1095),
    (AGG_SECTOR_IDX_NET_TAX,   "उत्पादित वस्तुमा खुद कर",                      1095, 1124),
    (AGG_SECTOR_IDX_GDP,       "कुल गार्हस्थ्य उत्पादन (उत्पादकको मूल्यमा)",  1124, 1175),
]

# Confidence threshold below which a cell is suspect
LOW_CONF_THRESHOLD = 0.75

# Snap tolerance: a token whose nearest anchor is more than this far away is
# marked suspect (probable column-placement error).
COL_SNAP_TOL_PX = 80.0

# ---------------------------------------------------------------------------
# Digit normalization
# ---------------------------------------------------------------------------
_DEV_DIGITS = "०१२३४५६७८९"
_ARAB_DIGITS = "0123456789"
_DEV_TO_ARAB = str.maketrans(_DEV_DIGITS, _ARAB_DIGITS)

# Arabic-Indic (Extended Arabic-Indic) ٠١٢٣٤٥٦٧٨٩
_ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"
_ARAB_IND_TO_ARAB = str.maketrans(_ARABIC_INDIC, _ARAB_DIGITS)


def _has_devanagari_digit(s: str) -> bool:
    return any(c in _DEV_DIGITS for c in s)


def _has_arabic_digit(s: str) -> bool:
    return any(c in _ARAB_DIGITS for c in s)


def _has_arabic_indic_digit(s: str) -> bool:
    return any(c in _ARABIC_INDIC for c in s)


def _is_mixed_script(s: str) -> bool:
    """True if s mixes any two of: Devanagari digits, Latin/Arabic digits, Arabic-Indic."""
    scripts = sum([
        _has_devanagari_digit(s),
        _has_arabic_digit(s),
        _has_arabic_indic_digit(s),
    ])
    return scripts > 1


def _normalize_to_arabic(s: str) -> str:
    """Translate Devanagari + Arabic-Indic digits → ASCII Arabic. Strips spaces."""
    return s.translate(_DEV_TO_ARAB).translate(_ARAB_IND_TO_ARAB).replace(" ", "")


# Strip markup artifacts like <b>…</b> that Surya occasionally wraps around tokens.
_MARKUP_RE = re.compile(r"<[^>]+>")


def _strip_markup(s: str) -> str:
    return _MARKUP_RE.sub("", s)


def _extract_numeric(raw: str) -> str | None:
    """Try to extract a clean integer string from raw OCR text.

    Returns the digit string (no commas, Arabic numerals) if the token looks
    like a valid number; None if it cannot be parsed as one.  Commas (grouping
    separators in Nepal's lakh/crore system) are stripped.
    """
    clean = _strip_markup(raw).strip()
    normalized = _normalize_to_arabic(clean)
    # Remove commas (South-Asian grouping), then check it is all digits.
    bare = normalized.replace(",", "")
    if bare.isdigit() and len(bare) > 0:
        return bare
    return None


def _try_parse_value(raw: str) -> int | None:
    """Parse OCR text to integer (Rs. crore, no decimals in this table)."""
    digits = _extract_numeric(raw)
    if digits is None:
        return None
    return int(digits)


# ---------------------------------------------------------------------------
# Suspect detection helpers
# ---------------------------------------------------------------------------

def _suspect_reasons(
    raw: str,
    confidence: float,
    parsed_value: int | None,
    snap_dist: float,
) -> list[str]:
    reasons: list[str] = []
    if confidence < LOW_CONF_THRESHOLD:
        reasons.append(f"low_confidence ({confidence:.3f} < {LOW_CONF_THRESHOLD})")
    clean = _strip_markup(raw).strip()
    if _is_mixed_script(clean):
        reasons.append("mixed_digit_scripts")
    if parsed_value is None:
        reasons.append("unparseable_as_integer")
    if snap_dist > COL_SNAP_TOL_PX:
        reasons.append(f"column_snap_dist {snap_dist:.0f}px > {COL_SNAP_TOL_PX}px tol")
    return reasons


# ---------------------------------------------------------------------------
# Column-snapping
# ---------------------------------------------------------------------------

def _nearest_col(x_centre: float) -> tuple[int, float]:
    """Return (col_index, distance_px) for the closest column anchor."""
    best_idx = 0
    best_dist = abs(x_centre - COL_X_ANCHORS[0])
    for i, anchor in enumerate(COL_X_ANCHORS):
        d = abs(x_centre - anchor)
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx, best_dist


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class CellRecord:
    sector_label_ne: str
    sector_idx: int
    province: str
    year: str
    raw_ocr_text: str
    parsed_value: int | None
    confidence: float
    bbox: list[float]   # [x0, y0, x1, y1] in px at render_scale 3.0
    is_suspect: bool
    suspect_reasons: list[str]


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_ocr_json(ocr_data: dict[str, Any]) -> list[CellRecord]:
    """Extract all value cells from the OCR text_lines list."""
    lines = ocr_data["text_lines"]

    # Build all row bands: sectors + aggregates
    all_bands: list[tuple[int, str, float, float]] = list(SECTOR_DEFS) + list(AGG_DEFS)

    # Index lines by their y-centre into a band
    def y_centre(line: dict[str, Any]) -> float:
        x0, y0, x1, y1 = line["bbox"]
        return (y0 + y1) / 2.0

    def x_centre(line: dict[str, Any]) -> float:
        x0, y0, x1, y1 = line["bbox"]
        return (x0 + x1) / 2.0

    cells: list[CellRecord] = []

    for sector_idx, label_ne, y_min, y_max in all_bands:
        # Collect numeric-looking lines that fall in this y-band.
        # We use y-centre to assign to the correct row band.
        band_lines = [
            line for line in lines
            if y_min <= y_centre(line) < y_max
            and y_centre(line) > 399  # skip headers (y < 400)
        ]

        for line in band_lines:
            raw = line["text"]
            conf = float(line["confidence"])
            bbox = list(line["bbox"])
            xc = x_centre(line)

            # Skip clearly non-numeric lines (labels): if the stripped+markup-
            # removed text has no digit characters at all, skip.
            clean = _strip_markup(raw).strip()
            has_any_digit = _has_devanagari_digit(clean) or _has_arabic_digit(clean) or _has_arabic_indic_digit(clean)
            if not has_any_digit:
                continue

            # Try to snap to a column
            col_idx, snap_dist = _nearest_col(xc)
            _, province, year = COLUMN_DEFS[col_idx]

            # Try to parse the value
            parsed_value = _try_parse_value(raw)

            reasons = _suspect_reasons(raw, conf, parsed_value, snap_dist)
            is_suspect = len(reasons) > 0

            cells.append(CellRecord(
                sector_label_ne=label_ne,
                sector_idx=sector_idx,
                province=province,
                year=year,
                raw_ocr_text=raw,
                parsed_value=parsed_value,
                confidence=conf,
                bbox=bbox,
                is_suspect=is_suspect,
                suspect_reasons=reasons,
            ))

    return cells


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def _build_matrix(
    cells: list[CellRecord],
    sector_indices: list[int],
) -> dict[tuple[int, int], CellRecord]:
    """Return {(sector_idx, col_idx): CellRecord} for the given sector indices."""
    matrix: dict[tuple[int, int], CellRecord] = {}
    for cell in cells:
        if cell.sector_idx in sector_indices:
            ci = _col_idx(cell.province, cell.year)
            key = (cell.sector_idx, ci)
            if key not in matrix or cell.confidence > matrix[key].confidence:
                matrix[key] = cell
    return matrix


def _col_idx(province: str, year: str) -> int:
    for i, (_, p, y) in enumerate(COLUMN_DEFS):
        if p == province and y == year:
            return i
    raise ValueError(f"No column for {province!r} {year!r}")


def reconcile(cells: list[CellRecord]) -> dict[str, Any]:
    """Run the 4 reconciliation gates. Return a structured report dict."""

    # Build lookup: (sector_idx, col_idx) -> CellRecord (best confidence)
    lookup: dict[tuple[int, int], CellRecord] = {}
    for cell in cells:
        ci = _col_idx(cell.province, cell.year)
        key = (cell.sector_idx, ci)
        if key not in lookup or cell.confidence > lookup[key].confidence:
            lookup[key] = cell

    SECTOR_IDXS = list(range(18))  # 0..17
    PROVINCES = [p for _, p, y in COLUMN_DEFS if y == YEAR_A]  # 8 provinces
    YEARS = [YEAR_A, YEAR_B]

    results: list[dict[str, Any]] = []

    # Gate 1: Σ(17 sector cells) == GVA basic, per column
    gate1: list[dict[str, Any]] = []
    for ci, (_, province, year) in enumerate(COLUMN_DEFS):
        sector_values: list[int] = []
        missing: list[int] = []
        suspect_in_col: list[int] = []
        for si in SECTOR_IDXS:
            rec = lookup.get((si, ci))
            if rec is None:
                missing.append(si)
            elif rec.parsed_value is None:
                suspect_in_col.append(si)
            else:
                sector_values.append(rec.parsed_value)

        gva_rec = lookup.get((AGG_SECTOR_IDX_GVA_BASIC, ci))
        gva_value = gva_rec.parsed_value if gva_rec else None

        col_sum = sum(sector_values) if sector_values else None
        diff = (col_sum - gva_value) if (col_sum is not None and gva_value is not None) else None

        gate1.append({
            "province": province,
            "year": year,
            "col_idx": ci,
            "sector_sum": col_sum,
            "gva_basic_printed": gva_value,
            "diff": diff,
            "missing_sectors": missing,
            "unparseable_sectors": suspect_in_col,
            "passes": diff == 0 if diff is not None else None,
        })

    # Gate 2: GVA basic + net_tax == GDP, per column
    gate2: list[dict[str, Any]] = []
    for ci, (_, province, year) in enumerate(COLUMN_DEFS):
        gva_rec = lookup.get((AGG_SECTOR_IDX_GVA_BASIC, ci))
        tax_rec = lookup.get((AGG_SECTOR_IDX_NET_TAX, ci))
        gdp_rec = lookup.get((AGG_SECTOR_IDX_GDP, ci))
        gva_val = gva_rec.parsed_value if gva_rec else None
        tax_val = tax_rec.parsed_value if tax_rec else None
        gdp_val = gdp_rec.parsed_value if gdp_rec else None
        lhs = (gva_val + tax_val) if (gva_val is not None and tax_val is not None) else None
        diff = (lhs - gdp_val) if (lhs is not None and gdp_val is not None) else None
        gate2.append({
            "province": province,
            "year": year,
            "col_idx": ci,
            "gva_basic": gva_val,
            "net_tax": tax_val,
            "gva_plus_tax": lhs,
            "gdp_printed": gdp_val,
            "diff": diff,
            "passes": diff == 0 if diff is not None else None,
        })

    # Gate 3: Σ(7 provinces) == Nepal, per row and year
    gate3: list[dict[str, Any]] = []
    all_rows = list(range(21))  # 0..17 sectors + 3 aggregates
    nepal_provinces = [p for p in PROVINCES if p != "नेपाल"]
    for si in all_rows:
        for year in YEARS:
            province_values: list[int] = []
            missing_provs: list[str] = []
            for prov in nepal_provinces:
                ci = _col_idx(prov, year)
                rec = lookup.get((si, ci))
                if rec is None:
                    missing_provs.append(prov)
                elif rec.parsed_value is not None:
                    province_values.append(rec.parsed_value)
                else:
                    missing_provs.append(f"{prov}(unparseable)")

            nepal_ci = _col_idx("नेपाल", year)
            nepal_rec = lookup.get((si, nepal_ci))
            nepal_val = nepal_rec.parsed_value if nepal_rec else None

            prov_sum = sum(province_values) if province_values else None
            diff = (prov_sum - nepal_val) if (prov_sum is not None and nepal_val is not None) else None

            # Get sector label
            all_sector_labels = {s: l for s, l, _, _ in (list(SECTOR_DEFS) + list(AGG_DEFS))}
            label = all_sector_labels.get(si, f"sector_{si}")

            gate3.append({
                "sector_idx": si,
                "sector_label": label,
                "year": year,
                "province_sum": prov_sum,
                "nepal_printed": nepal_val,
                "diff": diff,
                "missing": missing_provs,
                "passes": diff == 0 if diff is not None else None,
            })

    # Gate 4: Nepal GDP magnitude check
    gate4: list[dict[str, Any]] = []
    for year in YEARS:
        ci = _col_idx("नेपाल", year)
        rec = lookup.get((AGG_SECTOR_IDX_GDP, ci))
        val = rec.parsed_value if rec else None
        # Expected: ~570000 crore for 2080/81
        expected_approx = 570000 if year == YEAR_A else None
        gate4.append({
            "year": year,
            "nepal_gdp_crore": val,
            "expected_approx_crore": expected_approx,
            "raw_ocr": rec.raw_ocr_text if rec else None,
            "is_suspect": rec.is_suspect if rec else None,
        })

    return {
        "gate1_sector_sum_vs_gva": gate1,
        "gate2_gva_plus_tax_vs_gdp": gate2,
        "gate3_province_sum_vs_nepal": gate3,
        "gate4_nepal_gdp_magnitude": gate4,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_cells_json(cells: list[CellRecord], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Extract column and row header labels directly from OCR
    column_headers = {
        "provinces_ne": ["कोशी", "मधेस", "वागमती", "गण्डकी", "लुम्बिनी", "कर्णाली", "सुदूरपश्चिम", "नेपाल"],
        "years": [YEAR_A, YEAR_B],
        "year_labels_raw": {
            "2080/81": "२०८०/८१",
            "2081/82": "२०८१/८२•",
        },
        "note": "नेपाल column labelled 'कुल मूल्य अभिवृद्धि' in header; interpreted as national total",
    }
    row_headers = {
        "sector_labels_ne": [label for _, label, _, _ in SECTOR_DEFS],
        "aggregate_labels_ne": [label for _, label, _, _ in AGG_DEFS],
    }
    payload = {
        "source_page": SOURCE_PAGE,
        "parser_version": PARSER_VERSION,
        "unit": "रू. करोडमा",
        "price_basis": "प्रचलित मूल्यमा (current prices)",
        "column_headers": column_headers,
        "row_headers": row_headers,
        "cells": [asdict(c) for c in cells],
    }
    out_path = out_dir / "cells.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}", file=sys.stderr)


def write_reconciliation_report(
    cells: list[CellRecord],
    recon: dict[str, Any],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "reconciliation_report.md"

    suspects = [c for c in cells if c.is_suspect]

    lines: list[str] = []
    a = lines.append

    a("# Reconciliation Report — अनुसूची १३.१")
    a("")
    a(f"Source page: {SOURCE_PAGE} | Parser: v{PARSER_VERSION}")
    a(f"Table title: प्रदेशगत कुल मूल्य अभिवृद्धि (औद्योगिक वर्गीकरण अनुसार)")
    a(f"Unit: रू. करोडमा | Price basis: प्रचलित मूल्यमा")
    a("")
    a("## 1. Extracted Header Labels")
    a("")
    a("### Province columns (left → right)")
    a("| Col pair | Province (Nepali) | Year A | Year B |")
    a("|----------|-------------------|--------|--------|")
    for i in range(0, 16, 2):
        ci_a, prov, ya = COLUMN_DEFS[i]
        ci_b, _,    yb = COLUMN_DEFS[i + 1]
        a(f"| {i//2 + 1} | {prov} | {ya} | {yb} |")
    a("")
    a("**Year labels in OCR:** `२०८०/८१` (YearA, actual) and `२०८१/८२•` (YearB, provisional/estimated)")
    a("")
    a("**Province note:** The 8th column header reads `कुल मूल्य अभिवृद्धि` — this is the national")
    a("aggregate (Nepal total), labeled `नेपाल` in this report. Header confidence: 1.000.")
    a("")
    a("### Row labels (sector + aggregate)")
    a("")
    a("| Idx | Sector label (Nepali) |")
    a("|-----|-----------------------|")
    for si, label, _, _ in SECTOR_DEFS:
        a(f"| {si} | {label} |")
    a("")
    a("**Aggregate rows:**")
    a("")
    a("| Idx | Label (Nepali) |")
    a("|-----|----------------|")
    for si, label, _, _ in AGG_DEFS:
        a(f"| {si} | {label} |")
    a("")

    # --- Gate 1 summary ---
    a("## 2. Gate 1 — Σ(18 sector rows) == कुल मूल्य अभिवृद्धि (GVA basic), per column")
    a("")
    a("| Province | Year | Sector sum | GVA basic printed | Diff | Pass? |")
    a("|----------|------|-----------|-------------------|------|-------|")
    for row in recon["gate1_sector_sum_vs_gva"]:
        prov = row["province"]
        yr = row["year"]
        ss = row["sector_sum"]
        gva = row["gva_basic_printed"]
        diff = row["diff"]
        passes = row["passes"]
        missing = row["missing_sectors"]
        unparseable = row["unparseable_sectors"]
        note = ""
        if missing:
            note += f" MISSING sectors:{missing}"
        if unparseable:
            note += f" UNPARSEABLE sectors:{unparseable}"
        a(f"| {prov} | {yr} | {ss} | {gva} | {diff} | {passes}{note} |")
    a("")

    # --- Gate 2 summary ---
    a("## 3. Gate 2 — GVA basic + खुद कर == कुल गार्हस्थ्य उत्पादन (GDP), per column")
    a("")
    a("| Province | Year | GVA basic | Net tax | Sum | GDP printed | Diff | Pass? |")
    a("|----------|------|-----------|---------|-----|-------------|------|-------|")
    for row in recon["gate2_gva_plus_tax_vs_gdp"]:
        a(f"| {row['province']} | {row['year']} | {row['gva_basic']} | {row['net_tax']} | {row['gva_plus_tax']} | {row['gdp_printed']} | {row['diff']} | {row['passes']} |")
    a("")

    # --- Gate 3 summary ---
    a("## 4. Gate 3 — Σ(7 provinces) == नेपाल, per sector row and year")
    a("")
    a("*Only rows with a non-None diff are shown; None means ≥1 cell missing/unparseable.*")
    a("")
    a("| Sector | Year | Province sum | Nepal printed | Diff | Pass? |")
    a("|--------|------|--------------|---------------|------|-------|")
    for row in recon["gate3_province_sum_vs_nepal"]:
        if row["diff"] is None:
            continue
        a(f"| {row['sector_label'][:50]} | {row['year']} | {row['province_sum']} | {row['nepal_printed']} | {row['diff']} | {row['passes']} |")
    a("")
    a("**Rows where diff is None (missing/unparseable cells prevent the sum):**")
    a("")
    a("| Sector | Year | Missing/unparseable |")
    a("|--------|------|---------------------|")
    for row in recon["gate3_province_sum_vs_nepal"]:
        if row["diff"] is None and row["missing"]:
            a(f"| {row['sector_label'][:50]} | {row['year']} | {row['missing']} |")
    a("")

    # --- Gate 4 ---
    a("## 5. Gate 4 — Nepal GDP Magnitude Check")
    a("")
    a("| Year | Nepal GDP (रू. करोडमा) | Expected ≈ | Suspect? | Raw OCR |")
    a("|------|------------------------|------------|---------|---------|")
    for row in recon["gate4_nepal_gdp_magnitude"]:
        a(f"| {row['year']} | {row['nepal_gdp_crore']} | {row['expected_approx_crore']} | {row['is_suspect']} | `{row['raw_ocr']}` |")
    a("")
    a("**Note:** Nepal GDP for FY2080/81 should be ≈ 570,000 crore (≈ 5.7 trillion NPR).")
    a("")

    # --- Suspect list ---
    a("## 6. Suspect Cell List")
    a("")
    a(f"Total suspects: {len(suspects)} out of {len(cells)} cells")
    a("")
    if suspects:
        a("| Sector | Province | Year | Raw OCR | Parsed | Conf | Bbox [x0,y0,x1,y1] | Reasons |")
        a("|--------|----------|------|---------|--------|------|---------------------|---------|")
        for s in suspects:
            reasons_str = "; ".join(s.suspect_reasons)
            bbox_str = f"[{','.join(str(int(v)) for v in s.bbox)}]"
            a(f"| {s.sector_label_ne[:30]} | {s.province} | {s.year} | `{s.raw_ocr_text}` | {s.parsed_value} | {s.confidence:.3f} | {bbox_str} | {reasons_str} |")
    a("")

    # --- Single-cell repair proposals ---
    a("## 7. Single-Cell Arithmetic Repair Proposals")
    a("")
    a("For each gate-3 row (province sum vs Nepal) that fails by exactly one suspect cell,")
    a("a proposed repair is listed. **These are proposals only — Mother must verify against")
    a("the rendered page before any value is accepted.**")
    a("")

    proposals: list[dict[str, Any]] = []

    # Check gate3 rows with exactly one known suspect that could explain the diff
    for row in recon["gate3_province_sum_vs_nepal"]:
        diff = row.get("diff")
        if diff is None or diff == 0:
            continue
        si = row["sector_idx"]
        year = row["year"]
        # Find suspects for this sector+year
        row_suspects = [
            c for c in suspects
            if c.sector_idx == si and c.year == year and c.parsed_value is not None
        ]
        # If exactly one suspect, compute what the corrected value would be
        if len(row_suspects) == 1:
            s = row_suspects[0]
            proposed = s.parsed_value - diff
            proposals.append({
                "sector_label": row["sector_label"],
                "year": year,
                "province": s.province,
                "raw_ocr": s.raw_ocr_text,
                "parsed_value": s.parsed_value,
                "proposed_value": proposed,
                "diff_fixed": diff,
                "identity": f"Σ(7 provinces)={row['province_sum']} vs Nepal={row['nepal_printed']}; diff={diff}",
                "bbox": s.bbox,
            })

    if proposals:
        a("| Sector | Year | Province | Raw OCR | Parsed | Proposed | Diff | Identity |")
        a("|--------|------|----------|---------|--------|----------|------|----------|")
        for p in proposals:
            a(f"| {p['sector_label'][:30]} | {p['year']} | {p['province']} | `{p['raw_ocr']}` | {p['parsed_value']} | **{p['proposed_value']}** | {p['diff_fixed']} | {p['identity'][:60]} |")
    else:
        a("*No single-cell repair proposals (no gate-3 row fails with exactly one suspect).*")
    a("")

    # --- Verdict ---
    a("## 8. Verdict")
    a("")

    g1_pass = sum(1 for r in recon["gate1_sector_sum_vs_gva"] if r["passes"] is True)
    g1_total = len(recon["gate1_sector_sum_vs_gva"])
    g2_pass = sum(1 for r in recon["gate2_gva_plus_tax_vs_gdp"] if r["passes"] is True)
    g2_total = len(recon["gate2_gva_plus_tax_vs_gdp"])
    g3_pass = sum(1 for r in recon["gate3_province_sum_vs_nepal"] if r["passes"] is True)
    g3_total = len(recon["gate3_province_sum_vs_nepal"])
    g3_na = sum(1 for r in recon["gate3_province_sum_vs_nepal"] if r["passes"] is None)

    a(f"- **Gate 1** (sector sum = GVA basic): {g1_pass}/{g1_total} columns pass exactly")
    a(f"- **Gate 2** (GVA + net tax = GDP): {g2_pass}/{g2_total} columns pass exactly")
    a(f"- **Gate 3** (7-province sum = Nepal): {g3_pass}/{g3_total} rows pass exactly; {g3_na} rows N/A (missing cells)")
    a(f"- **Gate 4** (Nepal GDP magnitude): see table above")
    a("")
    a("**Unresolved cells requiring Mother verification against rendered page:**")
    a("")
    unresolved = [
        c for c in suspects
        if c.parsed_value is None or "mixed_digit_scripts" in c.suspect_reasons
    ]
    if unresolved:
        for c in unresolved:
            a(f"- Sector {c.sector_idx} ({c.sector_label_ne[:40]}), {c.province}, {c.year}: "
              f"raw=`{c.raw_ocr_text}` bbox={[int(v) for v in c.bbox]}")
    else:
        a("*None — all cells parsed to integers (some remain suspect for other reasons).*")
    a("")
    a("*Report generated by economic_survey_gva.py v{PARSER_VERSION}*".format(
        PARSER_VERSION=PARSER_VERSION))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# __main__ entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    import io
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

    # Resolve paths relative to scrapers/ directory
    # __file__ = .../scrapers/surya_ocr/parsers/economic_survey_gva.py
    # parents[0] = parsers/, parents[1] = surya_ocr/, parents[2] = scrapers/
    scrapers_dir = Path(__file__).resolve().parents[2]
    ocr_abs = scrapers_dir / OCR_PATH

    if not ocr_abs.exists():
        sys.stderr.write(f"ERROR: OCR JSON not found at {ocr_abs}\n")
        sys.exit(1)

    with open(ocr_abs, encoding="utf-8") as f:
        ocr_data = json.load(f)

    cells = parse_ocr_json(ocr_data)
    recon = reconcile(cells)

    out_dir = scrapers_dir / "surya_ocr/_ai_pass/es2081_annex13_1"
    write_cells_json(cells, out_dir)
    write_reconciliation_report(cells, recon, out_dir)

    # Print a concise summary to stdout for Mother
    total = len(cells)
    suspect_count = sum(1 for c in cells if c.is_suspect)
    unparseable = sum(1 for c in cells if c.parsed_value is None)
    print(json.dumps({
        "status": "ok",
        "total_cells": total,
        "suspect_cells": suspect_count,
        "unparseable_cells": unparseable,
        "artifacts": [
            str(out_dir / "cells.json"),
            str(out_dir / "reconciliation_report.md"),
        ],
    }, ensure_ascii=False))


if __name__ == "__main__":
    _main()
