# Money Flow — feature context

**The national money-flow Sankey** — the capstone view that ties Nepal's live macro flows into ONE picture: money entering the country (remittance, foreign aid, merchandise exports), passing through the economy, and leaving to pay for imports. **THE insight: remittance (NPR 1.73 tn) is the dominant inflow and more than funds the merchandise trade deficit (imports NPR 1.80 tn − exports NPR 0.28 tn = NPR 1.53 tn).** Money earned abroad — not goods sold — is what keeps Nepal's external books level.

Lens / pillar: Lens 2 family — a combined Money Map; serves Pillar 1 "Money In" and Pillar 2 "Money Out" together. This is the synthesis story.
Route(s): `/money-flow`
Status: live · FY 2081/82 (remittance + trade); foreign-aid edition FY 2077/78

This is a NEW, separate page from `/money-map` (the intergovernmental fiscal-transfer Sankey). They are different flows — do not merge or cross-edit them.

## Data in (three sources, three units)
All three are fetched independently in one `Promise.all`; a missing source degrades gracefully (it does not blank the page). Read-only; no repository edits.
- **Remittance** — `approved_indicator_values` slug `dne-remittance-inflow`, unit `npr_million`, FY 2081/82 = `1,731,270.33` (grade B).
- **Foreign aid** — `foreign_aid_facts` latest edition (FY 2077/78), unit `npr_lakh`, `donor` dimension only, grant (`605,277`) + loan (`2,994,993`) = `3,600,270` (grade B).
- **Merchandise trade** — `dne_facts` `customs-merchandise-imports` / `customs-merchandise-exports`, `commodity` dimension, FY 2081/82, unit `npr_thousand`: imports `1,804,122,731.44`, exports `277,030,201.56` (grade A).
- (GDP nominal `dne-gdp-nominal` = 6,107 npr_billion exists as context but is intentionally NOT in the Sankey — kept focused, not cluttered.)

## ⚠️ Unit normalization (ADR-0011) — the reason `format.ts` exists
Each source is stored in a **different** unit. A Sankey with mixed units is meaningless, so EVERY magnitude is converted to **NPR billion** before it enters a node or link. Conversion lives ONLY in `format.ts` (never inline a divisor):

    npr_million  → NPR bn  ÷ 1,000        remittance  1,731,270    → 1,731 bn
    npr_lakh     → NPR bn  ÷ 10,000        aid         3,600,270    → 360 bn
    npr_thousand → NPR bn  ÷ 1,000,000     imports     1,804,122,731 → 1,804 bn

`queries.ts` calls `normalizeToBillion(value, unit)` which dispatches on the row's declared `unit` and returns `null` for an unrecognised unit (the flow is then skipped / errored — never silently mis-scaled).

## Node / link model (verified balanced)
A Money-In → Nepal Economy → Money-Out flow, 3 columns:
- **Column 0 (sources)**: Remittance (1,731), Foreign aid grants+loans (360), Merchandise exports (277) → each links to the economy hub.
- **Column 1 (hub)**: Nepal economy; through-value = total inflows = **2,368 bn**.
- **Column 2 (sinks)**: Merchandise imports (1,804) + **Retained in the economy** (564) — the residual.

`Retained in the economy = total inflows − merchandise imports` (clamped ≥ 0). It is an **explicitly-labelled honest residual** (NOT a fudge): if imports ever exceed inflows, the residual clamps to 0 and `outflowsExceedInflows` is set so the page states the shortfall instead of drawing a negative band. The Sankey is conservation-balanced: inflows→economy (2,368.33) == economy→sinks (2,368.33), diff 0.0000 (verified against the live DB).

Headline figures carried for the KPI strip / prose: `totalInflowsBillion` 2,368, `tradeDeficitBillion` 1,527 (imports−exports), `remittanceSharePct` **73.1%**.

