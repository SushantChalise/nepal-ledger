# Money Map — feature context

**D3 Sankey visualization** of how Nepal's federal government distributes intergovernmental fiscal transfers to 753 local governments by grant type and local-level type.

Lens / pillar: Lens 2 — Money Map; serves Pillar 2 "Money Out" (government spending flows) and Pillar 3 "Money Captured"
Route(s): `/money-map`
Status: live · Ministry of Finance — Intergovernmental Fiscal Transfer Schedule FY 2082/83

## Data in
- `local_government_fiscal_transfers` joined to `entities` (kind = 'local_level'), aggregated by `grant_type` + `local_level_type` via `getFiscalTransferSankeyData()` (`src/features/money-map/server/queries.ts`)
- Amounts are stored and returned in **NPR crore** (1 crore = 10 million NPR). Never treat raw values as NPR thousands or NPR millions.
- Reads production only; no staging equivalent for fiscal transfers.

## Files
- `server/queries.ts` — async function `getFiscalTransferSankeyData()` that returns `Result<SankeyData>`; builds a 3-column Sankey graph (Federal → 8 grant types → 4 local-level types) via a single GROUP BY SQL query validated with Zod at the DB boundary
- `format.ts` — `formatNprCrore(nprCrore: number): string`; Nepali financial convention (≥100 crore → arab, ≥1 → crore, <1 → lakh); **not** `'use client'` — intentionally a plain module
- `components/SankeyDiagram.tsx` — `'use client'`; renders full Sankey SVG (≥640px) or stacked-bar fallback (<640px) with a visually-hidden accessible table always present; uses `computeSankeyLayout` + `sankeyLinkHorizontal` from `src/lib/viz/adapters/d3-sankey.ts`
- `page` at `src/app/money-map/page.tsx` — async Server Component; calls `getFiscalTransferSankeyData()`, calls `formatNprCrore()` for the header total, renders typed empty and error states, passes `SankeyData` to `<SankeyDiagram>`

## Invariants (don't break these)
- All amounts are **NPR crore**. The `unit` field in every row is `npr_crore`. Format via `formatNprCrore()` from `format.ts` — do not inline different formatting.
- `format.ts` MUST remain a plain (non-`'use client'`) module. It is imported by both the Server page and the `'use client'` SankeyDiagram. Making it a client module would 500 the server page (see Gotchas).
- D3 type-bridging `as` casts belong ONLY in `src/lib/viz/adapters/d3-sankey.ts` (sanctioned cast location per CONTEXT_RULES.md). `SankeyDiagram.tsx` has zero `as unknown as`.
- Typed empty state (`nodes.length === 0`) and typed error state (`!result.ok`) must remain; never throw from the page.
- The 3-column layout (Federal → GrantType → LocalLevelType) is a schema invariant. The query assumes `entities.metadata->>'local_level_type'` is populated for all `kind = 'local_level'` entities — rows with `null` local_level_type are coerced to `'unknown'`.

## Gotchas
- **`format.ts` must not be `'use client'`** — this bit us during development. If a module exported from a `'use client'` file is imported by a Server Component, Next.js 500s the page at render time. The fix: keep `format.ts` as a plain module with no React imports, so both server and client contexts can safely import it.
- D3 sankey's TypeScript types require `source`/`target` as `SankeyNode` objects, but the `nodeId` accessor makes plain string IDs work at runtime. The `as unknown as` casts in `d3-sankey.ts` are the standard workaround — do not attempt to "fix" them without understanding d3-sankey's type vs. runtime mismatch.
- `ResizeObserver` in `SankeyDiagram` is not cleaned up (observer reference is not stored for disconnect). This is intentional: the component is page-level and lives for the lifetime of the route. Revisit if the diagram becomes embeddable in a layout that mounts/unmounts it frequently.
- Grant type labels (`GRANT_TYPE_LABELS`) in `queries.ts` must stay in sync with the `GrantType` enum in `src/lib/db/schema/enums.ts`. Adding a new grant type in the DB schema requires updating both.

## Related
- ADRs: ADR-0003 (no API parsing), ADR-0004 (Supabase Storage)
- Docs: `docs/DATA_PIPELINE.md`, `docs/UI_ACCEPTANCE.md` (mobile fallback + accessibility gates), `src/lib/viz/adapters/d3-sankey.ts` (sanctioned cast location), `docs/CONTEXT_RULES.md` §"Cast Escape Hatches"
