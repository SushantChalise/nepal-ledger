"""Parser for NRB CMEFs Table 2(B) — National Consumer Price Index.

Source ID: ``nrb-ncpi-table`` (see docs/SOURCE_REGISTRY.md Tier 1).
On-disk dir uses an underscore (``nrb_ncpi``) because Python module names
forbid hyphens; the canonical source_id keeps the hyphenated form.
"""

from .parser import PARSER_VERSION, SOURCE_ID, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse"]
