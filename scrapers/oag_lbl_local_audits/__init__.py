"""OAG local-body audit-report acquisition scraper (source_id: oag-lbl-local-audits).

API-based discovery + content-addressed archival of the 753 local levels'
individual final audit reports. The OAG site is a JS SPA, but its backend
exposes a clean JSON API (`/api/front/local-level-report?page=N`, ~601 pages /
6,000+ reports) that this scraper paginates. See README.md, ADR-0024, and
docs/research/oag-lbl-local-audits-audit.md.
"""
