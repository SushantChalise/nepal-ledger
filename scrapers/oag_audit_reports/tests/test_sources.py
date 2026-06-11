"""Tests for oag_audit_reports.sources — the curated catalog + selection."""

from __future__ import annotations

from oag_audit_reports.sources import KNOWN_REPORTS, SOURCE_ID, ReportRef, select_reports


def test_catalog_is_non_empty_and_well_formed() -> None:
    assert len(KNOWN_REPORTS) >= 1
    for ref in KNOWN_REPORTS:
        assert ref.source_id == SOURCE_ID
        assert ref.url.startswith("https://")
        assert ref.title
        assert ref.language in ("en", "ne")
        assert ref.doc_kind in ("annual_report", "report_summary")
        # FY label is "YYYY/YY".
        assert "/" in ref.audited_fiscal_year_bs


def test_ref_keys_are_unique() -> None:
    keys = [r.ref_key for r in KNOWN_REPORTS]
    assert len(keys) == len(set(keys))


def test_verified_seed_entry_present() -> None:
    verified = [r for r in KNOWN_REPORTS if r.verified]
    assert any(r.edition == 58 and r.language == "en" for r in verified)


def test_ref_key_shape() -> None:
    ref = ReportRef(
        edition=61,
        audited_fiscal_year_bs="2079/80",
        language="ne",
        doc_kind="report_summary",
        title="t",
        url="https://oag.gov.np/x.pdf",
        verified=False,
    )
    assert ref.ref_key == "61-ne-report_summary"


def test_select_reports_filters_by_edition_and_language() -> None:
    catalog = (
        ReportRef(58, "2076/77", "en", "annual_report", "a", "https://x/a.pdf", True),
        ReportRef(58, "2076/77", "ne", "annual_report", "b", "https://x/b.pdf", False),
        ReportRef(61, "2079/80", "en", "annual_report", "c", "https://x/c.pdf", False),
    )
    assert len(select_reports(catalog)) == 3
    assert len(select_reports(catalog, editions=frozenset({58}))) == 2
    assert len(select_reports(catalog, language="en")) == 2
    only = select_reports(catalog, editions=frozenset({58}), language="ne")
    assert len(only) == 1
    assert only[0].url == "https://x/b.pdf"
