# Trade — feature context

**Customs foreign-trade detail.** Renders Nepal's merchandise trade — total imports vs exports, the structural deficit, and the top commodities (by HS code) and partner countries on each side — for BS fiscal year 2081/82.

Lens / pillar: serves Pillar 2 "Money Out" (the goods side — rupees that leave to pay for imports Nepal does not produce)
Route(s): `/trade`
Status: live · Department of Customs Foreign Trade Statistics (`dne_facts`, source id `customs-monthly-trade`, Grade A)

## What this is (and is NOT)
The two measures are **merchandise customs values**, compiled from ASYCUDA World declarations:
- `customs-merchandise-imports` — goods imported into Nepal.
- `customs-merchandise-exports` — goods exported from Nepal.
"Trade balance" = exports − imports (negative = deficit). This is **merchandise** trade only — it is NOT the full current account (no services, no remittance, no income). Never call the deficit the "current-account deficit".

## Data in
- `dne_facts` WHERE `base_indicator_slug IN ('customs-merchandise-imports','customs-merchandise-exports')`, via `getTradeOverview(periodBs?, topN?)` (`src/features/trade/server/queries.ts`).
- Three dimensions exist per measure: `commodity` (HS code as `dimension_value`, description as `dimension_label`), `country`, `customs_office`. The page surfaces **commodity** and **country**; `customs_office` is not rendered.
- Reads production only (`dne_facts`); read-only. No repository edits (does not touch `src/lib/db/repositories/dne-facts.ts`).
- Provenance: 6,886 annual facts (imports 5,264 commodity + 164 country + 29 customs; exports 1,236 + 164 + 29) ingested by `scripts/ingest-customs-trade.ts` from `scrapers/customs_trade/parser.py` (FY 2081/82 annual workbook). Monthly editions (`Jestha 2082` year_to_date, `Shrawan 2081` monthly) also exist.

## Unit (ADR-0011 — read the sheet header, don't fuzzy-match)
Every row is `unit = 'npr_thousand'` (every FTS value sheet states "(figures are in Rs. Thousands)"). **Raw thousands are never displayed.** Conversion lives in `format.ts`:

    NPR billion  = value_thousand / 1_000_000
    NPR trillion = value_thousand / 1_000_000_000   (headline totals only)

Worked examples (FY 2081/82 annual, verified against the live DB): total imports 1,804,122,731 thousand → **NPR 1.80 tn**; total exports 277,030,202 thousand → **NPR 277.03 bn**; deficit **NPR 1.53 tn**; export coverage 277/1,804 = **15.4%**; imports = **6.5×** exports. Per-commodity figures (e.g. Diesel 128,761,649 thousand → NPR 128.76 bn) use `formatNprBillion`; headline totals use the magnitude-aware `formatNprMagnitude`.

## Ranking / totals (the query)
`getTradeOverview` does, for one period (default `'2081/82'`):
- **Totals + distinct commodity counts** — one GROUP BY over the commodity dimension. The commodity-dimension sum is the canonical period total; it equals the country-dimension sum (verified — both 1,804,122,731 thousand for imports). A second cheap aggregate gets the distinct country counts.
- **Four ranked lists** — top-N (default 15) members of {imports, exports} × {commodity, country}, each a scoped `ORDER BY value DESC, dimension_value ASC LIMIT topN` query (tie-break by slug for stable order), run in `Promise.all`.
- **Available periods** — `DISTINCT (reporting_period_bs, reporting_period_type)`, annual sorted first, for the footer note.
- Each list carries `totalMembers` (the FULL distinct count) so the page states "top 15 of 5,264 … the remainder is not shown" — **never implying completeness** (Data Continuity Protocol). Shares are computed against the side total, not the shown subset.

