"""Extract structured data from FCGO CFS overview tables (pages ~28–58).

Phase 2 of the FCGO extraction strategy. The CFS Overview section contains
~45 tables with 5-year time series on revenue, expenditure, COFOG functional
classification, debt, and macro indicators. pymupdf ``find_tables()`` reads
them correctly — including the landscape-rotated pages that pdfplumber fails on.

Targets (v1.1.0):
    Table 28 — Macro indicators (GDP, GNI, saving/investment ratios, per-capita)
    Table 29 — Budget operations as % of GDP (expenditure, revenue, debt ratios)
    Table 10 — COFOG functional expenditure (10 sectors, % of total)
    Table 16 — Outstanding debt stock (domestic/external, NPR million)
    Table 37 — Debt composition ratios (outstanding/GDP, servicing split)

Each table yields rows for ALL fiscal years in the header (typically 5 FYs).
A single FY 2022/23 PDF produces ~200 staging rows from these 5 tables.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, datetime
from typing import Final

import pymupdf

from _common.periods import fiscal_year_ad_label, fiscal_year_label, mid_month_ad
from _common.types import ParserError, StagingRowDraft

_FY_COL_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})/(\d{2,4})$")

_AD_TO_BS_FY_OFFSET: Final[int] = 57


def _parse_fy_header(header_row: list[str | None]) -> list[int | None]:
    """Parse the FY header row into AD-start years (None for non-FY columns)."""
    result: list[int | None] = []
    for cell in header_row:
        if cell is None:
            result.append(None)
            continue
        text = cell.strip().replace("\n", "")
        m = _FY_COL_RE.match(text)
        if m is None:
            result.append(None)
            continue
        lead = int(m.group(1))
        suffix_str = m.group(2)
        suffix = int(suffix_str) if len(suffix_str) == 2 else int(suffix_str) % 100
        if suffix != (lead + 1) % 100:
            result.append(None)
            continue
        if lead < 2015:
            result.append(None)
            continue
        result.append(lead)
    return result


def _parse_value(raw: str | None) -> float | None:
    """Parse a table cell value. Returns None for empty/unparseable cells."""
    if raw is None:
        return None
    text = raw.strip().replace("\n", "")
    if not text or text == "-" or text == "–":
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace(",", "")
    try:
        val = float(text)
    except ValueError:
        return None
    return -val if negative else val


def _build_base_row(ad_fy_start: int, pub_ad_fy_start: int) -> StagingRowDraft:
    """Build a base StagingRowDraft for a given fiscal year."""
    bs_fy_start = ad_fy_start + _AD_TO_BS_FY_OFFSET
    period_start = mid_month_ad("Shrawan", bs_fy_start)
    period_end = mid_month_ad("Ashadh", bs_fy_start)
    pub_bs_year = (pub_ad_fy_start + _AD_TO_BS_FY_OFFSET) + 2
    pub_ad = datetime(pub_ad_fy_start + 2, 5, 15, tzinfo=UTC)
    pub_bs = f"{pub_bs_year} Jestha 15"
    return StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="",
        reporting_period_type="annual",
        reporting_period_bs=f"FY {fiscal_year_label(bs_fy_start)}",
        reporting_period_ad_start=period_start,
        reporting_period_ad_end=period_end,
        publication_date_ad=pub_ad,
        publication_date_bs=pub_bs,
        fiscal_year_bs=fiscal_year_label(bs_fy_start),
        fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        confidence_grade_proposed="A",
        parser_notes=None,
    )


RowMapping = tuple[str, str, str]


def _normalize(text: str) -> str:
    """Collapse whitespace for fuzzy text matching."""
    return re.sub(r"\s+", " ", text).strip()


def _find_page_with_table(doc: pymupdf.Document, anchor: str) -> int | None:
    """Find the first page that contains anchor text AND has tables.

    Normalizes whitespace so line-broken text still matches. Skips TOC
    pages and other pages that mention the anchor but have no tables.
    """
    norm_anchor = _normalize(anchor).lower()
    for i in range(doc.page_count):
        page_text = _normalize(doc[i].get_text()).lower()
        if norm_anchor not in page_text:
            continue
        if doc[i].find_tables().tables:
            return i
    return None


def _extract_from_table(
    doc: pymupdf.Document,
    anchor_text: str,
    row_mappings: list[RowMapping],
    pub_ad_fy_start: int,
    table_note: str,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Extract indicators from a single overview table.

    Locates the table by finding the page with ``anchor_text``, then scans
    all tables on that page for matching row labels. Returns staging rows
    for every (row × FY-column) cell that has a parseable value.
    """
    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    page_idx = _find_page_with_table(doc, anchor_text)
    if page_idx is None:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=f"table anchor not found: {anchor_text!r}",
            )
        )
        return staging_rows, errors

    page = doc[page_idx]
    tables = page.find_tables()
    if not tables.tables:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=f"no tables on page {page_idx + 1} near {anchor_text!r}",
            )
        )
        return staging_rows, errors

    best_table = None
    best_fy_cols: list[tuple[int, int]] = []
    for t in tables.tables:
        data = t.extract()
        if len(data) < 3:
            continue
        fy_years = _parse_fy_header(data[1] if len(data) > 1 else data[0])
        fy_cols = [(ci, yr) for ci, yr in enumerate(fy_years) if yr is not None]
        if len(fy_cols) > len(best_fy_cols):
            best_table = data
            best_fy_cols = fy_cols

    if best_table is None or not best_fy_cols:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    f"no table with FY columns found on page {page_idx + 1}"
                ),
            )
        )
        return staging_rows, errors

    label_to_mapping: dict[str, RowMapping] = {}
    for row_prefix, slug, unit in row_mappings:
        label_to_mapping[row_prefix.lower()] = (row_prefix, slug, unit)

    for row in best_table[2:]:
        if not row or not row[0]:
            continue
        row_label = str(row[0]).strip().replace("\n", " ")
        row_label_lower = row_label.lower()

        matched_mapping: RowMapping | None = None
        for prefix_lower, mapping in label_to_mapping.items():
            if row_label_lower.startswith(prefix_lower):
                matched_mapping = mapping
                break

        if matched_mapping is None:
            continue

        _, slug, unit = matched_mapping
        for col_idx, ad_fy in best_fy_cols:
            if col_idx >= len(row):
                continue
            val = _parse_value(row[col_idx])
            if val is None:
                continue
            base = _build_base_row(ad_fy, pub_ad_fy_start)
            staging_rows.append(
                replace(
                    base,
                    indicator_slug_raw=slug,
                    value=val,
                    unit=unit,
                    parser_notes=table_note,
                )
            )

    if not staging_rows:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=f"no matching rows found in table near {anchor_text!r}",
            )
        )

    return staging_rows, errors


