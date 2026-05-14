"""NRB Banking & Financial Statistics monthly XLSX parser — v0.1.0.

Source: NRB Banking & Financial Statistics monthly publications. Each
snapshot XLSX contains 14 sheets (early files, BS 2078) or 25 sheets
(BS 2080+). In v0.1.0 we extract four headline sheets:

* **C4** — Major Financial Indicators (Pulse-grade ratios)
* **C5** — Statement of Assets and Liabilities (banking-sector balance sheet)
* **C6** — Profit and Loss Statement (profitability aggregates)
* **C7** — Statement of Loans and Advances (sector-wise lending — feeds the
  Vertical-16 "Collateral State" stream)

Sheets C8..C25 (per-bank breakdowns) are deferred to v0.2.0; see
``docs/tasks/`` for the follow-up brief.

Indicator-slug scheme
---------------------
Slugs are kebab-case and derived deterministically from the Excel label.
For C5/C6 where labels follow a section/sub-item hierarchy (e.g.
``CAPITAL FUND`` / ``a. Paid-up Capital``), we prepend the section slug
joined by ``--``::

    "capital-fund--paid-up-capital"
    "borrowings--nrb"
    "interest-expenses--deposit-liabilities--saving-a-c"

For C7 the sector labels are flat::

    "agricultural-and-forest-related"
    "construction"

For C4 the section letter ("A. Credit, Deposit Ratios (%)") becomes the
prefix::

    "credit-deposit-ratios--total-deposit-gdp"

Slug prefix per sheet
---------------------
The orchestrator embeds the sheet name when persisting; we therefore do
NOT prefix the slug with ``c5-`` etc. The combination of
``(source_sheet, indicator_slug, bank_class, period)`` is the unique
business key (mirrors the index on ``banking_sector_facts``).

Contract
--------
``parse(source_document_path, source_document_id) -> ParserResult`` —
returns a ``ParserResult`` whose ``staging_rows`` are
``StagingBfiRowDraft`` instances. The orchestrator serialises them to the
staging JSON shape documented in the worker brief.

Versioning
----------
Bump ``PARSER_VERSION`` on every behaviour change. v0.1.0 is the initial
import covering C4..C7.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import openpyxl

from _common.types import (
    BankClass,
    ParserError,
    ParserResult,
    StagingBfiRowDraft,
)

from ._filename import FilenameUnparseableError, parse_snapshot_filename
from ._periods import label_to_period, snapshot_period_ad
from ._sheets import (
    detect_c5like_layout,
    find_c4_columns,
    iter_c4_indicators,
    iter_c5like_indicators,
    sheet_to_rows,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "nrb-bfi-monthly"

# Confidence: NRB-published, machine-readable XLSX -> A.
_CONFIDENCE: Final[str] = "A"

# Sheets we parse in v0.1.0.
_C4_SHEET: Final[str] = "C4"
_C5LIKE_SHEETS: Final[tuple[str, ...]] = ("C5", "C6", "C7")


@dataclass(frozen=True)
class _SnapshotContext:
    """Per-snapshot resolved metadata (filename-derived)."""

    snapshot_period_bs_label: str    # "Saun 2082"
    snapshot_period_ad_start: datetime
    snapshot_period_ad_end: datetime
    bs_month: str
    bs_year: int
    fiscal_year_bs: str
    publication_date_ad: datetime
    publication_date_bs: str
    devanagari_in_labels: bool       # True if any Devanagari digit found


def _snapshot_context(path: Path) -> _SnapshotContext:
    """Build per-file metadata from the filename.

    Publication dates are placeholders (ad_start of the snapshot period +
    14 days). The TS validation layer refines them when the manual upload
    workflow records the actual publication date.
    """
    bs_month, bs_year = parse_snapshot_filename(path)
    ad_start, ad_end = snapshot_period_ad(bs_month, bs_year)
    # Publication ≈ ~6 weeks after the BS month closes, per NRB practice.
    publication = datetime(ad_end.year, ad_end.month, ad_end.day, tzinfo=UTC)
    # Cheap approximation; orchestrator overrides.
    publication = publication.replace(day=min(28, ad_end.day))
    fiscal_year_bs = _fiscal_year_for(bs_month, bs_year)
    return _SnapshotContext(
        snapshot_period_bs_label=f"{bs_month} {bs_year}",
        snapshot_period_ad_start=ad_start,
        snapshot_period_ad_end=ad_end,
        bs_month=bs_month,
        bs_year=bs_year,
        fiscal_year_bs=fiscal_year_bs,
        publication_date_ad=publication,
        publication_date_bs=f"{fiscal_year_bs} ({bs_month})",
        devanagari_in_labels=False,
    )


def _fiscal_year_for(bs_month: str, bs_year: int) -> str:
    """Return BS FY label that contains ``(bs_month, bs_year)``."""
    if bs_month in {"Magh", "Falgun", "Chait", "Baisakh", "Jestha", "Ashadh"}:
        fy_start = bs_year - 1
    else:
        fy_start = bs_year
    return f"{fy_start}/{(fy_start + 1) % 100:02d}"


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse a single NRB BFI XLSX into a ``ParserResult``.

    Arguments:
        source_document_path: filesystem path to the downloaded XLSX.
        source_document_id: opaque ID from ``source_documents``; threaded
            through but not embedded in rows.

    Returns:
        ``ParserResult`` with ``status``, ``staging_rows``
        (``StagingBfiRowDraft`` list), and structured errors.
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
        ctx = _snapshot_context(path)
    except FilenameUnparseableError as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="PeriodAmbiguous",
                    error_detail=str(exc),
                    source_excerpt=path.name,
                )
            ],
        )

    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except (OSError, ValueError, KeyError) as exc:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"xlsx open failed: {exc}",
                )
            ],
        )

    staging_rows: list[StagingBfiRowDraft] = []
    errors: list[ParserError] = []

    try:
        for sheet_name in (_C4_SHEET, *_C5LIKE_SHEETS):
            if sheet_name not in wb.sheetnames:
                errors.append(
                    ParserError(
                        error_class="ColumnMissing",
                        error_detail=f"sheet {sheet_name} not present in workbook",
                        source_excerpt=path.name,
                    )
                )
                continue
            ws = wb[sheet_name]
            rows = sheet_to_rows(ws)
            if sheet_name == _C4_SHEET:
                emitted, sheet_errors = _parse_c4(rows, ctx)
            else:
                emitted, sheet_errors = _parse_c5like(rows, sheet_name, ctx)
            staging_rows.extend(emitted)
            for err in sheet_errors:
                errors.append(
                    ParserError(
                        error_class=err.error_class,
                        error_detail=f"[{sheet_name}] {err.error_detail}",
                        source_excerpt=err.source_excerpt,
                    )
                )
    finally:
        wb.close()

    if not staging_rows:
        return ParserResult(
            status="failure",
            parser_version=PARSER_VERSION,
            errors=errors
            or [
                ParserError(
                    error_class="Other",
                    error_detail="no rows emitted from any sheet",
                )
            ],
        )

    status = "partial" if errors else "success"
    return ParserResult(
        status=status,  # type: ignore[arg-type]
        parser_version=PARSER_VERSION,
        staging_rows=staging_rows,  # type: ignore[arg-type]
        errors=errors,
    )


# ─── C4 ──────────────────────────────────────────────────────────────────


def _parse_c4(
    rows: list[list[object]],
    ctx: _SnapshotContext,
) -> tuple[list[StagingBfiRowDraft], list[ParserError]]:
    """Emit rows from sheet C4 (Major Financial Indicators).

    C4 has no time-series — only the latest snapshot column per
    bank-class. Each (indicator, bank_class) pair becomes one row keyed to
    the snapshot period.
    """
    out: list[StagingBfiRowDraft] = []
    errors: list[ParserError] = []
    located = find_c4_columns(rows)
    if located is None:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail="could not locate C4 bank-class header row",
            )
        )
        return out, errors
    col_map, label_col, header_row = located

    indicators = iter_c4_indicators(rows, col_map, label_col, header_row)
    # Unit detection for C4: it's a percentages/ratios + some rupee
    # absolute totals. Most rows are %; we default to "percent" and the
    # validation layer can override per-indicator.
    unit = "percent"

    for slug, values in indicators:
        for bank_class, value in values.items():
            if value is None:
                continue
            out.append(
                StagingBfiRowDraft(
                    source_sheet="C4",
                    indicator_slug=slug,
                    bank_class=bank_class,
                    bank_entity_slug=None,
                    value=value,
                    unit=unit,
                    reporting_period_type="monthly",
                    reporting_period_bs=ctx.snapshot_period_bs_label,
                    reporting_period_ad_start=ctx.snapshot_period_ad_start,
                    reporting_period_ad_end=ctx.snapshot_period_ad_end,
                    publication_date_ad=ctx.publication_date_ad,
                    publication_date_bs=ctx.publication_date_bs,
                    fiscal_year_bs=ctx.fiscal_year_bs,
                    confidence_grade_proposed="A",
                    parser_notes=None,
                )
            )
    return out, errors


# ─── C5 / C6 / C7 ────────────────────────────────────────────────────────


def _parse_c5like(
    rows: list[list[object]],
    sheet_name: str,
    ctx: _SnapshotContext,
) -> tuple[list[StagingBfiRowDraft], list[ParserError]]:
    out: list[StagingBfiRowDraft] = []
    errors: list[ParserError] = []

    layout = detect_c5like_layout(rows, sheet_name)
    if layout is None:
        errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=f"could not detect {sheet_name} layout",
            )
        )
        return out, errors

    indicators = iter_c5like_indicators(rows, layout)
    for slug, emissions in indicators:
        for bank_class, period, value in emissions:
            resolved = label_to_period(period.period_label, period.period_year)
            if resolved is None:
                errors.append(
                    ParserError(
                        error_class="PeriodAmbiguous",
                        error_detail=(
                            f"unparseable period label "
                            f"{period.period_label!r} {period.period_year}"
                        ),
                        source_excerpt=slug,
                    )
                )
                continue
            ad_start, ad_end, period_bs, fy_bs, _bs_m, _bs_y = resolved
            out.append(
                StagingBfiRowDraft(
                    source_sheet=sheet_name,
                    indicator_slug=slug,
                    bank_class=_normalise_bank_class(bank_class),
                    bank_entity_slug=None,
                    value=value,
                    unit=layout.unit,
                    reporting_period_type="monthly",
                    reporting_period_bs=period_bs,
                    reporting_period_ad_start=ad_start,
                    reporting_period_ad_end=ad_end,
                    publication_date_ad=ctx.publication_date_ad,
                    publication_date_bs=ctx.publication_date_bs,
                    fiscal_year_bs=fy_bs,
                    confidence_grade_proposed="A",
                    parser_notes=None,
                )
            )
    return out, errors


def _normalise_bank_class(value: str) -> BankClass:
    """Pin string -> BankClass literal. Kept for explicit narrowing.

    Detected values are already a ``BankClass`` literal at construction;
    this helper documents the invariant.
    """
    valid: set[str] = {
        "commercial",
        "development",
        "finance",
        "microfinance",
        "infrastructure",
        "system_total",
    }
    if value not in valid:
        raise ValueError(f"unexpected bank_class {value!r}")
    return value  # type: ignore[return-value]
