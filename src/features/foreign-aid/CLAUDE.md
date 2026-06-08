# Foreign Aid — feature context

**Who funds Nepal (Money In).** Renders foreign aid entering Nepal ranked by development partner (donor) and by recipient ministry (sector), each split into **grant** (need not be repaid) vs **loan** (must be repaid), for the latest White Book edition (FY 2020/21, BS 2077/78), with a compact prior-edition (FY 2015/16) comparison.

Lens / pillar: Pillar 1 "Money In" — external financing spine (who funds Nepal, in what form, to which ministry)
Route(s): `/foreign-aid`
Status: live · MoF White Book (Source Book for Projects Financed with Foreign Assistance), source id `mof-whitebook-foreign-aid` (Grade B)

## What this is (and is NOT)
The two measures are the **headline grant/loan totals** per dimension member:
- `foreign-aid-grant` — the White Book "Total Grant" column (cash + reimbursable + direct payment + commodity). Aid that need NOT be repaid.
- `foreign-aid-loan` — the "Total Loan" column. Aid that MUST be repaid (adds to external debt).
"Total aid" = grant + loan. The grant/loan distinction is the editorial point — never collapse it or imply all aid is free money. This is money flowing IN (external financing), not government spending or revenue.

## Data in
- `foreign_aid_facts` (ADR-0017) WHERE `dimension_kind IN ('donor','sector')` AND `reporting_period_bs = '2077/78'` (latest) AND `base_indicator_slug IN ('foreign-aid-grant','foreign-aid-loan')`, via `getForeignAidBreakdown()` (`src/features/foreign-aid/server/queries.ts`). A second small query reads the FY2015/16 donor totals for the comparison line.
- Reads production only (`foreign_aid_facts`); read-only. No repository edits (does not touch `src/lib/db/repositories/foreign-aid-facts.ts`).
- Provenance: 278 rows total — FY2020/21 (134: 44 donors + 23 sectors × 2 measures, `npr_lakh`) + FY2015/16 (144: 46 donors + 26 sectors × 2 measures, `npr_thousand`), ingested by `scripts/ingest-whitebook.ts` from `scrapers/mof_whitebook/parser.py`.

## ⚠️ Unit (ADR-0011 / ADR-0017 — the crux; unit VARIES BY EDITION)
Unlike every other feature, the source unit is **not constant**: the White Book stamps a different money unit on each edition, carried verbatim per-row in the `unit` column. Raw values must NEVER be summed across editions. The conversion to NPR billion is keyed on the row's own `unit` and lives in `format.ts` (`toBillion(value, unit)`):

    npr_lakh     : NPR = value × 100,000 → bn = value / 10,000      (1 lakh = 1e5; 1 bn = 1e9)
    npr_thousand : NPR = value × 1,000   → bn = value / 1,000,000   (1 thousand = 1e3)

Worked examples (donor grant+loan totals, asserted against live DB):
- FY 2020/21: 3,600,270 `npr_lakh` ÷ 10,000 = 360.027 → **"NPR 360.0 bn"** (grant 60.5 + loan 299.5; COVID-year loan surge — IDA/DPC, IMF/RCF, ADB/PBL).
- FY 2015/16: 205,894,111 `npr_thousand` ÷ 1,000,000 = 205.894 → **"NPR 205.9 bn"** (grant-heavy pre-COVID: 110.9 grant vs 95.0 loan).

The query converts each row to billion with ITS OWN unit **before** any addition, so every monetary field on the output types (`AidMember`, `AidBreakdown`, `priorDonor`) is already NPR billion — downstream never sees a raw lakh/thousand figure, and a cross-edition sum can only ever happen on the safe (billion) scale.

## Pivot / ranking (the query)
One GROUP BY `dimension_value` per `dimension_kind` with conditional aggregates collapses each member's two measure rows into one output row (same shape as state-enterprises):
- `MAX(value) FILTER (WHERE base_indicator_slug = 'foreign-aid-grant')` → grant
- `MAX(value) FILTER (WHERE base_indicator_slug = 'foreign-aid-loan')` → loan
- `MIN(unit)` — `unit` is homogeneous within one edition, so MIN is a safe marginal pick.
- Ordered by `COALESCE(grant,0) + COALESCE(loan,0) DESC`, tie-broken by label. Sorting by the RAW summed value is correct here because the SQL is always scoped to a single edition (one unit); the billion conversion happens after, in TS.
- A measure absent for a member (null) is treated as a genuine 0 (the member has only grant or only loan, e.g. IMF/RCF is loan-only) — never a fabricated fill.
- Cross-check: the donor grand total equals the sector grand total (same aid, two views) — asserted equal during the build.

