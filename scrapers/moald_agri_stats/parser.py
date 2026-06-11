"""MoALD Statistical Information on Nepalese Agriculture — deterministic parser.

Source ID: ``moald-agri-stats``
Input: annual PDF compendium with clean Latin-script text layer.

Extracts (all → ``dne_facts`` via ``dimensional_rows``):
  Table 1.1: 10-year cereal area/production/yield × crop_type
  Summary §1.4: 3-year cash crop area/production × crop_type
  Summary §1.5: 3-year pulse area/production × crop_type
  Summary §2.2: 3-year livestock production × product
  Summary §3:   3-year fertilizer sales × fertilizer_type

Page detection: parser scans for "SUMMARY STATISTICS" and "Table 1.1" anchors,
so it works against both the full 224-page PDF and a 4-page test fixture.

Period mapping (Table 1.1): AD YYYY/YY → BS FY (YYYY+57)/(YY+57 % 100).

ADR-0003: deterministic only; no LLM. ADR-0015: dimensional facts.

Version log:
  0.1.0 — initial: Table 1.1 cereals (10 yr) + summary §1.4/§1.5/§2.2/§3 (3 yr)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pdfplumber

from _common.periods import fiscal_year_ad_label, fiscal_year_label, mid_month_ad
from _common.types import ParserError, ParserStatus, ReportingPeriodType

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "moald-agri-stats"
_CONF: Final[str] = "B"

# Three summary fiscal years present in §1.3–§3
_SUM_YEARS: Final[tuple[int, ...]] = (2078, 2079, 2080)

# Table 1.1 column order: PADDY MAIZE MILLET BUCKWHEAT WHEAT BARLEY
_T11_CROPS: Final[tuple[str, ...]] = (
    "paddy", "maize", "millet", "buckwheat", "wheat", "barley"
)

_CASH_CROPS: Final[tuple[tuple[str, str], ...]] = (
    ("Oilseeds", "oilseeds"),
    ("Potato", "potato"),
    ("Sugarcane", "sugarcane"),
    ("Jute", "jute"),
    ("Cotton", "cotton"),
)

_PULSES: Final[tuple[tuple[str, str], ...]] = (
    ("Lentil", "lentil"),
    ("Chickpea", "chickpea"),
    ("Pigeon Pea", "pigeon-pea"),
    ("Black Gram", "black-gram"),
    ("Grass Pea", "grass-pea"),
    ("Horse Gram", "horse-gram"),
    ("Soyabean", "soyabean"),
    ("Others", "others"),
    # Himali bean: 2078/79 data absent; deferred to v0.2.0
)

# Livestock rows: (regex_pattern, dimension_value, unit)
_LIVESTOCK_ROWS: Final[tuple[tuple[str, str, str], ...]] = (
    (r"MILK PRODUCTION \(Mt\.\)", "milk-total", "metric_tonne"),
    (r"- COW MILK", "milk-cow", "metric_tonne"),
    (r"- BUFF\. MILK", "milk-buffalo", "metric_tonne"),
    (r"MEAT \(NET\) PRODUCTION \(Mt\.\)", "meat-total", "metric_tonne"),
    (r"- BUFF\b", "meat-buffalo", "metric_tonne"),
    (r"- MUTTON", "meat-sheep", "metric_tonne"),
    (r"- CHEVON", "meat-goat", "metric_tonne"),
    (r"- PORK", "meat-pork", "metric_tonne"),
    (r"- CHICKEN", "meat-chicken", "metric_tonne"),
    (r"EGG PRODUCTION", "eggs-total", "thousand_units"),
    (r"- HEN EGG", "eggs-hen", "thousand_units"),
    (r"- DUCK EGG", "eggs-duck", "thousand_units"),
    (r"WOOL PRODUCTION", "wool", "kg"),
)

_T11_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^(\d{4}\s*/\s*\d{2})"
    + r"(?:\s+([\d,]+)\s+([\d,]+)\s+([\d.]+))" * 6
    + r"\s*$",
    re.MULTILINE,
)
_THREE_NUM_TAIL: Final[str] = r"([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$"
_SIX_NUM_TAIL: Final[str] = (
    r"([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$"
)


# ---------------------------------------------------------------------------
# Dimensional fact types (mirror customs_trade / mof_redbook)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionalRowDraft:
    base_indicator_slug: str
    base_indicator_name: str
    dimension_kind: str
    dimension_value: str
    dimension_label: str
    value: float
    unit: str
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str
    reporting_period_ad_start: datetime
    reporting_period_ad_end: datetime
    fiscal_year_bs: str
    fiscal_year_ad_label: str
    confidence_grade: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "base_indicator_slug": self.base_indicator_slug,
            "base_indicator_name": self.base_indicator_name,
            "dimension_kind": self.dimension_kind,
            "dimension_value": self.dimension_value,
            "dimension_label": self.dimension_label,
            "value": self.value,
            "unit": self.unit,
            "reporting_period_type": self.reporting_period_type,
            "reporting_period_bs": self.reporting_period_bs,
            "reporting_period_ad_start": self.reporting_period_ad_start.isoformat(),
            "reporting_period_ad_end": self.reporting_period_ad_end.isoformat(),
            "fiscal_year_bs": self.fiscal_year_bs,
            "fiscal_year_ad_label": self.fiscal_year_ad_label,
            "confidence_grade": self.confidence_grade,
        }


@dataclass(frozen=True)
class AgriResult:
    status: ParserStatus
    parser_version: str
    dimensional_rows: list[DimensionalRowDraft]
    errors: list[ParserError]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "parser_version": self.parser_version,
            "dimensional_rows": [r.to_json_dict() for r in self.dimensional_rows],
            "errors": [e.to_json_dict() for e in self.errors],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _n(s: str) -> float:
    return float(s.replace(",", ""))


def _annual_row(
    slug: str,
    name: str,
    dim_kind: str,
    dim_val: str,
    dim_label: str,
    value: float,
    unit: str,
    bs_start: int,
) -> DimensionalRowDraft:
    fy_bs = fiscal_year_label(bs_start)
    fy_ad = fiscal_year_ad_label(bs_start)
    return DimensionalRowDraft(
        base_indicator_slug=slug,
        base_indicator_name=name,
        dimension_kind=dim_kind,
        dimension_value=dim_val,
        dimension_label=dim_label,
        value=value,
        unit=unit,
        reporting_period_type="annual",
        reporting_period_bs=fy_bs,
        reporting_period_ad_start=mid_month_ad("Shrawan", bs_start),
        reporting_period_ad_end=mid_month_ad("Ashadh", bs_start),
        fiscal_year_bs=fy_bs,
        fiscal_year_ad_label=fy_ad,
        confidence_grade=_CONF,
    )


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------


def _extract_cereal_table11(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    anchor = text.find("Table 1.1")
    if anchor == -1:
        return rows, [ParserError("RegexMismatch", "Table 1.1 anchor not found", None)]
    section = text[anchor:]
    seen: set[str] = set()
    for m in _T11_ROW_RE.finditer(section):
        year_raw = m.group(1).replace(" ", "")   # "2021 /22" → "2021/22"
        if year_raw in seen:
            continue
        seen.add(year_raw)
        bs_start = int(year_raw[:4]) + 57        # AD 2013 → BS 2070
        vals = m.groups()[1:]                     # 18 values: (area, prod, yield) × 6
        for i, crop in enumerate(_T11_CROPS):
            base = i * 3
            label = crop.capitalize()
            rows.append(_annual_row("agri-cereal-area", "Cereal crop area", "crop_type", crop, label, _n(vals[base]), "hectare", bs_start))
            rows.append(_annual_row("agri-cereal-production", "Cereal crop production", "crop_type", crop, label, _n(vals[base + 1]), "metric_tonne", bs_start))
            rows.append(_annual_row("agri-cereal-yield", "Cereal crop yield", "crop_type", crop, label, float(vals[base + 2]), "metric_tonne_per_hectare", bs_start))
    if not seen:
        errors.append(ParserError("RegexMismatch", "No Table 1.1 data rows matched", None))
    return rows, errors


def _extract_section_6col(
    text: str,
    anchor_str: str,
    crops: tuple[tuple[str, str], ...],
    slug_area: str,
    name_area: str,
    slug_prod: str,
    name_prod: str,
    dim_kind: str,
    end_str: str | None = None,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Extract 3-year (area, production) tables anchored by ``anchor_str``."""
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    anchor = text.find(anchor_str)
    if anchor == -1:
        return rows, [ParserError("RegexMismatch", f"Anchor '{anchor_str}' not found", None)]
    section = text[anchor:]
    if end_str:
        end = section.find(end_str)
        if end != -1:
            section = section[:end]
    for crop_label, crop_slug in crops:
        m = re.search(
            rf"^{re.escape(crop_label)}\s+{_SIX_NUM_TAIL}",
            section, re.MULTILINE,
        )
        if not m:
            errors.append(ParserError("RegexMismatch", f"Crop '{crop_label}' not found in '{anchor_str}'", None))
            continue
        vals = [_n(g) for g in m.groups()]
        # vals: [area_78, prod_78, area_79, prod_79, area_80, prod_80]
        for idx, bs_start in enumerate(_SUM_YEARS):
            a, p = vals[idx * 2], vals[idx * 2 + 1]
            rows.append(_annual_row(slug_area, name_area, dim_kind, crop_slug, crop_label, a, "hectare", bs_start))
            rows.append(_annual_row(slug_prod, name_prod, dim_kind, crop_slug, crop_label, p, "metric_tonne", bs_start))
    return rows, errors


