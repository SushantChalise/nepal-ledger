"""Download a discovered local-body report to a content-addressable archive.

Streams in 64 KiB chunks to a temp file, hashes, renames to ``<sha256>.pdf``,
writes a sidecar ``<sha256>.json`` with the ref + archived metadata. Idempotent:
a second run with the same content is a no-op (returns None). No PDF parsing.
Mirrors oag_audit_reports.archive.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import httpx

from _common.hashing import sha256_of_file
from oag_lbl_local_audits.discover import LocalReportRef

USER_AGENT: Final[str] = "nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)"
_CHUNK_BYTES: Final[int] = 1 << 16  # 64 KiB
_HTTP_ERROR_MIN: Final[int] = 400


class ArchiveError(RuntimeError):
    """Raised on unrecoverable download / hashing failure."""


@dataclass(frozen=True)
class ArchivedReport:
    sha256: str
    local_path: str
    bytes: int
    url: str
    fetched_at: str
    content_type: str


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _write_sidecar(sidecar_path: Path, ref: LocalReportRef, archived: ArchivedReport) -> None:
    payload = {"schema_version": "1", "ref": asdict(ref), "archived": asdict(archived)}
    sidecar_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )


def archive_report(
    ref: LocalReportRef,
    output_dir: Path,
    *,
    timeout_s: int = 120,
    client: httpx.Client | None = None,
    polite_sleep_s: float = 1.0,
) -> ArchivedReport | None:
    """Download ``ref.url`` into ``output_dir``; return None if the hash exists.

    Raises ArchiveError on HTTP 4xx/5xx or disk I/O failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    owns_client = client is None
    http = client or httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    tmp_path: Path | None = None
    try:
        try:
            with http.stream("GET", ref.url, timeout=timeout_s) as resp:
                if resp.status_code >= _HTTP_ERROR_MIN:
                    raise ArchiveError(f"HTTP {resp.status_code} fetching {ref.url}")
                content_type = resp.headers.get("Content-Type", "application/pdf")
                fd, tmp_name = tempfile.mkstemp(
                    prefix=".oag-lbl-", suffix=".pdf.part", dir=str(output_dir)
                )
                tmp_path = Path(tmp_name)
                total = 0
                with os.fdopen(fd, "wb") as out:
                    for chunk in resp.iter_bytes(_CHUNK_BYTES):
                        if not chunk:
                            continue
                        out.write(chunk)
                        total += len(chunk)
        except httpx.HTTPError as exc:
            raise ArchiveError(f"network failure fetching {ref.url}: {exc!r}") from exc
        if tmp_path is None or not tmp_path.exists():
            raise ArchiveError(f"temp file missing after download of {ref.url}")
        digest = sha256_of_file(tmp_path)
        final_path = output_dir / f"{digest}.pdf"
        if final_path.exists():
            tmp_path.unlink(missing_ok=True)
            return None
        os.replace(tmp_path, final_path)
        tmp_path = None
        archived = ArchivedReport(
            sha256=digest,
            local_path=str(final_path.resolve()),
            bytes=total,
            url=ref.url,
            fetched_at=_now_iso(),
            content_type=content_type,
        )
        _write_sidecar(output_dir / f"{digest}.json", ref, archived)
        if polite_sleep_s > 0:
            time.sleep(polite_sleep_s)
        return archived
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if owns_client:
            http.close()
