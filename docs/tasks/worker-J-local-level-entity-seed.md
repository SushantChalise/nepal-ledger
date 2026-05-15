# Worker J — Local-level entity seed (753 municipalities)

**Spawn type:** general-purpose
**Diff cap:** 500 code-only non-test source lines

## Goal

Seed the `entities` table with the canonical 753 local-level (gaunpalika / nagarpalika / mahanagar) rows. Without this, every domain-fact parser that joins on `entities` (Worker P1 fiscal transfers, future census-derived facts, future MoF book parsers) produces 0 rows because the entity resolver returns NULL.

The canonical 753-row list is published in MoF's cleaned fiscal-transfer XLSX (Sheet2 of `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx`) — it includes federal_code, name (Devanagari + English), district, province for every local level.

## Why this is its own brief

Worker P1's fiscal-transfers parser depends on this seed but couldn't ship it without expanding scope further over the diff cap. Worker P3's census parser also depends on entity resolution but used the `_GAPANAME_OVERRIDES` map to bridge — the override list is meant to handle name drift, not the absence of seeds entirely.

## Scope Fence

Create:
- `scripts/seed-local-level-entities.ts` — Node CLI, reads the canonical XLSX, normalizes via `_common.devanagari_normalization`, upserts 753 rows into `entities` with `kind = 'local_level'`, `slug = <federal_code>`. Idempotent. `--dry-run` supported.
- `scripts/_seed-helpers/` if any shared helpers emerge
- A Python helper script if the XLSX read is easier in Python — but only if the row count is small enough that subprocess overhead isn't worth it (it's 753 rows; probably Node-side is fine via `xlsx` or `exceljs` npm package)

Edit:
- `package.json` — add `"seed:local-levels": "tsx scripts/seed-local-level-entities.ts"`
- `docs/sources/_index.md` (regenerate if seed changes)

**Out of scope:**
- Province-level or district-level entities (separate seed; these come from a different MoF schedule)
- Federal/central agencies (already in entities table)
- Backfilling census_facts or fiscal_transfers rows that may have been skipped due to missing entities

## Acceptance Criteria

- [ ] Running `pnpm seed:local-levels --dry-run` prints 753 row insertions
- [ ] Running without `--dry-run` upserts 753 rows; re-run is a no-op
- [ ] After seeding, `pnpm ingest:fiscal-transfers` produces zero `unresolved_entities` warnings
- [ ] All `pnpm` gates green
- [ ] Code-only non-test source lines under 500

## What to Return

Standard 6-section report.
