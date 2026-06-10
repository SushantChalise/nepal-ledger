"""Tests for oag_audit_reports.manifest — append-only JSONL provenance log."""

from __future__ import annotations

from pathlib import Path

from oag_audit_reports.manifest import append_event, read_events


def test_append_then_read_round_trip(tmp_path: Path) -> None:
    append_event(
        tmp_path,
        event_type="archived",
        url="https://oag.gov.np/site_uploads/x.pdf",
        ref_key="58-en-annual_report",
        payload={"sha256": "abc", "bytes": 10},
    )
    append_event(
        tmp_path,
        event_type="error",
        url="https://oag.gov.np/site_uploads/y.pdf",
        ref_key="61-ne-annual_report",
        payload={"phase": "archive"},
    )
    events = read_events(tmp_path)
    assert len(events) == 2
    assert events[0].event_type == "archived"
    assert events[0].ref_key == "58-en-annual_report"
    assert events[0].schema_version == "1"
    assert events[1].event_type == "error"
    assert events[1].payload["phase"] == "archive"


def test_read_events_empty_when_no_manifest(tmp_path: Path) -> None:
    assert read_events(tmp_path) == []


def test_append_is_additive_not_truncating(tmp_path: Path) -> None:
    append_event(tmp_path, event_type="archived", url="u1", ref_key="k1")
    append_event(tmp_path, event_type="archived", url="u2", ref_key="k2")
    assert len(read_events(tmp_path)) == 2
