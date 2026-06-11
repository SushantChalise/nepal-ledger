"""DoFE Labour Migration monthly PDF parser — deterministic Python.

Source: Department of Foreign Employment (DoFE) monthly "Countrywise Labour
Approval" report — published via https://dofe.gov.np/api/category/monthly
(GIWMS API, JSON). Each monthly PDF is uploaded to giwmscdnone.gov.np.

Strategy:
    The PDF has a multi-page "Countrywise Labour Approval" table (typically
    pages 1–2) followed by District-wise and RA-wise breakdowns.  The
    table uses pdfplumber's automatic table extractor reliably: 7 column
    groups × 3 sub-columns (Male / Female / Total) + S.N. + Country = 23
    columns per row.

    Column mapping (0-indexed):
        0   S.N.
        1   Country
        2–4  Recruiting Agency  Male / Female / Total
        5–7  Individual-New     Male / Female / Total
        8–10 G-to-G             Male / Female / Total
        11–13 Individual-ReEntry Male / Female / Total
        14–16 Legalization       Male / Female / Total
        17–19 Total with ReEntry Male / Female / Total  ← PRIMARY metric
        20–22 Total without ReEntry Male / Female / Total

    We extract "Total with ReEntry" (cols 17–19) as it includes all
    approved departure categories.  The Grand Total row (S.N. == None /
    country == "Grand Total") is recorded with country slug "total".

    Only country-wise pages are parsed; district and RA pages are skipped.

Period detection:
    Title pattern: "Countrywise Labour Approval for <BS_Month>[ -]<BS_Year>"
    e.g. "Countrywise Labour Approval for Chaita- 2082"
         "Countrywise Labour Approval for Mangsir 2082"
    Parsed from the first page of each page group.

Known breakage modes:
    - New country added → no error; emitted as slug derived from name
    - Column count changes (layout shift) → ColumnMissing error
    - Grand Total row missing → totals row omitted, no parser error
    - Scanned image PDF (no text layer) → failure with EncodingError

Revision policy:
    DoFE uploads monthly; no revisions observed.  Download and re-parse
    if the file URL changes.  Version PARSER_VERSION on any behaviour change.

Versioning:
    Bump PARSER_VERSION on any behaviour change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pdfplumber

from _common.periods import (
    BsMonth,
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
SOURCE_ID: Final[str] = "dofe-labour-migration"

# ── Constants ─────────────────────────────────────────────────────────────────

# Expected column count for the country-wise table.
_EXPECTED_COLS: Final[int] = 23

# Index of "Total with ReEntry Total" column (male=17, female=18, total=19).
_COL_TOTAL_WITH_REENTRY_TOTAL: Final[int] = 19

# Publication lag: DoFE typically publishes within 30 days of month end.
_PUB_LAG_DAYS: Final[int] = 30

# ── Country slug mapping ──────────────────────────────────────────────────────

# Canonical slug for each country name variant found in DoFE tables.
# Keys are lowercase-stripped.  Unknown countries get auto-generated slugs.
COUNTRY_SLUGS: Final[dict[str, str]] = {
    "qatar": "qatar",
    "uae": "uae",
    "united arab emirates": "uae",
    "saudi arabia": "saudi-arabia",
    "malaysia": "malaysia",
    "kuwait": "kuwait",
    "bahrain": "bahrain",
    "oman": "oman",
    "republic of korea": "korea",
    "south korea": "korea",
    "korea": "korea",
    "japan": "japan",
    "israel": "israel",
    "australia": "australia",
    "canada": "canada",
    "united kingdom": "united-kingdom",
    "usa": "usa",
    "united states": "usa",
    "united states of america": "usa",
    "singapore": "singapore",
    "new zealand": "new-zealand",
    "china": "china",
    "india": "india",
    "turkey": "turkey",
    "romania": "romania",
    "cyprus": "cyprus",
    "maldives": "maldives",
    "mauritius": "mauritius",
    "portugal": "portugal",
    "malta": "malta",
    "republic of bulgaria": "bulgaria",
    "croatia": "croatia",
    "poland": "poland",
    "moldova": "moldova",
    "austria": "austria",
    "greece": "greece",
    "serbia": "serbia",
    "grand total": "total",
    "other countries": "other",
}

# ── BS month vocabulary ────────────────────────────────────────────────────────

# Canonical BS month names in fiscal-year order.
_FY_MONTHS: Final[tuple[BsMonth, ...]] = (
    "Shrawan", "Bhadra", "Ashwin", "Kartik", "Mangsir", "Poush",
    "Magh", "Falgun", "Chait", "Baisakh", "Jestha", "Ashadh",
)

# Map to 1-based FY position.
_BS_MONTH_FY_POS: Final[dict[str, int]] = {
    m.lower(): i + 1 for i, m in enumerate(_FY_MONTHS)
}

# Extra aliases (different romanisations found in DoFE documents).
_BS_MONTH_ALIASES: Final[dict[str, str]] = {
    "chaita": "Chait",
    "chait": "Chait",
    "chaitra": "Chait",
    "baisakh": "Baisakh",
    "baishakh": "Baisakh",
    "jestha": "Jestha",
    "jeshtha": "Jestha",
    "ashad": "Ashadh",
    "asadh": "Ashadh",
    "ashadh": "Ashadh",
    "shrawan": "Shrawan",
    "shravan": "Shrawan",
    "bhadra": "Bhadra",
    "bhadar": "Bhadra",
    "ashwin": "Ashwin",
    "asoj": "Ashwin",
    "kartik": "Kartik",
    "mangsir": "Mangsir",
    "mangshir": "Mangsir",
    "poush": "Poush",
    "push": "Poush",
    "magh": "Magh",
    "falgun": "Falgun",
    "phagun": "Falgun",
    "phalgum": "Falgun",
}

# Title pattern: "Countrywise Labour Approval for <BS_Month>[ -]<BS_Year>"
_TITLE_RE: Final[re.Pattern[str]] = re.compile(
    r"Countrywise\s+Labour\s+Approval\s+for\s+(\w+)\s*[-–]?\s*(\d{4})",
    re.IGNORECASE,
)


def _country_slug(country_name: str) -> str:
    """Map a raw country name to a canonical slug.

    Falls back to a lowercased-hyphenated version for unknown names.
    """
    key = country_name.strip().lower()
    if key in COUNTRY_SLUGS:
        return COUNTRY_SLUGS[key]
    # Auto-generate: lowercase, spaces → hyphens, strip non-alphanumeric-hyphen.
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return slug


def _indicator_slug(country_slug: str) -> str:
    """Compose the indicator slug from the country slug."""
    return f"dofe-departures-{country_slug}-monthly"


@dataclass(frozen=True)
class _PeriodInfo:
    bs_month: BsMonth
    bs_year: int
    bs_fy_start: int
    reporting_period_bs: str
    fiscal_year_bs: str
    fiscal_year_ad_label: str


def _detect_period(
    text: str, errors: list[ParserError]
) -> _PeriodInfo | None:
    """Extract the BS month/year from the countrywise title line."""
    m = _TITLE_RE.search(text[:3000])
    if not m:
        errors.append(ParserError(
            error_class="PeriodAmbiguous",
            error_detail=(
                "title pattern not found in first 3000 chars — "
                "'Countrywise Labour Approval for <Month> <Year>' missing"
            ),
        ))
        return None

    raw_month = m.group(1).strip().lower()
    raw_year = m.group(2).strip()

    # Resolve BS month.
    canonical = _BS_MONTH_ALIASES.get(raw_month)
    if canonical is None:
        # Try direct match against canonical names.
        for bm in _FY_MONTHS:
            if bm.lower() == raw_month:
                canonical = bm
                break
    if canonical is None:
        errors.append(ParserError(
            error_class="PeriodAmbiguous",
            error_detail=f"unrecognised BS month in title: {m.group(1)!r}",
            source_excerpt=m.group(0),
        ))
        return None

    bs_month: BsMonth = canonical  # type: ignore[assignment]
    bs_year = int(raw_year)

    fy_pos = _BS_MONTH_FY_POS[bs_month.lower()]
    # FY starts in Shrawan (pos 1) of bs_fy_start; months pos ≤ 9 are in the
    # first calendar year, months pos ≥ 10 cross into bs_fy_start + 1.
    bs_fy_start = bs_year if fy_pos <= 9 else bs_year - 1

    period_bs = f"{bs_year}/{(bs_year + 1) % 100:02d} {bs_month}"

    return _PeriodInfo(
        bs_month=bs_month,
        bs_year=bs_year,
        bs_fy_start=bs_fy_start,
        reporting_period_bs=period_bs,
        fiscal_year_bs=fiscal_year_label(bs_fy_start),
        fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
    )


def _is_country_page(page_text: str) -> bool:
    """True iff this page contains a countrywise table."""
    return bool(_TITLE_RE.search(page_text[:3000]))


def _parse_country_rows(
    table: list[list[str | None]],
) -> list[tuple[str, int]]:
    """Extract (country_name, total_with_reentry_total) from a table.

    Skips header rows (S.N. == "S.N.") and blank rows.
    Returns Grand Total as country_name="Grand Total".
    """
    rows: list[tuple[str, int]] = []
    for row in table:
        if not row or len(row) < _EXPECTED_COLS:
            continue
        sn = row[0]
        country = row[1]
        if country is None:
            continue
        country = str(country).strip()
        if country == "Country" or country == "":
            continue

        total_str = row[_COL_TOTAL_WITH_REENTRY_TOTAL]
        if total_str is None:
            continue
        total_str = str(total_str).strip()
        if not total_str.isdigit():
            continue

        rows.append((country, int(total_str)))
    return rows


def _extract_all_country_rows(
    pdf: pdfplumber.PDF,
    errors: list[ParserError],
) -> list[tuple[str, int]]:
    """Iterate pages, collect rows from countrywise tables only."""
    all_rows: list[tuple[str, int]] = []
    found_country_page = False

    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if not _is_country_page(text):
            if found_country_page:
                # Past the country-section; stop.
                break
            continue

        found_country_page = True
        tables = page.extract_tables()
        if not tables:
            errors.append(ParserError(
                error_class="PageLayoutChanged",
                error_detail=f"page {i + 1}: countrywise header present but no table extracted",
            ))
            continue

        table = tables[0]
        # Validate column count from the header row.
        # pdfplumber occasionally adds a trailing None column on continuation
        # pages (observed: Mangsir 2082 page 2 → 24 cols). Tolerate extra
        # trailing columns; only fail if fewer than expected.
        for row in table:
            if row and row[0] == "S.N.":
                if len(row) < _EXPECTED_COLS:
                    errors.append(ParserError(
                        error_class="ColumnMissing",
                        error_detail=(
                            f"page {i + 1}: expected at least {_EXPECTED_COLS} columns, "
                            f"got {len(row)}"
                        ),
                        source_excerpt=str(row[:6]),
                    ))
                break

        all_rows.extend(_parse_country_rows(table))

    return all_rows


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse one DoFE monthly country-wise labour approval PDF.

    Arguments:
        source_document_path: filesystem path to the downloaded PDF.
        source_document_id: opaque FK from ``source_documents``; threaded
            through for orchestrator symmetry.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``, ``errors``.
    """
    _ = source_document_id

    path = Path(source_document_path)
    if not path.exists():
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[ParserError(
                error_class="Other",
                error_detail=f"source file not found: {path}",
            )],
        )

    errors: list[ParserError] = []

    try:
        pdf = pdfplumber.open(str(path))
    except (OSError, ValueError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[ParserError(
                error_class="EncodingError",
                error_detail=f"pdf open failed: {exc}",
            )],
        )

    with pdf:
        # Detect period from first page text.
        first_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
        period = _detect_period(first_text, errors)
        if period is None:
            return ParserResult(
                status="failure",
                parser_version=PARSER_VERSION,
                errors=errors,
            )

        country_rows = _extract_all_country_rows(pdf, errors)

    if not country_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors or [ParserError(
                error_class="PageLayoutChanged",
                error_detail="no country rows extracted from any page",
            )],
        )

    # Build period timestamps.
    period_mid = mid_month_ad(period.bs_month, period.bs_year)
    pub_ad = period_mid + timedelta(days=_PUB_LAG_DAYS)
    pub_bs = f"~{period.fiscal_year_bs} (heuristic)"

    base = StagingRowDraft(
        indicator_slug_raw="",
        value=0.0,
        unit="count",
        reporting_period_type="monthly",
        reporting_period_bs=period.reporting_period_bs,
        reporting_period_ad_start=period_mid,
        reporting_period_ad_end=period_mid,
        publication_date_ad=pub_ad,
        publication_date_bs=pub_bs,
        fiscal_year_bs=period.fiscal_year_bs,
        fiscal_year_ad_label=period.fiscal_year_ad_label,
        confidence_grade_proposed="A",
        parser_notes=None,
    )

    staging_rows: list[StagingRowDraft] = []
    seen_slugs: set[str] = set()

    for country_name, total in country_rows:
        slug = _country_slug(country_name)
        ind_slug = _indicator_slug(slug)

        # De-duplicate (multi-page tables repeat some rows).
        if ind_slug in seen_slugs:
            continue
        seen_slugs.add(ind_slug)

        notes: str | None = None
        if slug not in COUNTRY_SLUGS.values():
            notes = f"auto-generated slug for unknown country: {country_name!r}"

        row = replace(
            base,
            indicator_slug_raw=ind_slug,
            value=float(total),
            parser_notes=notes,
        )
        staging_rows.append(row)

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors or [ParserError(
                error_class="PageLayoutChanged",
                error_detail="no staging rows built",
            )],
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
    Writes JSON to stdout.
    Exit codes:
      0: parser ran (status may still be 'failure'; consumer reads stdout)
      2: usage error
      1: catastrophic crash (let Python propagate)
    """
    import json
    import sys
    from dataclasses import asdict

    if len(sys.argv) != 3:
        sys.stderr.write(
            "usage: parser.py <source_document_path> <source_document_id>\n"
        )
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