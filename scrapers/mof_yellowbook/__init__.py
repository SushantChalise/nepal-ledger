"""MoF Yellow Book (Annual Performance Review of Public Enterprises) parser.

See ``parser.py`` for the v0.1.0 implementation and the source profile at
``docs/sources/dpm-public-enterprises-annual.md`` for breakage modes and
revision policy. Emits ADR-0015 dimensional facts (dimension = public
enterprise) for the DNE dimensional ingest CLI.
"""

from __future__ import annotations

from .parser import PARSER_VERSION, SOURCE_ID, parse_yellowbook

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse_yellowbook"]
