# Pre-Ingest Recon — OAG Annual Audit Reports (`oag-audit-reports`)

**source_id:** `oag-audit-reports`
**Agency:** Office of the Auditor General (OAG / महालेखापरीक्षकको कार्यालय)
**Auditor:** Mother Opus
**Date:** 2026-06-10
**Status:** RECONNAISSANCE (pre-acquisition) — corpus not yet downloaded/archived
**Doctrine:** mirrors [docs/research/cbs-nphc-2021-audit.md](cbs-nphc-2021-audit.md); feeds [ADR-0024](../decisions/0024-government-audit-fact-domain.md) and the [oag-audit-reports](../sources/oag-audit-reports.md) profile.

> Scope of this doc: the **national consolidated Annual Report** feed. The 753 individual local-body reports (`oag-lbl-local-audits`) need their own recon (§10) and are not covered in depth here.

---

## 0. TL;DR

- OAG publishes one consolidated **Annual Report per fiscal year** as a PDF, in **two language editions**: a full **Nepali** report and a partial **English** edition. Plus a short **Report Summary** PDF (English available).
- **Verified by probe** (one file fetched + read with pdfplumber): the English edition of the **58th** report is **born-digital** (selectable text, embedded Times New Roman/Calibri + Devanagari Kalimati/Mangal fonts), 84 pages → **Tier 0** extraction, no OCR.
- **Critical trap:** the report's **title year is the submission/BS year, not the audited fiscal year**. The 58th report is titled "Annual Report, 2021 (2078)" but its foreword states it covers "audits of **fiscal year 2019/20**" = **FY 2076/77 BS**. Parsers MUST read the audited FY from the foreword, never infer it from the title.
- **Critical coverage gap:** the **English edition explicitly excludes** per-entity detail (federal ministries, provincial entities, local levels). Tier-level aggregates + major observations are in English; **per-entity rows require the Nepali edition.**
- Authority verdict: **the Nepali full report is canonical** for per-entity `audit_entity_summaries` / `audit_beruju_lines` / `audit_findings`; the English edition is sufficient only for tier/class aggregates + headline findings.
- License: Government of Nepal public document (constitutional report to the President under Art. 294). Treat as `gov_open`. **PII:** none expected (entity-level financial figures + named offices, not individuals).

---

## 1. The publication landscape

| Surface | URL | Notes |
|---|---|---|
| New site (SPA) | `https://oag.gov.np/` | JS-rendered; report PDFs live under `/site_uploads/`. Not server-scrapeable without a headless browser. |
| Legacy site | `https://old.oag.gov.np/menu-category/926/en` (Annual Report), `/930/en` (Report Summary), `/972/en` (Performance Audit) | Server-rendered listings, BUT **TLS certificate is expired** (fetch needs cert-ignore or archive.org). |
| Local-level portal | `https://oag.gov.np/local-level/report/en` | Per-local-level final reports — see §10. |
| Example probed file | `https://oag.gov.np/site_uploads/bg1-Some%20sections%20of%20Annual%20Report%202078%20English%20Version..pdf` | 58th, English, 84pp, born-digital. |

File naming is irregular (random-prefix slugs like `bg1-…`, `kwN-…`), so a stable per-edition URL pattern does NOT exist — acquisition is manual/curated, not a templated fetch. This matches the registry's `ingestion_mode: manual_upload`.

---

## 2. Edition ↔ fiscal-year mapping (anchored)

Anchored on two primary-source facts: 58th = audits of FY 2019/20 (foreword, probed) and 61st = FY 2079/80 (Rs 236 bn current-year irregularity, press coverage).

| Edition | Audited FY (BS) | Audited FY (AD) | Notes |
|---|---|---|---|
| 58th | **2076/77** | 2019/20 | Probed. Titled "2021 (2078)". Covid backlog: 133 entities unaudited. |
| 59th | 2077/78 | 2020/21 | |
| 60th | 2078/79 | 2021/22 | "Sixtieth Annual Report 2023 Summary" exists (English). |
| 61st | 2079/80 | 2022/23 | ~Rs 236 bn current-year irregularity. |
| 62nd | 2080/81 | 2023/24 | |
| 63rd | 2081/82 | 2024/25 | Latest; ~Rs 755 bn cumulative outstanding. |

