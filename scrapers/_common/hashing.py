"""SHA-256 utilities for the source-document archive contract."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_BYTES = 1 << 16  # 64 KiB


def sha256_of_file(path: str | Path) -> str:
    """Return the lowercase hex SHA-256 digest of a file's bytes.

    Reads in 64 KiB chunks so large PDFs don't bloat memory.
    Used by the orchestration layer to verify `source_documents.file_hash_sha256`
    before invoking a parser.
    """
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()