# ---------------------------------------------------------------------------
# Table definitions: (row_label_prefix, indicator_slug, unit)
# ---------------------------------------------------------------------------

_MACRO_ROWS: Final[list[RowMapping]] = [
    ("Gross Domestic Product (GDP)", "fcgo-macro-gdp-nominal-annual", "npr_million"),
    ("Gross National Income (GNI)", "fcgo-macro-gni-nominal-annual", "npr_million"),
    ("Gross National Disposable", "fcgo-macro-gndi-nominal-annual", "npr_million"),
    ("Final Consumption Expenditure", "fcgo-macro-consumption-pct-gdp-annual", "percent"),
    ("Gross Domestic Saving", "fcgo-macro-domestic-saving-pct-gdp-annual", "percent"),
    ("Gross National Saving", "fcgo-macro-national-saving-pct-gdp-annual", "percent"),
    ("Exports of Goods", "fcgo-macro-exports-pct-gdp-annual", "percent"),
    ("Imports of Goods", "fcgo-macro-imports-pct-gdp-annual", "percent"),
    ("Gross Fixed Capital Formation", "fcgo-macro-gfcf-pct-gdp-annual", "percent"),
    ("Resources Gap", "fcgo-macro-resources-gap-pct-gdp-annual", "percent"),
    ("Workers Remittances", "fcgo-macro-remittances-pct-gdp-annual", "percent"),
    ("Product Tax", "fcgo-macro-product-tax-pct-gdp-annual", "percent"),
    ("Total Tax", "fcgo-macro-total-tax-pct-gdp-annual", "percent"),
    ("Per capita GDP", "fcgo-macro-per-capita-gdp-annual", "npr"),
    ("Per capita GNI", "fcgo-macro-per-capita-gni-annual", "npr"),
    ("Per capita GNDI", "fcgo-macro-per-capita-gndi-annual", "npr"),
]

_BUDGET_RATIO_ROWS: Final[list[RowMapping]] = [
    ("Expenditure", "fcgo-budget-expenditure-pct-gdp-annual", "percent"),
    ("Recurrent", "fcgo-budget-recurrent-pct-gdp-annual", "percent"),
    ("Capital", "fcgo-budget-capital-pct-gdp-annual", "percent"),
    ("Financing", "fcgo-budget-financing-pct-gdp-annual", "percent"),
    ("Revenue", "fcgo-budget-revenue-pct-gdp-annual", "percent"),
    ("Foreign grant receipt", "fcgo-budget-foreign-grants-pct-gdp-annual", "percent"),
    ("Total Debt Received", "fcgo-budget-total-debt-received-pct-gdp-annual", "percent"),
    ("Domestic loan receipt", "fcgo-budget-domestic-loan-pct-gdp-annual", "percent"),
    ("Foreign loan receipt", "fcgo-budget-foreign-loan-pct-gdp-annual", "percent"),
    ("Total Outstanding Debt", "fcgo-budget-outstanding-debt-pct-gdp-annual", "percent"),
    ("Outstanding external debt", "fcgo-budget-outstanding-external-debt-pct-gdp-annual", "percent"),
    ("Outstanding domestic debt", "fcgo-budget-outstanding-domestic-debt-pct-gdp-annual", "percent"),
    ("Total Debt Servicing", "fcgo-budget-debt-servicing-pct-gdp-annual", "percent"),
    ("Re-payment of external debt", "fcgo-budget-external-debt-repayment-pct-gdp-annual", "percent"),
    ("Re-payment of domestic debt", "fcgo-budget-domestic-debt-repayment-pct-gdp-annual", "percent"),
    ("Total Investment", "fcgo-budget-total-investment-pct-gdp-annual", "percent"),
    ("Investment – share", "fcgo-budget-investment-share-pct-gdp-annual", "percent"),
    ("Investment – loan", "fcgo-budget-investment-loan-pct-gdp-annual", "percent"),
]

