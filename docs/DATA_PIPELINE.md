# Data Pipeline — Staging → Validation → Approved

Scraped data does not enter production tables directly. Every scraper writes to staging. A validation job promotes staging rows only if schema, period, units, source hash, and confidence checks pass. This is the quarantine that keeps the Fact Ledger honest.

---

## The Flow

```
┌─────────────────┐
│ External source │  (NRB, FCGO, Customs, NSO, ...)
└────────┬────────┘
         │ download
         ▼
┌─────────────────┐         hash + timestamp
│ source_documents│ ◄────── archive to Supabase Storage (immutable; R2 in Phase 2)
└────────┬────────┘
         │ parse
         ▼
┌─────────────────┐
│   parser_runs   │  (one row per parse attempt — success or failure)
└────────┬────────┘
         │ if success
         ▼
┌──────────────────────────┐
│ staging_indicator_values │  (untrusted, awaits validation)
└────────┬─────────────────┘
         │ validation job
         ▼
┌──────────────────────────┐         ┌────────────────────┐
│      validate            │ ──────► │ data_quality_flags │  (if issues found)
└────────┬─────────────────┘         └────────────────────┘
         │ if all checks pass
         ▼
┌───────────────────────────┐
│ approved_indicator_values │  (production — what queries return)
└───────────────────────────┘
```

Only `approved_indicator_values` is read by the Pulse, Money Map, Fact Ledger, calculators, and stories. Staging is never queried by feature code.

---

## Database Tables (Spec)

These tables are added in the Day 4–10 foundation milestone. Drizzle schema location: `src/lib/db/schema/data-pipeline.ts`.

### `source_documents`

Append-only archive of every downloaded source file.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `source_id` | text | FK → `source_registry.source_id` |
| `original_url` | text | The URL we downloaded from |
| `storage_provider` | enum | `supabase` (Year 1) / `r2` (Phase 2 onward) |
| `storage_key` | text | Path inside the storage bucket — e.g., `<source-id>/<yyyy-mm-dd>/<filename>` |
| `file_hash_sha256` | text | Content hash for dedup + integrity |
| `file_size_bytes` | bigint | |
| `content_type` | text | `application/pdf`, `text/csv`, etc. |
| `downloaded_at` | timestamptz | |
| `reporting_period_label` | text | Best-guess label at download time (e.g., "Nine-Months 2082/83") — refined by parser |
| `notes` | text | freeform |

**Rule:** rows are never updated or deleted. New download of same source = new row.

### `parser_runs`

One row per parser execution.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `source_document_id` | uuid | FK → `source_documents` |
| `parser_path` | text | e.g., `scrapers/nrb/cmefs/parser.py` |
| `parser_version` | text | semver |
| `started_at` | timestamptz | |
| `ended_at` | timestamptz | |
| `status` | enum | `success`, `partial`, `failure` |
| `staging_rows_written` | int | |
| `error_summary` | text | nullable |
| `stdout_tail` | text | last ~2KB of parser output |

### `parser_errors`

Granular error rows for failed parses. Useful for debugging without re-running parsers.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `parser_run_id` | uuid | FK → `parser_runs` |
| `error_class` | text | e.g., `ColumnMissing`, `RegexMismatch`, `UnitAmbiguous`, `PageLayoutChanged` |
| `error_detail` | text | message |
| `source_excerpt` | text | the offending text chunk if extractable |
| `created_at` | timestamptz | |

### `staging_indicator_values`

Untrusted output of parsers. Cleared after promotion or rejection.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `parser_run_id` | uuid | FK → `parser_runs` |
| `source_document_id` | uuid | FK → `source_documents` |
| `indicator_id` | uuid | FK → `indicators` (resolved at parse time; nullable if unknown) |
| `indicator_slug_raw` | text | What the parser saw — useful for unknown indicators |
| `value` | numeric | |
| `unit` | text | |
| `reporting_period_type` | enum | from CALENDAR_AND_PERIODS |
| `reporting_period_bs` | text | |
| `reporting_period_ad_start` | timestamptz | |
| `reporting_period_ad_end` | timestamptz | |
| `publication_date_ad` | timestamptz | |
| `publication_date_bs` | text | |
| `fiscal_year_bs` | text | |
| `confidence_grade_proposed` | enum | A/B/C |
| `parser_notes` | text | |
| `inserted_at` | timestamptz | |

### `data_quality_flags`

Validation issues found during the promotion step.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `staging_row_id` | uuid | FK |
| `flag_type` | enum | `SchemaInvalid`, `PeriodAmbiguous`, `UnitUnrecognized`, `DuplicateOfApproved`, `RevisionMismatch`, `ValueOutOfPlausibleRange`, `IndicatorUnknown`, `SourceHashCollision` |
| `severity` | enum | `blocking`, `warning` |
| `detail` | text | |
| `created_at` | timestamptz | |
| `resolved_at` | timestamptz | nullable |
| `resolution_note` | text | nullable |

### `approved_indicator_values`

Production. The only table feature code queries for indicator data.

(Same columns as `staging_indicator_values` minus `parser_run_id` and `confidence_grade_proposed`. Adds `revision_number`, `promoted_at`, `promoted_by`.)

---

## The Validation Job

A scheduled or manually-triggered job that walks unpromoted `staging_indicator_values` and decides per row: promote, reject, or flag for human review.

### Checks (in order — first blocking failure ends per-row)

