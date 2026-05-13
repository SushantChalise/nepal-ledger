# ADR-0002: Cloudflare Workers + OpenNext as Primary Hosting (Not Pages)

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** Mother Opus, user
- **Supersedes:** Hosting choice in [ADR-0001](0001-tech-stack.md) (refined, not reversed — Cloudflare remains the host)
- **Tags:** infra, hosting, deployment

## Context

[ADR-0001](0001-tech-stack.md) chose Cloudflare as the host with "Cloudflare Pages (primary) / Vercel (fallback)." During the Day-0 doctrine hardening review, this was challenged: Cloudflare's own current guidance positions Pages for static-first / lightweight-SSR sites and routes full-stack Next.js apps (App Router + React Server Components + Server Actions + ISR + Middleware) to **Cloudflare Workers via the OpenNext adapter** (`@opennextjs/cloudflare`).

Nepal Ledger uses:
- App Router with React Server Components throughout
- Server Actions (calculator form submissions, Fact Ledger challenge submissions, newsletter signups)
- ISR (Pulse regenerates after data refresh)
- Middleware (i18n routing for `/en/*` and `/ne/*`)
- Streaming (article hero sections + interactive charts)

These are precisely the features that OpenNext on Workers supports and Pages handles less well.

## Decision

**Primary hosting:** Cloudflare Workers via `@opennextjs/cloudflare`.

**Static-only fallback:** Cloudflare Pages (used only if a specific subroute is provably 100% static; not the default).

**Emergency fallback:** Vercel (one-button revert by changing DNS; `vercel.json` committed).

## Alternatives Considered

### Option A: Cloudflare Pages with `@cloudflare/next-on-pages` (the v5 plan)
- Works for many Next.js apps but Cloudflare's framework guide explicitly routes full-stack SSR Next.js to Workers as of the current docs.
- Future feature support may lag behind the Workers adapter.
- Rejected.

### Option B: Vercel as primary
- Native Next.js — least friction.
- 100GB/month bandwidth cap on free tier — meaningful for a mobile-heavy Nepal/diaspora audience that might burst on a viral story.
- Kept as emergency fallback only.

### Option C (chosen): Cloudflare Workers + OpenNext
- Unlimited bandwidth, ~100K requests/day on free tier (generous for a niche publication).
- Supports App Router, RSC, Route Handlers, SSR, ISR, Server Actions, streaming, Middleware, image optimization, PPR.
- Same R2 / Workers KV ecosystem we already plan to use.
- Zero-egress data flow between R2 and Workers — efficient for source-document serving.

## Consequences

### Positive
- Aligns with Cloudflare's current best-practice path for Next.js full-stack apps.
- All planned features supported.
- Zero hosting cost in Year 1; cheap Year 2 upgrade path ($5/mo flat for 10M req).
- Same edge network as the rest of the stack — single ops surface.

### Negative
- **Node.js middleware introduced in Next.js 15.2 is not yet supported by OpenNext.** Workaround: keep middleware in the Edge runtime (which we already use for i18n).
- **OpenNext build/preview on native Windows is not fully supported.** Mitigated by [WINDOWS_DEV.md](../WINDOWS_DEV.md) — WSL2 or GitHub Actions for production-like preview.
- Adds a small ops layer (the OpenNext adapter version is its own thing we pin).

### Neutral / unknown
- Long-term OpenNext maintenance health. Cloudflare publicly endorses it; risk seems low.
- ISR semantics on Workers may differ subtly from Vercel's. We test-drive each ISR-dependent feature in WSL2 + CI before relying on it.

## Implementation Notes

- `wrangler.toml` committed at repo root.
- `package.json` scripts:
  - `pnpm dev` — Next.js dev server (Windows OK)
  - `pnpm build` — `next build`
  - `pnpm preview` — OpenNext build + `wrangler dev` (run in WSL2)
  - `pnpm deploy` — `wrangler deploy` (run in CI; manual deploys only from WSL2 if blocked)
- CI workflow `.github/workflows/deploy-production.yml` deploys on push to `main`.
- Preview deploys per PR via Cloudflare's GitHub integration.
- A `vercel.json` is committed alongside `wrangler.toml` so the Vercel emergency fallback is one DNS swap away — see [CLOUD_STACK.md](../CLOUD_STACK.md) §"Emergency fallback".

## References

- Cloudflare Workers + Next.js guide: https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/
- OpenNext for Cloudflare: https://opennext.js.org/cloudflare
- [CLOUD_STACK.md](../CLOUD_STACK.md) §"Cloudflare Workers + OpenNext"
- [WINDOWS_DEV.md](../WINDOWS_DEV.md) — Windows + WSL2 workflow
- [ADR-0001](0001-tech-stack.md) — original tech-stack ADR
