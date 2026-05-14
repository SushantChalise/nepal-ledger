"""Tests for nso_archive.manifest — append-only JSONL provenance log."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nso_archive.manifest import (
    MANIFEST_FILENAME,
    SCHEMA_VERSION,
    ManifestEventType,
    append_event,
    read_events,
)


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def test_append_event_creates_file_and_writes_one_line(tmp_path: Path) -> None:
    append_event(
        tmp_path,
        event_type="archived",
        url="https://example/a.pdf",
        category_id="1058",
        payload={"sha256": "abc", "bytes": 7},
    )
    path = tmp_path / MANIFEST_FILENAME
    assert path.exists()
    assert _line_count(path) == 1


def test_append_event_is_append_only(tmp_path: Path) -> None:
    append_event(tmp_path, event_type="archived", url="u1", category_id="1058")
    append_event(tmp_path, event_type="skipped_duplicate", url="u2", category_id="1058")
    append_event(tmp_path, event_type="error", url="u3", category_id="1058")
    assert _line_count(tmp_path / MANIFEST_FILENAME) == 3


def test_event_types_round_trip(tmp_path: Path) -> None:
    types: list[ManifestEventType] = [
        "archived",
        "skipped_duplicate",
        "discovery_only",
        "error",
    ]
    for i, t in enumerate(types):
        append_event(tmp_path, event_type=t, url=f"u{i}", category_id="1058")
    events = read_events(tmp_path)
    assert [e.event_type for e in events] == types


def test_every_line_carries_schema_version(tmp_path: Path) -> None:
    for i in range(5):
        append_event(
            tmp_path,
            event_type="archived",
            url=f"u{i}",
            category_id="1058",
            payload={"i": i},
        )
    path = tmp_path / MANIFEST_FILENAME
    for line in path.open("r", encoding="utf-8"):
        record = json.loads(line)
        assert record["schema_version"] == SCHEMA_VERSION


def test_read_events_empty_when_no_file(tmp_path: Path) -> None:
    assert read_events(tmp_path) == []


def test_payload_round_trips_structured_data(tmp_path: Path) -> None:
    payload = {"title": "Gender 2023", "bytes": 1024, "tags": ["gender", "2023"]}
    append_event(
        tmp_path,
        event_type="archived",
        url="https://x/y.pdf",
        category_id="1058",
        payload=payload,
    )
    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0].payload == payload


@pytest.mark.parametrize(
    "event_type",
    ["archived", "skipped_duplicate", "discovery_only", "error"],
)
def test_event_type_accepted(tmp_path: Path, event_type: ManifestEventType) -> None:
    event = append_event(
        tmp_path,
        event_type=event_type,
        url="https://x/y.pdf",
        category_id="1058",
    )
    assert event.event_type == event_type
    assert event.schema_version == SCHEMA_VERSION
