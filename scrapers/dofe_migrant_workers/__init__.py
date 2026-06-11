"""DoFE migrant-worker labour-permit COUNTS deterministic parser (ADR-0026).

Public surface:
    parse(xlsx_path) -> list[dict]   — permit-fact rows (MigrationPermitFactInput shape)
    reconcile(records) -> dict       — district/country/migrant monthly totals
    PARSER_VERSION
"""

from __future__ import annotations

from .parser import PARSER_VERSION, parse, reconcile

__all__ = ["PARSER_VERSION", "parse", "reconcile"]
