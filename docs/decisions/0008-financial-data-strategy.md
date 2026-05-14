# ADR-0008: Financial Data Strategy + Year 1 Domain Schema

- **Status:** Accepted
- **Date:** 2026-05-14
- **Deciders:** Mother Opus (PR-6 review); user ratified after the 6-drift retrofit
- **Tags:** data-strategy, schema, source-registry, doctrine

## Context

The `Financial Data/` corpus (50 NRB BFI monthly XLSX + 64 MoF PDFs across redbook / whitebook / yellowbook / agreement / intergovernmental subdirs + 99 CBS NPHC 2021 files + the pre-cleaned FY 2082/83 fiscal-transfer XLSX) has been on disk since project init. [`docs/FINANCIAL_DATA_STRATEGY.md`](../FINANCIAL_DATA_STRATEGY.md) was drafted to inventory the corpus, propose an extraction sequence respecting the Surya/Claude-CLI doctrine ([ADR-0003](0003-ai-assisted-parsing-policy.md)), and propose the schema shape needed to land it.

The proposed schema was **partially implemented ahead of the strategy doc being formally accepted** — migration 0002 (`src/lib/db/migrations/0001_0002_entities_admin_facts.sql`, PR #17, commit `06efa64`) shipped `entities`, `administrative_units`, `local_government_fiscal_transfers`, `census_facts`, `banking_sector_facts`, and the OCR tracking trio (`ocr_tile_manifests`, `ocr_cell_extractions`, `ocr_stitch_disagreements`). PR #17's commit message references "ADR-0009" but no such ADR was ever filed. The strategy doc thus became canonical-by-default while remaining marked "Draft for user review," creating ambiguity flagged by [`docs/DATA_REQUIREMENTS.md`](../DATA_REQUIREMENTS.md) §6 OQ-3.

## Decision

Lock [`docs/FINANCIAL_DATA_STRATEGY.md`](../FINANCIAL_DATA_STRATEGY.md) as the canonical plan for the `Financial Data/` corpus under this ADR (ADR-0008). The strategy doc has been retrofitted to:

1. Reflect the schema work that already shipped in migration 0002 (split "Proposed schema additions" into "Already landed" vs. "Still proposed" subsections).
2. Reclaim the ADR-0008 number that PR #17's commit message orphaned as "ADR-0009"; the next ADR (0009) is reserved for the Source Registry amendment flow.
3. Enumerate the Source Registry pre-requisites that gate Phase A2 / Phase B parsers (`nrb-bfi-monthly`, `mof-redbook`, `mof-whitebook`, `mof-yellowbook`, `mof-intergovernmental`, `mof-agreements`).
4. Drop the now-resolved Open Question about `.gitignore` (already covered at `.gitignore:59`).
5. Carry an ADR-style header block (title / status / date / number / supersedes / superseded-by).

Concretely:

- The phasing (Phase A1 / A2 / A3 → Phase B1–B5 → Phase C continuous) is locked.
- The schema split between shipped tables (migration 0002) and pending domain tables (`pe_annual_financials`, `foreign_aid_projects`, `loan_agreements`, `public_enterprises`) is locked; pending tables ship per-parser-PR rather than as a bulk migration.
- Source Registry rows for the six MoF/NRB feeds must be added before their parsers run, under the ADR-0009 amendment flow (one PR per source, no ADR per source).
- The `manual_match_reasoning.py` Devanagari substitution map and `rapidfuzz` municipality matcher have already been ported to `scrapers/_common/` (commit `f5d3290`, PR #20) and are reusable.

## Consequences

### Positive

- One canonical document covers the entire `Financial Data/` corpus: what's there, what schema holds it, in what order it lands.
- The "Draft → Accepted" ambiguity that [`docs/DATA_REQUIREMENTS.md`](../DATA_REQUIREMENTS.md) OQ-3 surfaced is closed.
- Parser briefs can cite ADR-0008 + a specific Phase letter as their scope authority.
- The Source Registry pre-requisites list makes the parser-vs-registry coupling explicit; no parser ships without its registry row.

### Negative

- Domain tables for `pe_annual_financials`, `foreign_aid_projects`, `loan_agreements`, `public_enterprises` are not in a migration yet; their shape will be locked when their parser brief lands. Risk: small-scope schema thrash if early-parser brief discovers a row shape that doesn't match the speculative shape in the strategy doc.
- The "ADR-0009" reference in PR #17's commit message remains permanently incorrect; the historical note in the strategy doc plus this ADR's Context section are the audit trail.

### Neutral

- Six Source Registry rows must be added before Phase A2 / B parsers can run. This work is sequenced under ADR-0009 (forthcoming).

## References

- [`docs/FINANCIAL_DATA_STRATEGY.md`](../FINANCIAL_DATA_STRATEGY.md) — the now-locked canonical plan
- `src/lib/db/migrations/0001_0002_entities_admin_facts.sql` — the migration that codified the schema portion of this strategy
- PR #17 (commit `06efa64`) — the schema landing PR (commit message orphan-references "ADR-0009")
- PR #20 (commit `f5d3290`) — Devanagari normalization + municipality resolver port
- [`docs/DATA_REQUIREMENTS.md`](../DATA_REQUIREMENTS.md) §6 OQ-3 — the open question this ADR resolves
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — parsing policy this strategy respects
- [ADR-0004](0004-supabase-storage-instead-of-r2.md) — storage target for source documents in this corpus
