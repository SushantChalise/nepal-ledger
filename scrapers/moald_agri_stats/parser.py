"""MoALD Statistical Information on Nepalese Agriculture — deterministic parser.

Source ID: ``moald-agri-stats``
Input: annual PDF compendium. The 2080/81 edition is a 224-page clean digital
text layer (NO OCR required — every data page has a perfect text layer; only the
blank chapter-divider pages are empty). pdfplumber text extraction is strictly
higher-fidelity than OCR here, so per ADR-0011 we read the text layer directly.

Extracts (all → ``dne_facts`` via ``dimensional_rows``, ADR-0015):

NATIONAL TIME-SERIES (full historical depth):
  Table 1.1  cereal area/production/yield × crop_type        — 11 yr (BS 2070/71–2080/81)
  Table 2.1  cash crop area/production/yield × crop_type     — 10 yr (BS 2071/72–2080/81)
  Table 3.1  pulse area/production/yield × crop_type         — 12 yr (BS 2069/70–2080/81)
  Table 4.1  livestock population × livestock_category       — 10 yr
  Table 4.2  livestock production × livestock_product        — 11 yr
  Table 6.1  fruit area/productive/production/yield × type   — 10 yr
  Table 7.1  vegetable area/production/yield                 — 10 yr
  Table 9.1  fertilizer sales × fertilizer_type              — 14 yr (BS 2067/68–2080/81)
  §1.6       spice area/production × crop_type               — 3 yr

PROVINCIAL CROSS-SECTION (FY 2080/81):
  Table 1.2  cereal production × province_crop (composite, ADR-0018)
  Table 2.2  cash crop area/production/yield × province_crop
  Table 7.2  vegetable area/production/yield × province

DISTRICT CROSS-SECTION (FY 2080/81):
  Table 1.3  aggregate cereal area/production/yield × district (all 77 districts)

Period mapping: AD fiscal-year string YYYY/YY → BS (YYYY+57)/(YY+57 % 100).
  e.g. AD 2013/14 → BS 2070/71; AD 2023/24 → BS 2080/81.

DEFERRED to v0.3.0 (documented in README): the transposed multi-page district
matrices (per-crop districts 1.4–1.6, oilseed-by-commodity 2.4, pulses 3.2,
livestock 4.3–4.10, fruits 6.2–6.4, vegetables 7.3 [40 pp.], fertilizer 9.2,
population 8.2); macro GDP (Table 10.x — overlaps mof-economic-survey-gva); trade
by HS code (Table 11.x — overlaps customs-monthly-trade); agri loans (Table 14.x
— overlaps nrb banking). The latter three need a canonical-source ADR before
ingest to avoid Fact-Ledger double-counting.

ADR-0003: deterministic only; no LLM. ADR-0015: dimensional facts.
ADR-0018: composite dimension_value (``province__crop``) for 2-D slices.

Version log:
  0.1.0 — initial: Table 1.1 cereals + summary §1.4/§1.5/§2.2/§3 (3-yr).
  0.2.0 — full-depth national time-series (cash/pulse/livestock/fruit/veg/fert),
          provincial cross-sections (cereal/cash/veg), cereal-by-district, spices.
          Supersedes the 3-yr summary extractors with authoritative full series.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

import pdfplumber

from _common.periods import fiscal_year_ad_label, fiscal_year_label, mid_month_ad
from _common.types import ParserError, ParserStatus, ReportingPeriodType

PARSER_VERSION: Final[str] = "0.2.0"
SOURCE_ID: Final[str] = "moald-agri-stats"
_CONF: Final[str] = "B"
_MIN_CLI_ARGV: Final[int] = 2  # program name + pdf path
_FY_LATEST_BS: Final[int] = 2080  # FY 2080/81, the cross-section year

# +57 fiscal offset: AD FY start year + 57 = BS FY start year.
_BS_OFFSET: Final[int] = 57

_PROVINCES: Final[tuple[str, ...]] = (
    "koshi", "madhesh", "bagmati", "gandaki", "lumbini", "karnali", "sudurpaschim",
)
# Source spells Sudurpaschim three ways; canonicalize all to one slug.
_PROVINCE_ALIASES: Final[dict[str, str]] = {
    "sudurpashchim": "sudurpaschim",
    "sudurpaschim": "sudurpaschim",
    "sudurpschhim": "sudurpaschim",
}


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
# Shared helpers
# ---------------------------------------------------------------------------

_NUM_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"^-?[\d,]+(?:\.\d+)?$")
_YEAR_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})\s*/\s*(\d{2,4})$")
# Leading fiscal-year token at the start of a data row. Tolerates the source's
# inconsistent spacing in recent years ("2023 /24" prints with an inner space).
_LEAD_YEAR_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(\d{4}\s*/\s*\d{2,4})\s+(.+)$")


def _num(token: str) -> float | None:
    """Parse one whitespace-delimited token. '-' / '...' → None (missing cell)."""
    t = token.strip()
    if t in {"-", "--", "...", ""}:
        return None
    if _NUM_TOKEN_RE.match(t):
        return float(t.replace(",", ""))
    return None


def _row_tokens(rest: str) -> list[float | None]:
    """Tokenize the numeric tail of a data row, preserving '-' as positional None."""
    out: list[float | None] = []
    for tok in rest.split():
        if tok in {"-", "--", "..."}:
            out.append(None)
        elif _NUM_TOKEN_RE.match(tok):
            out.append(float(tok.replace(",", "")))
    return out


def _bs_from_ad_fy(ad_fy_token: str) -> int | None:
    """'2014/15' (possibly '2014 /15') → BS start year 2071. None if unparseable."""
    m = _YEAR_RE.match(ad_fy_token.replace(" ", ""))
    if not m:
        return None
    return int(m.group(1)) + _BS_OFFSET


def _province_slug(name: str) -> str | None:
    key = re.sub(r"[^a-z]", "", name.lower())
    return _PROVINCE_ALIASES.get(key, key if key in _PROVINCES else None)


def _district_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def _slice(text: str, anchor: str, *, max_chars: int = 6000) -> str | None:
    """Return the text window starting at ``anchor`` up to the next table heading
    or ``max_chars``, whichever comes first. None if anchor absent.

    The boundary is case-insensitive: the source mixes 'Table 2.2' (national
    summary tables) with 'TABLE 2.3' (district tables), and a case-sensitive
    boundary would let a national-table slice bleed into the following district
    table and mis-parse its province-prefixed rows.
    """
    pos = text.find(anchor)
    if pos == -1:
        return None
    tail = text[pos + len(anchor) : pos + len(anchor) + max_chars]
    nxt = tail.lower().find("\ntable ")
    if nxt != -1:
        tail = tail[:nxt]
    return tail


_TOTAL_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:nepal|total|n\s*e\s*p\s*a\s*l)\b", re.IGNORECASE
)


def _annual_row(
    slug: str, name: str, dim_kind: str, dim_val: str, dim_label: str,
    value: float, unit: str, bs_start: int,
) -> DimensionalRowDraft:
    fy_bs = fiscal_year_label(bs_start)
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
        fiscal_year_ad_label=fiscal_year_ad_label(bs_start),
        confidence_grade=_CONF,
    )


# Unit constants
_HA: Final[str] = "hectare"
_MT: Final[str] = "metric_tonne"
_MT_HA: Final[str] = "metric_tonne_per_hectare"
_NUMBER: Final[str] = "number"
_KG: Final[str] = "kg"
_THOUSAND: Final[str] = "thousand_units"

# Metric triple (area, production, yield) → (slug suffix, unit)
_AREA_PROD_YIELD: Final[tuple[tuple[str, str], ...]] = (
    ("area", _HA), ("production", _MT), ("yield", _MT_HA),
)
_APY: Final[int] = len(_AREA_PROD_YIELD)  # 3 — area/production/yield columns

# Structural row-shape constants (avoid bare magic numbers in comparisons).
_KEY_TAIL_PARTS: Final[int] = 2  # str.split(None, 1) → [label, numeric-tail]


# ---------------------------------------------------------------------------
# Wide time-series extractor (year-as-row, crops-as-columns)
# ---------------------------------------------------------------------------


def _extract_wide_series(
    text: str,
    anchor: str,
    crops: tuple[tuple[str, str], ...],
    slug_prefix: str,
    name_prefix: str,
    table_label: str,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Year-row × (crop × area/prod/yield) tables: 1.1, 2.1, and pulses 3.1.

    ``crops`` is a tuple of (crop_slug, crop_label) in column order. Each data
    row = year token + len(crops)*3 numbers. Rows with a different count are
    skipped with a logged error (handles the variable pulse Himili-Bean column).
    """
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, anchor)
    if section is None:
        return rows, [ParserError("RegexMismatch", f"{table_label}: anchor not found", None)]
    expected = len(crops) * 3
    seen: set[tuple[int, str]] = set()
    for line in section.splitlines():
        m = _LEAD_YEAR_RE.match(line)
        if not m:
            continue
        bs_start = _bs_from_ad_fy(m.group(1))
        if bs_start is None:
            continue
        toks = _row_tokens(m.group(2))
        if len(toks) != expected:
            continue  # not a clean crop-row (variable layouts handled by dedicated extractors)
        for ci, (crop_slug, crop_label) in enumerate(crops):
            area, prod, yld = toks[ci * 3], toks[ci * 3 + 1], toks[ci * 3 + 2]
            for val, (suffix, unit) in zip((area, prod, yld), _AREA_PROD_YIELD, strict=False):
                if val is None:
                    continue
                key = (bs_start, f"{slug_prefix}-{suffix}:{crop_slug}")
                if key in seen:
                    continue
                seen.add(key)
                rows.append(_annual_row(
                    f"{slug_prefix}-{suffix}", f"{name_prefix} {suffix}",
                    "crop_type", crop_slug, crop_label, val, unit, bs_start,
                ))
    if not rows:
        errors.append(ParserError("RegexMismatch", f"{table_label}: no data rows matched", None))
    return rows, errors