**Breakage mode (confirmed):** title-year ≠ audited-FY. The `fiscal_year_bs` column must be populated from the foreword's stated audited FY, and a fixture must pin this for at least one edition.

---

## 3. Document anatomy (from the probed 58th English edition)

Six chapters:

1. Foreword (audited-FY statement, headline audited+irregularity figures, settlement)
2. Audit Objectives, Scope and Methodology
3. **Chapter 1 — Details of Audited Entities** (entity counts per tier)
4. **Chapter 2 — Status of Audit Irregularity** ← the *beruju* numbers (`audit_entity_summaries` + `audit_beruju_lines`)
5. **Chapter 3 — Major Audit Observations** ← the narrative findings (`audit_findings`)
6. **Chapter 4 — Implementation Status of Audit Reports** (settlement/follow-up)
7. (Ch. 5 Reforms; Ch. 6 Office Activities — low ingest value)

The headline figures appear in prose in the Foreword AND in tables in Ch. 1–2 — parse the **tables** as canonical; use the prose as a reconciliation cross-check.

---

## 4. English vs Nepali — the canonical-source decision

The 58th English edition states verbatim: *"This English Version … excludes the translation of specific audit observations related to the Federal Ministries & Entities, Provincial Ministries & Entities and Local Levels."*

| Need | English edition | Nepali edition |
|---|---|---|
| Tier/class aggregates (federal/provincial/local/corporation/boards/DCC totals) | ✅ present | ✅ present |
| Headline cumulative / settled / recovered | ✅ present | ✅ present |
| Major observations (top findings) | ✅ present (English prose — easy `audit_findings`) | ✅ present (Nepali) |
| **Per-entity rows** (each ministry / province / local level) | ❌ **excluded** | ✅ **only here** |

**Decision:** `audit_entity_summaries`/`audit_beruju_lines` at **aggregate (NULL-entity) grain** + headline `audit_findings` can be sourced from the **English** edition (Tier 0, low risk) — a fast first win. **Per-entity grain requires the Nepali edition** (born-digital but Devanagari → Tier 0 text + `_common/devanagari_normalization.py`, possibly Tier 1 font mapping). Sequence English-aggregates first, Nepali-per-entity second.

---

## 5. Mapping to the schema (with real probed figures, 58th / FY 2076/77)

Aggregate `audit_entity_summaries` rows (NULL entity, `aggregate_scope` per class), unit = NPR:

| audit_subject_class | aggregate_scope | audited_amount_npr | beruju_raised_npr | entities | notes (raw) |
|---|---|---|---|---|---|
| federal_government | all_federal | 1,555.81 bn | 44.39 bn (2.85%) | 3,079 | |
| provincial_government | all_provincial | 237.41 bn | 6.50 bn (2.74%) | 1,019 | |
| local_government | all_local | 815.99 bn | 40.83 bn (5%) | 699 | incl. 5 backlog; **not 753** (Covid) |
| committee_board_authority | boards_other | 163.57 bn | — | — | "Boards & Other Institutions" |
| public_corporation | all_corporations | 2,555.13 bn | — | — | +1,120.79 bn via consultation |

Headline scalars (whole-report aggregate row): `cumulative_outstanding_npr` = 418.85 bn (prior yr 418.32 bn); `settled_this_year_npr` (recovered) = 6.17 bn; total-to-be-settled = 676.41 bn. These map to `audit_amount_basis` ∈ {current_year_raised, cumulative_outstanding, settled_this_year}.

**This validates the schema** — every probed figure has a home. Note "advances not due not accounted in the irregularity figure this year" → an `audit_amount_basis`/comparability nuance to record per edition.

---

## 6. Extraction strategy