## Files
- `server/queries.ts` — `getForeignAidBreakdown()` returns `Result<ForeignAid>` (`byDonor` + `bySector` each a ranked `AidBreakdown`, `fiscalYearBs/Ad`, `confidence`, optional `priorDonor`); conditional-aggregate GROUP BY pivots, Zod-validated at the DB boundary; typed `NotFound`/`QueryFailed`, never throws. The prior-edition comparison degrades to `null` on absence or query failure (optional context, never blocks the headline). Exports `LATEST_PERIOD_BS = '2077/78'`, `PRIOR_PERIOD_BS = '2072/73'`, and the two base-measure slug constants.
- `format.ts` — `toBillion(value, unit)` (the per-unit conversion), `formatBillion` ("NPR X.XX bn" on a pre-converted billion number), `formatNprBillion` (raw value + unit → label in one step), `formatSharePct`, and the `ForeignAidUnit` type. **Not** `'use client'` — plain module imported by the Server page and the server table.
- `components/AidBreakdownTable.tsx` — **Server Component** (no `'use client'` — a static sorted table needs none). Reused for both donor and sector breakdowns via a `memberNoun` + `captionId` prop. Semantic `<table>` with `<caption>`, `<th scope="col">`, `<th scope="row">` per member; grant / loan / total columns in NPR billion; a decorative (`aria-hidden`) grant-vs-loan composition bar with a text + colour legend; `overflow-x-auto` for narrow viewports.
- `page` at `src/app/foreign-aid/page.tsx` — async Server Component; reuses Pulse `KpiCard` (total aid, total grant, total loan, top donor); "what this shows" prose foregrounding the grant-vs-loan / repayment distinction and the COVID-year comparison; the donor table, the sector table, and a source/confidence (Grade B)/unit footer that states the per-edition lakh-vs-thousand conversion explicitly. Renders typed empty/error states; never throws.

## Invariants (don't break these)
- **Unit VARIES BY EDITION; convert per-row with the row's own `unit` (`toBillion`) BEFORE summing.** Never print raw lakh/thousand; never add raw values across editions. All conversion goes through `format.ts` — do not inline a divisor, and do not assume a single global unit.
- The two measures are **grant vs loan** — keep the distinction visible (grants need not be repaid; loans add to external debt). Never label aggregate aid as "free money" or as government spending/revenue.
- Render `dimension_label` donor/ministry names **faithfully** as stored (English "unofficial translation", incl. source spacing artifacts like "MOF- Financing"). Do not "fix"/normalise names.
- Confidence is **B** (White Book — budget-book allocations revised across editions). Source label is exactly "MoF White Book — Source Book for Projects Financed with Foreign Assistance".
- `format.ts` MUST remain a plain (non-`'use client'`) module — importing a client module from a Server Component 500s the page (the money-map/tourism-rupee gotcha).
- Typed empty state (`byDonor.members.length === 0 || byDonor.grandTotal <= 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- `reporting_period_bs` is hard-filtered to `'2077/78'` for the headline ranking (the latest edition). If a newer White Book edition is ingested, bump `LATEST_PERIOD_BS` rather than mixing fiscal years into one ranking.
- The page does NOT add the SiteNav link — Mother owns `src/components/layout/SiteNav.tsx`.

## Gotchas
- `foreign_aid_facts.value` is `numeric(20,4)` → postgres-js returns it as a string (e.g. `"564947.0000"`); coerced with `Number()` inside `toBillion` (which has a `Number.isFinite` guard). A measure missing for a member comes back `null` from the `FILTER` aggregate → treated as 0.
- The Zod boundary schema constrains `unit` to `z.enum(['npr_lakh','npr_thousand'])`, so a row carrying any other unit is rejected at the boundary rather than silently mis-scaled. `toBillion`'s `default` branch returns 0 (a typed dead-end) for the same reason — both guard the same drift.
- Floating-point: converted billions carry tiny residue (e.g. `360.02700000000004`); display always rounds via `toLocaleString`/`toFixed`, and the donor-vs-sector equality check uses a `< 1e-6` tolerance, not `===`.
- No `cn()` helper exists in this repo; className strings are plain template literals, matching the other route pages.
- The composition bar is purely decorative (`aria-hidden`): the grant/loan split is stated in adjacent text cells, so meaning is never carried by colour alone (WCAG AA). The bar + legend are hidden `<640px` (the `sm:` breakpoint) where horizontal space is tight; the numeric columns remain. The KPI grid is 1-col `<640px` → safe at 360px.
- No D3 / viz adapter is used — the bar is a plain CSS flex composition, so this feature has zero `as` casts and ships no client JS.

## Related
- ADRs: ADR-0017 (`docs/decisions/0017-foreign-aid-fact-model.md` — the fact model + unit policy), ADR-0011 (data-unit identity / magnitude verification), ADR-0013 (BS fiscal-year period dating), ADR-0015 (`dne_facts` dimensional precedent), ADR-0003 (no API parsing).
- Docs: `docs/sources/mof-whitebook-foreign-aid.md` (source profile), `scrapers/mof_whitebook/parser.py` (parser + unit/scope rationale), `docs/UI_ACCEPTANCE.md` (accessibility + content gates).
- Pattern reference: `src/features/state-enterprises/*` (closest analog — ranked grant/loan-style dimensional breakdown from a `*_facts` table, Result + safeQuery + Zod-at-boundary, decorative composition bar) and `src/features/migration-source/*`.