_CEREAL_CROPS: Final[tuple[tuple[str, str], ...]] = (
    ("paddy", "Paddy"), ("maize", "Maize"), ("millet", "Millet"),
    ("buckwheat", "Buckwheat"), ("wheat", "Wheat"), ("barley", "Barley"),
)
_CASH_CROPS: Final[tuple[tuple[str, str], ...]] = (
    ("oilseed", "Oilseed"), ("potato", "Potato"), ("sugarcane", "Sugarcane"),
    ("jute", "Jute"), ("cotton", "Cotton"),
)
_PULSE_CROPS_A: Final[tuple[tuple[str, str], ...]] = (
    ("lentil", "Lentil"), ("chickpea", "Chickpea"), ("pigeon-pea", "Pigeon Pea"),
    ("black-gram", "Black Gram"), ("grass-pea", "Grass Pea"),
)


def _extract_pulse_series_b(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Pulses 3.1 second subtable: Horse Gram / Soyabean / [Himili Bean] / Others / Total.

    Variable layout: early years omit the Himili-Bean column (12 numbers); later
    years include it (15). We map by count and skip the 'Total' aggregate column.
    """
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, "Year Horse Gram Soyabean Himili Bean Others + Total")
    if section is None:
        return rows, [ParserError("RegexMismatch", "Table 3.1b: anchor not found", None)]
    # Column layouts keyed by number-count (excluding the Total triple we skip).
    layout_himili = (("horse-gram", "Horse Gram"), ("soyabean", "Soyabean"),
                     ("himili-bean", "Himili Bean"), ("others", "Others"))  # + Total(skip)
    layout_plain = (("horse-gram", "Horse Gram"), ("soyabean", "Soyabean"),
                    ("others", "Others"))  # + Total(skip)
    # +1 for the trailing 'Total' aggregate column (parsed but skipped), ×_APY metrics.
    cols_himili = (len(layout_himili) + 1) * _APY
    cols_plain = (len(layout_plain) + 1) * _APY
    for line in section.splitlines():
        m = _LEAD_YEAR_RE.match(line)
        if not m:
            continue
        bs_start = _bs_from_ad_fy(m.group(1))
        if bs_start is None:
            continue
        toks = _row_tokens(m.group(2))
        layout: tuple[tuple[str, str], ...]
        if len(toks) == cols_himili:
            layout = layout_himili
        elif len(toks) == cols_plain:
            layout = layout_plain
        else:
            continue
        for ci, (crop_slug, crop_label) in enumerate(layout):
            area, prod, yld = toks[ci * 3], toks[ci * 3 + 1], toks[ci * 3 + 2]
            for val, (suffix, unit) in zip((area, prod, yld), _AREA_PROD_YIELD, strict=False):
                if val is None:
                    continue
                rows.append(_annual_row(
                    f"agri-pulse-{suffix}", f"Pulse {suffix}",
                    "crop_type", crop_slug, crop_label, val, unit, bs_start,
                ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 3.1b: no rows matched", None))
    return rows, errors


# ---------------------------------------------------------------------------
# Transposed time-series extractor (category-as-row, years-as-columns)
# ---------------------------------------------------------------------------


def _extract_transposed_series(
    text: str,
    anchor: str,
    rows_cfg: tuple[tuple[str, str, str, str], ...],
    bs_years: tuple[int, ...],
    slug: str,
    name: str,
    dim_kind: str,
    table_label: str,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Transposed tables: 4.1 (livestock pop), 4.2 (products), 9.1 (fertilizer).

    ``rows_cfg`` = tuple of (label_regex, dim_value, dim_label, unit). Values are
    RIGHT-ALIGNED to ``bs_years`` — a row with fewer numbers than years maps to
    the most-recent years (the missing data is always the earliest years, e.g.
    fish production starts mid-series).
    """
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, anchor, max_chars=4000)
    if section is None:
        return rows, [ParserError("RegexMismatch", f"{table_label}: anchor not found", None)]
    n_years = len(bs_years)
    for label_re, dim_val, dim_label, unit in rows_cfg:
        m = re.search(rf"^{label_re}\s+(.+)$", section, re.MULTILINE)
        if not m:
            errors.append(ParserError(
                "RegexMismatch", f"{table_label}: row '{dim_val}' not found", None,
            ))
            continue
        toks = [t for t in _row_tokens(m.group(1)) if t is not None]
        if not toks or len(toks) > n_years:
            errors.append(ParserError(
                "ValueUnparseable",
                f"{table_label}: row '{dim_val}' has {len(toks)} values vs {n_years} years",
                None,
            ))
            continue
        offset = n_years - len(toks)  # right-align
        for i, val in enumerate(toks):
            bs_start = bs_years[offset + i]
            rows.append(_annual_row(slug, name, dim_kind, dim_val, dim_label, val, unit, bs_start))
    return rows, errors


