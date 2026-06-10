"""NSO NLSS-IV Summary Report parser — deterministic Python.

Source: National Statistics Office, **Nepal Living Standards Survey IV (NLSS-IV)
2022-23 Summary Report**. Published February 2024.
Official portal: https://data.nsonepal.gov.np/dataset/poverty-status-2023
Mirror PDF:     https://giwmscdnone.gov.np/media/app/public/36/posts/1707800524_89.pdf
Archive path:   Financial Data/nso_nlss/NLSS_IV_Summary_2022-23.pdf
Source ID:      ``nlss-survey``

Strategy:
    The NLSS-IV Summary Report has a clean Latin-script text layer — no OCR is
    needed. ``pdfplumber.extract_tables()`` returns empty for the data pages in
    this PDF (values are typeset as fixed-width aligned text, not PDF table
    objects). The parser uses ``page.extract_text()`` and section-anchored regex
    patterns to extract values from the full text stream.

    Table A4 stores the Gini index on the 0–100 scale; this parser divides by
    100 before emitting so every ``nlss-gini-consumption`` row is on the 0–1
    ``ratio`` scale consistent with Table 9 (which uses the 0–1 form directly).

Target indicators (v0.1.0):

    NLSS-IV 2022/23 (14 rows):
        Poverty headcount (percent):
            - nlss-poverty-headcount-national      20.27
            - nlss-poverty-headcount-urban         18.34
            - nlss-poverty-headcount-rural         24.66
            - nlss-poverty-headcount-koshi         17.19
            - nlss-poverty-headcount-madhesh       22.53
            - nlss-poverty-headcount-bagmati       12.59
            - nlss-poverty-headcount-gandaki       11.88
            - nlss-poverty-headcount-lumbini       24.35
            - nlss-poverty-headcount-karnali       26.69
            - nlss-poverty-headcount-sudurpaschim  34.16
        Welfare aggregates:
            - nlss-per-capita-consumption-annual   130853 (npr)
            - nlss-gini-consumption                0.300  (ratio)
            - nlss-food-share-consumption          53.0   (percent)
            - nlss-non-food-share-consumption      47.0   (percent)

    NLSS-III 2010/11 comparison values (6 rows, from report's own trend tables):
        - nlss-poverty-headcount-national  25.16
        - nlss-poverty-headcount-urban     15.46
        - nlss-poverty-headcount-rural     27.43
        - nlss-gini-consumption            0.328
        - nlss-food-share-consumption      62.0
        - nlss-non-food-share-consumption  38.0

Period dating:
    NLSS-IV survey year: AD 2022/23 = BS FY 2079/80
      period_start = mid-Shrawan 2079 (≈ 2022-07-15)
      period_end   = mid-Ashadh  2079 (≈ 2023-06-15)

    NLSS-III survey year: AD 2010/11 = BS FY 2067/68
      period_start = mid-Shrawan 2067 (≈ 2010-07-15)
      period_end   = mid-Ashadh  2067 (≈ 2011-06-15)

Confidence: ``A`` — primary NSO published survey report, official poverty line.

Versioning: bump PARSER_VERSION on any behaviour change.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pdfplumber

from _common.periods import (
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
)
from _common.types import (
    ParserError,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "nlss-survey"

# ── Survey-year constants ────────────────────────────────────────────────────

# NLSS-IV: AD 2022/23 = BS FY 2079/80 (Shrawan 2079 ≈ July 2022)
_BS_FY_NLSS4: Final[int] = 2079

# NLSS-III: AD 2010/11 = BS FY 2067/68 (Shrawan 2067 ≈ July 2010)
_BS_FY_NLSS3: Final[int] = 2067

# Publication anchor for the summary report (NSO, February 2024)
_PUBLICATION_DATE_AD: Final[datetime] = datetime(2024, 2, 15, tzinfo=UTC)
_PUBLICATION_DATE_BS: Final[str] = "2080 Magh 15"

# ── Section-anchor regexes ───────────────────────────────────────────────────

# Figure 1: "Figure 1. Average annual per capita nominal consumption expenditures,
#             by analytical domain, NLSS-IV" (page 13 of the summary PDF)
_FIG1_ANCHOR_RE: Final = re.compile(
    r"Figure\s+1\.\s+Average\s+annual\s+per\s+capita\s+nominal\s+consumption",
    re.IGNORECASE,
)
# The NEPAL row in Figure 1; value has no thousands separator in this edition.
_FIG1_NEPAL_RE: Final = re.compile(r"\bNEPAL\s+([\d]+)\b")

# Figure 2: "Figure 2. Food and non-food share in annual adjusted per person
#             consumption expenditure" (page 16).
# Extracts all four percentage values that follow. The four values always form
# two complementary pairs (each pair sums to 100): {62,38} = NLSS-III and
# {53,47} = NLSS-IV. The pairing is validated at runtime; mismatching emits a
# typed error rather than silently emitting wrong data.
_FIG2_ANCHOR_RE: Final = re.compile(
    r"Figure\s+2\.\s+Food\s+and\s+non-food\s+share",
    re.IGNORECASE,
)
_PCT_VALUE_RE: Final = re.compile(r"(\d+)%")

# Table 9: "Table 9. Poverty profile of Nepal in 2022-23" (page 21).
# Rows: "Nepal 20.27 4.52 1.48 0.300", "Urban 18.34 ...", "Rural 24.66 ..."
_TBL9_ANCHOR_RE: Final = re.compile(r"Table\s+9\.\s+Poverty\s+profile", re.IGNORECASE)
# Captures headcount (group 1) and Gini (group 2) from the Nepal row.
# Gini is in 0–1 form in Table 9 (e.g. 0.300).
_TBL9_NEPAL_RE: Final = re.compile(
    r"^Nepal\s+([\d.]+)\s+[\d.]+\s+[\d.]+\s+(0\.\d+)", re.MULTILINE
)
_TBL9_URBAN_RE: Final = re.compile(r"^Urban\s+([\d.]+)\s+", re.MULTILINE)
_TBL9_RURAL_RE: Final = re.compile(r"^Rural\s+([\d.]+)\s+", re.MULTILINE)

# Table 11: "Table 11. Provincial poverty, 2022-23" (page 22).
# Row example: "Koshi 17.19 3.84 1.25 13.80 16.26"
_TBL11_ANCHOR_RE: Final = re.compile(r"Table\s+11\.\s+Provincial\s+poverty", re.IGNORECASE)
_PROVINCE_ROW_RE: Final = re.compile(
    r"^(Koshi|Madhesh|Bagmati|Gandaki|Lumbini|Karnali|Sudurpaschim)\s+([\d.]+)\s+",
    re.MULTILINE,
)

# Table A1: "Table A1: Poverty headcount, First Survey 1995-96 to Fourth Survey 2022-23"
# Columns in order: 1995-96 | 2003-04 | 2010-11 | 2022-23
# We capture the NLSS-III value (group 1) and NLSS-IV value (group 2).
_TBLA1_ANCHOR_RE: Final = re.compile(r"Table\s+A1:\s+Poverty\s+headcount", re.IGNORECASE)
_TBLA1_NEPAL_RE: Final = re.compile(
    r"^Nepal\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)", re.MULTILINE
)
_TBLA1_URBAN_RE: Final = re.compile(
    r"^Urban\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)", re.MULTILINE
)
_TBLA1_RURAL_RE: Final = re.compile(
    r"^Rural\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)", re.MULTILINE
)

# Table A4: "Table A4: Gini index, 1995-96 to 2022-23" (page 27).
# Values on 0–100 scale; divide by 100 before emitting.
# Row examples: "Third Survey (2010-11) 32.8 35.3 31.1" (col 0 = Nepal)
#               "Fourth Survey (2022-23) 30.0 30.3 28.7"
_TBLA4_ANCHOR_RE: Final = re.compile(r"Table\s+A4:\s+Gini\s+index", re.IGNORECASE)
_TBLA4_NLSS3_RE: Final = re.compile(
    r"Third\s+Survey[^)]*\)\s+([\d.]+)\s+", re.IGNORECASE
)
_TBLA4_NLSS4_RE: Final = re.compile(
    r"Fourth\s+Survey[^)]*\)\s+([\d.]+)\s+", re.IGNORECASE
)

# Province-to-slug mapping (case-insensitive match on first token of row label).
_PROVINCE_SLUGS: Final[dict[str, str]] = {
    "koshi": "nlss-poverty-headcount-koshi",
    "madhesh": "nlss-poverty-headcount-madhesh",
    "bagmati": "nlss-poverty-headcount-bagmati",
    "gandaki": "nlss-poverty-headcount-gandaki",
    "lumbini": "nlss-poverty-headcount-lumbini",
    "karnali": "nlss-poverty-headcount-karnali",
    "sudurpaschim": "nlss-poverty-headcount-sudurpaschim",
}


# ── Period helpers ───────────────────────────────────────────────────────────


def _nlss_period(bs_fy_start: int) -> tuple[datetime, datetime]:
    """Return (period_start, period_end) for a BS fiscal-year start year.

    NLSS survey spans the full fiscal year: mid-Shrawan .. mid-Ashadh.
    Period helpers use the 15th of the approximate AD month (±2 day tolerance
    on the validation side).
    """
    return mid_month_ad("Shrawan", bs_fy_start), mid_month_ad("Ashadh", bs_fy_start)


def _base_row(bs_fy_start: int) -> StagingRowDraft:
    """Construct the shared StagingRowDraft fields for a survey round."""
    period_start, period_end = _nlss_period(bs_fy_start)
    return StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="percent",
        reporting_period_type="annual",
        reporting_period_bs=f"FY {fiscal_year_label(bs_fy_start)}",
        reporting_period_ad_start=period_start,
        reporting_period_ad_end=period_end,
        publication_date_ad=_PUBLICATION_DATE_AD,
        publication_date_bs=_PUBLICATION_DATE_BS,
        fiscal_year_bs=fiscal_year_label(bs_fy_start),
        fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        confidence_grade_proposed="A",
        parser_notes=None,
    )


# ── Section extractors ───────────────────────────────────────────────────────


def _extract_percapita(text: str) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Figure 1: national average annual per-capita consumption (NPR)."""
    if not _FIG1_ANCHOR_RE.search(text):
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Figure 1 caption not found — per-capita indicator skipped",
            )
        ]
    m = _FIG1_NEPAL_RE.search(text)
    if not m:
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="NEPAL row not found in Figure 1 — per-capita indicator skipped",
            )
        ]
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return [], [
            ParserError(
                error_class="ValueUnparseable",
                error_detail=f"Figure 1 NEPAL value unparseable: {m.group(1)!r}",
                source_excerpt=m.group(0),
            )
        ]
    row = replace(
        _base_row(_BS_FY_NLSS4),
        indicator_slug_raw="nlss-per-capita-consumption-annual",
        value=value,
        unit="npr",
        parser_notes="Figure 1; national average annual nominal per-capita consumption, updated 2022-23 methodology",
    )
    return [row], []


