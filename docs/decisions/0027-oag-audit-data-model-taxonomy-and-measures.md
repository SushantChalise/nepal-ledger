# ADR-0027: OAG audit data model — taxonomy lookup + presentation/measure separation

- **Status:** Accepted
- **Date:** 2026-06-11
- **Deciders:** Mother Opus; user ratified (independent review: 2 Claude reviewers + OpenAI Codex second opinion)
- **Tags:** schema, data-strategy, audit, oag, money-wasted
- **Amends:** [ADR-0024](0024-government-audit-fact-domain.md) (the audit fact domain). ADR-0024 stays accepted; this ADR revises its `beruju_category` representation and adds two fact tables + presentation/measure columns.

## Context

ADR-0024 locked the audit fact domain (`audit_entity_summaries`, `audit_beruju_lines`, `audit_findings`) and the first national parser shipped against it ([PR #67](https://github.com/SushantChalise/nepal-ledger/pull/67), English aggregates). An independent review of that parser — two Claude reviewers plus an OpenAI Codex second opinion, all probing the real 58th-edition PDF — found the extraction **correct but narrow**, and surfaced a **structural** flaw in the data model that the "it reconciles to the rupee" check had masked.

### What the review found

1. **A reconciled total does not prove correct extraction.** The parser proved arithmetic consistency against one printed grand total (NRs 104,384.3 M) while two `beruju_category` mappings were semantically wrong and the model conflated three distinct concerns.

2. **`beruju_category` conflated taxonomy, presentation, and measure.** The single flat enum mixed *what kind* of irregularity (taxonomy), *what level* a row sits at (leaf / subtotal / grand total), and silently dropped the report's own parent rows to avoid double-counting — which also destroyed the ability to verify "printed subtotal == sum of leaves."

3. **Two category mappings were wrong** (checked against the OAG's own taxonomy, printed on p33 of the 58th report): `balance not brought forward → responsibility_not_transferred` and `reimbursement not received → revenue_arrears`. Both are sub-types of *to be regularized*; the second collided with the genuinely separate "Revenue Arrears" stock figure (NRs 215,568.7 M) that the report keeps on its own table (p35).

4. **The unique key was insufficient.** `(audit_subject_class, audited_entity_id, aggregate_scope, fiscal_year_bs, amount_basis, beruju_category)` cannot tell apart the same category appearing in the *classification* table, the *settlement* table, and the *per-ministry* table — different meanings, same key → the precedence-guarded upsert would erase or merge incompatible rows the moment per-ministry / settlement lines are added.

5. **Whole tables of in-domain data were unmodelled:** per-ministry beruju (p36–37, which *reconciles to the federal aggregate* — disproving ADR-0024's assumption that per-entity detail needs the Nepali edition), the outstanding-stock table (p35: revenue arrears, foreign reimbursements, audit backlogs, overdue principal), the Section-38 paragraph-count reconciliation (p51), and ~157 numbered recommendations (Ch.5) for `audit_findings`.

### The OAG's own beruju taxonomy (authoritative — printed on p33, per the Audit Act)

> Three main categories — **recoverable**, **to be regularized**, **advance** — each with leaves:
> - recoverable → *embezzled & falsified*, *loss & damage*, *other recoverable*
> - to be regularized → *irregular*, *evidences/documents not submitted*, *balances not brought forward*, *reimbursement not received*
> - advance → *staff advance*, *mobilization advance*, *other institutional advance*

The reports tabulate at **variable granularity**: "Recoverable" appears as a single line in the Ch.2 classification table but could appear as its three leaves elsewhere; "Advance" appears as a parent total *and* its three sub-rows on the same page.

## Decision

Separate the three conflated concerns. Model the **taxonomy** as a seeded **lookup table** (not a `pgEnum`), and add explicit **presentation** and **source-identity** columns so reconciliation is level-aware and rows from different source tables never collide.

### 1. Taxonomy → `beruju_categories` lookup table (replaces the `beruju_category` enum)

A seeded reference table is the single source of truth for the OAG taxonomy:

| column | notes |
|---|---|
| `code` (PK, text) | stable code, e.g. `recoverable`, `tbr_irregular`, `tbr_evidence_not_submitted`, `tbr_balance_not_brought_forward`, `tbr_reimbursement_not_received`, `adv_staff`, `adv_mobilization`, `adv_other_institutional`, `rec_embezzled_falsified`, `rec_loss_damage`, `rec_other`, `other` |
| `main_category` (text) | `recoverable` \| `to_be_regularized` \| `advance` \| `other` |
| `name_en`, `name_ne` | display labels |
| `act_reference` | the Audit Act clause, where known |
| `display_order` (int) | report order |

`audit_beruju_lines.beruju_category` becomes a **FK → `beruju_categories.code`** (restrict). `main_category` is reached by join (the lookup is the source of truth; not denormalized).

**Why a lookup table, not `pgEnum` (diverges from repo convention; the divergence is the point):** every other fact domain uses `pgEnum`, and the OAG taxonomy is statutorily fixed — so a `pgEnum` *would* be defensible. We chose the lookup table deliberately for: (a) carrying `name_en`/`name_ne`/`act_reference`/`display_order` as data rather than code comments; (b) avoiding Postgres's `ALTER TYPE ADD VALUE` constraints (can't run in a transaction on older PG, values can't be dropped) while the model is still settling; (c) letting the parser's category map join against rows instead of hard-coding enum members. The cost is heavier joins and one non-conventional table — accepted, and recorded here so the inconsistency is intentional, not drift.

The legacy `beruju_category` `pgEnum` (which contained the two wrong values `revenue_arrears` + `responsibility_not_transferred`) is **dropped** — the audit tables hold zero rows today, so there is no backfill.

### 2. Presentation + measure columns on `audit_beruju_lines` (these are NOT taxonomy → small fixed `pgEnum`s are correct)

- `aggregation_role` `pgEnum`: `detail` | `subtotal` | `grand_total`. **Parent/total rows are stored, not skipped** — tagged `subtotal`/`grand_total` and excluded from default analytical sums. This preserves source fidelity and lets reconciliation check printed-subtotal == Σ leaves.
- `value_origin` `pgEnum`: `printed` | `computed`. A row lifted from the report is `printed`; a parser-derived rollup is `computed`.
- `source_table_code` (text): which source table the row came from, e.g. `ch2_irregularity_classification`, `ch2_settlement`, `ch1_audited_by_class`, `ch_federal_by_ministry`. Documented convention, not an enum (source tables vary by edition).
- keep `beruju_category_label_raw` + add `source_row_label` (the exact printed row label).

**Revised unique key** (`NULLS NOT DISTINCT`):
`(source_document_id, audit_subject_class, audited_entity_id, aggregate_scope, fiscal_year_bs, amount_basis, beruju_category, aggregation_role, source_table_code)`.
Adding `source_table_code` + `aggregation_role` is what stops the cross-table collision in finding #4.

### 3. Entity hierarchy — reuse the existing `entity_kind`

No new `entity_level` enum. `entities.kind` already has `ministry`, `department`, `province`, `local_level`, `public_enterprise`, etc. Per-ministry rows (p36–37) FK `audited_entity_id` → an `entities` row with `kind='ministry'`; the level is read from the entity. Ministries are seeded document-grounded (from the report's own ministry list) in the per-ministry PR.

### 4. Two new fact tables (p35 and p51 are different *measures* — they do not belong in `beruju_lines`)

**`audit_financial_stocks`** — outstanding-balance stock tables (p35). One row per (report, FY, subject_class/entity, `stock_type`):
- `stock_type` `pgEnum`: `audit_backlog` | `revenue_arrears` | `foreign_grant_reimbursable` | `foreign_loan_reimbursable` | `overdue_principal` | `overdue_interest` | `other`.
- `opening_npr/raw`, `addition_npr/raw`, `settlement_npr/raw`, `adjustment_npr/raw`, `closing_npr/raw` + `source_unit`/`source_scale` + shared provenance.
- Identity `closing = opening + addition − settlement ± adjustment` is a reconciliation gate.
- **`revenue_arrears` lives here, never again as a `beruju_category`** (that conflation was the original bug).

**`audit_paragraph_metrics`** — Section-38 record reconciliation (p51): counts (and optional amounts) of audit paragraphs, not money classified by type. One row per (report, FY, subject_class/entity, `paragraph_status`):
- `paragraph_status` `pgEnum`: `issued` | `settled_on_response` | `carried_forward` | `remaining`.
- `paragraph_count` (int), `amount_npr/raw` (nullable) + `source_unit`/`source_scale` + shared provenance.

`audit_findings` stays textual (titles/narrative/recommendations) — it does **not** carry paragraph counts.

### 5. Settlement lifecycle → real `amount_basis` lines (not just summary scalars)

The p34 settlement table's columns become `audit_beruju_lines` rows at `source_table_code='ch2_settlement'` with `amount_basis ∈ {opening_outstanding, adjustment, settled_this_year, cumulative_outstanding}` (the enum already has these). The headline `settled_this_year` / `cumulative_outstanding` continue to also live on `audit_entity_summaries` as the denormalized headline scalars.

### 6. Reconciliation strategy — level-aware, multi-source (a total alone is not enough)

1. Per (entity/scope, FY, source_table), Σ `detail` rows == the printed `subtotal` row.
2. Σ `subtotal` rows == the printed `grand_total` row.
3. **Cross-source per-tier check:** the settlement table's current-year-irregularity column and the classification table's per-class total are *independent* printed sources for the same figure (e.g. federal 44,392.0 vs 44,392.1) — reconcile them, flag drift beyond a documented rounding tolerance.
4. Default analytical sums filter `aggregation_role='detail'` AND `value_origin='printed'`.
5. Positional extraction (`row[1..4]`) is validated by the per-tier checks above — a tier swap that preserves the grand total is caught by step 3.

## Consequences

- The audit migration (idx `0008_0009`, on top of `0007_0008_observation_type`) drops the `beruju_category` enum + column, adds the `beruju_categories` lookup table (seeded), the new columns on `audit_beruju_lines`, the revised unique index, and the two new fact tables + their enums. Safe with zero backfill (pre-ingest).
- The Zod parser-output contract (`audit-types.ts`) and the repository helpers gain the new fields + two new draft/upsert paths; the parser tags every row with `aggregation_role`, `value_origin`, `source_table_code`.
- The 58th parser is rebased onto this model before [PR #67](https://github.com/SushantChalise/nepal-ledger/pull/67) merges — the two wrong category labels never reach `main`.
- New seed: `beruju_categories` (11 OAG taxonomy rows + `other`), seeded like the source registry.
- A lookup table for one taxonomy is a one-off divergence from the `pgEnum` convention; justified above, isolated to this domain.

## Alternatives rejected

- **Add two enum values, keep the flat model** — leaves the taxonomy/presentation/measure conflation and the insufficient key; the collision resurfaces at per-ministry/settlement time.
- **`pgEnum` for the taxonomy** — convention-consistent and defensible (statutory taxonomy), but can't carry bilingual labels/act-refs as data and hits `ALTER TYPE` friction while the model settles. (User chose the lookup table.)
- **Cram p35/p51 into `beruju_lines`** — re-introduces the exact semantic contamination (`revenue_arrears`) the review flagged; stock balances and paragraph counts are different measures.
- **Keep skipping parent rows** — easier sums, but loses source fidelity and the printed-subtotal reconciliation check.
