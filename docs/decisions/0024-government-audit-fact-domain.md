# ADR-0024: Government audit reports — a distinct fact domain

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** Mother Opus; user ratified (design review, 10 revisions)
- **Tags:** schema, data-strategy, audit, oag, money-wasted

## Context

The Office of the Auditor General (OAG / महालेखापरीक्षक) publishes the audit data behind the **Money Wasted** pillar and the **Local Ledger (753)** vertical ([STRATEGY.md](../STRATEGY.md) Pillar 4, Vertical #10). Two feeds are already registered as paused stubs ([ADR-0009](0009-source-registry-single-source-of-truth.md)):

- [`oag-audit-reports`](../sources/oag-audit-reports.md) — the consolidated **Annual Report** (61st = FY 2079/80 … 63rd ≈ Rs 755 bn cumulative *beruju*). One bilingual PDF/year over four subject classes (federal, provincial, local, public corporations) with per-ministry/per-province detail and tier-level aggregates.
- [`oag-lbl-local-audits`](../sources/oag-lbl-local-audits.md) — the **753 individual local-body final audit reports** (per-municipality, mostly Nepali, often scanned → OCR-dependent).

The entire ingestion pipeline today is **time-series shaped** (`staging_indicator_values` → `approved_indicator_values`, [DATA_PIPELINE.md](../DATA_PIPELINE.md)). Audit data is not a time series. It is **entity-keyed, fiscal-year-keyed, category-classified irregularity amounts (*beruju*) plus narrative findings**. Forcing it into `indicator_values` would collapse the per-entity and per-category structure those products need, and would have no place for the qualitative findings.

No model exists for this data, so neither feed's parser can be written. This ADR locks the data model — schema, enums, repository contract, and parser-output contract — so the parsers (later PRs) only have to populate it. It deliberately reuses the extraction machinery already in the repo (tiered recovery, [`scrapers/_common/devanagari_normalization.py`](../../scrapers/_common/devanagari_normalization.py), [`scrapers/_common/municipality_resolver.py`](../../scrapers/_common/municipality_resolver.py), the OCR provenance tables in [`ocr-tracking.ts`](../../src/lib/db/schema/ocr-tracking.ts), and the findings in [`surya-ocr-findings.md`](../research/surya-ocr-findings.md)).

## Decision

Government audit reports get a **new fact domain** — three direct-to-fact-table tables, written by deterministic parsers after a reconciliation gate, never through the indicator staging pipeline. Pattern base: [`local_government_fiscal_transfers`](../../src/lib/db/schema/fiscal-transfers.ts).

1. **Three tables** ([`src/lib/db/schema/audit-facts.ts`](../../src/lib/db/schema/audit-facts.ts)):
   - `audit_entity_summaries` — headline scalars per (subject_class, entity-or-aggregate, FY): audited amount, beruju raised, settled, cumulative outstanding.
   - `audit_beruju_lines` — that beruju broken down per (`amount_basis`, `beruju_category`); tall, like `grant_type` on fiscal transfers.
   - `audit_findings` — individual structured narrative observations.

2. **Five enums** ([`enums.ts`](../../src/lib/db/schema/enums.ts)):
   - `audit_subject_class` — `federal_government | provincial_government | local_government | public_corporation | constitutional_body | committee_board_authority | other_institution`. (Named for the SUBJECT class, not "tier" — corporations and constitutional bodies are not government tiers.)
   - `beruju_category` — `recoverable | irregular | evidence_not_submitted | advance_outstanding | revenue_arrears | responsibility_not_transferred | other`. The exact source label is preserved in `beruju_category_label_raw`.
   - `audit_amount_basis` — `current_year_raised | settled_this_year | cumulative_outstanding | opening_outstanding | adjustment | other`. A single category recurs across bases.
   - `extraction_method` — `text_layer | preeti_fix | surya_ocr | manual_review` (mirrors the tiered-recovery doctrine).
   - `review_status` — `unreviewed | auto_accepted | human_verified | flagged` (default `unreviewed`).

3. **Tier-aggregate rows carry a NULL entity.** The Annual Report publishes whole-class totals that map to no single entity. `audited_entity_id` is nullable; `audit_subject_class` is always set; `aggregate_scope` (+ `aggregate_label_raw`) distinguishes multiple aggregates within one class/FY. Natural keys use **`UNIQUE NULLS NOT DISTINCT`** so re-ingesting an aggregate is a no-op, not a silent duplicate.

4. **Raw amount provenance is mandatory.** Every normalized `*_npr` is paired with the exact printed `*_raw` expression plus table-level `source_unit` and `source_scale` (the raw→NPR multiplier). Canonical stored amounts are full NPR; raw is preserved for OCR auditability.

5. **OCR provenance is recorded on the fact row.** `extraction_method`, `ocr_cell_extraction_id` (FK → `ocr_cell_extractions`, set null), `source_page`/`source_table_ref`/`source_cell_ref` (findings use `source_page_start/end` + `source_section_path`), and `review_status`.

6. **`confidence_grade` is NOT NULL with no default.** The parser must state it (Tier 0 → A, Tier 2 → B); an OCR row can never silently inherit grade A. Enforced by the Zod draft and a repository test.

7. **Finding identity is `finding_ordinal` + `source_locator_hash`, not `para_ref`.** Local reports have repeated/missing/OCR-damaged paragraph numbers. `para_ref` is retained as data only.

8. **Source precedence resolves feed overlap.** `source_precedence smallint` (annual_report = 1, local_body_report = 2). Primary rule is disjoint scoping (annual → class aggregates + non-local entities; local-body → municipalities). The safety mechanism is a precedence-guarded upsert (`ON CONFLICT DO UPDATE … WHERE excluded.source_precedence >= existing.source_precedence`), never blind `DO NOTHING`, so a stronger source never loses to a weaker one already present.

9. **The reconciliation gate is a parser-side ship requirement.** For each (entity/scope, FY), `sum(audit_beruju_lines.amount_npr)` per `amount_basis` must equal the matching summary scalar; per-entity figures must sum to the class aggregate; aggregates to the printed grand total — to the rupee, or the FY is deferred. A parser may not promote rows until a per-document validation report passes (the "Parser Ship Gate", PR D/PR E).

10. **Promotion order is whole-document-validate-then-write.** Parsers extract the full document/FY, normalize, resolve entities, build drafts, validate Zod + reconciliation, emit a validation report, and only then bulk-upsert inside one transaction. No partial fact-table promotion before reconciliation passes.

**Scope boundaries:** this ADR's work is schema + enums + migration + repositories + parser-output Zod contract + tests + enriched source profiles. It ingests no data. Corpus acquisition, the pre-ingest audit, entity seeds (provinces/ministries/departments/corporations) + a resolver extension, the parsers, and source activation are later PRs.

## Alternatives Considered

### Option A: Reuse `approved_indicator_values`
- **Pro:** No new tables; existing validation/promotion machinery.
- **Con:** Indicator values are single scalars keyed by (slug, period). Audit data is (entity × subject_class × FY × amount_basis × beruju_category) plus prose findings — the slug namespace would explode and the qualitative findings have nowhere to live.
- Rejected.

### Option B: One wide table
- **Pro:** Fewer tables.
- **Con:** Headline scalars, the category breakdown, and narrative findings are three different grains. Collapsing them forces totals to masquerade as categories and findings to share a row shape with aggregates.
- Rejected.

### Option C (chosen): Three normalized tables + raw/OCR/precedence provenance
- **Pro:** Each grain has a clean natural key; reconciliation is a queryable invariant; OCR provenance and source precedence are first-class.
- **Con:** Wider than the clean-XLSX fact tables; five new enums. Justified by OCR-heavy Nepali sources and locked here so parsers never re-migrate.
- Accepted.

## Consequences

### Positive
- The two OAG feeds have a model their parsers can populate without schema churn; the chosen "aggregates + structured findings" grain is fully expressible.
- Reconciliation (category → entity → class → grand total) is a queryable invariant, the strongest defense against OCR/parser drift.
- Raw-amount + OCR-locator + `review_status` columns make every audit number re-derivable from its source cell — the auditability the Fact Ledger rests on.
- Precedence-guarded upserts mean a local-body final report can override an annual-report local summary without a weaker number ever silently winning.

### Negative
- Five new enums and three wide tables are a larger schema surface than `fiscal_transfers`. Mitigated: enums are closed and ADR-gated; the wide columns are mostly nullable provenance.
- The fact tables now reference `ocr_cell_extractions`, coupling the audit domain to the OCR subsystem. Acceptable — the link is nullable and only set for `surya_ocr` rows.

### Neutral
- The OCR-heavy local feed (`oag-lbl-local-audits`) depends on the Surya tile-OCR harness, which currently lives in the `loving-wing-7bdcb4` worktree and must merge to `main` before that parser (PR E) is built. The schema/contract in this ADR has no such dependency.
- Domain-fact convention is preserved: no `revision_number` column. OAG restatements of a prior FY in a later report are handled by the documented roll-forward (`data_correction` event + re-parse); a `revision_number` can be added by a future migration if restatements prove common.
- Migration `0006_0007_audit_facts.sql` is additive; existing tables and migrations are unchanged.

## References

- [`src/lib/db/schema/audit-facts.ts`](../../src/lib/db/schema/audit-facts.ts) — the three tables
- [`src/lib/db/schema/enums.ts`](../../src/lib/db/schema/enums.ts) — the five enums
- [`src/lib/db/migrations/0006_0007_audit_facts.sql`](../../src/lib/db/migrations/0006_0007_audit_facts.sql) — the migration
- [`src/lib/db/repositories/audit-facts.ts`](../../src/lib/db/repositories/audit-facts.ts) — precedence-guarded upsert helpers
- [`src/lib/ingestion/audit-types.ts`](../../src/lib/ingestion/audit-types.ts) — the parser-output Zod contract
- [`docs/sources/oag-audit-reports.md`](../sources/oag-audit-reports.md) · [`docs/sources/oag-lbl-local-audits.md`](../sources/oag-lbl-local-audits.md) — the two source profiles
- [`docs/research/surya-ocr-findings.md`](../research/surya-ocr-findings.md) — Surya OCR reference (Devanagari regression #475, `--detect_boxes`, DPI cap)
- [DATA_PIPELINE.md](../DATA_PIPELINE.md) §"Confidence Grade Assignment" — A/B/C rules (OAG audit numbers = A)
- [ADR-0009](0009-source-registry-single-source-of-truth.md) — the source registry these feeds are registered in
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — production parsers stay deterministic Python
