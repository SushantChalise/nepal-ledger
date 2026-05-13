"""Parser contract protocol — see docs/DATA_PIPELINE.md §"Parser Contract".

Every concrete parser exposes:
- ``PARSER_VERSION``: module-level semver string (bump on behavior change)
- ``SOURCE_ID``: module-level string matching source_registry.source_id
- ``parse(source_document_path, source_document_id) -> ParserResult``

Rules (ADR-0003):
- Idempotent: same input -> same output bytes-for-bytes.
- No network calls. No DB writes. Pure file-in -> dataclass-out.
- Never raise on bad data — return ``status='partial'`` or ``'failure'``
  with structured ``errors[]``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import ParserResult


@runtime_checkable
class ParserModule(Protocol):
    PARSER_VERSION: str
    SOURCE_ID: str

    @staticmethod
    def parse(source_document_path: str, source_document_id: str) -> ParserResult: ...
