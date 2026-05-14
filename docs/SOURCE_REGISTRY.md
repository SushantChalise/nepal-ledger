# Source Registry

The platform's core asset is **auditable economic truth**, not "data". Every external data feed gets a registry entry before a scraper is written, before a row hits production. Without this discipline, the Fact Ledger silently mixes A-tier and C-tier inputs and the credibility moat dies.

Under [ADR-0009](decisions/0009-source-registry-single-source-of-truth.md), the `source_registry` table is the **single source of truth** for what we track. The seed script (`scripts/seed-source-registry.ts`) is the canonical declarative form. The generated index at [`docs/sources/_index.md`](sources/_index.md) is the human-readable enumeration; this document only carries the schema, workflow, and per-source Markdown template.

This document defines:
1. The schema of the source registry
2. The workflow for adding a new source
3. The Markdown profile template

> **For the current registered set:** see [`docs/sources/_index.md`](sources/_index.md) (generated; do not hand-edit) or query the live `source_registry` table.

---

## Schema

Every source gets a row in `source_registry` (database table) and a Markdown profile in `docs/sources/<source-id>.md`. The database row is the live truth; the Markdown is the human-readable companion.

### Required fields

| Field | Type | Example |
|-------|------|---------|
| `source_id` | string (kebab) | `nrb-cmefs-monthly` |
| `agency` | string | `Nepal Rastra Bank` |
| `agency_short` | string | `NRB` |
| `dataset_name` | string | `Current Macroeconomic and Financial Situation` |
| `source_url` | URL | `https://www.nrb.org.np/category/current-macroeconomic-situation/` |
| `publication_frequency` | enum | `monthly`, `quarterly`, `annual`, `daily`, `seasonal`, `ad-hoc` |
| `expected_release_window` | string | `25th–30th of the month following the reporting period` |
| `reporting_period_type` | enum | `monthly`, `quarterly`, `annual`, `nine-months`, `cumulative-ytd` |
| `file_format` | enum | `pdf`, `csv`, `xlsx`, `xls`, `html`, `json`, `xml` |
| `requires_table_extraction` | boolean | `true` if PDF tables need pdfplumber |
| `historical_coverage` | string | `FY 2073/74 onward (~2016)` |
| `license_status` | enum | `public-domain`, `gov-open`, `cc-by`, `proprietary`, `unclear` |
| `parser_owner` | string (kebab) | `scrapers/parse_cmefs.py` |
| `parser_version` | semver | `1.0.0` |
| `revision_policy` | string | `Provisional values revised in next release; historical values stable after 2 cycles` |
| `known_breakage_modes` | string[] | `["url-changes-each-fy", "pdf-format-shifts-at-fy-boundary"]` |
| `confidence_default` | enum | `A`, `B`, `C` |
| `notes` | string | freeform |
| `registered_at` | timestamp | auto |
| `last_verified_at` | timestamp | manual, monthly |

### Computed/derived

- `indicators_produced` — array of indicator slugs this source feeds (joined via `indicator_source_map`)
- `last_successful_ingest_at` — joined from `parser_runs`
- `last_failed_ingest_at` — joined from `parser_runs`
- `confidence_grade_observed` — most-recent ingest's confidence label (may differ from `confidence_default` for one cycle)

---

## Workflow for Adding a New Source

**No scraper is written until the source is registered.** This is non-negotiable.

1. Identify the source. Open its publication page in a browser. Verify it actually publishes what you expect.
2. Write the Markdown profile at `docs/sources/<source-id>.md` (template below).
3. Insert the row into `source_registry` via a Drizzle migration (`migrations/NNNN_add_source_<id>.sql`).
4. Identify which indicators this source produces. Either:
   - Add new rows to `indicators` (also via migration), OR
   - Map to existing indicators via `indicator_source_map`.
5. Write the parser (`scrapers/<source-id>/parser.py`). Parser writes ONLY to `staging_indicator_values` (see [DATA_PIPELINE.md](DATA_PIPELINE.md)).
6. Write at least one parser test against an archived sample.
7. Open PR. Reviewer (Mother) checks: registry row sane, indicators mapped, parser test green, sample archived in Supabase Storage (R2 in Phase 2).
8. After merge: first manual ingest. Verify staging output, promote to approved.

A scraper merged without a source registry entry is reverted on sight.

---

## Markdown Profile Template

`docs/sources/<source-id>.md`:

```markdown
# Source: <Agency> — <Dataset Name>

**source_id:** `<source-id>`
**Status:** Active | Paused | Deprecated
**Last verified:** YYYY-MM-DD

## What this is
<One paragraph: what the dataset reports, why we ingest it>

## Publication
- URL: <link>
- Frequency: <monthly | quarterly | …>
- Expected window: <e.g. "25th–30th of month following">
- Format: <pdf | csv | xlsx | html>

## What we extract
- <indicator slug 1> — <one-line description>
- <indicator slug 2> — <one-line description>

## Provenance
- Confidence default: <A | B | C>
- License: <public-domain | gov-open | …>
- Reporting period type: <monthly | quarterly | …>

## Known breakage modes
- <e.g. "URL changes each fiscal year — search-pattern fallback in parser">
- <e.g. "PDF column headers shifted in FY 2081/82 — handled by parser v1.2">

## Revision policy
<How the source revises historical values; how we handle revisions>

## Parser
- Path: `scrapers/<source-id>/parser.py`
- Version: <semver>
- Owner: <Mother Opus | name>
- Tested against: `docs/sources/<source-id>/samples/`

## Archive policy
- All downloaded files stored in Supabase Storage bucket `source-archive` (Phase 2: migrate to R2 — see [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md)) under key `<source-id>/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests
<auto-populated table or link to monitoring dashboard>
```

---

## Adding a source (recap)

Per ADR-0009, adding a source is a regular PR (no ADR):

1. Add a row to `scripts/seed-source-registry.ts`. Pick the `tier` (0–4 or null), `ingestion_mode` (`automated_cron` / `manual_upload` / `reference_only`), and `status`.
2. Run `pnpm gen:source-index` and commit the updated `docs/sources/_index.md`.
3. Create `docs/sources/<source-id>.md` (use the template above; stub is fine, breakage modes / revision policy can be filled in on the parser PR).
4. Run `pnpm check:source-registry` to confirm the contract holds.

Schema/enum/tier-definition changes — that's an ADR.

---

## Cross-Reference

- Schema implementation lives in `src/lib/db/schema/source-registry.ts` (added Day 4–10).
- Parser pipeline conventions: [DATA_PIPELINE.md](DATA_PIPELINE.md).
- Date/period handling: [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md).
- Archival storage: [CLOUD_STACK.md](CLOUD_STACK.md) §"Supabase Storage" (primary); [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md) for the R2-deferred decision.
- Confidence grading rules: [STRATEGY.md](STRATEGY.md) §"The Visible Fact Ledger".
