"""Discover local-body audit reports from the OAG backend JSON API.

The OAG site is a JS SPA, but its backend serves a Laravel-paginated endpoint:

    GET https://oag.gov.np/api/front/local-level-report?page=N
    -> { "reports": { "data": [ {row}, ... ], "last_page": 601,
                      "total": 6008, "per_page": 10, "current_page": N },
         "provinces": [...], "fiscal_years": [...] }

Each row carries the municipality / province / district, the fiscal-year label
("2083 (2081/82)" — publish-BS-year and the AUDITED FY in parens), and a
`files[].location` PDF URL. This module paginates the endpoint and yields a
typed `LocalReportRef` per (report, file) — no HTML scraping, no TLS bypass.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Final

import httpx

API_URL: Final[str] = "https://oag.gov.np/api/front/local-level-report"
SOURCE_ID: Final[str] = "oag-lbl-local-audits"
_HTTP_ERROR_MIN: Final[int] = 400
# "2083 (2081/82)" -> audited FY "2081/82"; also tolerate "2081/082".
_AUDITED_FY_RE: Final[re.Pattern[str]] = re.compile(r"\((\d{4})\s*/\s*(\d{2,4})\)")


class DiscoveryError(RuntimeError):
    """Raised on an unrecoverable API/pagination failure."""


@dataclass(frozen=True)
class LocalReportRef:
    """One acquirable local-body report PDF + its provenance metadata."""

    report_id: int
    municipality_name: str
    district_name: str
    province_name: str
    fiscal_year_label: str  # raw, e.g. "2083 (2081/82)"
    audited_fiscal_year_bs: str | None  # parsed "2081/82" (None if absent)
    published_date: str | None
    lang: str | None
    url: str
    size_bytes: int | None
    source_id: str = SOURCE_ID

    @property
    def ref_key(self) -> str:
        """Stable manifest/dedup key per (report, language)."""
        return f"{self.report_id}-{self.lang or 'na'}"


def parse_audited_fy(label: str | None) -> str | None:
    """Extract the audited FY ("2081/82") from a label like "2083 (2081/82)"."""
    if not label:
        return None
    m = _AUDITED_FY_RE.search(label)
    if not m:
        return None
    start, end = m.group(1), m.group(2)
    return f"{start}/{end[-2:]}"


def _rows_from_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int, int]:
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise DiscoveryError("API payload missing 'reports' paginator object")
    data = reports.get("data")
    if not isinstance(data, list):
        raise DiscoveryError("API 'reports.data' is not a list")
    last_page = int(reports.get("last_page") or 1)
    current = int(reports.get("current_page") or 1)
    return data, last_page, current


def _refs_from_row(row: dict[str, Any]) -> Iterator[LocalReportRef]:
    def name_of(key: str) -> str:
        v = row.get(key)
        return str(v.get("name")) if isinstance(v, dict) and v.get("name") else ""

    fy_label = name_of("fiscal_year")
    files = row.get("files")
    if not isinstance(files, list):
        return
    for f in files:
        if not isinstance(f, dict):
            continue
        url = f.get("location")
        if not isinstance(url, str) or not url.lower().endswith(".pdf"):
            continue
        size = f.get("size")
        yield LocalReportRef(
            report_id=int(row.get("id") or 0),
            municipality_name=name_of("municipality") or str(row.get("name") or ""),
            district_name=name_of("district"),
            province_name=name_of("province"),
            fiscal_year_label=fy_label,
            audited_fiscal_year_bs=parse_audited_fy(fy_label),
            published_date=row.get("published_date"),
            lang=f.get("lang"),
            url=url,
            size_bytes=int(size) if isinstance(size, int | float) else None,
        )


def discover_reports(
    client: httpx.Client,
    *,
    page_from: int = 1,
    page_to: int | None = None,
    timeout_s: int = 30,
    polite_sleep_s: float = 0.5,
) -> Iterator[LocalReportRef]:
    """Paginate the API from ``page_from`` to ``page_to`` (or the API's last
    page) and yield a ``LocalReportRef`` per report file. Raises DiscoveryError
    on HTTP/parse failure."""
    page = page_from
    while True:
        try:
            resp = client.get(API_URL, params={"page": page}, timeout=timeout_s)
        except httpx.HTTPError as exc:
            raise DiscoveryError(f"network failure on page {page}: {exc!r}") from exc
        if resp.status_code >= _HTTP_ERROR_MIN:
            raise DiscoveryError(f"HTTP {resp.status_code} on page {page}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise DiscoveryError(f"page {page} response was not JSON: {exc}") from exc
        rows, last_page, _ = _rows_from_payload(payload)
        for row in rows:
            yield from _refs_from_row(row)
        stop_at = last_page if page_to is None else min(page_to, last_page)
        if page >= stop_at:
            break
        page += 1
        if polite_sleep_s > 0:
            time.sleep(polite_sleep_s)
