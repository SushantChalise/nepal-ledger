"""MoF Red Book (annual budget) → budget-allocation dimensional facts.

Public surface mirrors the Yellow Book / White Book dimensional parsers so the
cloned ingest CLI (`scripts/ingest-redbook.ts`) reads the same ``dimensional_rows``
JSON. See ``parser.py`` for the STEP-0 PDF-acquisition assessment and scope.
"""

from __future__ import annotations

from mof_redbook.parser import (
    PARSER_VERSION,
    RedbookResult,
    parse_redbook,
)

__all__ = [
    "PARSER_VERSION",
    "RedbookResult",
    "parse_redbook",
]