def _bs_year_span(first_ad: int, last_ad: int) -> tuple[int, ...]:
    """Inclusive BS-start year list for AD fiscal years first_ad..last_ad."""
    return tuple(range(first_ad + _BS_OFFSET, last_ad + _BS_OFFSET + 1))


# Livestock population 4.1: AD 2014/15..2023/24
_LIVESTOCK_POP_YEARS: Final[tuple[int, ...]] = _bs_year_span(2014, 2023)
# Livestock products 4.2: AD 2013/14..2023/24
_LIVESTOCK_PROD_YEARS: Final[tuple[int, ...]] = _bs_year_span(2013, 2023)
# Fertilizer 9.1: AD 2010/11..2023/24
_FERT_YEARS: Final[tuple[int, ...]] = _bs_year_span(2010, 2023)

_LIVESTOCK_POP_ROWS: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("CATTLE", "cattle", "Cattle", _NUMBER),
    ("BUFFALOES", "buffaloes", "Buffaloes", _NUMBER),
    ("SHEEP", "sheep", "Sheep", _NUMBER),
    ("GOAT", "goat", "Goat", _NUMBER),
    ("PIGS", "pigs", "Pigs", _NUMBER),
    ("FOWL", "fowl", "Fowl", _NUMBER),
    ("DUCK", "duck", "Duck", _NUMBER),
    ("MILKING COW", "milking-cow", "Milking cow", _NUMBER),
    ("MILKING BUFFALOES", "milking-buffalo", "Milking buffaloes", _NUMBER),
    ("LAYING HEN", "laying-hen", "Laying hen", _NUMBER),
    ("LAYING DUCK", "laying-duck", "Laying duck", _NUMBER),
)

