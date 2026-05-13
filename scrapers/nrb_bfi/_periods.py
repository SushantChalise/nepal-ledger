"""Period-column -> (BS label, AD start/end) resolution for BFI snapshots.

NRB BFI snapshots tag period columns with English mid-month labels such as
``Mid-July 2025`` or ``Mid-Aug 2025``. By NRB convention this is the
snapshot taken AT mid-{month} — i.e. the cumulative position at roughly the
15th of that AD month, which itself sits ~one day before the BS month-end.

For staging-data purposes we follow ``_common.periods.mid_month_ad``: emit
``reporting_period_ad_end`` = AD-15 of the labelled month. The reporting
period start is the previous mid-month (so a "Mid-Aug 2025" snapshot covers
Mid-July 2025 -> Mid-Aug 2025).

Mapping the AD mid-month label back to a BS month/year for storage uses the
inverse of ``_common.periods._BS_MONTH_TO_AD_MONTH`` plus the AD year, with
the same July break used by that module.
"""

from __future__ import annotations

import calendar
import re
from datetime import UTC, datetime
from typing import Final

from _common.periods import BS_MONTHS, BsMonth

# Mid-month abbreviation (from the XLSX header) -> (ad_month_int, BS month)
_LABEL_TO_AD_MONTH: Final[dict[str, int]] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

# AD month integer -> BS month that **ends** in that AD month.
# Mid-July 2025 is the boundary between Ashadh 2082 and Shrawan 2082 — NRB
# uses it as the end-of-FY snapshot label for Ashadh.
_AD_MONTH_TO_BS_MONTH: Final[dict[int, BsMonth]] = {
    7: "Ashadh",   # Mid-July -> end of Ashadh (FY-end)
    8: "Shrawan",  # Mid-Aug -> end of Shrawan
    9: "Bhadra",
    10: "Ashwin",
    11: "Kartik",
    12: "Mangsir",
    1: "Poush",
    2: "Magh",
    3: "Falgun",
    4: "Chait",
    5: "Baisakh",
    6: "Jestha",
}

# NRB FY year transition: months Aug..Jul.
_FY_BREAK_AD_MONTH: Final[int] = 7
_AD_DEC: Final[int] = 12
_AD_JAN: Final[int] = 1
_AD_JUL: Final[int] = 7
_AD_JUN: Final[int] = 6
_MID_MONTH_DAY: Final[int] = 15
_NEPALI_MONTH_START_DAY: Final[int] = 17
_NEPALI_MONTH_END_DAY: Final[int] = 16
# BS year N corresponds to AD year (N - _BS_YEAR_TO_AD_DELTA) when the month
# is Shrawan..Poush; otherwise (N - _BS_YEAR_TO_AD_DELTA + 1).
_BS_YEAR_TO_AD_DELTA: Final[int] = 57

_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"mid[-\s]*([a-z]+)\s*$", re.IGNORECASE
)


def parse_mid_month_label(label: str) -> int | None:
    """Return the AD month integer (1-12) for a header like ``Mid-Aug``.

    Returns None if the label doesn't match.
    """
    m = _LABEL_RE.match(label.strip().lower())
    if not m:
        return None
    return _LABEL_TO_AD_MONTH.get(m.group(1))


def label_to_period(
    label: str,
    year: int,
) -> tuple[datetime, datetime, str, str, BsMonth, int] | None:
    """Resolve a ``(Mid-<Month>, YYYY)`` header into period bounds.

    Returns (ad_start, ad_end, reporting_period_bs, fiscal_year_bs,
             bs_month, bs_year) or ``None`` if the label is unrecognised.

    - ``ad_end`` = 15th of the AD month named in the label.
    - ``ad_start`` = 15th of the preceding AD month.
    - ``reporting_period_bs`` formatted as ``"<BsMonth> <BsYear> (mid-end)"``.
    - ``fiscal_year_bs`` is the FY containing ``bs_month``/``bs_year``.
    """
    ad_month = parse_mid_month_label(label)
    if ad_month is None:
        return None
    ad_end = datetime(year, ad_month, _MID_MONTH_DAY, tzinfo=UTC)
    prev_month = _AD_DEC if ad_month == _AD_JAN else ad_month - 1
    prev_year = year - 1 if ad_month == _AD_JAN else year
    ad_start = datetime(prev_year, prev_month, _MID_MONTH_DAY, tzinfo=UTC)

    bs_month = _AD_MONTH_TO_BS_MONTH[ad_month]
    # Empirically every mid-month label maps to BS year = AD_year + 57.
    # Mid-July 2025 -> Ashadh 2082 (end of FY 2081/82); Mid-Aug 2025 ->
    # Shrawan 2082 (start of FY 2082/83). The fiscal-year split is
    # encoded in ``_fiscal_year_label_from`` below.
    bs_year = year + _BS_YEAR_TO_AD_DELTA
    fiscal_year_bs = _fiscal_year_label_from(bs_month, bs_year)
    reporting_period_bs = f"{bs_month} {bs_year} ({label.strip()} {year})"
    return ad_start, ad_end, reporting_period_bs, fiscal_year_bs, bs_month, bs_year


def _fiscal_year_label_from(bs_month: BsMonth, bs_year: int) -> str:
    """Return ``YYYY/YY`` BS-fiscal-year label for a (month, year) pair.

    BS FY starts in Shrawan. So a (month, year) where month ∈
    {Shrawan..Ashadh} of the same FY is labelled by its start year.
    """
    # BS year N runs Shrawan N -> Ashadh (N + 1).
    #   Shrawan..Poush of BS year N -> FY N/(N+1)
    #   Magh..Jestha of BS year N -> FY (N - 1)/N
    #   Ashadh of BS year N -> FY (N - 1)/N (end-of-FY month, labelled by start)
    idx = BS_MONTHS.index(bs_month)
    poush_idx = BS_MONTHS.index("Poush")
    fy_start = bs_year - 1 if (bs_month == "Ashadh" or idx > poush_idx) else bs_year
    return f"{fy_start}/{(fy_start + 1) % 100:02d}"


def snapshot_period_ad(bs_month: BsMonth, bs_year: int) -> tuple[datetime, datetime]:
    """Return AD (start, end) for a BS month given the (month, year)
    parsed from the filename.

    Approximate: BS month N spans mid-X to mid-(X+1) where X is the AD
    month listed in ``_common.periods._BS_MONTH_TO_AD_MONTH``. We treat
    start = day 17 of X (Nepali month-start) and end = day 16 of X+1.
    """
    ad_month = _bs_to_ad_month(bs_month)
    # Year: Shrawan..Poush of BS year N -> AD year (N - 57). Magh..Ashadh
    # -> AD year (N - 56).
    idx = BS_MONTHS.index(bs_month)
    poush_idx = BS_MONTHS.index("Poush")
    delta = _BS_YEAR_TO_AD_DELTA if idx <= poush_idx else (_BS_YEAR_TO_AD_DELTA - 1)
    ad_year = bs_year - delta
    start = datetime(ad_year, ad_month, _NEPALI_MONTH_START_DAY, tzinfo=UTC)
    if ad_month == _AD_DEC:
        end_month, end_year = _AD_JAN, ad_year + 1
    else:
        end_month, end_year = ad_month + 1, ad_year
    end_day = min(_NEPALI_MONTH_END_DAY, calendar.monthrange(end_year, end_month)[1])
    end = datetime(end_year, end_month, end_day, tzinfo=UTC)
    return start, end


def _bs_to_ad_month(bs_month: BsMonth) -> int:
    """Return AD month integer (1-12) that BS month roughly starts in."""
    table = {
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
    return table[bs_month]
