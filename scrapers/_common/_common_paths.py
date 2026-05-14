"""Filesystem-path constants shared across Nepal Ledger parsers.

The ``Financial Data/`` tree is gitignored — these helpers locate it at
runtime so parser code stays decoupled from absolute paths. We only expose
*directories*; the canonical xlsx and other large fixtures are NEVER
exported back into the repo.
"""

from __future__ import annotations

from pathlib import Path

# scrapers/_common/_common_paths.py -> scrapers/_common/ -> scrapers/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """Absolute path to the Nepal Ledger repo root."""
    return _REPO_ROOT


def financial_data_root() -> Path:
    """Absolute path to the gitignored ``Financial Data/`` tree.

    Existence is not asserted here — individual loaders check for the
    specific file they need and raise a clear error if missing.
    """
    return _REPO_ROOT / "Financial Data"
