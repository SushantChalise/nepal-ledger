"""Discover OAG Annual Reports from the backend JSON API.

The SPA's backend serves the recent annual reports at:

    GET https://oag.gov.np/api/front/annual-reports
    -> { "annual_reports": [ { "name": "63rd Annual Report ... 2083",
                               "fiscal_year": {"name": "2083"},
                               "files": [ {"location": "...pdf", "lang": "en"} ] } ] }

The API exposes the PUBLISH year only (e.g. "2083"); the AUDITED fiscal year is
derived from the edition ordinal (the 58th report audited FY 2076/77 — see
docs/research/oag-audit-reports-audit.md). This module fetches the endpoint and
yields the curated-catalog `ReportRef` type, so it slots into the same archive
machinery as `sources.KNOWN_REPORTS`.
"""

from __future__ import annotations

import re
from typing import Any, Final, cast

import httpx

from oag_audit_reports.sources import Language, ReportRef

API_URL: Final[str] = "https://oag.gov.np/api/front/annual-reports"
_HTTP_ERROR_MIN: Final[int] = 400
# Edition 58 audited FY 2076/77 (probed); edition N audited FY (2076+(N-58))/...
_BASE_EDITION: Final[int] = 58
_BASE_FY_START: Final[int] = 2076
_EDITION_RE: Final[re.Pattern[str]] = re.compile(r"\b(\d{1,3})(?:st|nd|rd|th)\b", re.IGNORECASE)


class DiscoveryError(RuntimeError):
    """Raised on an unrecoverable API failure."""


def audited_fy_for_edition(edition: int) -> str:
    """Map an OAG report edition ordinal to its audited fiscal year ("2081/82")."""
    start = _BASE_FY_START + (edition - _BASE_EDITION)
    return f"{start}/{(start + 1) % 100:02d}"


def _edition_from_name(name: str) -> int | None:
    m = _EDITION_RE.search(name)
    return int(m.group(1)) if m else None


def _refs_from_report(rep: dict[str, Any]) -> list[ReportRef]:
    name = str(rep.get("name") or "").strip()
    edition = _edition_from_name(name)
    if edition is None:
        return []
    audited = audited_fy_for_edition(edition)
    out: list[ReportRef] = []
    files = rep.get("files")
    if not isinstance(files, list):
        return out
    for f in files:
        if not isinstance(f, dict):
            continue
        url = f.get("location")
        if not isinstance(url, str) or not url.lower().endswith(".pdf"):
            continue
        lang_raw = str(f.get("lang") or "ne").lower()
        language: Language = cast(Language, lang_raw) if lang_raw in ("en", "ne") else "ne"
        out.append(
            ReportRef(
                edition=edition,
                audited_fiscal_year_bs=audited,
                language=language,
                doc_kind="annual_report",
                title=name,
                url=url,
                verified=True,
                notes="Discovered via /api/front/annual-reports.",
            )
        )
    return out


def discover_reports(client: httpx.Client, *, timeout_s: int = 30) -> list[ReportRef]:
    """Fetch the annual-reports API and return a `ReportRef` per report file."""
    try:
        resp = client.get(API_URL, timeout=timeout_s)
    except httpx.HTTPError as exc:
        raise DiscoveryError(f"network failure fetching {API_URL}: {exc!r}") from exc
    if resp.status_code >= _HTTP_ERROR_MIN:
        raise DiscoveryError(f"HTTP {resp.status_code} fetching {API_URL}")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise DiscoveryError(f"response was not JSON: {exc}") from exc
    reports = payload.get("annual_reports") if isinstance(payload, dict) else None
    if not isinstance(reports, list):
        raise DiscoveryError("API payload missing 'annual_reports' array")
    out: list[ReportRef] = []
    for rep in reports:
        if isinstance(rep, dict):
            out.extend(_refs_from_report(rep))
    return out
