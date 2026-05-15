"""NRB Banking & Financial Institutions monthly XLSX parser package.

Source id: ``nrb-bfi-monthly-xlsx`` (see docs/sources/nrb-bfi-monthly-xlsx.md).

This package ships **schema-discovery infrastructure + a parser for the
canonical month** (Bhadau 2082). The full 49-month corpus is parsed in
follow-up batches grouped by schema similarity — see
``docs/tasks/worker-P2-followup-bfi-batches.md``.
"""

from __future__ import annotations

from .parser import PARSER_VERSION, SOURCE_ID, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "parse"]
