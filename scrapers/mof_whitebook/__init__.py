"""MoF White Book (Source Book for Projects Financed with Foreign Assistance).

Deterministic Python parser (ADR-0003) that turns the two clean English summary
tables of the White Book into ADR-0017 dimensional foreign-aid facts. See
``parser.py`` for the full source-acquisition assessment and scope.
"""

from __future__ import annotations

from mof_whitebook.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    WhitebookResult,
    parse_whitebook,
)

__all__ = [
    "PARSER_VERSION",
    "SOURCE_ID",
    "WhitebookResult",
    "parse_whitebook",
]
