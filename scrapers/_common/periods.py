"""Canonical period vocabulary mirror of src/lib/dates/* (TypeScript).

YEAR 1 SCOPE NOTE: This module does NOT do BS<->AD math. Mother's guidance
(see docs/tasks/worker-C-python-scrapers.md and docs/CALENDAR_AND_PERIODS.md
§"BS <-> AD Conversion"): the authoritative BS<->AD wrapper is the TS
`src/lib/dates/index.ts`. Python parsers use lightweight mid-month
approximations (15th of the corresponding AD month) and the validation layer
on the TS side refines them. DO NOT install a Python BS-AD library without
an ADR.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

# Canonical English transliteration; must match src/lib/dates/types.ts.
BsMonth = Literal[
    "Shrawan",
    "Bhadra",
    "Ashwin",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chait",
    "Baisakh",
    "Jestha",
    "Ashadh",
]

BS_MONTHS: tuple[BsMonth, ...] = (
    "Shrawan",
    "Bhadra",
    "Ashwin",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chait",
    "Baisakh",
    "Jestha",
    "Ashadh",
)

# July: BS months with AD month >= this belong to (bs_year - 57); below it
# they belong to (bs_year - 56). Module-level so ruff/PLR2004 stays happy.
_AD_YEAR_BREAK_MONTH = 7

# Approximate AD start-of-month integer (1-12) for each BS month.
# Used ONLY for mid-month placeholder timestamps. Off-by-one days are expected
# and explicitly handled by the validation layer.
_BS_MONTH_TO_AD_MONTH: dict[BsMonth, int] = {
    "Shrawan": 7,
    "Bhadra": 8,
    "Ashwin": 9,
    "Kartik": 10,
    "Mangsir": 11,
    "Poush": 12,
    "Magh": 1,
    "Falgun": 2,
    "Chait": 3,
    "Baisakh": 4,
    "Jestha": 5,
    "Ashadh": 6,
}


def fiscal_year_label(bs_start_year: int) -> str:
    """Render BS fiscal-year label as ``YYYY/YY``, e.g. ``2082/83``."""
    return f"{bs_start_year}/{(bs_start_year + 1) % 100:02d}"


def fiscal_year_ad_label(bs_start_year: int) -> str:
    """Approximate AD label for a BS fiscal year, e.g. BS 2082 starts in AD 2025."""
    ad_start = bs_start_year - 57
    return f"{ad_start}/{(ad_start + 1) % 100:02d}"


def mid_month_ad(bs_month: BsMonth, bs_year: int) -> datetime:
    """Return a UTC datetime at the 15th of the AD month that approximates
    mid-``bs_month`` ``bs_year``. Lightweight placeholder; refined downstream.
    """
    ad_month = _BS_MONTH_TO_AD_MONTH[bs_month]
    # BS year N starts in AD year (N - 57); months Shrawan..Poush map to that
    # AD year, Magh..Ashadh map to AD year + 1.
    ad_year = bs_year - 57 if ad_month >= _AD_YEAR_BREAK_MONTH else bs_year - 56
    return datetime(ad_year, ad_month, 15, tzinfo=UTC)


def nine_months_span_ad(bs_fy_start_year: int) -> tuple[datetime, datetime]:
    """AD span for the first nine BS months of a fiscal year (Shrawan..Chait).

    Returns (start_of_Shrawan_approx, end_of_Chait_approx). Approximate to the
    15th of the boundary months; tolerance is ±2 days at the validation layer.
    """
    start = mid_month_ad("Shrawan", bs_fy_start_year)
    end = mid_month_ad("Chait", bs_fy_start_year)
    return start, end
