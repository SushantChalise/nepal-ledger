"""FCGO Consolidated Financial Statements parser (English edition).

See ``parser.py`` for the v1.0.0 implementation (pymupdf backend; 9
indicators) and the source profile at
``docs/sources/fcgo-consolidated-financial-statements.md`` for breakage
modes and revision policy.
"""

from __future__ import annotations

from .parser import PARSER_VERSION, SOURCE_ID, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse"]
