# ADR-0026: Migration Permit Fact Domain (DoFE labour permits)

- **Status:** Accepted
- **Date:** 2026-06-11
- **Deciders:** Mother Opus (user-approved 2026-06-11)
- **Tags:** schema, data-domain, migration

## Context

The NDRI Migration Atlas's richest *new* data layer is the Department of Foreign Employment (DoFE) labour-permit corpus: permits issued by **destination country**, **origin district**, **skill class** (Fig 11), **permit category** (Fig 8: new individual / re-entry / recruitment-agency / G2G), **sex**, and **fiscal year / month**. None of these dimensions fit the time-series `approved_indicator_values` pipeline (they would explode the indicator-slug namespace), and they are not census facts. They are a distinct **dimensional fact domain**, exactly like `dne_facts` (ADR-0015), `banking_sector_facts`, and `audit_facts` (ADR-0024) — populated direct-to-fact-table, entity-keyed for origin.

This ADR establishes the schema + enums. **Foundation only — no corpus parsed, no data ingested** (mirrors the audit-facts foundation, ADR-0024). The deterministic Python parser (ADR-0003) and the activation of source `dofe-labour-migration` (currently `paused`) are follow-up work.

## Decision

A new dimensional fact table **`migration_permit_facts`**, one row per `(period × destination × origin × skill × category × sex)` cell, with NULL in a dimension meaning "marginal/aggregate over that dimension" (the same convention as the census + DNE models).

### Columns
| column | type | notes |
|---|---|---|
| `id` | uuid pk | |
| `fiscal_year_bs` | text **NOT NULL** | e.g. `2080/81` (ADR-0013 BS fiscal-year dating) |
| `month_num` | integer (nullable) | Nepali month 1–12; **NULL = annual aggregate** |
| `destination_country` | text (nullable) | country name; **NULL = all-countries marginal** |
| `destination_region` | `migration_destination_region` enum (nullable) | region bucket; NULL = marginal |
| `origin_entity_id` | uuid (nullable) → `entities.id` `onDelete: set null` | origin **district** (or local level) entity; **NULL = all-Nepal** |
| `skill_class` | `migration_skill_class` enum (nullable) | NULL = marginal |
| `permit_category` | `migration_permit_category` enum (nullable) | NULL = marginal |
| `sex` | `migration_sex` enum **NOT NULL** | `male` / `female` / `total` |
| `permits` | numeric(20, 0) **NOT NULL** | permit **count** (integers; no fractional permits) |
| `unit` | text **NOT NULL** default `'permits'` | |
| `source_document_id` | uuid **NOT NULL** → `source_documents.id` `onDelete: restrict` | provenance |
| `confidence_grade` | `confidence_grade` enum **NOT NULL** default `'A'` | DoFE permits are administrative records |
| `promoted_at` | timestamptz **NOT NULL** defaultNow | |
| `promoted_by` | text **NOT NULL** | |

### Enums (new, in `schema/enums.ts`)
- `migration_skill_class`: `['unskilled', 'semi_skilled', 'skilled', 'highly_skilled', 'professional']` (Atlas Fig 11; MoLESS classifies re-entry permits as `skilled`).
- `migration_permit_category`: `['new_individual', 'reentry', 'recruitment_agency', 'g2g']` (Atlas Fig 8).
- `migration_destination_region`: `['india', 'saarc_other', 'asean', 'middle_east', 'other_asia', 'europe', 'africa', 'americas', 'other']` (aligned with the census Hhld19 region buckets so the two domains reconcile).
- `migration_sex`: `['male', 'female', 'total']` — **unless a generic sex enum already exists** in `enums.ts`, in which case reuse it (check first).

### Idempotency — natural key with NULLS NOT DISTINCT
A single **unique constraint** over the full dimension tuple
`(fiscal_year_bs, month_num, destination_country, destination_region, origin_entity_id, skill_class, permit_category, sex)`,
declared with **`.nullsNotDistinct()`** (the `unique()` constraint builder, *not* `uniqueIndex()` — see [[worktree-toolchain-no-node-modules]]). Marginal rows carry NULLs; `NULLS NOT DISTINCT` makes them collide so re-ingest is idempotent via `onConflictDoNothing()` (mirrors the `audit_facts` aggregate-row pattern, ADR-0024, and avoids the coalesce-sentinel workaround `banking_sector_facts` needed).

### Repository + parser contract
- `src/lib/db/repositories/migration-permit-facts.ts` — `insertMigrationPermitFact`, `bulkInsertMigrationPermitFacts` (`onConflictDoNothing().returning()`), and a `findMigrationPermitFacts` reader, mirroring `banking-sector-facts.ts` (safeQuery + Result, never throws).
- `src/lib/ingestion/migration-permit-types.ts` — the Zod parser-output contract (`MigrationPermitFactInput`) the future deterministic parser must satisfy, mirroring `src/lib/ingestion/audit-types.ts`. Type-driven (Zod → derived type), so the parser PR has a typed target.

## Alternatives Considered

- **Force into `approved_indicator_values`** — the 6-way dimensional cross-tab would explode the slug namespace and lose origin-entity keying. Rejected (the same reason banking/dne/audit got their own tables).
- **Reuse `dne_facts`** — `dne_facts` is NRB's DNE corpus with its own dimension semantics; co-mingling DoFE permits would blur provenance and revision detection. Rejected.
- **Coalesce-sentinel unique index** (as `banking_sector_facts` uses for its one nullable entity column) — with *seven* nullable dimensions the sentinel approach is unwieldy; `NULLS NOT DISTINCT` (available in our Postgres) expresses the intent directly. Adopted (matches the newer `audit_facts` choice).
- **Separate per-cut tables** (one per dimension) — fragments the corpus and prevents cross-dimension queries. Rejected; one wide table with marginal NULLs is the established pattern.

## Consequences

### Positive
- DoFE permits get a typed, entity-keyed home that reconciles with census migration (shared region buckets) and feeds the Migration lens (permit trends, destination maps, skill profile, BLAs).
- Idempotent re-ingest with no sentinel gymnastics.
- The Zod contract gives the future parser a type-driven target.

### Negative / follow-up
- **Foundation only** — no data until the deterministic DoFE parser lands (ADR-0003) and flips source `dofe-labour-migration` to `active`.
- A wide nullable-dimension table needs disciplined parser output (every row must declare which dimensions are marginal); the Zod contract + the unique constraint enforce this.

## References
- [ADR-0024](0024-government-audit-fact-domain.md) — the direct-to-fact-table + NULL-aggregate + NULLS-NOT-DISTINCT pattern this mirrors.
- [ADR-0015](0015-dne-dimensional-fact-model.md) — dimensional fact precedent.
- [ADR-0013](0013-dne-ad-fiscal-year-periods.md) — BS fiscal-year dating.
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — deterministic parser only (the future ingest).
- `docs/research/MIGRATION_ATLAS_PLAN.md` §4.4 — the DoFE granular fact model in the pillar plan.
- Pattern: `src/lib/db/schema/banking-sector-facts.ts` + `src/lib/db/repositories/banking-sector-facts.ts` + `src/lib/ingestion/audit-types.ts`.
