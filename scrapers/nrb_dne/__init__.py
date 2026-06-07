"""NRB Database on Nepalese Economy (DNE) XLSX time-series parser.

Covers all five sectoral pages of the NRB DNE portal:
Real, External, Fiscal, Monetary, Financial.

Source id: ``nrb-dne-xlsx`` (see docs/sources/nrb-dne-xlsx.md — pending
registration by Mother).

The DNE XLSX files share a common wide layout: indicators as rows, fiscal
periods (annual "2079/80" or monthly "Shrawan 2082") as columns. This
parser normalises every XLSX into long-format ``StagingRowDraft`` rows.
"""

from __future__ import annotations

from .parser import (
    PARSER_VERSION,
    SOURCE_ID,
    DimensionalRowDraft,
    DneParserResult,
    parse,
    parse_dne,
)

__all__ = [
    "PARSER_VERSION",
    "SOURCE_ID",
    "DimensionalRowDraft",
    "DneParserResult",
    "parse",
    "parse_dne",
]
