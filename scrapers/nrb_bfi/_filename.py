"""Parse NRB BFI XLSX filenames into a canonical (BS month, BS year) tuple.

Filenames in this corpus are inconsistent: ``Shrawan-2078-2.xlsx``,
``Saun-2082-Publish.xlsx``, ``Bhadau_2082_Publish.xlsx``,
``Ashar2079_Publish.xlsx``, ``Asoj_2079_PublishV1.xlsx`` — different
separators, multiple transliterations for the same BS month, and trailing
``-2``/``V1``/``Publish`` decorations.

We use a deterministic table of accepted spellings (no fuzzy matching) so
filename drift is loud (we raise) rather than silent (we'd guess).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from _common.periods import BsMonth

# Map every transliteration we have observed across the 50-file corpus
# (lower-cased) to its canonical BS month.
_BS_MONTH_ALIASES: Final[dict[str, BsMonth]] = {
    "shrawan": "Shrawan",
    "saun": "Shrawan",
    "shravan": "Shrawan",
    "bhadra": "Bhadra",
    "bhadau": "Bhadra",
    "bhadu": "Bhadra",
    "ashwin": "Ashwin",
    "asoj": "Ashwin",
    "asoz": "Ashwin",
    "kartik": "Kartik",
    "kartika": "Kartik",
    "mangsir": "Mangsir",
    "mangshir": "Mangsir",
    "manghir": "Mangsir",
    "manghsir": "Mangsir",
    "poush": "Poush",
    "push": "Poush",
    "magh": "Magh",
    "falgun": "Falgun",
    "phalgun": "Falgun",
    "phagun": "Falgun",
    "chait": "Chait",
    "chaitra": "Chait",
    "baisakh": "Baisakh",
    "baishakh": "Baisakh",
    "vaisakh": "Baisakh",
    "vaishakh": "Baisakh",
    "jestha": "Jestha",
    "jeth": "Jestha",
    "ashadh": "Ashadh",
    "asadh": "Ashadh",
    "ashar": "Ashadh",
    "asar": "Ashadh",
    "asadha": "Ashadh",
}

_BS_YEAR_RANGE: Final[tuple[int, int]] = (2070, 2099)

_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]+|[0-9]+")


class FilenameUnparseableError(ValueError):
    """Raised when the stem cannot be resolved to a (month, year) tuple."""


def parse_snapshot_filename(path: str | Path) -> tuple[BsMonth, int]:
    """Return the canonical (BsMonth, bs_year) for an NRB BFI XLSX path.

    Raises ``FilenameUnparseableError`` on unknown month spellings or out-of-
    range BS years — the parser then emits a ``PeriodAmbiguous`` ParserError
    rather than guessing.
    """
    stem = Path(path).stem
    tokens = _TOKEN_RE.findall(stem)
    month: BsMonth | None = None
    year: int | None = None
    for tok in tokens:
        if tok.isalpha():
            candidate = _BS_MONTH_ALIASES.get(tok.lower())
            if candidate is not None and month is None:
                month = candidate
        elif tok.isdigit():
            n = int(tok)
            if _BS_YEAR_RANGE[0] <= n <= _BS_YEAR_RANGE[1] and year is None:
                year = n
    if month is None or year is None:
        raise FilenameUnparseableError(
            f"Cannot resolve BS month/year from filename stem {stem!r}; "
            f"got month={month!r}, year={year!r}"
        )
    return month, year