## Files
- `server/queries.ts` — `getTradeOverview(periodBs = '2081/82', topN = 15)` returns `Result<TradeOverview>` (totals, `tradeBalance`, four `TradeBreakdown`s {members ranked desc, `totalMembers`}, `availablePeriods`, `confidence`). All SQL Zod-validated at the DB boundary; typed `NotFound`/`QueryFailed`; never throws. Exports the measure-slug, dimension-kind, `DEFAULT_PERIOD_BS`, `DEFAULT_TOP_N` constants.
- `format.ts` — `formatNprBillion` ("NPR X.XX bn"), `formatNprMagnitude` (auto bn/tn for totals), `thousandToBillion`, `formatSharePct`, `formatCoverageRatio` (exports÷imports %), `formatImportMultiple` (imports÷exports ×). **Not** `'use client'` — plain module imported by the Server page and server tables.
- `components/TradeRankTable.tsx` — **Server Component**; one generic ranked table for any breakdown (commodity or country, import or export). Semantic `<table>` with `<caption>`, `<th scope="col">`, `<th scope="row">`; value + share columns; a decorative (`aria-hidden`) share bar; HS code shown under commodity labels; `overflow-x-auto`.
- `components/TradeBalanceBar.tsx` — **Server Component**; two proportional bars (imports vs exports) scaled to the larger side, with figures + coverage % as text. Decorative bars (`aria-hidden`).
- `page` at `src/app/trade/page.tsx` — async Server Component; reuses Pulse `KpiCard` (imports / exports / deficit / coverage); "what this shows" prose, the balance bar, four ranked sections (each with a "top N of M" sub-label), concentration prose, and a source/confidence (Grade A)/unit footer. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Unit is NPR thousand at rest; display NPR billion (÷ 1,000,000) or NPR trillion for totals.** Never print raw thousands. All conversion goes through `format.ts` — do not inline a different divisor.
- These are **merchandise customs values** — NOT the current account, NOT services/remittance. The deficit is the *merchandise* trade deficit.
- Render commodity descriptions and country names **faithfully** as stored. Some HS descriptions carry source typos / truncations (e.g. "Liquidified Petrolium Gas", "direct reduct on"). Do not "fix"/normalise them; the HS code is shown alongside as the stable identifier.
- **Top-N honesty:** there are 5,264 import commodities. The page renders only the top N and always states "top N of M … remainder not shown". Never imply the full set is rendered. `totalMembers` must keep coming from `COUNT(DISTINCT dimension_value)`, not from the shown rows.
- Confidence is **A** (official customs-declaration records). Source label is exactly "Department of Customs — Foreign Trade Statistics".
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map/tourism-rupee gotcha).
- Typed empty state (`totalImports <= 0 && totalExports <= 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- The page hard-defaults to `reporting_period_bs = '2081/82'` (the annual file — the headline floor). Monthly/YTD periods coexist in the data; the footer notes them. If you add a period selector, keep it Server-rendered and keep the annual as the default.

## Gotchas
- `dne_facts.value` is `numeric(20,4)` → postgres-js returns it as a string (e.g. `"128761649.2307"`); coerced with `Number()` after a `Number.isFinite` guard. `ORDER BY value DESC` ranks numerically (the column is numeric, not text) — verified against the live DB (Diesel/soya oil/petrol top imports; India then China top partners).
- The commodity total and the country total for one period are the **same** aggregate (both dimensions partition the same trade value). We take the commodity sum as canonical; do not add them together.
- No `cn()` helper exists in this repo; className strings are plain template literals, matching the other route pages.
- Bars are purely decorative (`aria-hidden`): every value and share is stated in text, so meaning is never carried by colour/width alone (WCAG AA). The share-bar column is hidden `<640px` (the `sm:` breakpoint); the value + share columns remain.
- No D3 / viz adapter is used — bars are plain CSS widths, so this feature has zero `as` casts and ships no client JS.
- The SiteNav `/trade` link is added by Mother in `src/components/layout/SiteNav.tsx` — NOT in this feature's scope.

## Related
- ADRs: ADR-0015 (`dne_facts` dimensional model), ADR-0011 (data-unit identity / magnitude verification), ADR-0013 (BS fiscal-year period dating), ADR-0003 (no API parsing).
- Docs: `docs/sources/customs-monthly-trade.md` (source profile + unit/period rationale), `scrapers/customs_trade/` (parser), `docs/UI_ACCEPTANCE.md` (accessibility + content gates).
- Pattern reference: `src/features/state-enterprises/*` (closest analog — `dne_facts` npr_thousand→billion ranked table) and `src/features/migration-source/*` (top-N ranked breakdown). `src/features/money-map/server/queries.ts` for the Result + safeQuery + Zod-at-boundary pattern.
