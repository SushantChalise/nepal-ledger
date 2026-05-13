# ADR-0006: Next.js 16, Not 15

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** Mother Opus, user (delegated authority for the overnight burst)
- **Supersedes:** Next.js version reference in [ADR-0001](0001-tech-stack.md) (refined, not reversed)
- **Tags:** infra, framework, scaffold

## Context

[ADR-0001](0001-tech-stack.md) chose Next.js 15 in the Day-0 doctrine. During the Day 1–3 bootstrap, `pnpm dlx create-next-app@latest` delivered Next.js 16.2.6 as the current stable. The scaffold proceeded with 16 because:

1. Downgrading the scaffold would require pinning create-next-app to an older version and patching for backward-compat — work that buys nothing.
2. Every feature ADR-0002 enumerates (App Router, RSC, Route Handlers, SSR, ISR, Server Actions, streaming, Middleware, image optimization, PPR) is supported by Next 16.
3. `@opennextjs/cloudflare@1.19.9` declares Next 15 + 16 compatibility in its peer-deps.
4. Next 16 includes Turbopack as the default `dev` bundler, the `use cache` directive (Cache Components), and the new `unstable_after()` semantics — all forward-compatible with our planned architecture.

The friction would be greater if doctrine continued to cite Next 15 while reality used Next 16. Code agents picking up the project would read "Next.js 15" in docs, reach for Next-15-specific patterns, and ship inconsistencies.

## Decision

**Doctrine is updated to reference Next.js 16.** All future ADRs and docs cite Next 16 features and constraints. Future Next minor/major bumps follow the same lightweight ADR pattern (one ADR per major version line) unless the bump introduces meaningful migration cost.

Concretely:
- [ADR-0001](0001-tech-stack.md) tech-stack row: "Next.js 15" → "Next.js 16"
- [docs/BACKEND_PLAN.md](../BACKEND_PLAN.md) §"The Tech Stack (Decided)": same
- [docs/CONVENTIONS.md](../CONVENTIONS.md): no changes — the patterns we cite (Server Components, Server Actions, `use client` islands, `<Image>`, App Router) work identically on Next 16

## Alternatives Considered

### Option A: Downgrade scaffold to Next 15

- **Pro:** matches doctrine literally
- **Con:** create-next-app doesn't support a `--version` flag; would require manually pinning `next@^15` in package.json and downgrading `eslint-config-next`, `@types/*`, and possibly `tailwindcss`. None of these have a load-bearing reason to be 15 specifically.
- Rejected.

### Option B: Stay on Next 16, update doctrine (chosen)

- **Pro:** zero churn; consistent moving forward; cheaper to maintain
- **Con:** doctrine drift from the original ADR-0001 — addressed by this ADR

### Option C: Defer decision until later

- Increases the window in which agents read mismatched info. Rejected.

## Consequences

### Positive

- Turbopack default in `next dev` — meaningfully faster HMR than the webpack default of Next 15
- Cache Components (`'use cache'`, `cacheLife`, `cacheTag`, `updateTag`) available when we wire ISR for Pulse + Monthly Verdict (Day 29–45 milestone)
- `unstable_after()` for after-response work (useful when we add Sentry breadcrumb / analytics flushes)
- Latest `eslint-config-next` matches the runtime, no version drift in lint rules

### Negative

- Some third-party libraries that didn't update for React 19 may still complain. So far no actual blockers in our locked stack.
- OpenNext for Cloudflare's tree-shaking config in `withSentryConfig` is webpack-only (per ADR-0005 §"Cloudflare Workers Compatibility Note"); Next 16 + Turbopack + OpenNext esbuild means we strip the webpack options post-Sentry-wizard regardless. No new risk.

### Neutral / unknown

- Whether any Next 16 internal API change bites OpenNext later. We track @opennextjs/cloudflare release notes per ADR-0002's "Failure mode (less likely)" mitigation.

## References

- [ADR-0001](0001-tech-stack.md) — original tech stack
- [ADR-0002](0002-cloudflare-workers-opennext.md) — hosting + OpenNext compatibility
- [ADR-0005](0005-sentry-setup.md) — webpack-only tree-shake option handling
- Next.js 16 release notes (verify against current docs before relying on a specific feature)
