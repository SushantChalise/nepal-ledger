"""OAG audit-report acquisition scraper (source_id: oag-audit-reports).

A curated-catalog fetch+archive tool, NOT an HTML crawler: the new OAG site is
a JS SPA with no stable report-URL pattern and the legacy site serves an
expired TLS certificate, so report PDF URLs are curated in ``sources.py`` and
downloaded deterministically with content-addressing + a provenance manifest.
See README.md and docs/research/oag-audit-reports-audit.md (ADR-0010).
"""
