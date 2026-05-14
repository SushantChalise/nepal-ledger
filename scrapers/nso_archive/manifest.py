"""Append-only JSONL manifest for the NSO archive.

Event types: archived | skipped_duplicate | discovery_only | error.
Every record carries ``schema_version: "1"``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

MANIFEST_FILENAME: Final[str] = "manifest.jsonl"
SCHEMA_VERSION: Final[str] = "1"

ManifestEventType = Literal["archived", "skipped_duplicate", "discovery_only", "error"]


@dataclass(frozen=True)
class ManifestEvent:
    event_type: ManifestEventType
    url: str
    category_id: str
    occurred_at: str
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def append_event(
    manifest_dir: Path,
    *,
    event_type: ManifestEventType,
    url: str,
    category_id: str,
    payload: dict[str, Any] | None = None,
) -> ManifestEvent:
    """Append one event to ``<manifest_dir>/manifest.jsonl`` and return it."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    event = ManifestEvent(
        event_type=event_type, url=url, category_id=category_id,
        occurred_at=_now_iso(), payload=payload or {},
    )
    with (manifest_dir / MANIFEST_FILENAME).open("a", encoding="utf-8") as fh:
        fh.write(event.to_json_line() + "\n")
    return event


def read_events(manifest_dir: Path) -> list[ManifestEvent]:
    """Read all events back. For tests and operator inspection."""
    path = manifest_dir / MANIFEST_FILENAME
    if not path.exists():
        return []
    out: list[ManifestEvent] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(ManifestEvent(
                event_type=data["event_type"], url=data["url"],
                category_id=data["category_id"], occurred_at=data["occurred_at"],
                payload=data.get("payload", {}),
                schema_version=data.get("schema_version", SCHEMA_VERSION),
            ))
    return out