## Files
- `format.ts` — unit normalizers `millionToBillion` / `lakhToBillion` / `thousandToBillion` (the ADR-0011 core) + display `formatNprBillion` ("NPR X bn"), `formatNprMagnitude` (auto bn/tn for totals), `formatSharePct`. **Not** `'use client'` — plain module imported by both the Server page and the client Sankey (the money-map/growth/trade RSC gotcha).
- `server/queries.ts` — `getMoneyFlowData(periodBs = '2081/82')` returns `Result<MoneyFlowData>`. Three per-source fetchers (`fetchRemittance`, `fetchTrade`, `fetchAid`) each return a typed Result; absence ≠ error (`aid: null` when no edition). Builds the 3-column node/link graph. All SQL Zod-validated at the DB boundary; typed `NotFound` (only when BOTH remittance AND trade are missing) / `QueryFailed`; never throws.
- `components/MoneyFlowSankey.tsx` — `'use client'`; full Sankey SVG (≥640px) via `computeSankeyLayout` + `sankeyLinkHorizontal` from `src/lib/viz/adapters/d3-sankey.ts`, stacked-bar inflow fallback (<640px) with a "view full diagram" disclosure, and an always-present visually-hidden accessible `<table>`. Mirrors money-map's `SankeyDiagram` field-for-field.
- `page` at `src/app/money-flow/page.tsx` — async Server Component; reuses Pulse `KpiCard` (total inflows / remittance / trade deficit / remittance share); "what this shows" prose carrying the remittance-funds-the-deficit story; the Sankey; an amber accounting note explaining the residual + the fiscal-year mismatch; source/confidence/unit footer. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **All flows are NPR billion in the node/link model**, normalized at the DB boundary from three different at-rest units. Never put a raw at-rest value into a node/link. All conversion goes through `format.ts` — do not inline a different divisor.
- **Foreign aid: sum exactly ONE dimension** (`donor`). The `donor` and `sector` cuts of the same (measure, period) are the SAME aggregate — summing both double-counts. The query filters `dimension_kind = 'donor'` and sums only the latest-edition rows.
- **The residual node is labelled and honest.** "Retained in the economy" = inflows − imports, clamped ≥ 0. Never relabel it as a measured figure; never draw a negative band (use `outflowsExceedInflows`).
- **Fiscal-year mismatch is stated, not hidden.** Remittance + trade are FY 2081/82; the aid edition is FY 2077/78. `aidFiscalYearBs` is carried separately and the page caveats it explicitly.
- **Merchandise trade only** — exports/imports here exclude services and income, so the deficit is the *merchandise* trade deficit, NOT the current-account deficit (same rule as `/trade`).
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page.
- D3 type-bridging `as` casts belong ONLY in `src/lib/viz/adapters/d3-sankey.ts` (ADR-0012). `MoneyFlowSankey.tsx` has zero `as unknown as`; the `link.source`/`link.target` reads are plain post-layout narrowings the adapter already guarantees.
- Typed empty state (NotFound → calm "no data yet") and typed error state (any other AppError) must remain; never throw from the page.
- Do NOT modify `/money-map` (`src/features/money-map/*`) — that is the separate fiscal-transfer Sankey.

## Gotchas
- The Sankey SVG is **aria-hidden / decorative**: every value is also printed as in-SVG text labels AND in the always-present visually-hidden `<table>`. Meaning is never carried by colour or band width alone (the money-map accessibility gotcha). Column colours (teal=in, blue=hub, amber=out) are reinforced by text labels on every node.
- `approved_indicator_values.value` is `numeric(24,6)`; `dne_facts.value` / `foreign_aid_facts.value` are `numeric(20,4)` → postgres-js returns all as strings; coerced with `Number()` after a `Number.isFinite` guard (`toFinite`).
- Remittance picks the highest `revision_number` for the period (the latest approved revision), matching the Data Continuity Protocol (revisions coexist; newest wins for display).
- The aid query groups by `(base_indicator_slug, reporting_period_bs)` ordered `reporting_period_bs DESC`, then sums only the rows whose period equals the first (latest) row's period — so a future newer White Book edition is picked up automatically.
- No `cn()` helper exists in this repo; className strings are plain template literals, matching the other route pages.
- The SiteNav `/money-flow` link is added by **Mother** in `src/components/layout/SiteNav.tsx` — NOT in this feature's scope.

## Related
- ADRs: ADR-0011 (data-unit identity / magnitude verification — the core of this feature), ADR-0012 (viz adapter cast location), ADR-0015 (`dne_facts` dimensional model), ADR-0017 (`foreign_aid_facts` model), ADR-0013 (BS fiscal-year period dating), ADR-0003 (no API parsing).
- Docs: `docs/UI_ACCEPTANCE.md` (accessibility + content gates), `src/lib/viz/adapters/d3-sankey.ts` (sanctioned cast location).
- Pattern reference: `src/features/money-map/*` (the Sankey component + Result/safeQuery/Zod-at-boundary pattern — mirrored here), `src/features/trade/*` (customs npr_thousand→billion, the deficit framing), `src/features/growth/*` (KpiCard strip + per-source Result pattern). Repositories consulted (not extended): `src/lib/db/repositories/{approved-indicator-values,dne-facts,foreign-aid-facts}.ts`.
