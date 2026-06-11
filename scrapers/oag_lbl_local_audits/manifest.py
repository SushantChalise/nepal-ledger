"""Append-only JSONL provenance manifest for the OAG local-body archive.

Event types: discovered | archived | skipped_duplicate | error.
Every record carries ``schema_version: "1"``. Mirrors oag_audit_reports.manifest.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

MANIFEST_FILENAME: Final[str] = "manifest.jsonl"
SCHEMA_VERSION: Final[str] = "1"

ManifestEventType = Literal["discovered", "archived", "skipped_duplicate", "error"]


@dataclass(frozen=True)
class ManifestEvent:
    event_type: ManifestEventType
    url: str
    ref_key: str
    occurred_at: str
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def append_event(
    manifest_dir: Path,
    *,
    event_type: ManifestEventType,
    url: str,
    ref_key: str,
    payload: dict[str, Any] | None = None,
) -> ManifestEvent:
    """Append one event to ``<manifest_dir>/manifest.jsonl`` and return it."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    event = ManifestEvent(
        event_type=event_type,
        url=url,
        ref_key=ref_key,
        occurred_at=_now_iso(),
        payload=payload or {},
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
            out.append(
                ManifestEvent(
                    event_type=data["event_type"],
                    url=data["url"],
                    ref_key=data["ref_key"],
                    occurred_at=data["occurred_at"],
                    payload=data.get("payload", {}),
                    schema_version=data.get("schema_version", SCHEMA_VERSION),
                )
            )
    return out
