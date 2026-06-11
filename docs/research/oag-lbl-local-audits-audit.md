# Pre-Ingest Recon — OAG Local-Body Audit Reports (`oag-lbl-local-audits`)

**source_id:** `oag-lbl-local-audits`
**Agency:** Office of the Auditor General (OAG / महालेखापरीक्षकको कार्यालय)
**Auditor:** Mother Opus
**Date:** 2026-06-11
**Status:** RECONNAISSANCE (pre-acquisition) — corpus not yet downloaded/archived
**Doctrine:** companion to [oag-audit-reports-audit.md](oag-audit-reports-audit.md); feeds [ADR-0024](../decisions/0024-government-audit-fact-domain.md) and the [oag-lbl-local-audits](../sources/oag-lbl-local-audits.md) profile.

> The national consolidated report is covered in [oag-audit-reports-audit.md](oag-audit-reports-audit.md). This doc covers the **753 individual local-body final audit reports** feed.

---

## 0. TL;DR

- Under **Audit Act 2075 §20(2)**, OAG issues an **individual final audit report per local level** (municipality / rural municipality) each fiscal year. These are published on a dedicated, **paginated portal** — `oag.gov.np/local-level/report/en` (~89+ pages observed) — plus a **search interface** `oag.gov.np/local-level/search-report/en`. Legacy per-FY listings exist on `old.oag.gov.np/menu-category/1169/en` (expired TLS cert).
- There is also a backend **NAMS — Nepal Audit Management System** (`nams.oag.gov.np`) — a potentially richer/structured source worth probing (likely auth-gated).
- Expected format: **PDF, Nepali-dominant, frequently scanned → Tier 2 Surya OCR**. Per-municipality layouts are **heterogeneous** (no single template).
- Coverage **varies per FY**: the 58th report audited 749/753 + backlogs; never assume a full 753 in any year.
- **Not yet probed at the file level** (the portal is a JS SPA; individual report URLs were not fetched in this recon). What IS established: the feed exists, is per-local-level, is paginated, and is governed by §20(2).
- **Hard dependency:** the Surya tile-OCR harness (`scrapers/surya_ocr/`, currently in the `loving-wing-7bdcb4` worktree) must reach `main` before this feed's parser (PR E) can be built. Entity resolution is already unblocked — the 753 `local_level` entities are seeded.

---

## 1. The publication landscape

| Surface | URL | Notes |
|---|---|---|
| Local-level report portal | `https://oag.gov.np/local-level/report/en` | Paginated (`?page=N`, ~89+ pages). JS SPA shell; the `?page=N` query param is a real discovery seam (see §6). |
| Search interface | `https://oag.gov.np/local-level/search-report/en` | Query by local level / FY — the likely path to a specific report. |
| Legacy per-FY listing | `https://old.oag.gov.np/menu-category/1169/en` ("Audit report of local body / level 2074") | Server-rendered but **expired TLS cert**. |
| NAMS backend | `https://nams.oag.gov.np/` | Audit Management System — potential structured source; probe separately (likely requires auth). |
| Demo env | `https://demo.oagnep.gov.np/local-level/report/en` | Staging mirror — useful for safe structure probing. |

`ingestion_mode = manual_upload` stands, but the **paginated portal is a more promising discovery seam than the national SPA** — see §6.

---

## 2. What each report contains (expected)

Each local-level final report is the per-municipality detail behind the national report's local-tier aggregate: audited amount, **beruju** by category, settlement, cumulative outstanding, and paragraph-level findings (the specific misuse — vehicle purchases, view towers, unspent conditional grants, procurement irregularities). To confirm field-by-field, a real report must be probed on acquisition.

---

## 3. Mapping to the schema (ADR-0024)

All rows are `audit_subject_class = 'local_government'` with a resolved municipality entity:

- `audit_entity_summaries` — per (local level, FY) headline scalars. **`source_precedence = 2`** so a local-body final report **overrides** the annual report's local summary on overlap.
- `audit_beruju_lines` — per-municipality beruju by `amount_basis` × `beruju_category`.
- `audit_findings` — the individual observations (the investigative detail for "What Did Your Municipality Do With Your Money?").

The aggregate-row / NULL-entity machinery is not needed here (every row is a specific local level).