_COFOG_ROWS: Final[list[RowMapping]] = [
    ("General Public Services", "fcgo-cofog-general-public-services-pct-annual", "percent"),
    ("Defense", "fcgo-cofog-defence-pct-annual", "percent"),
    ("Public Order", "fcgo-cofog-public-order-safety-pct-annual", "percent"),
    ("Economic Affairs", "fcgo-cofog-economic-affairs-pct-annual", "percent"),
    ("Environmental", "fcgo-cofog-environmental-protection-pct-annual", "percent"),
    ("Housing", "fcgo-cofog-housing-community-pct-annual", "percent"),
    ("Health", "fcgo-cofog-health-pct-annual", "percent"),
    ("Recreation", "fcgo-cofog-recreation-culture-pct-annual", "percent"),
    ("Education", "fcgo-cofog-education-pct-annual", "percent"),
    ("Social Security", "fcgo-cofog-social-security-pct-annual", "percent"),
]

_DEBT_STOCK_ROWS: Final[list[RowMapping]] = [
    ("Domestic Loan", "fcgo-debt-domestic-outstanding-annual", "npr_million"),
    ("External Loan", "fcgo-debt-external-outstanding-annual", "npr_million"),
    ("Total", "fcgo-debt-total-outstanding-annual", "npr_million"),
]

_DEBT_RATIO_ROWS: Final[list[RowMapping]] = [
    ("Outstanding External Debt/Total Debt", "fcgo-debt-external-share-pct-annual", "percent"),
    ("Outstanding Domestic Debt/Total Debt", "fcgo-debt-domestic-share-pct-annual", "percent"),
    ("Total Outstanding Debt/GDP", "fcgo-debt-total-pct-gdp-annual", "percent"),
    ("Outstanding Domestic Debt/GDP", "fcgo-debt-domestic-pct-gdp-annual", "percent"),
    ("Outstanding External Debt/GDP", "fcgo-debt-external-pct-gdp-annual", "percent"),
    ("Debt Servicing/GDP", "fcgo-debt-servicing-pct-gdp-annual", "percent"),
    ("Debt Servicing/Revenue", "fcgo-debt-servicing-pct-revenue-annual", "percent"),
    ("Debt Servicing/Export", "fcgo-debt-servicing-pct-exports-annual", "percent"),
]


# Table anchor text → (row_mappings, parser_note)
_TABLE_SPECS: Final[
    list[tuple[str, list[RowMapping], str]]
] = [
    (
        "Highlights of Macro Economic Indicators",
        _MACRO_ROWS,
        "CFS Overview Table 28: macro indicators (CBS national accounts via FCGO)",
    ),
    (
        "Macro Level Budget Operation",
        _BUDGET_RATIO_ROWS,
        "CFS Overview Table 29: budget operations as % of GDP",
    ),
    (
        "COFOG-wise Expenditure In Percentage",
        _COFOG_ROWS,
        "CFS Overview Table 10: COFOG functional expenditure (% of total)",
    ),
    (
        "Table 16 : Outstanding Debt",
        _DEBT_STOCK_ROWS,
        "CFS Overview Table 16: outstanding government debt stock (NPR million)",
    ),
    (
        "Table 37: Debt Ratio",
        _DEBT_RATIO_ROWS,
        "CFS Overview Table 37: debt composition and sustainability ratios",
    ),
]


def extract_overview_tables(
    doc: pymupdf.Document,
    pub_ad_fy_start: int,
) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Extract indicators from all targeted overview tables.

    Args:
        doc: An open pymupdf Document.
        pub_ad_fy_start: The AD fiscal-year start of the edition being parsed
            (e.g. 2022 for the FY 2022/23 publication). Used to set the
            ``publication_date_ad`` on all rows.

    Returns:
        A tuple of (staging_rows, errors). Tables that cannot be located
        produce errors but do not block extraction from other tables.
    """
    all_rows: list[StagingRowDraft] = []
    all_errors: list[ParserError] = []

    for anchor, mappings, note in _TABLE_SPECS:
        rows, errors = _extract_from_table(doc, anchor, mappings, pub_ad_fy_start, note)
        all_rows.extend(rows)
        all_errors.extend(errors)

    return all_rows, all_errors
