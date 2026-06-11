"""Tests for oag_audit_reports.archive — content-addressable downloader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from oag_audit_reports.archive import ArchiveError, archive_report
from oag_audit_reports.sources import ReportRef

PDF_BYTES = b"%PDF-1.4\n%fake oag report body for tests\n%%EOF\n"
PDF_SHA256 = hashlib.sha256(PDF_BYTES).hexdigest()
PDF_URL = "https://oag.gov.np/site_uploads/test-report.pdf"


def _ref(url: str = PDF_URL) -> ReportRef:
    return ReportRef(
        edition=58,
        audited_fiscal_year_bs="2076/77",
        language="en",
        doc_kind="annual_report",
        title="Test 58th Annual Report",
        url=url,
        verified=True,
    )


def _client(body: bytes = PDF_BYTES, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) != PDF_URL:
            return httpx.Response(404)
        return httpx.Response(status, content=body, headers={"Content-Type": "application/pdf"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_archive_writes_hash_named_file(tmp_path: Path) -> None:
    archived = archive_report(_ref(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    assert archived.sha256 == PDF_SHA256
    assert archived.bytes == len(PDF_BYTES)
    assert Path(archived.local_path).name == f"{PDF_SHA256}.pdf"
    assert Path(archived.local_path).read_bytes() == PDF_BYTES


def test_archive_writes_sidecar_with_ref_and_archived(tmp_path: Path) -> None:
    archived = archive_report(_ref(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    sidecar = tmp_path / f"{PDF_SHA256}.json"
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1"
    assert payload["ref"]["url"] == PDF_URL
    assert payload["ref"]["audited_fiscal_year_bs"] == "2076/77"
    assert payload["ref"]["edition"] == 58
    assert payload["archived"]["sha256"] == PDF_SHA256
    assert payload["archived"]["content_type"] == "application/pdf"


def test_archive_is_idempotent_skips_when_hash_exists(tmp_path: Path) -> None:
    (tmp_path / f"{PDF_SHA256}.pdf").write_bytes(PDF_BYTES)
    result = archive_report(_ref(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert result is None
    assert list(tmp_path.glob("*.json")) == []
    assert list(tmp_path.glob("*.part")) == []


def test_archive_raises_on_http_404(tmp_path: Path) -> None:
    bad = _ref(url="https://oag.gov.np/site_uploads/does-not-exist.pdf")
    with pytest.raises(ArchiveError):
        archive_report(bad, tmp_path, client=_client(), polite_sleep_s=0.0)
    assert list(tmp_path.glob("*.part")) == []
    assert list(tmp_path.glob(".oag-*")) == []


def test_archive_raises_on_http_500(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError):
        archive_report(
            _ref(), tmp_path, client=_client(status=500, body=b"server error"), polite_sleep_s=0.0
        )


def test_archive_creates_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested"
    assert not nested.exists()
    archived = archive_report(_ref(), nested, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    assert nested.is_dir()
