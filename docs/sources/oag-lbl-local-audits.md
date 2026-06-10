# Source: Office of the Auditor General — Local-body audit reports (OAG-LBL)

**source_id:** `oag-lbl-local-audits`  
**Status:** paused  
**Tier:** Tier 4  
**Registered at:** 2026-05-14  
**Last verified:** 2026-06-10

> Profile enriched under [ADR-0024](../decisions/0024-government-audit-fact-domain.md). Status stays `paused` until the parser ships (flips to `active` on the PR-E parser).

## What this is

The Auditor General's **individual final audit reports for the 753 local levels** (अन्तिम लेखापरीक्षण प्रतिवेदन) — one report per metropolitan/sub-metropolitan/municipality/rural-municipality, published per fiscal year. Where `oag-audit-reports` gives the *local-tier aggregate*, this feed gives the *per-municipality detail*: each local level's audited amount, beruju by category, settlement, cumulative outstanding, and paragraph-level findings. This is the data behind "What Did Your Municipality Do With Your Money?" — the per-unit half of **Budget Watch + Local Ledger (753)**.

## Publication

- URL: https://oag.gov.np/local-level/report/en (local-level report portal)
- Frequency: annual, per local level
- Format: pdf — **mostly Nepali, frequently scanned** (no usable text layer)
- Reporting period type: annual
- Requires table extraction: yes (+ OCR)

## What we extract

Same three audit tables as `oag-audit-reports`, but all rows are `audit_subject_class = 'local_government'` with a resolved municipality entity:

- `audit_entity_summaries` — per (local level, FY) headline scalars. `source_precedence = 2`, so a local-body final report **overrides** the annual report's local summary on overlap.
- `audit_beruju_lines` — per-municipality beruju by `amount_basis` × `beruju_category`.
- `audit_findings` — the individual observations that name specific misuse (vehicle purchases, view towers, unspent grants).

## Provenance

- Confidence default: B (OCR-heavy; A only for the rare born-digital report).
- License: gov_open
- Ingestion mode: manual_upload
- Reporting period type: annual

## Extraction strategy

Heavily **Tier 2 Surya OCR** ([surya-ocr-findings.md](../research/surya-ocr-findings.md)) — Nepali scans through the tile-OCR harness + `scrapers/_common/devanagari_normalization.py`. Municipality names resolve to the 753 seeded `entities` via `scrapers/_common/municipality_resolver.py` (≥85 auto-accept, 70–85 review, <85 park — **never invents an entity**). Reconciliation gate per report (category → entity totals) before any promotion.

> **Dependency:** the Surya tile-OCR harness (`scrapers/surya_ocr/`) + ADR-0021/0022 currently live in the `loving-wing-7bdcb4` worktree and must merge to `main` before this parser (PR E) can be built.

## Known breakage modes

- **Nepali-only + scanned** — Tier 2 OCR is the norm; Devanagari regression #475 mitigations apply.
- **Heterogeneous per-municipality formats** — 753 layouts; no single template. Parser must reconstruct tables from OCR cells, not assume structure.
- **Entity-name drift** — municipality names appear with spelling/Romanization variants; resolved (not guessed) via the fuzzy resolver; sub-threshold rows park for review.
- **Coverage gaps** — not every local level publishes every FY; absences are labelled "data discontinuity", never fabricated forward.
- **Volume** — up to 753 documents/FY; ingested in scope-fenced worker batches (cf. the P2/P3 batch pattern).

## Revision policy

Same as `oag-audit-reports`: beruju is cumulative and settled over years; new FY rows per `fiscal_year_bs`; restatements roll forward via `data_correction`, never overwrite.

## Parser

- Path: `scrapers/oag_lbl_local_audits/parser.py` (planned — PR E, after the Surya harness merges)
- Version: pending
- Owner: Mother Opus
- Tested against: `scrapers/oag_lbl_local_audits/fixtures/` (planned)

## Archive policy

Every downloaded report stored immutably in Supabase Storage under `oag-lbl-local-audits/<yyyy-mm-dd>/<filename>` with sha256 in `source_documents`. Never overwritten.

## Recent ingests

None yet — paused pending the Surya harness merge, corpus acquisition + pre-ingest audit (PR C), and parser (PR E).
