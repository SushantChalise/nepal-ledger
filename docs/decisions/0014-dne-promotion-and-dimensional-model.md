# ADR-0014: DNE promotion — single series only; dimensional matrices deferred

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, data-model, dne, indicators

## Context

[ADR-0013](0013-dne-ad-fiscal-year-periods.md) made the `nrb_dne` parser extract real NRB *Database on Nepalese Economy* External Sector files. The open question was how to promote those rows from `staging_indicator_values` into `approved_indicator_values`, given the validator blocks any `indicator_slug_raw` not present in the `indicators` table (`IndicatorUnknown`). CMEFs (7) and NCPI (78) were hand-seeded; DNE seemed to need a "register hundreds of slugs" step.

Investigating the actual parser output across the three currently-parsing files exposed why a blind auto-register is wrong:

| File | Distinct slugs | What the slugs actually are |
|------|---------------|------------------------------|
| Foreign-Trade | ~745 | **commodities** (`dne-agarbatti`, `dne-aircraft-spareparts`) |
| Migrant-Workers-Remittance | ~314 | **countries + Nepali districts** (`dne-afghanistan`, `dne-baglung`) |
| Balance-of-Payments-BPM6 | ~101 | genuine BoP line items, but with row-number artifacts (`dne-...-r92`) from repeated sub-labels |

Foreign Trade and Remittance are **dimensional matrices** — exports/imports *by commodity*, remittance *by source country* and *by recipient district*. Their row labels are dimension VALUES, not indicators. `approved_indicator_values` is a single-dimensional `(indicator, period, value)` model; forcing these in would either (a) register ~1,000 commodity/country/district "indicators" (catalogue pollution, meaningless joins) or (b) silently flatten a dimension into the slug. Both are modeling debt.

## Decision

**Promote only genuine single-dimensional DNE series into `approved_indicator_values`. Defer dimensional matrices to a future dimensional model — do not register their row labels as indicators.**

1. **Single-series files** (each row label is a real macro indicator over time) — e.g. forex-reserve totals, tourist-arrival totals, exchange-rate series, and a curated set of BoP headline aggregates — are promotable. Their slugs are auto-derivable into `indicators` via a generated seed (manageable count, genuine concepts).
2. **Dimensional matrices** (Foreign Trade by commodity, Remittance by country/district) are **NOT** promoted to `approved_indicator_values` and their row labels are **NOT** registered as indicators. They stay in `staging` (extracted, provenance-tracked) until a dimensional fact model exists.
3. **The dimensional model is a separate future ADR.** Options to evaluate then: a `dne_facts` table with explicit `indicator` + `dimension_kind` + `dimension_value` columns, or a generic `(indicator_id, dimension_key, dimension_value, period, value)` breakdown table. The Money Map / trade-composition views need this eventually; it is not built now.
4. **No catalogue pollution, ever.** A `dne-<commodity>` / `dne-<country>` / `dne-<district>` slug must never enter `indicators`. The auto-seed (when built) operates on an explicit allowlist of single-series files, not "every slug the parser emits".
5. **BoP `-rNN` artifacts** are a parser-disambiguation smell (repeated sub-labels under assets vs liabilities). A curated BoP headline promotion must target stable, unambiguous line items, not the raw row-label set.

## Alternatives Considered

- **Auto-register all ~1,000 slugs.** Rejected — pollutes the indicator catalogue with commodities/countries/districts; breaks the meaning of "indicator"; makes `indicators` unusable as a concept index.
- **Flatten the dimension into the slug (`dne-exports-agarbatti`).** Rejected — hides a real dimension, explodes slug count, and still can't answer "exports by commodity" cleanly.
- **Add a dimension column to `approved_indicator_values` now.** Rejected for this round — a schema change that affects every consumer (Pulse, Money Map) and deserves its own ADR with the dimensional model fully designed.
- **Block DNE entirely.** Rejected — the single-series files (reserves, tourism, BoP headlines) are genuine, valuable, and fit the existing model.

## Consequences

- DNE single-series data can reach `approved_indicator_values` via a small, curated auto-seed (built against an allowlist of single-series files).
- DNE trade/remittance breakdowns remain in `staging` — extracted and provenance-tracked, not lost, not promoted, not polluting the catalogue — until the dimensional model lands.
- The `indicators` table stays a clean concept index.
- A follow-up ADR must design the dimensional fact model before trade-by-commodity / remittance-by-country can power Money-Map composition views.

## References

- [ADR-0013](0013-dne-ad-fiscal-year-periods.md) — DNE AD-fiscal-year parsing
- [ADR-0010](0010-ingest-cli-conventions.md) — ingest CLI conventions / DNE umbrella source
- [DATA_PIPELINE.md](../DATA_PIPELINE.md) — staging → validation → approved
- `scrapers/nrb_dne/parser.py`
