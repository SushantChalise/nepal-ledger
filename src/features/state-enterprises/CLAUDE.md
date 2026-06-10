# State Enterprises — feature context

**Public Enterprise X-Ray.** Renders Nepal's state-owned enterprises (SOEs) ranked by total government capital exposure, split into government **equity** (paid-in share capital) vs outstanding government **loan principal**, for BS fiscal year 2080/81.

Lens / pillar: "Money Captured / Money Wasted" view — how much public capital is tied up in SOEs and how it is structured (equity vs debt)
Route(s): `/state-enterprises`
Status: live · MoF / DPM-Office Yellow Book (Annual Performance Review of Public Enterprises), Annex-1, source id `dpm-public-enterprises-annual` (Grade B)

## What this is (and is NOT)
The two measures are the government's **capital exposures** to each enterprise, NOT revenue or profit:
- `soe-government-share` — paid-in government **equity** / share capital (शेयर).
- `soe-loan-principal` — outstanding government **loan principal** (ऋण).
"Total exposure" = equity + loan. Never phrase any figure as the enterprise's revenue, profit, or subsidy — those are a deferred (disabled placeholder) section.

## Data in
- `dne_facts` WHERE `dimension_kind = 'public_enterprise'` AND `reporting_period_bs = '2080/81'` AND `base_indicator_slug IN ('soe-government-share','soe-loan-principal')`, via `getStateEnterpriseExposure()` (`src/features/state-enterprises/server/queries.ts`).
- Reads production only (`dne_facts`); read-only. No repository edits (does not touch `src/lib/db/repositories/dne-facts.ts`).
- Provenance: 84 rows (42 enterprises × 2 measures) ingested by `scripts/ingest-dne-yellowbook.ts` from `scrapers/mof_yellowbook/parser.py` (Annex-1 of the FY2080/81 edition).

## Unit (ADR-0011 — read the header, don't fuzzy-match)
Every row is `unit = 'npr_thousand'` (the Annex-1 header states "(रु. हजारमा)" = NPR thousand). **Raw thousands are never displayed.** The page converts to NPR billion:

    NPR billion = value_thousand / 1_000_000

Worked example (Nepal Electricity Authority government share): 181,330,245 thousand ÷ 1e6 = 181.330245 → **"NPR 181.33 bn"**. All conversion lives in `format.ts` (`formatNprBillion`, `thousandToBillion`).

## Pivot / ranking (the query)
One GROUP BY `dimension_value` with conditional aggregates collapses each enterprise's two measure rows into one output row:
- `MAX(value) FILTER (WHERE base_indicator_slug = 'soe-government-share')` → equity
- `MAX(value) FILTER (WHERE base_indicator_slug = 'soe-loan-principal')` → loan
- `dimension_label` / `reporting_period_bs` / `confidence_grade` are homogeneous per enterprise, so `MIN()` over them is a safe marginal pick.
- Ordered by `COALESCE(share,0) + COALESCE(loan,0) DESC`, tie-broken by label. A measure absent for an enterprise (null) is treated as a genuine 0 (the enterprise carries no equity / no loan) — never a fabricated fill of a present-but-unreadable value.

## Files
- `server/queries.ts` — `getStateEnterpriseExposure()` returns `Result<StateEnterprises>` (`enterprises` ranked desc, `totalShare`, `totalLoan`, `grandTotal`, `fiscalYearBs`, `confidence`); single conditional-aggregate GROUP BY, Zod-validated at the DB boundary; typed `NotFound`/`QueryFailed` states, never throws. Exports `REPORTING_PERIOD_BS = '2080/81'` + the two base-measure slug constants.
- `format.ts` — `formatNprBillion` ("NPR X.XX bn"), `formatNprBillionCompact`, `thousandToBillion`, `formatSharePct`. **Not** `'use client'` — plain module imported by the Server page and the server table.
- `components/EnterpriseExposureTable.tsx` — **Server Component** (no `'use client'` — a static sorted table needs no interactivity). Semantic `<table>` with `<caption>`, `<th scope="col">`, `<th scope="row">` per enterprise; equity / loan / total columns in NPR billion; a decorative (`aria-hidden`) equity-vs-loan composition bar with a text + colour legend; `overflow-x-auto` for narrow viewports.
- `page` at `src/app/state-enterprises/page.tsx` — async Server Component; reuses Pulse `KpiCard`; "what this shows" prose, the ranked table, a disabled "Profit, loss & subsidy — coming soon" placeholder, and a source/confidence (Grade B)/unit footer. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Unit is NPR thousand at rest; display NPR billion (÷ 1,000,000).** Never print raw thousands. All conversion goes through `format.ts` — do not inline a different divisor.
- The two measures are **government equity vs government loan principal** — capital exposure, NOT revenue/profit/subsidy. The profit/subsidy section is a deliberate disabled placeholder; never fabricate or zero-fill a return figure (Data Continuity Protocol). It is deferred because the Yellow Book's per-sector profit tables are in a different (lakh) unit and a ragged layout not yet deterministically parsed.
- Render `dimension_label` enterprise names **faithfully** as stored (some carry known pdfplumber glyph-reorder artifacts, e.g. `दग्ुध`). Do not "fix"/normalise/fabricate names; the kebab `slug` is shown alongside as a stable identifier.
- Confidence is **B** (Yellow Book — government annual review compiled from enterprise statements, revised across editions). Source label is exactly "MoF / DPM-Office Yellow Book — Annual Performance Review of Public Enterprises".
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map/tourism-rupee gotcha).
- Typed empty state (`enterprises.length === 0 || grandTotal <= 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- `reporting_period_bs` is hard-filtered to `'2080/81'` (the bundled edition). If a later Yellow Book edition is ingested, parameterise this rather than mixing fiscal years into one ranking.

## Gotchas
- `dne_facts.value` is `numeric(20,4)` → postgres-js returns it as a string (e.g. `"181330245.0000"`); coerced with `Number()` after a `Number.isFinite` guard. A measure missing for an enterprise comes back `null` from the `FILTER` aggregate → treated as 0.
- No `cn()` helper exists in this repo; className strings are plain template literals, matching the other route pages.
- The composition bar is purely decorative (`aria-hidden`): the equity/loan split is stated in adjacent text cells, so meaning is never carried by colour alone (WCAG AA). The bar + legend are hidden `<640px` (the `sm:` breakpoint) where horizontal space is tight; the numeric columns remain.
- No D3 / viz adapter is used — the bar is a plain CSS flex composition, so this feature has zero `as` casts and ships no client JS.

## Related
- ADRs: ADR-0015 (`dne_facts` dimensional model), ADR-0011 (data-unit identity / magnitude verification), ADR-0013 (BS fiscal-year period dating), ADR-0020 (`docs/decisions/0020-yellowbook-soe-annex1-scope.md` — Annex-1 scope), ADR-0003 (no API parsing).
- Docs: `docs/sources/dpm-public-enterprises-annual.md` (source profile), `scrapers/mof_yellowbook/README.md` + `parser.py` (parser + unit/scope rationale), `docs/UI_ACCEPTANCE.md` (accessibility + content gates).
- Pattern reference: `src/features/migration-source/*` (closest analog — dimensional/aggregated ranked breakdown) and `src/features/money-map/server/queries.ts` (Result + safeQuery + Zod-at-boundary).
