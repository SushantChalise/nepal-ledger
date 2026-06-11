# ADR-0026: MoALD Agri-Stats overlapping macro/trade/loan tables are cross-reference only (not ingested)

- **Status:** Proposed (pending user ratification on PR #58 review)
- **Date:** 2026-06-11
- **Deciders:** Mother Opus (proposed); user (to ratify)
- **Tags:** data-pipeline, fact-ledger, double-counting, moald-agri-stats, source-of-truth

## Context

The MoALD *Statistical Information on Nepalese Agriculture 2080/81* (source
`moald-agri-stats`) is a 224-page compendium. Beyond the agricultural data the
`scrapers/moald_agri_stats/parser.py` ingests (crop/livestock/horticulture/input
time-series + province/district cross-sections — see the parser docstring and
[`docs/sources/moald-agri-stats.md`](../sources/moald-agri-stats.md)), it also
**republishes** three blocks of macro data compiled by *other* agencies:

| Agri-Stats table | Content | Original compiling agency | Already a Nepal Ledger source |
|---|---|---|---|
| Table 10.1–10.12 | GDP / Gross Value Added by industrial division, expenditure approach, deflators, macro indicators | NSO national accounts | `mof-economic-survey-annual` → `dne_facts` GVA ([ADR-0023](0023-economic-survey-gva-dimensional-model.md)); `nrb-cmefs` / `nrb-dne` GDP |
| Table 11.1–11.2 | Exports / imports of selected agricultural commodities | Department of Customs (ASYCUDA) | `customs-monthly-trade` → `dne_facts` commodity×partner ([ADR-0018](0018-composite-dimension-for-cross-tabs.md)) |
| Table 14.1–14.3 | Sector-wise loans & advances of commercial banks / development banks / finance companies | Nepal Rastra Bank | `nrb-bfi-monthly-xlsx`, `nrb-loans-by-sector` |

These are **not** primary MoALD measurements. They are secondary reproductions
of figures whose authoritative custodian is NSO / Customs / NRB — sources Nepal
Ledger already ingests (or has registered) directly.

## Decision

**Do not ingest Agri-Stats tables 10.x, 11.x, or 14.x as facts.** They are
**cross-reference only**: usable for spot-checking the canonical series during a
story, but never written to `dne_facts` / `approved_indicator_values` from the
`moald-agri-stats` parser.

Rationale, in order of weight:

1. **Fact-Ledger integrity (no double-counting).** Every public claim is
   clickable to exactly one provenance row (STRATEGY.md, the Fact Ledger). The
   same GDP figure arriving from both `mof-economic-survey-annual` and
   `moald-agri-stats` would create two contradictory-looking provenance rows for
   one fact, or silently double a Money-Map flow if summed. ADR-0009 makes the
   *original* source registry the single source of truth; a republication is not
   a new source of truth.

2. **Provenance grade.** The canonical sources are graded by their nature —
   Customs trade is grade **A** (transaction-level ASYCUDA), NRB banking is the
   monetary authority. Agri-Stats reproduces them at grade **B** (administrative
   compilation, a year late). Ingesting the B copy would *degrade* data we
   already hold at A.

3. **Recency.** Agri-Stats is annual and lags; the canonical feeds (customs
   monthly, NRB monthly/quarterly) are fresher. The republished copy is strictly
   staler.

4. **Snapshot vs. revision.** The canonical sources carry their own revision
   lineage (Data Continuity Protocol). A figure frozen in one MoALD annual would
   fork that lineage.

## Consequences

- The parser's module docstring and the source profile list 10.x / 11.x / 14.x
  under **deferred — overlapping source**, now pointing at this ADR for the
  rationale (previously an open "needs canonical-source ADR" TODO).
- If, in future, a story needs an Agri-Stats macro number that the canonical
  source does *not* carry (e.g. an agriculture-specific GVA sub-aggregate not in
  the Economic Survey annex), that is a **genuinely new measure** and may be
  ingested under its own base slug — but only after confirming via
  [DATA_AUDIT.md](../DATA_AUDIT.md) that no canonical source already holds it.
  The default remains: republished ⇒ not ingested.
- This ADR does **not** restrict the agricultural tables the parser already
  ingests (crops, livestock, horticulture, fertilizer) — MoALD *is* the
  authoritative custodian for those, so they are primary facts.

## Alternatives considered

- **Ingest with a `republished_from` provenance flag.** Rejected: adds a schema
  concept and a dedup burden to the Fact Ledger to store data we already have,
  fresher and at a higher grade, elsewhere. No reader benefit.
- **Ingest only Table 15 (commodity → Agriculture-GVA % contribution).** This one
  is closer to MoALD-native (it allocates agricultural GVA across commodities).
  Deferred separately as a low-priority small national table, not under this ADR;
  it does not overlap an existing source and may be revisited on its own merits.