---

## 4. Extraction strategy

- **Tier 2 Surya OCR** is the expected default (Nepali scans), via the tile-OCR harness + `scrapers/_common/devanagari_normalization.py`. Some reports may be born-digital (Tier 0) — detect per file (`avg_words/page < ~10` ⇒ scanned).
- **Entity resolution:** municipality names resolve to the seeded 753 `local_level` entities via `scrapers/_common/municipality_resolver.py` (≥85 auto, 70–85 review, <85 **park** — never invents). The province seed (PR #45) adds the provincial parents if needed.
- **Reconciliation gate (ADR-0024 / ADR-0021):** each report's category lines must sum to its entity totals; and, as a cross-feed check, the sum of all local-body reports for an FY should reconcile to the national report's local-tier aggregate (a powerful consistency check unique to this feed).

---

## 5. Known breakage modes (for the profile + parser)

1. **Nepali-only + scanned** — Tier 2 OCR is the norm; Devanagari regression #475 mitigations apply.
2. **Heterogeneous per-municipality layouts** — 753 templates; parser must reconstruct tables from OCR cells, not assume structure.
3. **Per-FY coverage variance** — 749/753 + backlogs in the 58th; coverage count recorded, never assumed = 753; absences labelled "data discontinuity", never fabricated.
4. **Volume** — up to 753 documents/FY → scope-fenced worker batches (cf. the P2/P3 batch pattern).
5. **Legacy-site TLS cert expired**; new portal is a SPA — acquisition is curated/paginated, not a naive crawl.
6. **Entity-name drift** — spelling/Romanization variants; resolved (not guessed) via the fuzzy resolver; sub-threshold rows park.

---

## 6. Acquisition approach (toward a local scraper, PR ≥ E)

Two avenues, in preference order:

1. **Paginated portal discovery.** Unlike the national SPA, the local portal exposes `?page=N`. Probe whether `oag.gov.np/local-level/report/en?page=N` (and/or its underlying JSON API — inspect the SPA's network calls) returns enumerable report links server-side. If so, a discovery step can paginate N=1..last and harvest per-report PDF URLs — a real crawl, feeding the same `archive` + `manifest` machinery the national scraper (`scrapers/oag_audit_reports/`) already has. **This needs a live probe to confirm; not done in this recon.**
2. **NAMS API.** Investigate `nams.oag.gov.np` for a structured/bulk endpoint. Likely auth-gated; treat as a stretch source.
3. **Fallback: curated catalog** (as the national scraper does) for targeted local levels (e.g. the District MRI's 5 Year-1 districts), if bulk discovery proves unreliable.

The national `scrapers/oag_audit_reports/` package (archive/manifest/cli) is directly reusable; a local feed adds a **discovery** module (the paginated-portal harvester) — mirroring `scrapers/nso_archive`'s `discover.py`.

---

## 7. License / PII

Constitutional public documents under Audit Act §20(2) → `gov_open`. No personal data — per-office financial figures + named local levels. No redaction.

---

## 8. Dependencies & sequencing

- **Blocked on:** the Surya tile-OCR harness reaching `main` (from `loving-wing-7bdcb4`) — OCR-heavy by nature.
- **Unblocked:** entity resolution (753 `local_level` entities seeded; provinces in PR #45).
- **Recommended sequence:** (a) land the national feed first (PR D — Tier 0, fast); (b) once Surya is on `main`, do a **live probe** of the local portal pagination / NAMS to pick the acquisition avenue (§6); (c) build the local scraper's discovery module + the OCR parser as a batched PR (PR E), starting with the District MRI's 5 Year-1 districts before fanning out to all 753.

## 9. Open items to resolve on acquisition

- [ ] Live-probe `oag.gov.np/local-level/report/en?page=N` — server-rendered links or JSON API? Enumerable?
- [ ] Probe NAMS for a structured endpoint.
- [ ] Fetch 3–5 representative local reports (mix of provinces + local-level types) — confirm Tier (scanned vs digital), table structure, beruju category labels, and the entity-name forms used.
- [ ] Confirm the cross-feed reconciliation (Σ local reports for an FY ≈ national local-tier aggregate).
- [ ] Decide batch sizing (per-province? per-district?) for the 753-document ingestion.
