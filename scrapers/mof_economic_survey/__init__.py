"""MoF Economic Survey statistical-annex parser.

See ``parser.py`` for the v0.1.0 implementation and the source profile at
``docs/sources/mof-economic-survey-annual.md`` for the encoding-breakage
assessment and revision policy. ADR-0016 records the annex-only scope: extract
the clean Annex 6.1 (Foreign Employment Permits); defer the RTL-mirrored macro
annex and the CID-broken Nepali editions.
"""

from __future__ import annotations

from .parser import PARSER_VERSION, SOURCE_ID, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse"]
