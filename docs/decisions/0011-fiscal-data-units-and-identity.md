# ADR-0011: Fiscal Transfer Data — NPR Crore Unit and Federal-Code Identity

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, parsers, data-integrity

## Context

During the FY 2082/83 intergovernmental fiscal transfer ingest two separate defects were discovered and fixed in `scrapers/mof_fiscal_transfers/parser.py`. Both involved silent wrongness: the data loaded, the pipeline completed without errors, but the numbers in the database were wrong. Neither failure was caught by schema validation or type checks — both were semantic errors that required manual inspection to detect. They are documented here because the failure modes are general, not specific to this one source.

**Defect 1 — Unit mislabel.** The `_DEFAULT_UNIT` constant was initially set to `"npr_thousand"`. The amounts in the cleaned Fiscal Transfer XLSX are **NPR crore** (1 crore = 10 million NPR). The mislabel did not cause a parse error; it caused every persisted `amount_npr` value to be semantically off by a factor of 10,000. The total for all 753 local levels was approximately NPR 321 billion (32,157 crore); the `npr_thousand` label would have implied NPR 321 million — two orders of magnitude below the published FY 2082/83 intergovernmental transfer budget.

**Defect 2 — Fuzzy name collision producing duplicate-driven totals.** The first version of the parser resolved municipality identity by fuzzy-matching the name column. The cleaned Fiscal Transfer XLSX has an 8-digit federal Code column. By not reading that column, the fuzzy matcher occasionally mapped two distinct municipalities onto the same federal code. The `ON CONFLICT DO NOTHING` insert silently retained the first row; the second (correct) row was discarded. The net effect was that the FY 2082/83 grand total inflated to approximately NPR 530 arab (instead of the correct NPR 321 arab), and small municipalities with high early-row amounts ranked above major cities like Kathmandu and Pokhara. Post-fix, the top recipients are Pokhara Metropolitan City, Kathmandu Metropolitan City, and Birendranagar Municipality — consistent with published rankings.

## Decision

### Decision 1: NPR crore is the canonical unit for the cleaned Fiscal Transfer XLSX

The `_DEFAULT_UNIT` constant in `scrapers/mof_fiscal_transfers/parser.py` is set to `"npr_crore"` and this is the unit stored in `local_government_fiscal_transfers.unit`. Feature code and any future aggregation query must treat values in this table as NPR crore.

### Decision 2: Data-unit verification protocol for new numeric sources

Before any new numeric source is trusted, its unit must be reconciled by order-of-magnitude against a published aggregate total:

1. Sum the ingested values for the largest reasonable grouping (e.g., national total, fiscal year total).
2. Find an independently published total for the same grouping (budget speech, NRB annual report, MoF bulletin, NSO digest).
3. Confirm the ingested sum matches the published total within ±5%.
4. If it does not match, check unit assumptions first (thousand vs. lakh vs. crore vs. million vs. billion) before assuming a parsing error.

This check is required before promoting any new source's staging rows to `approved_indicator_values`, or before marking a direct-fact-table ingest as complete. It must be noted in the ingest CLI's summary output or in the source's profile doc.

### Decision 3: Identity comes from the workbook's own Code column, not fuzzy name matching

When a source document carries a canonical identifier column (an 8-digit federal code in the case of MoF fiscal transfers, or an equivalent government-assigned code for other sources), the parser reads identity from that column directly. Fuzzy name matching is used only as a fallback for source documents that lack a code column.

The rule: **code column → exact identity; no code column → fuzzy identity with warning**. A row whose code is unrecognisable (e.g., a district subtotal row with a non-8-digit code) is silently skipped, not fuzzy-resolved.

## Alternatives Considered

- **Keep `npr_thousand` label, scale amounts in feature code:** Hiding unit details in queries makes it impossible to audit individual rows. Unit should be stored as-ingested, with the parser's declared unit. Feature-code scaling from a stored unit is acceptable but the stored unit must be accurate.

- **Continue fuzzy name matching even when a code column exists:** Fuzzy matching worked on the minimal test fixture (which had no code column) and was not re-examined when the real file was ingested. The real file has an 8-digit code column that provides exact identity. Using fuzzy matching when exact identity is available introduces unnecessary collision risk and is slower. Rejected.

- **Add a post-ingest reconciliation check to CI:** CI cannot run against live production data. The reconciliation check is a manual step documented in the protocol above, not an automated gate. A future improvement would add a plausibility-band check to the validation job (`data_quality_flags` `ValueOutOfPlausibleRange`) — the pipeline already has this hook.

## Consequences

### Positive

- `local_government_fiscal_transfers.unit = 'npr_crore'` is explicit, queryable, and consistent with the parser source comment that explains the verification.
- The data-unit verification protocol generalises: any future source (BFI balance-sheet figures, PDMO debt amounts, customs trade values) runs the same check before trust.
- Federal-code-direct identity is exact, idempotent on re-run, and produces correct rankings. The verified post-fix totals (NPR 321.01 arab, top recipients Pokhara/Kathmandu/Birendranagar) match published MoF data.

### Negative

- Parsers that encounter a code column must add code-detection logic (`_detect_identity_columns`) in addition to name-column logic. More parser surface, but the logic is small and already present in `mof_fiscal_transfers/parser.py` as a reference.
- The verification protocol requires a published aggregate total to exist for cross-checking. Some sources (e.g., sub-national proxies, computed indicators) may lack a directly comparable published aggregate. In those cases, the check is done at a coarser grouping (national total, broad category).

### Neutral / unknown

- The FY 2082/83 cleaned Fiscal Transfer XLSX is the only source where this combination of defects occurred. Future MoF fiscal transfer releases should follow the same code-column-direct pattern, but the column naming may drift — `_CODE_COLUMN_KEYWORDS` in the parser covers known variants.

## References

- [`scrapers/mof_fiscal_transfers/parser.py`](../../scrapers/mof_fiscal_transfers/parser.py) — `_DEFAULT_UNIT = "npr_crore"` comment; `_detect_identity_columns`; `_direct_identity`
- [`scripts/ingest-fiscal-transfers.ts`](../../scripts/ingest-fiscal-transfers.ts) — the CLI that loads this parser
- [`src/lib/db/schema/fiscal-transfers.ts`](../../src/lib/db/schema/fiscal-transfers.ts) — `local_government_fiscal_transfers` table definition
- [ADR-0010](0010-ingest-cli-conventions.md) — ingest CLI conventions (batched entity resolution)
- [DATA_PIPELINE.md](../DATA_PIPELINE.md) §"The Validation Job" — `ValueOutOfPlausibleRange` plausibility band (future hook for automated unit checks)
