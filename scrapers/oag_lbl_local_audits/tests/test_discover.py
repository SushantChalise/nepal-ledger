"""Tests for oag_lbl_local_audits.discover — API pagination + FY parsing.

Uses httpx.MockTransport with the real paginator shape (no network).
"""

from __future__ import annotations

import httpx
import pytest

from oag_lbl_local_audits.discover import (
    DiscoveryError,
    discover_reports,
    parse_audited_fy,
)


def _row(report_id: int, muni: str, fy: str, url: str, lang: str = "en") -> dict[str, object]:
    return {
        "id": report_id,
        "name": muni,
        "published_date": "2026-06-06",
        "province": {"id": 3, "name": "Bagmati Province"},
        "district": {"id": 34, "name": "Sindhuli"},
        "municipality": {"id": 238, "name": muni},
        "fiscal_year": {"id": 77, "name": fy},
        "files": [{"location": url, "lang": lang, "extension": "pdf", "size": 1024}],
    }


def _page(rows: list[dict[str, object]], current: int, last: int) -> dict[str, object]:
    return {
        "reports": {"data": rows, "current_page": current, "last_page": last, "per_page": 10,
                    "total": 20},
        "provinces": [], "fiscal_years": [],
    }


def _client(pages: dict[int, dict[str, object]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        if page not in pages:
            return httpx.Response(404)
        return httpx.Response(200, json=pages[page])

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("2083 (2081/82)", "2081/82"),
        ("2082 (2080/81)", "2080/81"),
        ("2083", None),
        (None, None),
        ("garbage", None),
    ],
)
def test_parse_audited_fy(label: str | None, expected: str | None) -> None:
    assert parse_audited_fy(label) == expected


def test_discover_paginates_and_parses() -> None:
    pages = {
        1: _page(
            [_row(1, "Hariharpurgadhi Rural Municipality", "2083 (2081/82)", "https://x/a.pdf")],
            1,
            2,
        ),
        2: _page([_row(2, "Kamalamai Municipality", "2082 (2080/81)", "https://x/b.pdf")], 2, 2),
    }
    refs = list(discover_reports(_client(pages), polite_sleep_s=0.0))
    assert len(refs) == 2
    assert refs[0].municipality_name == "Hariharpurgadhi Rural Municipality"
    assert refs[0].audited_fiscal_year_bs == "2081/82"
    assert refs[0].province_name == "Bagmati Province"
    assert refs[0].url == "https://x/a.pdf"
    assert refs[0].ref_key == "1-en"
    assert refs[1].audited_fiscal_year_bs == "2080/81"


def test_discover_respects_page_to() -> None:
    pages = {1: _page([_row(1, "A", "2083 (2081/82)", "https://x/a.pdf")], 1, 5)}
    refs = list(discover_reports(_client(pages), page_to=1, polite_sleep_s=0.0))
    assert len(refs) == 1


def test_discover_skips_non_pdf_files() -> None:
    row = _row(1, "A", "2083 (2081/82)", "https://x/a.pdf")
    files = row["files"]
    assert isinstance(files, list)
    files.append({"location": "https://x/notes.docx", "lang": "ne", "extension": "docx"})
    refs = list(discover_reports(_client({1: _page([row], 1, 1)}), polite_sleep_s=0.0))
    assert len(refs) == 1
    assert refs[0].url == "https://x/a.pdf"


def test_discover_raises_on_http_error() -> None:
    with pytest.raises(DiscoveryError):
        list(discover_reports(_client({}), polite_sleep_s=0.0))


def test_discover_raises_on_malformed_payload() -> None:
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"x": 1})))
    with pytest.raises(DiscoveryError):
        list(discover_reports(bad, polite_sleep_s=0.0))
