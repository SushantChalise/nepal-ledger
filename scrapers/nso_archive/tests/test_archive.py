"""Tests for nso_archive.archive — content-addressable downloader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from nso_archive.archive import ArchiveError, archive_document
from nso_archive.discover import DiscoveredDocument

PDF_BYTES = b"%PDF-1.4\n%fake pdf body for tests\n%%EOF\n"
PDF_SHA256 = hashlib.sha256(PDF_BYTES).hexdigest()
PDF_URL = "https://nsonepal.gov.np/sites/default/files/gender-2023.pdf"


def _doc() -> DiscoveredDocument:
    return DiscoveredDocument(
        title="Statistics on Gender 2023",
        url=PDF_URL,
        category_id="1058",
        category_name="Gender & Social Statistics",
        published_at_scraped="2024-10-12",
        discovered_at="2026-05-14T00:00:00+00:00",
    )


def _client(body: bytes = PDF_BYTES, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) != PDF_URL:
            return httpx.Response(404)
        return httpx.Response(
            status,
            content=body,
            headers={"Content-Type": "application/pdf"},
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_archive_writes_hash_named_file(tmp_path: Path) -> None:
    archived = archive_document(_doc(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    assert archived.sha256 == PDF_SHA256
    assert archived.bytes == len(PDF_BYTES)
    assert Path(archived.local_path).name == f"{PDF_SHA256}.pdf"
    assert Path(archived.local_path).read_bytes() == PDF_BYTES


def test_archive_writes_sidecar_with_full_metadata(tmp_path: Path) -> None:
    archived = archive_document(_doc(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    sidecar = tmp_path / f"{PDF_SHA256}.json"
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1"
    assert payload["discovered"]["url"] == PDF_URL
    assert payload["discovered"]["category_id"] == "1058"
    assert payload["archived"]["sha256"] == PDF_SHA256
    assert payload["archived"]["content_type"] == "application/pdf"


def test_archive_is_idempotent_skips_when_hash_exists(tmp_path: Path) -> None:
    # Pre-populate the target file so the second run sees a duplicate.
    (tmp_path / f"{PDF_SHA256}.pdf").write_bytes(PDF_BYTES)
    result = archive_document(_doc(), tmp_path, client=_client(), polite_sleep_s=0.0)
    assert result is None
    # No new sidecar should have been written (only the pre-existing PDF).
    sidecars = list(tmp_path.glob("*.json"))
    assert sidecars == []
    # No stray .part files left behind.
    leftovers = list(tmp_path.glob("*.part"))
    assert leftovers == []


def test_archive_raises_on_http_404(tmp_path: Path) -> None:
    bad_doc = DiscoveredDocument(
        title="ghost",
        url="https://nsonepal.gov.np/does-not-exist.pdf",
        category_id="1058",
        category_name="x",
        published_at_scraped=None,
        discovered_at="2026-05-14T00:00:00+00:00",
    )
    with pytest.raises(ArchiveError):
        archive_document(bad_doc, tmp_path, client=_client(), polite_sleep_s=0.0)
    # No stray temp files left behind.
    assert list(tmp_path.glob("*.part")) == []
    assert list(tmp_path.glob(".nso-*")) == []


def test_archive_raises_on_http_500(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError):
        archive_document(
            _doc(),
            tmp_path,
            client=_client(status=500, body=b"server error"),
            polite_sleep_s=0.0,
        )


def test_archive_creates_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested"
    assert not nested.exists()
    archived = archive_document(_doc(), nested, client=_client(), polite_sleep_s=0.0)
    assert archived is not None
    assert nested.is_dir()
