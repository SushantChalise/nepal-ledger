# ADR-0009: Entities Dimension + Per-Domain Fact Tables

- **Status:** Accepted (schema shipped in migration 0002)
- **Date:** 2026-05-14
- **Deciders:** Mother Opus, user (accepted as proposed in the Financial Data strategy)
- **Tags:** schema, entities, domain-tables, drizzle

## Context

The schema originally shipped in migration 0001 was indicator-centric: `indicators` (concepts), `staging_indicator_values` / `approved_indicator_values` (time-series facts). This works for macro indicators like NCPI inflation YoY or NEPSE index — pure (concept × period × value) shapes.

The pre-staged Financial Data corpus surfaced three row shapes that don't naturally fit the indicator schema:

1. **Entity-keyed facts** — per-bank, per-public-enterprise, per-local-level. E.g. "Phungling Municipality received Rs 10.46 lakh formula-based equalization grant in FY 2082/83." The concept ("formula-based equalization grant amount") and the period ("FY 2082/83") aren't enough; we need the entity ("Phungling Municipality").

2. **Geographic-keyed facts** — per-district, per-local-level census facts. E.g. "Kathmandu Metropolitan City had 158,724 owned households in NPHC 2021." Same problem: needs the entity dimension.

3. **Cross-cutting domain facts** — banking concentration (per bank-class), foreign aid (per donor × project × FY), public enterprise financials (per PE × FY). Each has its own shape that doesn't compress to the generic indicator-value row.

Without an explicit entities dimension, these would collapse into the indicator-slug namespace (`noc-net-profit-fy2080-81`, `kasthamandap-municipality-equalization-grant-fy2082-83`) — exploding the slug count to 5–6 digits and making entity-profile queries (Vertical 4 "Public Enterprise X-Ray", Vertical 10 "Local Ledger") string-prefix searches.

## Decision