def _extract_food_shares(text: str) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Figure 2: national food and non-food shares (percent) for NLSS-IV and NLSS-III.

    Figure 2 embeds four percentage values in text order: 62, 53, 47, 38 (the
    layout places the NLSS-III food bar above NLSS-IV food bar, then NLSS-IV
    non-food above NLSS-III non-food, by visual height). The pairs that sum to
    100 identify the two rounds:
        NLSS-III: 62 + 38 = 100  (food=62, non-food=38)
        NLSS-IV : 53 + 47 = 100  (food=53, non-food=47)
    A checksum validates pairing before emitting; mismatch → typed error.
    """
    m_anchor = _FIG2_ANCHOR_RE.search(text)
    if not m_anchor:
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Figure 2 caption not found — food-share indicators skipped",
            )
        ]
    # Look for 4 percentages within ~200 chars after the anchor
    window = text[m_anchor.start() : m_anchor.start() + 300]
    pcts = _PCT_VALUE_RE.findall(window)
    if len(pcts) < 4:
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    f"Figure 2: expected 4 percentage values, found {len(pcts)} "
                    f"in the 300-char window after caption"
                ),
                source_excerpt=window[:200],
            )
        ]
    try:
        vals = [int(p) for p in pcts[:4]]
    except ValueError:
        return [], [
            ParserError(
                error_class="ValueUnparseable",
                error_detail=f"Figure 2: could not parse percentage values: {pcts[:4]}",
            )
        ]

    # Identify complementary pairs (each pair sums to 100)
    pair_a = (vals[0], vals[3])  # NLSS-III pair by positional convention
    pair_b = (vals[1], vals[2])  # NLSS-IV pair
    if pair_a[0] + pair_a[1] != 100 or pair_b[0] + pair_b[1] != 100:
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    f"Figure 2: complementary-pairs checksum failed; "
                    f"expected each pair to sum to 100, got "
                    f"pair_a={pair_a} (sum={sum(pair_a)}), "
                    f"pair_b={pair_b} (sum={sum(pair_b)}). "
                    f"Raw values: {vals[:4]}"
                ),
            )
        ]

    # NLSS-IV: food share = max of pair_b, non-food = min
    nlss4_food = float(max(pair_b))
    nlss4_nonfood = float(min(pair_b))
    # NLSS-III: food share = max of pair_a, non-food = min
    nlss3_food = float(max(pair_a))
    nlss3_nonfood = float(min(pair_a))

    note_fig2 = "Figure 2; comparable-methodology adjusted (2022 methodology applied to 2011 for comparability)"

    rows = [
        replace(
            _base_row(_BS_FY_NLSS4),
            indicator_slug_raw="nlss-food-share-consumption",
            value=nlss4_food,
            unit="percent",
            parser_notes="Figure 2 (NLSS-IV 2022/23); " + note_fig2,
        ),
        replace(
            _base_row(_BS_FY_NLSS4),
            indicator_slug_raw="nlss-non-food-share-consumption",
            value=nlss4_nonfood,
            unit="percent",
            parser_notes="Figure 2 (NLSS-IV 2022/23); " + note_fig2,
        ),
        replace(
            _base_row(_BS_FY_NLSS3),
            indicator_slug_raw="nlss-food-share-consumption",
            value=nlss3_food,
            unit="percent",
            parser_notes="Figure 2 (NLSS-III 2010/11 comparable); " + note_fig2,
        ),
        replace(
            _base_row(_BS_FY_NLSS3),
            indicator_slug_raw="nlss-non-food-share-consumption",
            value=nlss3_nonfood,
            unit="percent",
            parser_notes="Figure 2 (NLSS-III 2010/11 comparable); " + note_fig2,
        ),
    ]
    return rows, []


def _extract_table9(text: str) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Table 9: national/urban/rural poverty headcount + national Gini (NLSS-IV)."""
    if not _TBL9_ANCHOR_RE.search(text):
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Table 9 caption not found — national/urban/rural headcount + Gini skipped",
            )
        ]

    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    base = _base_row(_BS_FY_NLSS4)

    # Nepal row: headcount (group 1) + Gini in 0-1 form (group 2)
    m = _TBL9_NEPAL_RE.search(text)
    if m:
        try:
            rows.append(
                replace(
                    base,
                    indicator_slug_raw="nlss-poverty-headcount-national",
                    value=float(m.group(1)),
                    parser_notes="Table 9 (NLSS-IV); national poverty headcount rate",
                )
            )
            rows.append(
                replace(
                    base,
                    indicator_slug_raw="nlss-gini-consumption",
                    value=float(m.group(2)),
                    unit="ratio",
                    parser_notes="Table 9 (NLSS-IV); Gini index of per-capita consumption (0-1 scale)",
                )
            )
        except ValueError as exc:
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=f"Table 9 Nepal row parse error: {exc}",
                    source_excerpt=m.group(0),
                )
            )
    else:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Table 9: Nepal row not found",
            )
        )

    for label, slug, pat in (
        ("Urban", "nlss-poverty-headcount-urban", _TBL9_URBAN_RE),
        ("Rural", "nlss-poverty-headcount-rural", _TBL9_RURAL_RE),
    ):
        mu = pat.search(text)
        if mu:
            try:
                rows.append(
                    replace(
                        base,
                        indicator_slug_raw=slug,
                        value=float(mu.group(1)),
                        parser_notes=f"Table 9 (NLSS-IV); {label.lower()} poverty headcount rate",
                    )
                )
            except ValueError as exc:
                errors.append(
                    ParserError(
                        error_class="ValueUnparseable",
                        error_detail=f"Table 9 {label} row parse error: {exc}",
                        source_excerpt=mu.group(0),
                    )
                )
        else:
            errors.append(
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail=f"Table 9: {label} row not found",
                )
            )

    return rows, errors


