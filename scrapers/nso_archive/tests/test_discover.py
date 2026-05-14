"""Tests for nso_archive.discover. No network access; uses fixtures + mocks."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from nso_archive.discover import (
    DiscoveryError,
    _build_paginated_url,
    _extract_category_id,
    _parse_date,
    _parse_page,
    discover_documents,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
CATEGORY_HTML = (FIXTURE_DIR / "category_1058.html").read_text(encoding="utf-8")
CATEGORY_URL = "https://nsonepal.gov.np/category/1058/"
EMPTY_HTML = """<!doctype html><html><body><h1>Empty Category</h1>
<ul><li>No documents here.</li></ul></body></html>"""


def _make_client(routes: dict[str, str]) -> httpx.Client:
    """Build an httpx.Client routed via MockTransport for deterministic tests."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = routes.get(str(request.url))
        if body is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, text=body, headers={"Content-Type": "text/html"})

    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------------- pure helpers ----------------


def test_extract_category_id_from_url() -> None:
    assert _extract_category_id("https://nsonepal.gov.np/category/1058/") == "1058"
    assert _extract_category_id("https://nsonepal.gov.np/about/") == ""


def test_parse_date_iso_and_slash_formats() -> None:
    assert _parse_date("Published on 2024-10-12") == "2024-10-12"
    assert _parse_date("Published on 2023/05/04") == "2023-05-04"
    assert _parse_date("no date here") is None
    # Impossible calendar date returns None rather than crashing.
    assert _parse_date("2024-13-99") is None


def test_build_paginated_url_handles_query() -> None:
    assert _build_paginated_url("https://x/category/1/", 1) == "https://x/category/1/"
    assert _build_paginated_url("https://x/category/1/", 2) == "https://x/category/1/?page=2"
    assert _build_paginated_url("https://x/category/1/?q=a", 3) == "https://x/category/1/?q=a&page=3"


# ---------------- _parse_page ----------------


def test_parse_page_finds_all_pdfs_and_resolves_urls() -> None:
    docs = _parse_page(
        CATEGORY_HTML,
        page_url=CATEGORY_URL,
        category_id="1058",
        discovered_at="2026-05-14T00:00:00+00:00",
    )
    urls = [d.url for d in docs]
    # 4 unique PDF URLs after deduplication (mirror link collapsed).
    assert len(docs) == 4
    assert all(u.startswith("https://nsonepal.gov.np/") for u in urls)
    assert "https://nsonepal.gov.np/sites/default/files/2024-10/gender-statistics-2023.pdf" in urls
    # HTML link must not appear.
    assert all(not u.endswith(".html") for u in urls)


def test_parse_page_captures_listing_date() -> None:
    docs = _parse_page(
        CATEGORY_HTML,
        page_url=CATEGORY_URL,
        category_id="1058",
        discovered_at="2026-05-14T00:00:00+00:00",
    )
    by_title = {d.title: d for d in docs}
    assert by_title["Statistics on Gender 2023"].published_at_scraped == "2024-10-12"
    assert by_title["Social Indicators of Nepal 2022"].published_at_scraped == "2023-05-04"
    # Legacy doc has no date in nearby text.
    assert by_title["Legacy Report (no listed date)"].published_at_scraped is None


def test_parse_page_returns_empty_when_no_pdfs() -> None:
    docs = _parse_page(
        EMPTY_HTML,
        page_url="https://x/category/9999/",
        category_id="9999",
        discovered_at="2026-05-14T00:00:00+00:00",
    )
    assert docs == []


def test_parse_page_extracts_category_name() -> None:
    docs = _parse_page(
        CATEGORY_HTML,
        page_url=CATEGORY_URL,
        category_id="1058",
        discovered_at="2026-05-14T00:00:00+00:00",
    )
    assert docs[0].category_name == "Gender & Social Statistics"


# ---------------- discover_documents (transport-mocked) ----------------


def test_discover_documents_against_fixture_via_mock_transport() -> None:
    client = _make_client({CATEGORY_URL: CATEGORY_HTML})
    docs = discover_documents(
        CATEGORY_URL,
        client=client,
        polite_sleep_s=0.0,
        pagination_cap=1,
    )
    assert len(docs) == 4
    assert {d.category_id for d in docs} == {"1058"}


def test_discover_documents_paginates_and_stops_when_empty() -> None:
    page2_url = CATEGORY_URL + "?page=2"
    routes = {CATEGORY_URL: CATEGORY_HTML, page2_url: EMPTY_HTML}
    client = _make_client(routes)
    docs = discover_documents(
        CATEGORY_URL,
        client=client,
        polite_sleep_s=0.0,
        pagination_cap=5,
    )
    # Stops at page 2 (empty), still returns the 4 docs from page 1.
    assert len(docs) == 4


def test_discover_documents_raises_on_404() -> None:
    client = _make_client({})  # any URL -> 404
    with pytest.raises(DiscoveryError):
        discover_documents(
            CATEGORY_URL,
            client=client,
            polite_sleep_s=0.0,
            pagination_cap=1,
        )


def test_discover_documents_returns_empty_when_page_has_no_pdfs() -> None:
    client = _make_client({CATEGORY_URL: EMPTY_HTML})
    docs = discover_documents(
        CATEGORY_URL,
        client=client,
        polite_sleep_s=0.0,
        pagination_cap=1,
    )
    assert docs == []
