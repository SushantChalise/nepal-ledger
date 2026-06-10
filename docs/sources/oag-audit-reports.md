# Source: Office of the Auditor General — Annual audit reports (federal + sectoral)

**source_id:** `oag-audit-reports`  
**Status:** paused  
**Tier:** Tier 3  
**Registered at:** 2026-05-14  
**Last verified:** 2026-06-10

> Profile enriched under [ADR-0024](../decisions/0024-government-audit-fact-domain.md). Status stays `paused` until the parser ships (flips to `active` on the PR-D parser).

## What this is

The Auditor General's **consolidated Annual Report** (संवैधानिक निकायको वार्षिक प्रतिवेदन) — the headline audit of all government money. Each edition covers one fiscal year across four audit-subject classes: **federal, provincial, local, and public corporations** (plus constitutional bodies and committees/boards). The defining metric is **beruju** (बेरुजु) — flagged audit irregularities — reported per subject and aggregated by class: amount audited, beruju raised this year, settled (फर्स्यौट), and cumulative outstanding. Recent editions: 61st (FY 2079/80, ~Rs 236 bn raised), 62nd (FY 2080/81), 63rd (FY 2081/82, ~Rs 755 bn cumulative outstanding). This is the spine of the **Money Wasted** pillar and the federal half of **Budget Watch + Local Ledger**.

## Publication

- URL: https://oag.gov.np/ — Report Summary at https://oag.gov.np/menu-category/930/en; full PDFs under old.oag.gov.np/uploads
- Frequency: annual (released several months after FY close, typically around the budget session)
- Format: pdf — bilingual (full Nepali report + a separate English summary)
- Reporting period type: annual (Shrawan 1 → Ashadh end of the audited FY)
- Requires table extraction: yes

## What we extract

Into the audit fact domain ([ADR-0024](../decisions/0024-government-audit-fact-domain.md)):

- `audit_entity_summaries` — per (subject_class, entity-or-aggregate, FY): audited amount, beruju raised, settled this year, cumulative outstanding. Tier/class aggregates carry a NULL entity + `aggregate_scope`.
- `audit_beruju_lines` — that beruju broken down per `amount_basis` × `beruju_category` (recoverable / irregular / evidence-not-submitted / advance-outstanding / …).
- `audit_findings` — individual structured narrative observations (paragraph-level), classified and amount-tagged where the report gives one.

## Provenance

- Confidence default: A for text-layer figures; B for OCR-recovered values (parser sets per row, never inherited).
- License: gov_open
- Ingestion mode: manual_upload
- Reporting period type: annual

## Extraction strategy

Tiered recovery ([surya-ocr-findings.md](../research/surya-ocr-findings.md)): the English summary and recent Nepali editions are largely born-digital (Tier 0 pdfplumber); older/scanned editions fall to Tier 2 Surya OCR with `scrapers/_common/devanagari_normalization.py`. The **reconciliation gate** is mandatory: beruju category lines must sum to the entity's beruju total, per-entity to the class aggregate, and class aggregates to the printed grand total — to the rupee, or that FY is deferred (Parser Ship Gate, ADR-0024).

## Known breakage modes

- **Summary-table reorganization across editions** — the 60th/61st/62nd/63rd reports reshuffle which table carries which aggregate; parser must be version-/edition-conditional.
- **Devanagari OCR regression #475** — scanned editions need the detection-predictor + line-level path; null text is a bug, not "no data".
- **`TABLE_REC_MAX_BOXES=150` truncation** — long beruju schedules silently truncate unless the env var is raised per run.
- **Bilingual mismatch** — the English summary rounds/aggregates differently from the Nepali full tables; the Nepali tables are authoritative for amounts.
- **FY-label formatting** — `आ.व. 2079/80` / `2079।80` must normalize to canonical `"2079/80"`.

## Revision policy

Beruju is **cumulative and settled over time**: each year's report restates the prior cumulative outstanding net of settlement (फर्स्यौट). We model each FY's figures as new rows keyed by `fiscal_year_bs`; a later report's restatement of a prior FY rolls forward via a `data_correction` event + re-parse, never a silent overwrite.

## Parser

- Path: `scrapers/oag_audit_reports/parser.py` (planned — PR D)
- Version: pending
- Owner: Mother Opus
- Tested against: `scrapers/oag_audit_reports/fixtures/` (planned)

## Archive policy

Every downloaded report stored immutably in Supabase Storage under `oag-audit-reports/<yyyy-mm-dd>/<filename>` with sha256 in `source_documents`. Never overwritten.

## Recent ingests

None yet — paused pending corpus acquisition + pre-ingest audit (PR C) and parser (PR D).
