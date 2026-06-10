# ADR-0015: DNE dimensional fact model (`dne_facts`)

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, data-model, dne, schema

## Context

[ADR-0014](0014-dne-promotion-and-dimensional-model.md) deferred DNE's **dimensional matrices** — Foreign Trade (exports/imports *by commodity*, ~745 commodities) and Remittance (*by source country* and *by recipient district*) — because they don't fit the single-dimensional `(indicator, period, value)` shape of `approved_indicator_values`, and registering ~1,000 commodity/country/district row-labels as "indicators" would wreck the catalogue. ADR-0014 promised a dedicated dimensional model. This is it.

These matrices are the data behind the Money Map's composition views ("what does Nepal import, by commodity", "where do remittances come from") — high value, so they need a real home, not the slug hack.

## Decision

Add a dedicated **`dne_facts`** table for dimensional breakdowns, parallel to (not inside) `approved_indicator_values`. A dimensional fact is a *base measure* sliced by exactly one *dimension*.

### Schema (`src/lib/db/schema/dne-facts.ts`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid pk | `defaultRandom()` |
| `source_document_id` | uuid → `source_documents` | provenance |
| `base_indicator_slug` | text notnull | the MEASURE, e.g. `dne-merchandise-exports`, `dne-merchandise-imports`, `dne-remittance-inflow`. NOT the commodity/country. |
| `base_indicator_name` | text notnull | human label of the measure |
| `dimension_kind` | text notnull | `commodity` \| `country` \| `district` \| `currency` |
| `dimension_value` | text notnull | kebab slug of the dimension member, e.g. `agarbatti`, `qatar`, `baglung` |
| `dimension_label` | text notnull | raw source label (Devanagari/English) |
| `value` | numeric(20,4) notnull | |
| `unit` | text notnull | controlled vocab (`npr_million`, `count`, …) |
| `reporting_period_type` | text notnull | `annual` \| `monthly` |
| `reporting_period_bs` | text notnull | |
| `reporting_period_ad_start` / `_end` | timestamptz | |
| `fiscal_year_bs` / `fiscal_year_ad_label` | text | |
| `confidence_grade` | text notnull | A/B/C |
| `created_at` | timestamptz default now | |

**Unique index** on `(base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs, reporting_period_type, source_document_id)` → idempotent re-ingest via `ON CONFLICT DO NOTHING`.

`dimension_value` members are **NOT** registered in `indicators`. The base measures (`dne-merchandise-exports`, etc.) MAY be registered as indicators later for the headline total, but the per-dimension rows live only here.

### Parser contract (the DNE parser, matrix files)

For matrix files the parser emits, in its JSON output, a **`dimensional_rows`** array (alongside the existing `staging_rows` for single-series files; a given file populates one or the other). Each dimensional row:

```
{ base_indicator_slug, base_indicator_name, dimension_kind, dimension_value,
  dimension_label, value, unit, reporting_period_type, reporting_period_bs,
  reporting_period_ad_start, reporting_period_ad_end, fiscal_year_bs,
  fiscal_year_ad_label, confidence_grade }
```

The parser determines `base_indicator_slug` + `dimension_kind` per file/section (Foreign Trade exports sheet → `dne-merchandise-exports` / `commodity`; Remittance → `dne-remittance-inflow` / `country` or `district`). This keeps the `ParserResult` dataclass in `_common` unchanged for now — the DNE parser's `__main__` dict carries the extra key; the DNE ingest CLI reads it.

### Ingest routing

`ingest:dne` (or a sibling `ingest:dne-dimensional`) reads the parser JSON: `staging_rows` → the normal staging→validation→approved path (ADR-0014 single series); `dimensional_rows` → bulk-insert into `dne_facts` via its repository (chunked, `ON CONFLICT DO NOTHING`). No validation-job indicator resolution for dimensional rows — the base measure + dimension are self-describing.

## Alternatives Considered

- **Add `dimension_*` columns to `approved_indicator_values`.** Rejected — pollutes the single-series table every consumer (Pulse) reads; most rows would have NULL dimensions.
- **One row per (commodity) as an indicator.** Rejected in ADR-0014 (catalogue pollution).
- **Generic EAV `(entity, attribute, value)`.** Rejected — too loose; `dne_facts` with an explicit `dimension_kind`/`dimension_value` is queryable and typed enough for the Money-Map composition queries.

## Consequences

- Trade-by-commodity and remittance-by-country/district get a real, queryable home; Money-Map composition views become buildable.
- The DNE parser gains a `dimensional_rows` output for matrix files; the ingest splits single-series vs dimensional routing.
- `dne_facts` is provenance-tracked (`source_document_id`) and idempotent.
- Scope of first implementation: prove the model end-to-end on **Foreign Trade by commodity** (highest value). Remittance-by-country/district and any currency dimension follow the same contract next.

## References

- [ADR-0014](0014-dne-promotion-and-dimensional-model.md) — why matrices were deferred
- [ADR-0013](0013-dne-ad-fiscal-year-periods.md) — DNE period handling
- [DATA_PIPELINE.md](../DATA_PIPELINE.md), `scrapers/nrb_dne/parser.py`
