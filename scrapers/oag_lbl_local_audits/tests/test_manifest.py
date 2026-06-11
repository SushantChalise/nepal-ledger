"""Tests for oag_lbl_local_audits.manifest."""

from __future__ import annotations

from pathlib import Path

from oag_lbl_local_audits.manifest import append_event, read_events


def test_round_trip(tmp_path: Path) -> None:
    append_event(tmp_path, event_type="discovered", url="https://x/a.pdf", ref_key="1-en",
                 payload={"municipality": "Kamalamai Municipality"})
    append_event(tmp_path, event_type="archived", url="https://x/a.pdf", ref_key="1-en",
                 payload={"sha256": "abc"})
    events = read_events(tmp_path)
    assert len(events) == 2
    assert events[0].event_type == "discovered"
    assert events[0].payload["municipality"] == "Kamalamai Municipality"
    assert events[1].event_type == "archived"


def test_empty(tmp_path: Path) -> None:
    assert read_events(tmp_path) == []