Add a master `entities` dimension table plus per-domain fact tables. Shipped in migration 0002 (PR #17).

### `entities` (master dimension)

Polymorphic table. One row per addressable entity:

- **Banks** (`kind='bank'`): commercial, development, finance, microfinance, infrastructure
- **Public enterprises** (`kind='public_enterprise'`): NOC, NEA, NTC, NAC, FMTCL, NTDC, NDC, etc.
- **Local levels** (`kind='local_level'`): 753 entities (6 metro + 11 sub-metro + 276 muni + 460 rural-muni)
- **Districts** (`kind='district'`): 77 entities, parent_entity_id → province
- **Provinces** (`kind='province'`): 7 entities
- **Wards** (`kind='ward'`): ~6,176 entities, parent → local level
- **Polling stations** (`kind='polling_station'`): ~10,203 entities, parent → local level
- **Constituencies** (`kind='constituency'`): 165 federal-parliament constituencies
- **Cooperatives**, **business groups**, **ministries**, **departments**, **donors**: as needed

Self-referential parent_entity_id captures the hierarchy. Polymorphic `metadata jsonb` carries kind-specific extras (federal code, license class, district hint).

Unique on `(kind, slug)`. The slug is kebab-case for most kinds; for local levels it's the 8-digit federal code (e.g. `80101101`).

### `administrative_units` (1:1 specialization)

For entities of kind `province | district | local_level | ward | polling_station`, an `administrative_units` row carries the federal-political-system specifics:

- `federal_code` — Ministry of Federal Affairs code (1-digit / 3-digit / 8-digit / 11-digit / free-form)
- `local_level_type` — enum (metro / sub-metro / muni / rural-muni); NULL except for local-level rows
- `constituency_no` — federal parliament constituency for local-level rows
- `ward_no` — for ward rows
- `rural_urban` — classification
- `voter_count` — from the EC source

The 1:1 split lets queries against the generic entity dimension stay clean while the politico-specific columns live where they belong.

### Domain fact tables

Per-domain shape, separate from `approved_indicator_values`:

- **`local_government_fiscal_transfers`** — `(local_level_entity_id, fiscal_year, grant_type, amount_npr)`. 8 grant-type enum values per Nepal's fiscal-federalism law.
- **`census_facts`** — long-format `(entity_id, indicator_slug, census_year, value, indicator_family)`. The CBS NPHC 2021 89-CSV corpus.
- **`banking_sector_facts`** — `(bank_class, bank_entity_id_nullable, indicator_slug, period_*, value)`. The NRB BFI monthly XLSX series. NULL bank_entity for system-total rows.

Three more domain tables to follow when their parsers ship (not in migration 0002):

- `public_enterprises_annual_financials` (Yellow Book parser, Phase B2)
- `foreign_aid_projects` (White Book parser, Phase B4)
- `loan_agreements` (Agreement/* parser, Phase B5)

### `indicators` (existing) — gains optional `entity_id`

Future addition (deferred to migration 0003): `indicators.entity_id` FK for entity-scoped indicators. Macro indicators keep it NULL.

## Alternatives Considered

### A. String-prefix slugs (overload `indicators`)
`noc-net-profit`, `kasthamandap-municipality-equalization-grant-2082`. Zero schema change.

- Pro: Migration cost zero
- Con: Slug count explodes; querying "all NOC indicators" or "Kasthamandap's full row" becomes string-prefix LIKE; loses referential integrity; the entity dimension exists implicitly in strings instead of explicitly in rows
- Rejected.

### B. Separate tables per entity kind (per-domain)
`banks` table, `public_enterprises` table, `local_levels` table — no shared dimension.

- Pro: simplest per-domain queries
- Con: cross-domain joins ugly; no uniform "find this entity by slug" path; deduplication burden on every domain table
- Rejected.

### C (chosen). One `entities` dimension + 1:1 specialization for politicogeo + domain fact tables
- Pro: clean entity-profile queries; one dimension for cross-domain joins; politico-specific columns live where they belong
- Con: migration cost (one-time, small); some joins are 2-hop (`fact → entity → administrative_unit`)
- Accepted.

## Consequences

### Positive

- Entity-profile pages (Vertical 4 NOC, Vertical 10 Phungling Municipality) become single-table queries against `entities` + the relevant fact table
- Cross-entity rollups natural: "all metropolitan cities' total fiscal transfers FY 2082/83" = JOIN on `entities.kind='local_level'` + `administrative_units.local_level_type='metropolitan_city'`
- New entity kinds added by adding enum values + relevant facts; no schema churn per kind
- The `metadata` jsonb on `entities` absorbs kind-specific weirdness without polluting the dimension table

### Negative

- Slightly more verbose queries (vs. flat strings) — mitigated by Drizzle's relation helpers
- Polymorphism via `kind` means readers have to know which kind they're dealing with; mitigated by separate fact tables per kind

### Neutral / unknown

- Whether we need a separate `entity_aliases` table for the multi-language name variants (Nepali / English / common misspellings). For now `entities.name_ne` and `name_en` cover both; the `_common/municipality_resolver.py` handles match-on-ingest. Re-evaluate when we add OCR-derived rows that produce more name variants.

## Implementation status

Shipped in **migration 0002 (PR #17)**:
- `entities`
- `administrative_units`
- `local_government_fiscal_transfers`
- `census_facts`
- `banking_sector_facts`
- `ocr_tile_manifests` + `ocr_cell_extractions` + `ocr_stitch_disagreements` (OCR tracking; supports ADR-0008's tile pipeline)

Pending future migrations:
- `0003` — `indicators.entity_id` optional FK; `public_enterprises_annual_financials`; `foreign_aid_projects`; `loan_agreements`

## References

- Migration 0002: `src/lib/db/migrations/0001_0002_entities_admin_facts.sql`
- Schema files: `src/lib/db/schema/entities.ts` + `administrative-units.ts` + `fiscal-transfers.ts` + `census-facts.ts` + `banking-sector-facts.ts` + `ocr-tracking.ts`
- [`docs/FINANCIAL_DATA_STRATEGY.md`](../FINANCIAL_DATA_STRATEGY.md) §"Schema impact"
- ADR-0008 — Surya OCR routing (relies on the OCR tracking tables above)
