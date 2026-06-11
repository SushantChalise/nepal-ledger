"""Tests for oag_audit_reports.discover — annual-reports API discovery."""

from __future__ import annotations

import httpx
import pytest

from oag_audit_reports.discover import DiscoveryError, audited_fy_for_edition, discover_reports

API = "https://oag.gov.np/api/front/annual-reports"


@pytest.mark.parametrize(
    ("edition", "fy"),
    [(58, "2076/77"), (61, "2079/80"), (63, "2081/82"), (60, "2078/79")],
)
def test_audited_fy_for_edition(edition: int, fy: str) -> None:
    assert audited_fy_for_edition(edition) == fy


def _client(payload: object, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) != API:
            return httpx.Response(404)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_discover_builds_refs_with_derived_fy() -> None:
    payload = {
        "annual_reports": [
            {
                "name": "63rd Annual Report of the Auditor General, 2083",
                "fiscal_year": {"name": "2083"},
                "files": [
                    {"location": "https://oag.gov.np/site_uploads/r63.pdf", "lang": "en"},
                    {"location": "https://oag.gov.np/site_uploads/r63-np.pdf", "lang": "ne"},
                ],
            }
        ]
    }
    refs = discover_reports(_client(payload))
    assert len(refs) == 2
    assert refs[0].edition == 63
    assert refs[0].audited_fiscal_year_bs == "2081/82"
    assert {r.language for r in refs} == {"en", "ne"}
    assert all(r.verified and r.doc_kind == "annual_report" for r in refs)


def test_discover_skips_reports_without_edition() -> None:
    payload = {"annual_reports": [{"name": "Special Audit Report", "files": [
        {"location": "https://oag.gov.np/site_uploads/x.pdf", "lang": "en"}]}]}
    assert discover_reports(_client(payload)) == []


def test_discover_raises_on_bad_payload() -> None:
    with pytest.raises(DiscoveryError):
        discover_reports(_client({"nope": 1}))
