"""NSO Nepal PDF acquisition archiver (Layer-1). See README.md and ADR-0003."""

from __future__ import annotations

from nso_archive.archive import ArchivedDocument, archive_document
from nso_archive.discover import DiscoveredDocument, discover_documents
from nso_archive.manifest import ManifestEvent, append_event

__all__ = [
    "ArchivedDocument", "DiscoveredDocument", "ManifestEvent",
    "append_event", "archive_document", "discover_documents",
]
PACKAGE_VERSION = "0.1.0"
