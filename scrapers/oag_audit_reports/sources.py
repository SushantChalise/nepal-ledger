"""Curated catalog of OAG audit reports to acquire.

The new OAG site (oag.gov.np) is a JS SPA with no stable report-URL pattern,
and the legacy site (old.oag.gov.np) serves an expired TLS certificate — so
there is no reliable crawl. Acquisition is therefore curated
(``ingestion_mode = manual_upload``): each report's PDF URL is recorded here
as a ``ReportRef`` and the archiver downloads + content-addresses + provenances
it deterministically.

Adding a report: open it on oag.gov.np, copy the ``/site_uploads/<...>.pdf``
URL, and append a ``ReportRef``. Set ``verified=True`` only once the URL has
been fetched successfully. See README.md and
docs/research/oag-audit-reports-audit.md for the edition<->FY mapping and the
English-vs-Nepali canonical-source decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

Language = Literal["en", "ne"]
DocKind = Literal["annual_report", "report_summary"]

SOURCE_ID: Final[str] = "oag-audit-reports"


@dataclass(frozen=True)
class ReportRef:
    """One acquirable OAG report PDF, with provenance metadata."""

    edition: int  # the report's ordinal (58th, 61st, ...)
    audited_fiscal_year_bs: str  # the FY the report AUDITED, e.g. "2076/77"
    language: Language
    doc_kind: DocKind
    title: str
    url: str
    verified: bool  # True only after the URL has been fetched successfully
    notes: str = ""
    source_id: str = SOURCE_ID

    @property
    def ref_key(self) -> str:
        """Stable key for manifest correlation + catalog dedup."""
        return f"{self.edition}-{self.language}-{self.doc_kind}"


# Curated catalog. Seeded with the one report verified by fetch+read (the 58th
# English edition — born-digital, pdfplumber-clean). Extend as URLs are
# collected from the SPA. Known historical URLs live on the legacy domain
# (old.oag.gov.np, expired cert) — see README.md before adding those.
KNOWN_REPORTS: Final[tuple[ReportRef, ...]] = (
    ReportRef(
        edition=58,
        audited_fiscal_year_bs="2076/77",
        language="en",
        doc_kind="annual_report",
        title="Auditor General's 58th Annual Report, 2021 (2078) — English (selected sections)",
        url=(
            "https://oag.gov.np/site_uploads/"
            "bg1-Some%20sections%20of%20Annual%20Report%202078%20English%20Version..pdf"
        ),
        verified=True,
        notes=(
            "Born-digital (pdfplumber-clean), 84pp. Audited FY from foreword = "
            "2019/20 = BS 2076/77 (title year 2078 != audited FY). The English "
            "edition excludes per-entity detail; per-entity rows need the Nepali "
            "edition."
        ),
    ),
)


def select_reports(
    reports: tuple[ReportRef, ...] = KNOWN_REPORTS,
    *,
    editions: frozenset[int] | None = None,
    language: Language | None = None,
) -> list[ReportRef]:
    """Filter the catalog by edition / language. ``None`` = no filter on that axis."""
    out: list[ReportRef] = []
    for ref in reports:
        if editions is not None and ref.edition not in editions:
            continue
        if language is not None and ref.language != language:
            continue
        out.append(ref)
    return out
