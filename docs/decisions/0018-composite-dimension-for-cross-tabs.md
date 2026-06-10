# ADR-0018: Composite dimension for two-dimensional facts in `dne_facts`

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-model, dimensional, dne_facts, customs, trade

## Context

[ADR-0015](0015-dne-dimensional-fact-model.md) gave `dne_facts` a clean shape: a
fact is a *base measure* sliced by *exactly one* dimension
(`dimension_kind` + `dimension_value`). That covers commodity-only, country-only,
office-only breakdowns.

But some source tables are genuine **cross-tabs** — two dimensions at once. The
Department of Customs FTS workbook has commodity×partner sheets (sheet 4 imports,
sheet 6 exports): *"how much diesel did Nepal import **from India** specifically"*.
That is sliced by HS-commodity AND partner country simultaneously — it does not
fit the one-dimension contract. The original customs parser deferred these
sheets for exactly this reason.

Options to represent a 2-D fact:
1. A new table with two dimension columns (`dimension_a_kind/value`, `dimension_b_kind/value`) — a schema change + migration, and a parallel repo/ingest path.
2. A generic EAV blob — rejected in ADR-0015 (too loose).
3. **A composite dimension** encoded into the existing one-dimension contract.

## Decision

Represent a two-dimensional slice as a **composite dimension** in the existing
`dne_facts` table — **no new table, no migration**:

- **`dimension_value` = `<part-a>__<part-b>`** — the two members joined by a `__`
  (double-underscore) separator, where **both parts are separator-stable** (they
  never contain `__`). For customs: `<hs-code>__<country-slug>`, e.g.
  `27101930__india`. (HS codes are pure digits; country slugs are `[a-z0-9-]`.)
- **`dimension_kind`** names the composite axis, not a single dimension:
  `customs-import-source` (commodity × source country) and
  `customs-export-destination` (commodity × destination country).
- **`dimension_label`** is human-readable `<part-a label> → <part-b label>`,
  e.g. `Diesel → India`.
- **`base_indicator_slug` stays the SAME** single-dimension measure
  (`customs-merchandise-imports` / `customs-merchandise-exports`). The composite
  facts are therefore a strict **disaggregation** of the single-dimension facts.

### The reconciliation invariant (the safeguard)

Because the composite facts disaggregate the same measure, **summing a composite
axis back to one part must reconcile to the single-dimension total**. For
customs: Σ(partner facts for a commodity) == that commodity's single-dimension
total. This is **verified, not assumed** — the customs parser's test suite
asserts it against the real annual workbook: all 5,264 import + 1,236 export
commodities reconcile with worst relative diff **0.00000000%**, and the
grand-total rows match the headline (imports 1,804,122,731 / exports
277,030,201 npr_thousand). A composite extractor that doesn't reconcile has a
geometry bug and must not ship (ADR-0011 discipline).

### Ingest + storage

No ingest change: `ingest:customs-trade` routes `dimensional_rows` → `dne_facts`
generically; its Zod schema accepts arbitrary `dimension_kind`/`dimension_value`
strings; `dne_facts_unique_idx` already keys on `(dimension_kind, dimension_value)`;
all `dne_facts` text columns are uncapped. Composite rows flow through unchanged.

> **Operational note (live-DB only):** the single-dimension customs facts were
> already ingested (Wave 5). Because the source-document helper appends a new
> `source_documents` row per run (and the unique index includes
> `source_document_id`), re-running the full CLI on an already-ingested edition
> would *duplicate* the single-dimension facts and double-count downstream sums.
> So the composite backfill for the already-live annual edition was ingested
> **composite-only** (filtered to the two composite `dimension_kind`s), leaving
> the single-dimension facts untouched. On a fresh DB the single CLI run emits
> both kinds under one source_document and this nuance does not arise.

## Alternatives Considered

- **Two-dimension table + migration** — rejected for now: the composite encoding
  reuses the proven `dne_facts` machinery (repo, idempotency, ingest) with zero
  schema risk, and the reconciliation invariant keeps it honest. If a future
  consumer needs to filter/aggregate heavily on *both* axes independently and the
  `__`-split proves awkward in SQL, revisit with a dedicated matrix table.
- **Registering each (commodity,partner) pair as an indicator** — rejected
  (catalogue pollution, same as ADR-0014/0015).

## Consequences

- Customs commodity×partner cross-tab lands: ~38,884 composite facts (imports
  33,887 + exports 4,997), queryable as "where does commodity X go / come from".
- The `__` separator is a load-bearing convention: any future composite
  dimension MUST guarantee neither part contains `__`, and SHOULD carry a
  reconciliation test against the single-dimension total.
- `dimension_kind` vocabulary grows: `customs-import-source`,
  `customs-export-destination` (composite) alongside the single-dimension kinds.
- Querying one axis means a `split_part(dimension_value, '__', 1|2)` or a
  `LIKE 'prefix__%'` — acceptable for the current read patterns.

## References

- [ADR-0015](0015-dne-dimensional-fact-model.md) — the one-dimension `dne_facts` model this extends
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — verify by reconciliation/magnitude
- `scrapers/customs_trade/parser.py` (v0.2.0) + tests (the reconciliation assertion)
- `docs/sources/customs-monthly-trade.md`
