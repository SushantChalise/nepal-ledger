"""NRB CMEFs monthly bulletin parser (English edition).

See ``parser.py`` for the v0.1.0 implementation and the source profile at
``docs/sources/nrb-cmefs-monthly.md`` for breakage modes and revision policy.
"""

from __future__ import annotations

from .parser import PARSER_VERSION, SOURCE_ID, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse"]
