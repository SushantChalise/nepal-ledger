"""Two-mode CSV reader for CBS NPHC 2021 palika-grain cross-tabs.

The 89 CSVs under ``census-dataset/`` come in two layouts that the
pre-existing ``CENSUS_DATA_INDEX.json`` does NOT distinguish. See
``docs/research/cbs-nphc-2021-audit.md`` §2.1 for the audit detail.

Two modes
---------

**Mode A — title preamble (4 files: ``Hhld01..Hhld04``).**
The first row begins with three blank cells then a quoted ``"Table NN: ..."``
title. Five rows of presentation header precede the real machine-readable
column header on row index 5 (0-based). Data begins at row 6.

::

    R0: ,,,"Table 01: Number of households by type ..., NPHC 2021",,,,,,,
    R1: ,,,,,,,,,,
    R2: ,,,Area,,,Total,Type of ownership ,,,
    R3: ,,,,,,,Owned,Rented,Institutional*,Other
    R4: ,,,,,,,,,,
    R5: prov,dist,gapa,provname,dname,gapaname,rowtotal,a_Own,b_Rented,c_Institutnl,d_Other
    R6: 0,0,0,NEPAL,NEPAL,NEPAL,6660841,5728586,850562,36809,44884

**Mode B — clean row-0 header (85 files: everything else).**
Row 0 IS the machine-readable header; data begins at row 1.

Detection rule
--------------

Detection inspects ONLY the first non-empty line:

* if it starts with ``,,,`` AND contains the substring ``"Table `` (a literal
  double-quote followed by ``Table ``) → Mode A.
* otherwise → Mode B.

This is content-based, not file-name-based: a future CBS publication that
flips a Mode-A file to clean headers (or vice versa) will be handled
automatically without parser changes.

Output contract
---------------

:func:`read_census_csv` returns a :class:`CensusCsvReadResult` containing:

* the detected ``mode`` (``'A'`` or ``'B'``),
* the header row as ``list[str]``,
* an iterator of data rows, each as ``list[str]`` aligned to the header.

The reader does not coerce types, strip whitespace beyond what
:mod:`csv` already does, or filter aggregate rows; those concerns belong to
the parser layer.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CsvMode = Literal["A", "B"]

# Mode A: 5 prelude rows precede the header (row index 5 is the header,
# data starts at row 6). The values here are interpreted as 0-based.
_MODE_A_HEADER_ROW_INDEX = 5
_MODE_A_DETECTION_PREFIX = ",,,"
_MODE_A_DETECTION_NEEDLE = '"Table '


@dataclass(frozen=True)
class CensusCsvReadResult:
    """The header + data-row iterator emitted by :func:`read_census_csv`."""

    mode: CsvMode
    header: list[str]
    rows: Iterator[list[str]]


def detect_mode(first_line: str) -> CsvMode:
    """Classify a CSV by inspecting its first raw line.

    Mode A: starts with ``,,,`` AND contains ``"Table ``. Mode B otherwise.
    The detection is intentionally narrow — empty lines or unexpected
    preludes default to Mode B and let the parser fail loudly on a
    header-mismatch rather than silently misalign columns.
    """
    if first_line.startswith(_MODE_A_DETECTION_PREFIX) and _MODE_A_DETECTION_NEEDLE in first_line:
        return "A"
    return "B"


def read_census_csv(path: Path) -> CensusCsvReadResult:
    """Open a CBS NPHC 2021 CSV and yield its header + data rows.

    The detection peeks only at the first raw line (then re-opens the file)
    so we do not consume the iterator before the caller sees it.

    Caveat: the returned ``rows`` iterator owns an open file handle. Callers
    must drain it (e.g. ``list(result.rows)`` or a for-loop) before the
    underlying file is GC'd. The parser layer always materialises the rows
    immediately, so this is safe in practice.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        first_line = fh.readline()
    mode = detect_mode(first_line)

    fh_iter = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.reader(fh_iter)

    if mode == "A":
        # Discard the 5 prelude rows, then take the header row.
        for _ in range(_MODE_A_HEADER_ROW_INDEX):
            next(reader, None)
        header = next(reader, [])
    else:
        header = next(reader, [])

    if not header:
        fh_iter.close()
        raise ValueError(f"{path}: empty header (mode={mode})")

    header_clean = [cell.strip() for cell in header]

    def _iter_rows() -> Iterator[list[str]]:
        try:
            for raw in reader:
                # Pad short rows so callers can zip(header, row) safely.
                if len(raw) < len(header_clean):
                    raw = raw + [""] * (len(header_clean) - len(raw))
                yield raw
        finally:
            fh_iter.close()

    return CensusCsvReadResult(mode=mode, header=header_clean, rows=_iter_rows())