- **English aggregates + major observations:** Tier 0 (pdfplumber). Probe confirms clean text extraction. Lowest risk; ship first.
- **Nepali per-entity detail:** born-digital Devanagari (Kalimati/Mangal). Tier 0 text extraction + `_common/devanagari_normalization.py`; if the text layer is Preeti-encoded or geometry-scrambled, Tier 1 font transliteration. OCR (Tier 2) likely NOT needed for the national report (it is born-digital), unlike the local feed.
- **Reconciliation gate (ADR-0024 / ADR-0021):** per edition, tier aggregates must sum to the printed grand total ("total of NRs 3 trillion 675.92 billion has been audited"); category breakdown (Ch. 2) must sum to each tier's irregularity. Cross-check tables vs. the Foreword prose. Any mismatch → DEFER that edition.

---

## 7. Entity resolution & the seed dependency

- Aggregate rows need **no** entity (NULL + `aggregate_scope`) → English edition can ship before any entity seed.
- Per-entity rows need `entities` rows for **federal ministries/departments, 7 provinces, and corporations/boards/DCCs** — none of which are seeded yet (only the 753 `local_level` entities exist, Worker J). This is the **F1 prerequisite**. Local-level per-entity rows resolve against the existing 753 via `_common/municipality_resolver.py`.

---

## 8. Known breakage modes (for the profile + parser)

1. **Title-year ≠ audited-FY** — read FY from the foreword (confirmed).
2. **English edition omits per-entity detail** — don't expect per-ministry rows there.
3. **Legacy site TLS cert expired** — acquire from the new site / archive.org; record the working URL per edition.
4. **No stable URL pattern** — random slug prefixes; manual acquisition.
5. **Per-year coverage variance** — 699 (not 753) local levels in the 58th due to Covid backlog; "audit backlog" entities carry over. Coverage count must be recorded, never assumed = 753.
6. **Comparability shifts** — e.g. "advances not due" excluded from irregularity some years; record the basis note.
7. **Chapter/table reorganization across editions** — Ch. numbering looked stable 58th, but verify per edition; version the parser.
8. **Devanagari numerals + fonts** in the Nepali edition.

---

## 9. License / PII

Constitutional report submitted to the President (Art. 294); a public Government of Nepal document → `gov_open`. No personal data — figures are per-office/per-entity financial aggregates and named public offices. No redaction needed.

---

## 10. Local-level feed (`oag-lbl-local-audits`) — separate recon needed

Not probed here. Known: a dedicated portal (`oag.gov.np/local-level/report`) issues per-local-level final reports under Audit Act §20(2). Expectations to verify on its own recon: mostly **Nepali, frequently scanned (Tier 2 Surya OCR), heterogeneous per-municipality layouts, per-FY coverage gaps**, and dependence on the Surya harness merging from `loving-wing-7bdcb4`. A separate `docs/research/oag-lbl-local-audits-audit.md` should precede PR E.

---

## 11. Acquisition checklist (toward PR D)

Before the parser PR, acquire + archive (immutable `source_documents`, content-addressed) at minimum:

- [ ] Latest 3 editions, **both** language versions: 63rd (2081/82), 62nd (2080/81), 61st (2079/80) — Nepali (per-entity) + English (aggregates).
- [ ] The matching **Report Summary** PDFs (English) for cross-check.
- [ ] Record per file: working URL, edition, **audited FY (from foreword)**, language, sha256, page count, born-digital/scanned.
- [ ] Build a fixture from the probed 58th English edition (Ch. 1–2 pages) + one Nepali edition page (per-entity table) with a hand-verified `expected.json`.
- [ ] Confirm the reconciliation identity holds on the fixture before wiring the full parser.

**Sequencing recommendation (Mother's call):** PR C-entity-seeds (provinces/ministries/corporations) can proceed in parallel now (no corpus needed). PR D should ship **English-aggregates first** (Tier 0, NULL-entity rows — fast, low-risk, immediately useful to Money Wasted), then add **Nepali per-entity** rows once entity seeds land.