1. **Schema check.** All required fields present and typed. → `SchemaInvalid`
2. **Indicator resolution.** `indicator_id` set OR `indicator_slug_raw` matches an alias rule. → `IndicatorUnknown`
3. **Period parse.** `reporting_period_*` and `publication_date_*` fields parse to valid dates. BS/AD agreement within tolerance. → `PeriodAmbiguous`
4. **Unit recognition.** Unit string maps to a known unit in `indicator_units` (a lookup table). → `UnitUnrecognized`
5. **Plausibility band.** Value within ±X stdev of the trailing 24-month mean for this indicator. Wide bands; this catches order-of-magnitude errors (NPR vs. crore vs. lakh). → `ValueOutOfPlausibleRange`
6. **Duplicate check.** No existing approved row with same `(indicator_id, reporting_period_type, reporting_period_bs)` unless this row is a revision (different `source_document_id` AND value differs). → `DuplicateOfApproved`
7. **Revision flow.** If a prior approved row exists, this row must (a) cite a newer source document, (b) carry `revision_number = prior + 1`. → `RevisionMismatch`
8. **Source integrity.** `source_document_id`'s file hash matches the row in `source_documents` (no tampering since archive). → `SourceHashCollision`

### Outcomes

- **All checks pass:** insert into `approved_indicator_values`. Delete the staging row.
- **Blocking failure:** write a `data_quality_flag` row (severity = blocking). Staging row stays — awaits human review.
- **Warning only:** insert into `approved_indicator_values` AND write a `data_quality_flag` row (severity = warning). The promoted row carries a "warned" flag the indicator page can display.

### Human Review Workflow

Mother (or user) reviews blocking flags via a small `/admin/quality` page (or CLI):

- **Approve override:** force-promote with reason logged. (Used for known-good edge cases the validator can't model.)
- **Fix and re-run:** edit staging row, re-run validation. Logged in `data_quality_flags.resolution_note`.
- **Reject:** delete staging row. Logged with reason.
- **Re-parse:** mark the source document for re-parse with a new parser version.

No row enters production without either passing all checks or being explicitly overridden with a logged reason.

---

## Parser Contract

Every parser file (`scrapers/<source-id>/parser.py`) implements the same shape:

```python
def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """
    Read the file at the given path. Return a structured ParserResult containing:
      - status: 'success' | 'partial' | 'failure'
      - staging_rows: list[StagingIndicatorValueDraft]
      - errors: list[ParserError]
      - parser_version: str (semver)

    Never writes to the database directly. The orchestration layer
    handles all DB writes after calling parse().
    """
```

Rules:
- Parsers are **idempotent** — running twice on the same input produces the same output (or, if non-deterministic, that's a bug).
- Parsers **never assume the file's structure**. Every column/row is checked. Missing fields → `ParserError`, not a crash.
- Parsers **never call the network**. They operate on the file downloaded from Storage (Supabase Storage in Year 1, R2 in Phase 2) only.
- Parsers **declare their version**. A change in extraction logic = version bump.

---

## Confidence Grade Assignment

| Default | Applies when | Examples |
|---------|--------------|----------|
| **A** | Source is an official audited / authoritative publication AND parser is confident in extraction | NRB CMEFs published values, OAG audit numbers, PDMO debt bulletin |
| **B** | Source is official but preliminary OR parser extracted with some ambiguity | FCGO daily (preliminary), NRB CMEFs values flagged "P=Provisional" |
| **C** | Single source, or extracted from prose rather than a table, or computed from a less-trusted proxy | Estimated tourism leakage %, digital export proxies |

The parser proposes a confidence grade per row in `confidence_grade_proposed`. Validation can downgrade (never upgrade) based on context.

The Fact Ledger UI shows the FINAL confidence grade (from `approved_indicator_values.confidence_grade`), which is whatever made it through validation.

---

## Failure Modes & Responses

| Failure | Detection | Response |
|---------|-----------|----------|
| Source URL 404 (page moved) | Scraper run alert | Update `source_registry.source_url`; log known-breakage-mode; do not promote stale data |
| Source format changed (PDF layout shifts) | Parser fails extraction or values fall outside plausibility band | Parser bumps to new version with version-conditional logic; re-parse archived documents |
| Source disappears entirely | Repeated 404s | Mark source `Paused` in registry; visible "Data discontinuity since X" tag on affected indicators |
| Source publishes corrected historical values | Validation detects revision flow | Promote as `revision_number+1`; indicator page surfaces the change |
| Parser bug discovered after promotion | Manual or post-hoc | Roll forward: write a `data_correction` event; re-parse archived documents; promote corrected rows with revision flag |
| User submits a Fact Ledger challenge | UI workflow | Independent of pipeline; see `CONTENT_FORMATS.md` §"Correction / Challenge Workflow" |

The pipeline must **never silently overwrite or hide** a bad value. Every action leaves a row.

---

## What Feature Code Sees

```typescript
// In a feature like Pulse, you never reach for staging.
import { findLatestIndicatorValue } from '@/lib/db/repositories/indicator-values';

const inflation = await findLatestIndicatorValue('inflation-yoy', { period: 'monthly' });
// Returns: { value, unit, reporting_period_bs, publication_date_ad, confidence, source_url, revision_number, … }
```

Repositories query `approved_indicator_values` exclusively. The staging/validation layer is invisible to feature code.

---

## Cross-Reference

- Per-source registry rows: [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md).
- Date and period fields: [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md).
- Drizzle schema (Day 4–10 milestone): `src/lib/db/schema/data-pipeline.ts`.
- Parser implementations: `scrapers/<source-id>/parser.py`.
- Storage policy: [CLOUD_STACK.md](CLOUD_STACK.md) §"Supabase Storage" + [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md).
- Confidence grade rules: [STRATEGY.md](STRATEGY.md) §"The Visible Fact Ledger".