# 4.2 products. Order matters: specific labels before generic substrings.
_LIVESTOCK_PROD_ROWS: Final[tuple[tuple[str, str, str, str], ...]] = (
    (r"MILK PRODUCTION \(Mt\.\)", "milk-total", "Milk production", _MT),
    (r"COW MILK \(Mt\.\)", "milk-cow", "Cow milk", _MT),
    (r"BUFF\. MILK \(Mt\.\)", "milk-buffalo", "Buffalo milk", _MT),
    (r"MEAT \(NET\) PRODUCTION \(Mt\.\)", "meat-total", "Meat production (net)", _MT),
    (r"BUFF \(Mt\.\)", "meat-buffalo", "Buffalo meat", _MT),
    (r"MUTTON \(Sheep\) \(Mt\.\)", "meat-sheep", "Mutton (sheep)", _MT),
    (r"CHEVON \(Mt\.\)", "meat-goat", "Chevon (goat)", _MT),
    (r"PORK \(Mt\.\)", "meat-pork", "Pork", _MT),
    (r"CHICKEN \(Mt\.\)", "meat-chicken", "Chicken meat", _MT),
    (r"DUCK \(Mt\.\)", "meat-duck", "Duck meat", _MT),
    (r"EGG PRODUCTION \('000 Number\)", "eggs-total", "Egg production", _THOUSAND),
    (r"HEN EGG\('000 Number\)", "eggs-hen", "Hen egg", _THOUSAND),
    (r"DUCK EGG\('000 Number\)", "eggs-duck", "Duck egg", _THOUSAND),
    (r"WOOL PRODUCTION\(Kg\.\)", "wool", "Wool", _KG),
    (r"FISH PRODUCTION \(Mt\)", "fish", "Fish production", _MT),
)

