# ADR-0025: `observation_type` — actuals vs projections vs interpolated

- **Status:** Accepted
- **Date:** 2026-06-11
- **Deciders:** Mother Opus
- **Tags:** schema, data-strategy, international-data, calendar-periods, pulse

## Context

The international-data ingest program ([docs/INTERNATIONAL_DATA_RESEARCH.md](../INTERNATIONAL_DATA_RESEARCH.md)) introduces sources whose value is precisely the data the domestic feeds (NRB, MoF, CBS) do **not** carry: **forward-looking and model-derived numbers**.

- **IMF WEO** publishes a 5-year **projection** path alongside historical actuals — e.g. the April 2026 vintage gives `GGXWDG_NGDP` (gross debt % GDP) out to 2031. The projections are the headline value (they make the "Borrowed Time" pillar actionable), but a 2029 debt figure is categorically different from a 2021 actual.
- **WB PIP** with `fill_gaps=true` emits **interpolated** poverty/Gini values between survey anchor years (Nepal has only 4 actual surveys: 1995/96, 2003/04, 2010/11, 2022/23).
- **ILO modelled estimates (ILOEST)** are **model-derived** labour figures anchored to the last labour-force survey, not direct observations.

The existing pipeline (`staging_indicator_values` → `approved_indicator_values`, [DATA_PIPELINE.md](../DATA_PIPELINE.md)) has no way to express this distinction. Every row is implicitly an actual. If WEO projections land unmarked, a future-dated debt projection is indistinguishable from a published actual in the time series — the Pulse, Money Map, and Fact Ledger would present a forecast as fact. That violates the mission's provenance discipline ([CONTEXT_RULES.md](../CONTEXT_RULES.md), the Fact Ledger's "every claim clickable with confidence").

Encoding the distinction in the free-text `parser_notes`/`notes` field was rejected: it is a first-class semantic property that feature code must filter on (e.g. "show actuals solid, projections dashed"), and free-text fails the Type-Driven rule.

## Decision

Add a first-class **`observation_type`** to the indicator-values contract — a Postgres enum and a column on **both** `staging_indicator_values` and `approved_indicator_values`.

1. **Enum** (`observation_type` in [enums.ts](../../src/lib/db/schema/enums.ts)):
   - `actual` — a directly published / measured value (the default; every existing row).
   - `projection` — a forward-looking forecast (IMF WEO out-years).
   - `interpolated` — filled between observed anchor points (PIP `fill_gaps`).
   - `estimate` — model-derived where no direct observation exists (ILO modelled).
   - `provisional` — published but flagged by the source as subject to revision (e.g. NRB "P"/"R" vintages).

2. **Backwards-compatible default `'actual'`.** The column is `NOT NULL DEFAULT 'actual'` on both tables. The migration backfills every existing row to `actual`. No existing parser changes behaviour — they emit no `observation_type` and the default applies.

3. **Single serialization point.** The Python contract adds `observation_type: ObservationType = "actual"` to `StagingRowDraft` ([scrapers/_common/types.py](../../scrapers/_common/types.py)); because `to_json_dict` is defined once on the dataclass, every parser emits the field automatically. The TS Zod boundary ([src/lib/ingestion/types.ts](../../src/lib/ingestion/types.ts)) adds `observation_type: ObservationTypeSchema.default('actual')`, so even a parser that omits it validates.

4. **Carried through the pipeline.** `persistStaging` maps it onto the staging insert; `promoteStagingRow` copies it onto the approved row. It rides alongside `confidence_grade` — the two are orthogonal: a WEO projection is `confidence_grade='A'` (authoritative IMF) **and** `observation_type='projection'`.

5. **Period contract unchanged.** A projection still carries a real reporting period (FY2029 has a genuine AD start/end); `observation_type` is the only thing that marks it as not-yet-realised. The unique key on approved values (`indicator, period_type, period_bs, revision`) is unchanged — re-ingesting a later WEO vintage that revises a projection appends a new revision, exactly as actuals revisions already work.

## Consequences

- **Feature code must opt into projections.** Pulse/Money Map default queries should filter `observation_type = 'actual'` unless a view explicitly wants the forecast path. A follow-up touches the read repositories to expose the filter; until then, callers that ignore the column see all rows (acceptable — no source emits non-`actual` yet at migration time).
- **The cross-source benchmark check** ([benchmark.ts](../../src/lib/validation/benchmark.ts)) should compare like-with-like — only `actual` WEO vs `actual` DNE. Projections are never benchmarked against actuals.
- **One migration touches the two highest-traffic tables.** Because it is an additive `ADD COLUMN ... DEFAULT`, it is non-locking on Postgres ≥ 11 and safe.
- This is the substrate for the whole Batch-1 international program; `imf-weo` is the first consumer in the same PR.

## Alternatives considered

- **Free-text marker in `notes`** — rejected (not type-safe, not filterable; see Context).
- **Separate `projected_indicator_values` table** — rejected: doubles every read path and breaks the single-series-with-revisions model; a projection *is* an indicator value with a different epistemic status, not a different entity.
- **Confidence grade `C` for projections** — rejected: conflates authority (who says it) with realisation (has it happened). An IMF projection is high-authority; downgrading it to `C` would misrepresent a credible forecast as low-quality data.
