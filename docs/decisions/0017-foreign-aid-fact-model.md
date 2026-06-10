# ADR-0017: Foreign-aid dimensional fact model (`foreign_aid_facts`)

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus (drafted by Sonnet worker, batch #12)
- **Tags:** data-pipeline, data-model, foreign-aid, money-in, schema

## Context

The MoF **White Book** ("Source Book for Projects Financed with Foreign Assistance") is the annual budget-book record of foreign aid — grants and loans — entering Nepal, broken out two ways: **by development partner (donor)** and **by spending ministry (sector)**. This is the "Money In" external-financing story (Pillar 1: where Nepal's money comes from before it becomes wealth).

Its two headline summary tables ("Development Partnerwise Summary" and "Summary of Ministrywise Development Partners") are matrices of `(member × measure)`. Like the DNE trade/remittance matrices ([ADR-0015](0015-dne-dimensional-fact-model.md)), they don't fit the single-series `(indicator, period, value)` shape of `approved_indicator_values`, and registering each donor/ministry as an `indicator` would wreck the catalogue. ADR-0015 established the dimensional-fact pattern for exactly this case; this ADR applies it to a new domain.

A separate table (not a `dne_facts` reuse) is warranted because foreign aid is a distinct source, domain, and confidence regime from NRB's DNE matrices, with its own dimension vocabulary (donors/ministries vs commodities/countries) and its own unit story.

## Decision

Add a dedicated **`foreign_aid_facts`** table, parallel to `approved_indicator_values` and modelled field-for-field on `dne_facts`. A row is one *base aid measure* sliced by exactly one *dimension member*.

### Schema (`src/lib/db/schema/foreign-aid-facts.ts`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid pk | `defaultRandom()` |
| `source_document_id` | uuid → `source_documents` | provenance; `onDelete: restrict` |
| `base_indicator_slug` | text notnull | the MEASURE: `foreign-aid-grant` (Total Grant col) \| `foreign-aid-loan` (Total Loan col). NOT the donor/ministry. |
| `base_indicator_name` | text notnull | human label of the measure |
| `dimension_kind` | text notnull | `donor` \| `sector` |
| `dimension_value` | text notnull | kebab slug of the member, e.g. `adb-general`, `ministry-of-finance` |
| `dimension_label` | text notnull | raw source name |
| `value` | numeric(20,4) notnull | |
| `unit` | text notnull | `npr_lakh` \| `npr_thousand` — **verbatim from the edition's annotation** (see Unit) |
| `reporting_period_type` | reportingPeriodType enum notnull | `annual` |
| `reporting_period_bs` | text notnull | BS fiscal-year label |
| `reporting_period_ad_start` / `_end` | timestamptz (nullable for dne parity) | annual span bounds |
| `fiscal_year_bs` / `fiscal_year_ad_label` | text (nullable for dne parity) | |
| `confidence_grade` | confidenceGrade enum notnull, default `B` | |
| `created_at` | timestamptz default now | |

**Unique index** `foreign_aid_facts_unique_idx` on `(base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs, reporting_period_type, source_document_id)` → idempotent re-ingest via `ON CONFLICT DO NOTHING`. `dimension_kind` is in the key so the donor and sector cuts of the same measure/period never collide. Plus secondary indexes on `base_indicator_slug`, `(dimension_kind, dimension_value)`, and `reporting_period_bs`.

`dimension_value` members are **NOT** registered in `indicators`. The base measures MAY later be registered for a headline total, but the per-dimension rows live only here.

### Unit policy (ADR-0011) — DON'T normalise at ingest

The White Book's money unit **varies by edition** and is stamped on each summary-table page:

- FY 2020/21 : `(Rs. in '00000')` = Rs in 100,000 = **lakh** → `npr_lakh`
- FY 2015/16, FY 2013/14, FY 2014/15 : `(NRs'000s)` / `( Rs. 000 )` = Rs in 1,000 = **thousand** → `npr_thousand`

The parser **detects the annotation per page and emits the matching unit verbatim**; it never assumes or converts. Each row carries the unit detected on its own page, so a thousand-edition row and a lakh-edition row never silently combine. **Downstream consumers must read `unit` before summing across editions.** (This mirrors the Yellow Book's `npr_thousand`-from-header decision in [ADR-0020] / `mof_yellowbook`.) Magnitude sanity (donor Total rows): FY2015/16 = NPR 205.9 bn; FY2020/21 = NPR 360.0 bn (a COVID-year surge — IMF RCF, ADB-CARES, IDA budget support); both in/around the NPR 100–250 bn/yr band.

### Parser contract (`scrapers/mof_whitebook/parser.py`)

The parser emits a **`dimensional_rows`** array (no single-series `staging_rows`), identical in shape to the Yellow Book / DNE dimensional contract:

```
{ base_indicator_slug, base_indicator_name, dimension_kind, dimension_value,
  dimension_label, value, unit, reporting_period_type, reporting_period_bs,
  reporting_period_ad_start, reporting_period_ad_end, fiscal_year_bs,
  fiscal_year_ad_label, confidence_grade }
```

`dimension_kind` is `donor` for the Development-Partnerwise table and `sector` for the Ministrywise table. The two tables share a column block but the ministrywise table has an extra leading "GoN Budget" column, so the parser addresses the Total-Grant/Total-Loan columns by table-specific offsets.

### Ingest routing (`scripts/ingest-whitebook.ts`)

`ingest:whitebook` reads the parser JSON `dimensional_rows` and bulk-inserts into `foreign_aid_facts` via its repository (chunked, `ON CONFLICT DO NOTHING`) — exactly like `ingest:dne-yellowbook`. No validation-job indicator resolution; the base measure + dimension are self-describing.

## Scope (first implementation)

Extract **Total Grant** and **Total Loan** per dimension member from the two summary tables of the **clean English editions** (FY 2015/16, FY 2020/21, and the FY 2013/14 + FY 2014/15 editions whose filenames are Devanagari but whose body is the English "Unofficial Translation"). The bundled real-PDF test target is FY 2020/21 (134 facts: 44 donors + 23 ministries × 2 measures).

**Deferred (documented, not fabricated):** the grant/loan SUB-components (cash / reimbursable / direct-payment / commodity) within each member — they are present and clean but out of scope for the first cut; the project-level detail tables (per-budget-head project lists); and the **Preeti-encoded** editions (FY 2062/63, 2064/65, 2065/66, 2067/68) and a **mislabelled CID-broken** intergovernmental-transfer file in the same folder — un-mapping Preeti or OCR'ing CID is the reverse-engineering [ADR-0003](0003-ai-assisted-parsing-policy.md) forbids. The parser emits typed `PageLayoutChanged`/`PeriodAmbiguous` diagnostics for these, never a value.

## Alternatives Considered

- **Reuse `dne_facts` with `dimension_kind ∈ {donor, sector}`.** Rejected — foreign aid is a different source, domain, and confidence grade than NRB DNE matrices; co-mingling them in one table muddies provenance and the `base_indicator_slug` namespace. A parallel table with the same shape keeps the model uniform without conflating domains.
- **Add `dimension_*` columns to `approved_indicator_values`.** Rejected (same reason as ADR-0015): pollutes the single-series table Pulse reads.
- **Register each donor as an indicator.** Rejected (catalogue pollution, per ADR-0014/0015).
- **Normalise all editions to one unit at ingest.** Rejected — silently rebasing source figures violates ADR-0011's "preserve the source unit"; we carry the verbatim unit and let consumers convert with provenance.

## Consequences

- Foreign aid by donor and by sector gets a real, queryable, provenance-tracked home; the "Money In" external-financing story and donor-concentration views become buildable.
- A new fact table + repo + ingest CLI, all mirroring the `dne_facts` precedent → mechanical migration for Mother (wire into the schema barrel, `drizzle-kit generate`, apply).
- Cross-edition consumers MUST read `unit` (lakh vs thousand) — this is a deliberate, documented sharp edge, not a bug.
- The grant/loan sub-components and project-detail tables remain available for a follow-up that extends the same contract.

## References

- [ADR-0015](0015-dne-dimensional-fact-model.md) — the dimensional-fact precedent this mirrors
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — unit-verification protocol (read the annotation; don't fuzzy-match)
- [ADR-0013](0013-dne-ad-fiscal-year-periods.md) — AD→BS fiscal-year +57 offset
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — no OCR / transliteration (why Preeti + CID editions are deferred)
- `scrapers/mof_whitebook/parser.py`, `scripts/ingest-whitebook.ts`, `docs/sources/mof-whitebook-foreign-aid.md`