def _extract_table11(text: str) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Table 11: provincial poverty headcounts (NLSS-IV)."""
    if not _TBL11_ANCHOR_RE.search(text):
        return [], [
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Table 11 caption not found — provincial headcounts skipped",
            )
        ]

    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []
    base = _base_row(_BS_FY_NLSS4)

    for m in _PROVINCE_ROW_RE.finditer(text):
        province_key = m.group(1).lower()
        slug = _PROVINCE_SLUGS.get(province_key)
        if slug is None:
            continue
        try:
            rows.append(
                replace(
                    base,
                    indicator_slug_raw=slug,
                    value=float(m.group(2)),
                    parser_notes=f"Table 11 (NLSS-IV); {m.group(1)} province poverty headcount rate",
                )
            )
        except ValueError as exc:
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=f"Table 11 {m.group(1)} row parse error: {exc}",
                    source_excerpt=m.group(0),
                )
            )

    # Confirm all 7 provinces emitted
    emitted = {r.indicator_slug_raw for r in rows}
    expected = set(_PROVINCE_SLUGS.values())
    for missing in expected - emitted:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=f"Table 11: province row for slug {missing!r} not found",
            )
        )

    return rows, errors


def _extract_annex_a1(text: str) -> tuple[list[StagingRowDraft], list[ParserError]]:
    """Table A1: historical poverty headcounts — emits NLSS-III (2010/11) rows.

    Table A4 (on the same page) is also parsed for the NLSS-III Gini comparison.
    """
    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    # ── Table A1: headcount trend ─────────────────────────────────────────────
    m_a1_anchor = _TBLA1_ANCHOR_RE.search(text)
    if not m_a1_anchor:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Table A1 caption not found — NLSS-III headcount trend rows skipped",
            )
        )
    else:
        # Slice to text starting at the Table A1 anchor so we don't accidentally
        # match Table 9's Nepal/Urban/Rural rows (which appear earlier in the
        # page-concatenated stream and have identical first-column labels).
        a1_section = text[m_a1_anchor.start():]
        base3 = _base_row(_BS_FY_NLSS3)
        for label, slug, pat in (
            ("Nepal", "nlss-poverty-headcount-national", _TBLA1_NEPAL_RE),
            ("Urban", "nlss-poverty-headcount-urban", _TBLA1_URBAN_RE),
            ("Rural", "nlss-poverty-headcount-rural", _TBLA1_RURAL_RE),
        ):
            m = pat.search(a1_section)
            if m:
                try:
                    rows.append(
                        replace(
                            base3,
                            indicator_slug_raw=slug,
                            value=float(m.group(1)),  # group 1 = 2010-11 column
                            parser_notes=f"Table A1 (NLSS-III 2010/11); {label.lower()} poverty headcount rate",
                        )
                    )
                except ValueError as exc:
                    errors.append(
                        ParserError(
                            error_class="ValueUnparseable",
                            error_detail=f"Table A1 {label} row parse error: {exc}",
                            source_excerpt=m.group(0),
                        )
                    )
            else:
                errors.append(
                    ParserError(
                        error_class="PageLayoutChanged",
                        error_detail=f"Table A1: {label} row not found",
                    )
                )

    # ── Table A4: Gini index history ───────────────────────────────────────────
    if not _TBLA4_ANCHOR_RE.search(text):
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="Table A4 caption not found — NLSS-III Gini comparison row skipped",
            )
        )
    else:
        for survey_label, bs_fy, pat in (
            ("NLSS-III", _BS_FY_NLSS3, _TBLA4_NLSS3_RE),
        ):
            m = pat.search(text)
            if m:
                try:
                    # Table A4 values are on the 0–100 scale; convert to 0–1 ratio.
                    gini_ratio = float(m.group(1)) / 100.0
                    rows.append(
                        replace(
                            _base_row(bs_fy),
                            indicator_slug_raw="nlss-gini-consumption",
                            value=gini_ratio,
                            unit="ratio",
                            parser_notes=(
                                f"Table A4 ({survey_label}); Gini index of per-capita consumption "
                                f"(0–100 scale in source, divided by 100 → 0–1 ratio)"
                            ),
                        )
                    )
                except ValueError as exc:
                    errors.append(
                        ParserError(
                            error_class="ValueUnparseable",
                            error_detail=f"Table A4 {survey_label} Gini parse error: {exc}",
                            source_excerpt=m.group(0),
                        )
                    )
            else:
                errors.append(
                    ParserError(
                        error_class="PageLayoutChanged",
                        error_detail=f"Table A4: {survey_label} row not found",
                    )
                )

    return rows, errors


# ── PDF reading ──────────────────────────────────────────────────────────────


def _extract_pdf_text(path: Path) -> str:
    """Concatenate all page texts from a PDF via pdfplumber."""
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


# ── Public API ───────────────────────────────────────────────────────────────


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one NLSS-IV Summary Report PDF; emit welfare indicators.

    Emits 20 rows when the full report is supplied:
        14 NLSS-IV rows (indicators listed in module docstring §"NLSS-IV")
         6 NLSS-III comparison rows (national/urban/rural headcount + Gini +
           food/non-food shares)

    When only the 5-page test fixture is supplied (pages 13, 16, 21, 22, 27 of
    the original), the same 20 rows are produced because all five extractors
    find their anchors in those pages.

    Arguments:
        source_document_path: filesystem path to the PDF.
        source_document_id:   opaque ID from ``source_documents``; threaded
                              through for orchestrator-contract symmetry.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``, ``errors``.
    """
    _ = source_document_id

    path = Path(source_document_path)
    if not path.exists():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"source file not found: {path}",
                )
            ],
        )

    try:
        text = _extract_pdf_text(path)
    except (OSError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdfplumber failed to read {path.name}: {exc}",
                )
            ],
        )

    if not text.strip():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail="PDF yielded no text — possible image-only scan",
                )
            ],
        )

    staging_rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for extractor in (
        _extract_percapita,
        _extract_food_shares,
        _extract_table9,
        _extract_table11,
        _extract_annex_a1,
    ):
        section_rows, section_errors = extractor(text)
        staging_rows.extend(section_rows)
        errors.extend(section_errors)

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors
            or [
                ParserError(
                    error_class="PageLayoutChanged",
                    error_detail="No indicators extracted — all section anchors failed",
                )
            ],
        )

    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,
        errors=errors,
    )


def _main() -> None:
    """CLI entrypoint used by the Node ingestion orchestrator.

    Argv: ``parser.py <source_document_path> <source_document_id>``.
    Writes JSON to stdout. Exit codes:
      0 — parser ran (status may be 'failure'/'partial'; consumer reads stdout)
      2 — usage error
      1 — catastrophic crash (let Python propagate)
    """
    import json
    import sys
    from dataclasses import asdict

    if len(sys.argv) != 3:  # noqa: PLR2004
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    payload = asdict(result)
    for row in payload.get("staging_rows", []):
        for key in (
            "reporting_period_ad_start",
            "reporting_period_ad_end",
            "publication_date_ad",
        ):
            val = row.get(key)
            if isinstance(val, datetime):
                row[key] = val.isoformat()
    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    _main()