def _extract_livestock(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    anchor = text.find("2.2 Livestock Production")
    if anchor == -1:
        return rows, [ParserError("RegexMismatch", "2.2 Livestock Production anchor not found", None)]
    section = text[anchor:]
    three_re = re.compile(_THREE_NUM_TAIL, re.MULTILINE)
    for pat, dim_val, unit in _LIVESTOCK_ROWS:
        # Use .*? to absorb "(Sheep)", "(Kg.)", "('000 Number)" etc. between label and values
        m = re.search(rf"{pat}.*?{_THREE_NUM_TAIL}", section, re.MULTILINE)
        if not m:
            errors.append(ParserError("RegexMismatch", f"Livestock row '{dim_val}' not found", None))
            continue
        vals = [_n(g) for g in m.groups()]
        label = dim_val.replace("-", " ")
        for idx, bs_start in enumerate(_SUM_YEARS):
            rows.append(_annual_row("agri-livestock-production", "Livestock production", "livestock_product", dim_val, label, vals[idx], unit, bs_start))
    return rows, errors


def _extract_fertilizer(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    anchor = text.find("Annual Sales of Chemical Fertilizer")
    if anchor == -1:
        return rows, [ParserError("RegexMismatch", "Fertilizer section anchor not found", None)]
    section = text[anchor:]
    for label, slug in (("Urea", "urea"), ("DAP", "dap"), ("Potash", "potash"), ("Total", "total")):
        m = re.search(rf"^{re.escape(label)}\s+{_THREE_NUM_TAIL}", section, re.MULTILINE)
        if not m:
            errors.append(ParserError("RegexMismatch", f"Fertilizer row '{label}' not found", None))
            continue
        vals = [_n(g) for g in m.groups()]
        for idx, bs_start in enumerate(_SUM_YEARS):
            rows.append(_annual_row("agri-fertilizer-sales", "Chemical fertilizer sales", "fertilizer_type", slug, label, vals[idx], "metric_tonne", bs_start))
    return rows, errors


# ---------------------------------------------------------------------------
# Page detection + main parse entry
# ---------------------------------------------------------------------------


def _find_page(pages: list[Any], anchor: str, max_scan: int = 30) -> int:
    """Return the 0-based index of the first page within ``max_scan`` pages
    whose text contains ``anchor``, or -1 if not found."""
    for i, page in enumerate(pages[:max_scan]):
        if anchor in (page.extract_text() or ""):
            return i
    return -1


def parse(source_document_path: str) -> AgriResult:
    path = Path(source_document_path)
    if not path.exists():
        return AgriResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=[ParserError("Other", f"File not found: {source_document_path}", None)],
        )
    try:
        with pdfplumber.open(path) as pdf:
            pages = pdf.pages

            pg_sum = _find_page(pages, "SUMMARY STATISTICS")
            if pg_sum == -1:
                return AgriResult(
                    status="failure",
                    parser_version=PARSER_VERSION,
                    dimensional_rows=[],
                    errors=[ParserError("RegexMismatch", "SUMMARY STATISTICS page not found in first 30 pages", None)],
                )

            pg_t11 = _find_page(pages, "Table 1.1")
            if pg_t11 == -1:
                return AgriResult(
                    status="failure",
                    parser_version=PARSER_VERSION,
                    dimensional_rows=[],
                    errors=[ParserError("RegexMismatch", "Table 1.1 page not found in first 30 pages", None)],
                )

            # Summary stats span 3 pages starting from pg_sum
            sum_page_count = min(3, len(pages) - pg_sum)
            summary_text = "\n".join(
                pages[pg_sum + i].extract_text() or "" for i in range(sum_page_count)
            )
            table11_text = pages[pg_t11].extract_text() or ""
    except Exception as exc:
        return AgriResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=[ParserError("Other", f"PDF open error: {exc}", None)],
        )

    all_rows: list[DimensionalRowDraft] = []
    all_errors: list[ParserError] = []

    for r, e in (
        _extract_cereal_table11(table11_text),
        _extract_section_6col(
            summary_text, "1.4 Cash Crops",
            _CASH_CROPS,
            "agri-cashcrop-area", "Cash crop area",
            "agri-cashcrop-production", "Cash crop production",
            "crop_type", end_str="1.5 Pulses",
        ),
        _extract_section_6col(
            summary_text, "1.5 Pulses",
            _PULSES,
            "agri-pulse-area", "Pulse area",
            "agri-pulse-production", "Pulse production",
            "crop_type", end_str="1.6 Other Crops",
        ),
        _extract_livestock(summary_text),
        _extract_fertilizer(summary_text),
    ):
        all_rows.extend(r)
        all_errors.extend(e)

    status: ParserStatus = (
        "success" if not all_errors else ("partial" if all_rows else "failure")
    )
    return AgriResult(
        status=status,
        parser_version=PARSER_VERSION,
        dimensional_rows=all_rows,
        errors=all_errors,
    )


def _main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: parser.py <pdf_path>"}), file=sys.stderr)
        sys.exit(1)
    result = parse(sys.argv[1])
    print(json.dumps(result.to_json_dict(), ensure_ascii=False))


if __name__ == "__main__":
    _main()
