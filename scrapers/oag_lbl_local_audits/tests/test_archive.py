"""Tests for oag_lbl_local_audits.archive."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from oag_lbl_local_audits.archive import ArchiveError, archive_report
from oag_lbl_local_audits.discover import LocalReportRef

PDF_BYTES = b"%PDF-1.4\n%fake local report\n%%EOF\n"
PDF_SHA256 = hashlib.sha256(PDF_BYTES).hexdigest()
PDF_URL = "https://oag.gov.np/site_uploads/test-local.pdf"


def _ref(url: str = PDF_URL) -> LocalReportRef:
    return LocalReportRef(
        report_id=6089,
        municipality_name="Hariharpurgadhi Rural Municipality",
        district_name="Sindhuli",
        province_name="Bagmati Province",
        fiscal_year_label="2083 (2081/82)",
        audited_fiscal_year_bs="2081/82",
        published_date="2026-06-06",
        lang="en",
        url=url,
        size_bytes=len(PDF_BYTES),
    )


def _client(body: bytes = PDF_BYTES, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) != PDF_URL:
            return httpx.Response(404)
        return httpx.Response(status, content=body, headers={"Content-Type": "application/pdf"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_archive_writes_hash_named_file_and_sidecar(tmp_path: Path) -> None:
    archived = archive_report(_ref(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    assert archived.sha256 == PDF_SHA256
    assert Path(archived.local_path).name == f"{PDF_SHA256}.pdf"
    payload = json.loads((tmp_path / f"{PDF_SHA256}.json").read_text(encoding="utf-8"))
    assert payload["ref"]["municipality_name"] == "Hariharpurgadhi Rural Municipality"
    assert payload["ref"]["audited_fiscal_year_bs"] == "2081/82"
    assert payload["archived"]["sha256"] == PDF_SHA256


def test_archive_idempotent(tmp_path: Path) -> None:
    (tmp_path / f"{PDF_SHA256}.pdf").write_bytes(PDF_BYTES)
    assert archive_report(_ref(), tmp_path, client=_client(), polite_sleep_s=0.0) is None
    assert list(tmp_path.glob("*.json")) == []


def test_archive_raises_on_http_error(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError):
        archive_report(
            _ref(url="https://oag.gov.np/site_uploads/missing.pdf"),
            tmp_path,
            client=_client(),
            polite_sleep_s=0.0,
        )
    assert list(tmp_path.glob("*.part")) == []