_FERT_ROWS: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("Urea", "urea", "Urea", _MT),
    ("DAP", "dap", "DAP", _MT),
    ("Potash", "potash", "Potash", _MT),
    (r"Total AICL& STCL", "total", "Total (AICL & STCL)", _MT),
)


# ---------------------------------------------------------------------------
# Fruits 6.1 — type-grouped, year-per-line
# ---------------------------------------------------------------------------

_FRUIT_TYPES: Final[dict[str, tuple[str, str]]] = {
    "Citrus fruits": ("citrus", "Citrus fruits"),
    "Winter fruits": ("winter", "Winter fruits"),
    "Summer fruits": ("summer", "Summer fruits"),
    "Total fruits": ("total-fruit", "Total fruits"),
}
_FRUIT_METRICS: Final[tuple[tuple[str, str, str], ...]] = (
    ("total-area", "Fruit total area", _HA),
    ("productive-area", "Fruit productive area", _HA),
    ("production", "Fruit production", _MT),
    ("yield", "Fruit yield", _MT_HA),
)


def _extract_fruits(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, "Types Year Total Area", max_chars=4000)
    if section is None:
        return rows, [ParserError("RegexMismatch", "Table 6.1: anchor not found", None)]
    current: tuple[str, str] | None = None
    for line in section.splitlines():
        stripped = line.strip()
        for type_name, slug_label in _FRUIT_TYPES.items():
            if stripped.startswith(type_name):
                current = slug_label
                stripped = stripped[len(type_name):].strip()
                break
        if current is None:
            continue
        m = _LEAD_YEAR_RE.match(stripped)
        if not m:
            continue
        bs_start = _bs_from_ad_fy(m.group(1))
        if bs_start is None:
            continue
        toks = _row_tokens(m.group(2))
        if len(toks) != len(_FRUIT_METRICS):
            continue
        crop_slug, crop_label = current
        for val, (suffix, name, unit) in zip(toks, _FRUIT_METRICS, strict=False):
            if val is None:
                continue
            rows.append(_annual_row(
                f"agri-fruit-{suffix}", name, "crop_type",
                crop_slug, crop_label, val, unit, bs_start,
            ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 6.1: no fruit rows matched", None))
    return rows, errors


# ---------------------------------------------------------------------------
# Vegetables 7.1 — national series (S.No. Year Area Prod Yield)
# ---------------------------------------------------------------------------


def _extract_vegetable_series(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, "S.No. Year Area Prod. Yield", max_chars=2000)
    if section is None:
        return rows, [ParserError("RegexMismatch", "Table 7.1: anchor not found", None)]
    for line in section.splitlines():
        m = re.match(r"^\d+\s+(\d{4}\s*/\s*\d{2})\s+(.+)$", line.strip())
        if not m:
            continue
        bs_start = _bs_from_ad_fy(m.group(1))
        if bs_start is None:
            continue
        toks = _row_tokens(m.group(2))
        if len(toks) != _APY:
            continue
        for val, (suffix, unit) in zip(toks, _AREA_PROD_YIELD, strict=False):
            if val is None:
                continue
            rows.append(_annual_row(
                f"agri-vegetable-{suffix}", f"Vegetable {suffix}",
                "crop_type", "fresh-vegetable", "Fresh vegetables", val, unit, bs_start,
            ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 7.1: no vegetable rows matched", None))
    return rows, errors


# ---------------------------------------------------------------------------
# Spices §1.6 — national 3-yr (area + production)
# ---------------------------------------------------------------------------

_SPICE_ROWS: Final[tuple[tuple[str, str, str], ...]] = (
    ("Large Cardamom", "large-cardamom", "Large Cardamom"),
    ("Ginger", "ginger", "Ginger"),
    ("Garlic", "garlic", "Garlic"),
    ("Turmeric", "turmeric", "Turmeric"),
    ("Dry Chili", "dry-chili", "Dry Chili"),
)
_SUMMARY_BS_YEARS: Final[tuple[int, ...]] = (2078, 2079, 2080)
_SPICE_METRICS: Final[int] = 2  # area + production per year


def _extract_spices(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, "1.6 Other Crops", max_chars=1500)
    if section is None:
        return rows, [ParserError("RegexMismatch", "§1.6 Other Crops: anchor not found", None)]
    n_cols = _SPICE_METRICS * len(_SUMMARY_BS_YEARS)  # 6: area+production × 3 years
    # Tolerate a "(Productive area)" suffix (Large Cardamom) between label and numbers.
    cells = rf"((?:[\d,]+\s+){{{n_cols - 1}}}[\d,]+)"
    for label, slug, dim_label in _SPICE_ROWS:
        # [^\d\n]* stays on the label's own line (\D would cross newlines).
        m = re.search(rf"^{re.escape(label)}\b[^\d\n]*{cells}", section, re.MULTILINE)
        if not m:
            errors.append(ParserError("RegexMismatch", f"§1.6: spice '{slug}' not found", None))
            continue
        toks = _row_tokens(m.group(1))
        if len(toks) < n_cols:
            errors.append(ParserError(
                "ValueUnparseable", f"§1.6: spice '{slug}' has {len(toks)} values", None,
            ))
            continue
        for idx, bs_start in enumerate(_SUMMARY_BS_YEARS):
            area, prod = toks[idx * _SPICE_METRICS], toks[idx * _SPICE_METRICS + 1]
            if area is not None:
                rows.append(_annual_row(
                    "agri-spice-area", "Spice area", "crop_type",
                    slug, dim_label, area, _HA, bs_start,
                ))
            if prod is not None:
                rows.append(_annual_row(
                    "agri-spice-production", "Spice production", "crop_type",
                    slug, dim_label, prod, _MT, bs_start,
                ))
    return rows, errors


# ---------------------------------------------------------------------------
# Provincial cross-sections (FY 2080/81)
# ---------------------------------------------------------------------------


def _extract_cereal_by_province(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Table 1.2 — cereal PRODUCTION by province × crop (composite dimension)."""
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(
        text, "Province Paddy Maize Wheat Millet Barley Buckwheat Total", max_chars=1200,
    )
    if section is None:
        return rows, [ParserError("RegexMismatch", "Table 1.2: anchor not found", None)]
    crop_order = (("paddy", "Paddy"), ("maize", "Maize"), ("wheat", "Wheat"),
                  ("millet", "Millet"), ("barley", "Barley"), ("buckwheat", "Buckwheat"))
    for line in section.splitlines():
        if _TOTAL_ROW_RE.match(line):
            break  # national total row ends the provincial block
        parts = line.split(None, 1)
        if len(parts) != _KEY_TAIL_PARTS:
            continue
        prov = _province_slug(parts[0])
        if prov is None:
            continue
        toks = _row_tokens(parts[1])
        if len(toks) != len(crop_order) + 1:  # 6 crops + Total column
            continue
        for ci, (crop_slug, crop_label) in enumerate(crop_order):
            val = toks[ci]
            if val is None:
                continue
            rows.append(_annual_row(
                "agri-cereal-production", "Cereal production",
                "province-crop", f"{prov}__{crop_slug}",
                f"{parts[0].strip()} - {crop_label}", val, _MT, _FY_LATEST_BS,
            ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 1.2: no province rows matched", None))
    return rows, errors


def _extract_cashcrop_by_province(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Table 2.2 — cash crop area/prod/yield by province × crop (oilseed/sugarcane/potato)."""
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, "Province Oilseed Sugarcane Potato", max_chars=1400)
    if section is None:
        return rows, [ParserError("RegexMismatch", "Table 2.2: anchor not found", None)]
    crops = (("oilseed", "Oilseed"), ("sugarcane", "Sugarcane"), ("potato", "Potato"))
    for line in section.splitlines():
        if _TOTAL_ROW_RE.match(line):
            break  # national total row ends the provincial block
        parts = line.split(None, 1)
        if len(parts) != _KEY_TAIL_PARTS:
            continue
        prov = _province_slug(parts[0])
        if prov is None:
            continue
        toks = _row_tokens(parts[1])
        if len(toks) != len(crops) * _APY:  # 3 crops × area/prod/yield
            continue
        for ci, (crop_slug, crop_label) in enumerate(crops):
            area, prod, yld = toks[ci * 3], toks[ci * 3 + 1], toks[ci * 3 + 2]
            for val, (suffix, unit) in zip((area, prod, yld), _AREA_PROD_YIELD, strict=False):
                if val is None:
                    continue
                rows.append(_annual_row(
                    f"agri-cashcrop-{suffix}", f"Cash crop {suffix}",
                    "province-crop", f"{prov}__{crop_slug}",
                    f"{parts[0].strip()} - {crop_label}", val, unit, _FY_LATEST_BS,
                ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 2.2: no province rows matched", None))
    return rows, errors


def _extract_vegetable_by_province(
    text: str,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Table 7.2 — vegetable area/prod/yield by province (single commodity)."""
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    # Anchor on the unique two-line header. The bare "Province Area Production
    # Yield" recurs in many district tables; only 7.2 carries the "(Ha.) (Mt.)
    # (Mt./Ha)" sub-header (no trailing period, unlike 7.1's "(Mt./Ha.)").
    anchor = "Province Area Production Yield\n(Ha.) (Mt.) (Mt./Ha)"
    pos = text.find(anchor)
    if pos == -1:
        return rows, [ParserError("RegexMismatch", "Table 7.2: anchor not found", None)]
    section = text[pos : pos + 900]
    for line in section.splitlines():
        if _TOTAL_ROW_RE.match(line):
            break  # national total row ends the provincial block
        parts = line.split(None, 1)
        if len(parts) != _KEY_TAIL_PARTS:
            continue
        prov = _province_slug(parts[0])
        if prov is None:
            continue
        toks = _row_tokens(parts[1])
        if len(toks) != _APY:
            continue
        for val, (suffix, unit) in zip(toks, _AREA_PROD_YIELD, strict=False):
            if val is None:
                continue
            rows.append(_annual_row(
                f"agri-vegetable-{suffix}", f"Vegetable {suffix}",
                "province", prov, parts[0].strip(), val, unit, _FY_LATEST_BS,
            ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 7.2: no province rows matched", None))
    return rows, errors


# ---------------------------------------------------------------------------
# District cross-section (FY 2080/81) — Table 1.3 aggregate cereal
# ---------------------------------------------------------------------------


def _extract_cereal_by_district(text: str) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Table 1.3 — aggregate cereal area/prod/yield for every district.

    Rows look like 'Koshi TAPLEJUNG 23,258 63,440 2.73'. Province SUBTOTAL rows
    ('Koshi 772,510 2,710,787 3.51' — province then 3 numbers, no district) and
    the 'N E P A L' grand total are skipped (kept only for reconciliation).
    """
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    section = _slice(text, "Province District Area Production Yield", max_chars=9000)
    if section is None:
        return rows, [ParserError("RegexMismatch", "Table 1.3: anchor not found", None)]
    seen: set[str] = set()
    # Minimum valid district row = province + ≥1 name token + area/prod/yield.
    min_tokens = 2 + _APY
    for line in section.splitlines():
        toks = line.split()
        if len(toks) < min_tokens:
            continue  # province subtotal ('Koshi 772,510 …') or short line
        prov = _province_slug(toks[0])
        if prov is None:
            continue
        # District name is the run of non-numeric tokens after the province.
        di = 1
        name_parts: list[str] = []
        while di < len(toks) and not _NUM_TOKEN_RE.match(toks[di]) and toks[di] != "-":
            name_parts.append(toks[di])
            di += 1
        nums = _row_tokens(" ".join(toks[di:]))
        if not name_parts or len(nums) != _APY:
            continue  # province subtotal (no name) or malformed
        district = _district_slug(" ".join(name_parts))
        if district in seen or not district:
            continue
        seen.add(district)
        area, prod, yld = nums
        label = " ".join(name_parts).title()
        for val, (suffix, unit) in zip((area, prod, yld), _AREA_PROD_YIELD, strict=False):
            if val is None:
                continue
            rows.append(_annual_row(
                f"agri-cereal-{suffix}", f"Cereal {suffix}",
                "district", district, label, val, unit, _FY_LATEST_BS,
            ))
    if not rows:
        errors.append(ParserError("RegexMismatch", "Table 1.3: no district rows matched", None))
    return rows, errors


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


# Wide national time-series tables: (anchor, crops, slug_prefix, name_prefix, label).
_WIDE_TABLES: Final[tuple[tuple[str, tuple[tuple[str, str], ...], str, str, str], ...]] = (
    (
        "YEAR PADDY MAIZE MILLET BUCKWHEAT WHEAT BARLEY",
        _CEREAL_CROPS, "agri-cereal", "Cereal", "Table 1.1",
    ),
    (
        "YEAR OILSEED POTATO SUGARCANE JUTE COTTON",
        _CASH_CROPS, "agri-cashcrop", "Cash crop", "Table 2.1",
    ),
    (
        "Year Lentil Chickpea Pigeon Pea Black Gram Grass Pea",
        _PULSE_CROPS_A, "agri-pulse", "Pulse", "Table 3.1a",
    ),
)

# Transposed national time-series tables:
# (anchor, rows_cfg, bs_years, slug, name, dimension_kind, label).
_TRANSPOSED_TABLES: Final[tuple[tuple[Any, ...], ...]] = (
    (
        "CATEGORY 2014/15", _LIVESTOCK_POP_ROWS, _LIVESTOCK_POP_YEARS,
        "agri-livestock-population", "Livestock population", "livestock_category", "Table 4.1",
    ),
    (
        "PRODUCTS 2013/14", _LIVESTOCK_PROD_ROWS, _LIVESTOCK_PROD_YEARS,
        "agri-livestock-production", "Livestock production", "livestock_product", "Table 4.2",
    ),
    (
        "Type 2010/11", _FERT_ROWS, _FERT_YEARS,
        "agri-fertilizer-sales", "Chemical fertilizer sales", "fertilizer_type", "Table 9.1",
    ),
)

# Single-purpose extractors (no extra config args).
_Extractor = Callable[[str], tuple[list[DimensionalRowDraft], list[ParserError]]]
_SINGLETON_EXTRACTORS: Final[tuple[_Extractor, ...]] = (
    _extract_pulse_series_b,
    _extract_fruits,
    _extract_vegetable_series,
    _extract_spices,
    _extract_cereal_by_province,
    _extract_cashcrop_by_province,
    _extract_vegetable_by_province,
    _extract_cereal_by_district,
)


def parse(source_document_path: str) -> AgriResult:
    path = Path(source_document_path)
    if not path.exists():
        return AgriResult(
            "failure", PARSER_VERSION, [],
            [ParserError("Other", f"File not found: {source_document_path}", None)],
        )
    try:
        with pdfplumber.open(path) as pdf:
            doc_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:  # noqa: BLE001 — surface any PDF failure as a typed error
        return AgriResult(
            "failure", PARSER_VERSION, [],
            [ParserError("Other", f"PDF open error: {exc}", None)],
        )

    all_rows: list[DimensionalRowDraft] = []
    all_errors: list[ParserError] = []

    for anchor, crops, slug_prefix, name_prefix, label in _WIDE_TABLES:
        r, e = _extract_wide_series(doc_text, anchor, crops, slug_prefix, name_prefix, label)
        all_rows.extend(r)
        all_errors.extend(e)
    for cfg in _TRANSPOSED_TABLES:
        r, e = _extract_transposed_series(doc_text, *cfg)
        all_rows.extend(r)
        all_errors.extend(e)
    for extractor in _SINGLETON_EXTRACTORS:
        r, e = extractor(doc_text)
        all_rows.extend(r)
        all_errors.extend(e)

    status: ParserStatus = "success" if not all_errors else ("partial" if all_rows else "failure")
    return AgriResult(status, PARSER_VERSION, all_rows, all_errors)


def _main() -> None:
    # Force UTF-8 stdout so non-ASCII labels survive a Windows cp1252 console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < _MIN_CLI_ARGV:
        print(json.dumps({"error": "usage: parser.py <pdf_path>"}), file=sys.stderr)
        sys.exit(1)
    result = parse(sys.argv[1])
    print(json.dumps(result.to_json_dict(), ensure_ascii=False))


if __name__ == "__main__":
    _main()
