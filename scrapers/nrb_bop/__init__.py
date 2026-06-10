"""NRB Balance of Payments — historical BPM5 back-series parser.

Source id: ``nrb-bop``.  Promotes ``remittance-inflow-bpm5`` (annual, npr_million).
"""

from __future__ import annotations

from .parser import PARSER_VERSION, SOURCE_ID, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse"]
