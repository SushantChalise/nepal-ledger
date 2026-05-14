"""Discover PDFs linked from an NSO Nepal category index page.

httpx + BeautifulSoup(lxml). One retry on transport error (1s, 2s); no retry
on 4xx. Pagination via ``?page=N`` up to PAGINATION_PAGE_CAP. Relative URLs
are resolved against the page URL. See README.md for the politeness contract.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

USER_AGENT: Final[str] = "nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)"
PAGINATION_PAGE_CAP: Final[int] = 20
_HTTP_CLIENT_ERROR_MIN: Final[int] = 400
_HTTP_SERVER_ERROR_MIN: Final[int] = 500
_DATE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})/(\d{2})/(\d{2})"),
)


class DiscoveryError(RuntimeError):
    """Raised when a category page cannot be fetched or parsed."""


@dataclass(frozen=True)
class DiscoveredDocument:
    """One PDF link discovered on an NSO category listing page."""

    title: str
    url: str
    category_id: str
    category_name: str
    published_at_scraped: str | None
    discovered_at: str


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _extract_category_id(url: str) -> str:
    match = re.search(r"/category/(\d+)", url)
    return match.group(1) if match else ""


def _looks_like_pdf(href: str) -> bool:
    return href.lower().split("?", 1)[0].endswith(".pdf")


def _parse_date(text: str) -> str | None:
    """Return an ISO date if ``text`` contains a recognisable yyyy-mm-dd."""
    for pattern in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        y, mo, d = m.groups()
        try:
            return datetime(int(y), int(mo), int(d), tzinfo=UTC).date().isoformat()
        except ValueError:
            return None
    return None


def _nearest_text(node: Tag, max_chars: int = 200) -> str:
    """Text of the anchor's closest item container; do NOT climb past it."""
    container_tags = {"li", "p", "div", "tr", "article", "section"}
    cursor: Tag | None = node.parent if isinstance(node.parent, Tag) else None
    while cursor is not None and cursor.name not in container_tags:
        cursor = cursor.parent if isinstance(cursor.parent, Tag) else None
    return (cursor or node).get_text(" ", strip=True)[:max_chars]


def _extract_category_name(soup: BeautifulSoup) -> str:
    for selector in ("h1", ".page-title", "title"):
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return node.get_text(strip=True)
    return ""


def _parse_page(
    html: str, *, page_url: str, category_id: str, discovered_at: str
) -> list[DiscoveredDocument]:
    """Extract DiscoveredDocument records from one HTML page's body."""
    soup = BeautifulSoup(html, "lxml")
    category_name = _extract_category_name(soup)
    out: list[DiscoveredDocument] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = str(anchor["href"]).strip()
        if not href or not _looks_like_pdf(href):
            continue
        absolute = urljoin(page_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(DiscoveredDocument(
            title=anchor.get_text(strip=True) or absolute.rsplit("/", 1)[-1],
            url=absolute, category_id=category_id, category_name=category_name,
            published_at_scraped=_parse_date(_nearest_text(anchor)),
            discovered_at=discovered_at,
        ))
    return out


def _build_paginated_url(base_url: str, page: int) -> str:
    if page <= 1:
        return base_url
    parsed = urlparse(base_url)
    sep = "&" if parsed.query else "?"
    return f"{base_url}{sep}page={page}"


def _fetch(client: httpx.Client, url: str, *, timeout_s: int) -> httpx.Response:
    """Single GET with one polite retry on transport / 5xx errors. No retry on 4xx."""
    max_retries = 1
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.get(url, timeout=timeout_s)
        except (httpx.ConnectError, httpx.ReadError, httpx.ReadTimeout) as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            time.sleep(2**attempt)
            continue
        if _HTTP_CLIENT_ERROR_MIN <= resp.status_code < _HTTP_SERVER_ERROR_MIN:
            raise DiscoveryError(f"HTTP {resp.status_code} fetching {url}")
        if resp.status_code >= _HTTP_SERVER_ERROR_MIN:
            last_exc = DiscoveryError(f"HTTP {resp.status_code} fetching {url}")
            if attempt >= max_retries:
                break
            time.sleep(2**attempt)
            continue
        return resp
    raise DiscoveryError(f"failed to fetch {url}: {last_exc!r}")


def discover_documents(
    category_url: str,
    *,
    timeout_s: int = 30,
    client: httpx.Client | None = None,
    pagination_cap: int = PAGINATION_PAGE_CAP,
    polite_sleep_s: float = 1.0,
) -> list[DiscoveredDocument]:
    """Fetch the category page (+ paginated children) and return PDF metadata.

    Raises DiscoveryError on unrecoverable HTTP failure; returns [] if no PDFs.
    """
    category_id = _extract_category_id(category_url)
    discovered_at = _now_iso()
    results: list[DiscoveredDocument] = []
    seen: set[str] = set()
    owns_client = client is None
    http = client or httpx.Client(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
    try:
        for page in range(1, pagination_cap + 1):
            page_url = _build_paginated_url(category_url, page)
            resp = _fetch(http, page_url, timeout_s=timeout_s)
            page_docs = _parse_page(
                resp.text, page_url=page_url,
                category_id=category_id, discovered_at=discovered_at,
            )
            new_docs = [d for d in page_docs if d.url not in seen]
            if not new_docs:
                break
            for d in new_docs:
                seen.add(d.url)
                results.append(d)
            if page < pagination_cap and polite_sleep_s > 0:
                time.sleep(polite_sleep_s)
    finally:
        if owns_client:
            http.close()
    return results
