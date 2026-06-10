"""Department of Customs monthly Foreign Trade Statistics (FTS) parser package.

Source id: ``customs-monthly-trade``. Emits ADR-0015 ``dimensional_rows`` into
``dne_facts`` (dimension = commodity / country / customs_office). See
``parser.py`` for the layout contract and ``README.md`` for the acquisition
record and known breakage modes.
"""

from __future__ import annotations

from customs_trade.parser import PARSER_VERSION, SOURCE_ID, parse_customs_fts

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse_customs_fts"]
