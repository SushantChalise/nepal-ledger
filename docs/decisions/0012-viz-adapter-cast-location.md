# ADR-0012: D3 Viz Type-Bridges Live in src/lib/viz/adapters

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** ui, viz, conventions

## Context

D3's TypeScript typings use generic type parameters that frequently diverge from the runtime data shapes feature code wants to pass. Concretely, `d3-sankey`'s `SankeyGraph<N,L>` requires `source` and `target` on links to be typed as `string | number | SankeyNode<N,L>`, but at the call site the data has plain string IDs — `source: string`, `target: string`. The library resolves string IDs to node objects at runtime via a `nodeId` accessor, so the runtime behaviour is correct, but the TypeScript compiler rejects the plain-string form without a cast.

The same problem recurs with `sankey<N,L>().nodeId(...)`: the accessor receives a `SankeyNode<N,L>` but needs to return the `.id` field, which the generic `N` type does not expose. A cast bridges the generic `SankeyNode<N,L>` to `{ id: string }`.

Without a policy, these casts end up inline in feature components — `MoneyMap`, future `BorrowedTime` flow diagrams, district MRI charts. Inline casts in feature code violate CONTEXT_RULES.md Rule 6 ("No Silent Failure Patterns": no `any`; no `as unknown as`) and make the cast intent invisible to reviewers.

CONTEXT_RULES.md §"Cast Escape Hatches" item (c) already reserved `src/lib/viz/adapters/*` for exactly this use. This ADR makes that reservation concrete with a named function and an explicit policy.

## Decision

All D3 and charting-library type bridges are implemented in `src/lib/viz/adapters/`. Feature components stay cast-free.

**The concrete form established by `src/lib/viz/adapters/d3-sankey.ts`:**

- A single exported function (`computeSankeyLayout`) accepts a `LayoutInput<N, L>` with `links` typed as `{ source: string; target: string; value: number } & L` — the natural form feature code already has.
- The two required casts (`input as unknown as SankeyGraph<N,L>` and `.nodeId(n => (n as unknown as { id: string }).id)`) live inside the adapter function, not in any feature component.
- Feature components import `computeSankeyLayout` and the resolved-node/link types; they never import `sankey`, `SankeyGraph`, or raw d3 functions that require casts.

**The general policy:**

> Whenever a D3, Recharts, or other charting library requires a cast to bridge its generic type signature to the actual data shape used in the application, that cast lives in a file under `src/lib/viz/adapters/`. It is documented with a comment citing this ADR and the specific type mismatch being bridged. Feature components import the adapter's output types and functions only.

This policy extends to future charting libraries added to the project (e.g., Recharts for BFI time-series, Visx for the Money Funnel). Each library gets its own adapter file if it requires casts.

## Alternatives Considered

- **Inline casts in feature components with eslint-disable comments:** Casts scattered across ten feature files are impossible to audit. When the charting library upgrades and the cast changes, there is no single place to update. Rejected.

- **Declare `links` as `any[]` in feature code:** `any` is banned by Rule 6. Rejected.

- **Patch d3-sankey's type definitions:** DefinitelyTyped types are maintained externally; patching them locally creates drift with upstream and would need re-applying on every `@types/d3-sankey` upgrade. Rejected.

- **Use a different Sankey library with better TypeScript support:** The project uses `d3-sankey` as the canonical charting dependency (ADR-0001 stack includes D3). Switching libraries to avoid two casts is not proportionate.

- **One adapter file per feature instead of `src/lib/viz/adapters/`:** Feature-local adapters would not be reusable across the five D3-heavy features planned (Money Map, Money Funnel, Borrowed Time, Land Use Atlas, Tourism Rupee). A shared adapter folder amortises the work and keeps the sanctioned cast locations enumerable.

## Consequences

### Positive

- CONTEXT_RULES.md cast escape hatch (c) is now a concrete, named location with a working example.
- Every future PR diff that adds a cast in a feature component can be rejected by citing this ADR — no ambiguity.
- `src/lib/viz/adapters/d3-sankey.ts` serves as the reference implementation for other adapters (Recharts, Visx, etc.).
- Feature components stay cast-free, which makes them easier to typecheck and easier for junior contributors to read.

### Negative

- Feature code must import from the adapter rather than directly from `d3-sankey`. This is a minor indirection, and the adapter is a thin wrapper — it does not abstract the D3 API meaningfully.
- If the adapter function signature is too narrow for a new feature's data shape, the adapter needs to be extended. Mother must be consulted before extending adapters in ways that would require additional casts beyond the ones already documented.

### Neutral / unknown

- CONTEXT_RULES.md item (c) already required "a co-located test asserting the contract". The initial `d3-sankey.ts` adapter does not yet have such a test. A Vitest unit test that calls `computeSankeyLayout` with a minimal graph and asserts the returned nodes/links have expected coordinates is a follow-up item.

## References

- [`src/lib/viz/adapters/d3-sankey.ts`](../../src/lib/viz/adapters/d3-sankey.ts) — the reference implementation
- [CONTEXT_RULES.md](../CONTEXT_RULES.md) §"Cast Escape Hatches" item (c) — the policy this ADR makes concrete
- [ADR-0001](0001-tech-stack.md) — D3 is in the sanctioned stack
