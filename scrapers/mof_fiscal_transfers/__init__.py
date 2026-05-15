"""Parser for MoF Local Fiscal Transfers — FY 2082/83 (cleaned XLSX).

Source ID: ``local-fiscal-transfers-cleaned`` (Tier 1 domain-fact parser).
Unlike the indicator parsers, this one emits ``FiscalTransferRow`` records
that are inserted directly into the ``local_government_fiscal_transfers``
domain-fact table — no staging-validation step (one-shot annual corpus,
authoritative MoF data, confidence A).
"""

from .parser import PARSER_VERSION, SOURCE_ID, FiscalTransferRow, parse

__all__ = ["PARSER_VERSION", "SOURCE_ID", "FiscalTransferRow", "parse"]
