# ADR-0001: Tech Stack

- **Status:** Accepted (refined by later ADRs — see [ADR-0002](0002-cloudflare-workers-opennext.md) for hosting, [ADR-0003](0003-ai-assisted-parsing-policy.md) for AI parsing policy, [ADR-0004](0004-supabase-storage-instead-of-r2.md) for storage)
- **Date:** 2026-05-13
- **Deciders:** Mother Opus, user
- **Tags:** infra, framework, db, hosting

## Context

We need to build Nepal Ledger: a Next.js content-rich web platform with a live Pulse, multiple hero visualizations (D3 Sankey, geospatial atlas), a structured Knowledge Base, a Fact Ledger, three signature public utilities, monthly data ingestion from Nepal government sources (PDF + CSV), bilingual content (English + Nepali), and a YouTube + short-form distribution layer. The build is solo with AI assistance, targeting ~25 hours/week effort, on a deliberately-zero-cost free-tier cloud stack in Year 1.

The forces:
- The platform is a publication + dashboard hybrid (long-form articles + live data)
- Audience is 70%+ mobile (Nepal mobile internet is uneven; diaspora on metered connections)
- SEO matters (organic discovery is the primary acquisition channel)
- Multiple data refresh cadences (monthly NRB, daily FCGO, monthly Customs)
- Bilingual routing (English-first; Nepali alongside)
- Visual journalism is the moat (custom D3 + Recharts)
- Solo operator — operational simplicity matters
- Future features: search, auth, paid tier — runtime needed

## Decision

| Layer | Choice |
|-------|--------|
| Framework | Next.js 15 (App Router) + TypeScript strict |
| Package manager | pnpm |
| UI | Tailwind CSS v4 + shadcn/ui primitives |
| Charts | Recharts (custom) + Tremor (KPI cards) |
| Diagrams | D3.js |
| Database | Supabase Postgres + Drizzle ORM |
| File storage | Supabase Storage (Year 1) → Cloudflare R2 (Phase 2 when payment method on file — see ADR-0004) |
| Hosting | Cloudflare Workers via `@opennextjs/cloudflare` (see ADR-0002) |
| Email | Resend |
| Analytics | Cloudflare Web Analytics |
| Search | Pagefind |
| Errors | Sentry (free tier) |
| Scrapers | Python 3.12 + pdfplumber + httpx |
| CI/CD | GitHub Actions |
| Domain | Cloudflare Registrar |

## Alternatives Considered

### Framework: Astro vs Next.js

- **Astro:** static-site-first, zero-JS by default, excellent for pure content. Considered seriously in v4 of the strategy plan.
- **Next.js (chosen):** App Router supports dynamic Pulse + ISR for stories + Server Actions for forms + future auth + future paid tier. Astro would need a separate backend or framework swap when those features arrive. Solo dev already familiar with Next.js — zero learning tax.

### Database: Cloudflare D1 vs Supabase

- **Cloudflare D1:** SQLite-on-edge, free 5GB, pairs natively with Pages, low latency.
- **Supabase (chosen):** Postgres power for complex queries (joins, CTEs, window functions for indicator history), Drizzle ORM works perfectly with both but Postgres has richer types (jsonb, arrays, money), 500MB DB free, included Auth + Realtime + Storage if needed later. The Knowledge Base + Fact Ledger queries need Postgres expressiveness.

### Hosting: Vercel vs Cloudflare (Pages vs Workers)

- **Vercel:** Native Next.js. 100GB bandwidth/month free. Kept as emergency fallback.
- **Cloudflare Pages:** Originally chosen at v5 of the plan. Reconsidered when bootstrapping — see [ADR-0002](0002-cloudflare-workers-opennext.md). Pages is positioned for static-first sites; full-stack Next.js with App Router + RSC + Server Actions + ISR is better served by Workers + OpenNext.
- **Cloudflare Workers + OpenNext (chosen):** see ADR-0002.

### Object storage: AWS S3 vs Cloudflare R2 vs Supabase Storage

- **S3:** industry standard, but charges for egress (downloads). The platform's job involves serving PDFs and source documents repeatedly — egress would dominate the bill.
- **R2:** zero egress fees, 10GB free, S3-compatible API. **Requires a credit card on file even for the free tier.** User opted not to add a card during Year 1 prototype phase. Deferred to Phase 2 per [ADR-0004](0004-supabase-storage-instead-of-r2.md).
- **Supabase Storage (chosen Year 1):** included in the same free tier as the database; no credit card; same auth keys; 1GB storage, 5GB egress shared with DB. Sufficient for 6–12 months of ingestion at current volume. S3-compatible API means migration to R2 is a client-swap when payment method is on file.

### Package manager: npm vs pnpm

- **npm:** default, ubiquitous.
- **pnpm (chosen):** faster, stricter (catches phantom dependencies), monorepo-ready if we ever need it, the user already has it installed.

### ORM: Prisma vs Drizzle

- **Prisma:** mature, generates client, great DX.
- **Drizzle (chosen):** TypeScript-first (schema is the source of truth, types flow), lighter runtime, no separate generation step, better SQL transparency, smaller bundle. Migration story is solid.

## Consequences

### Positive
- Total Year 1 cost: ~$10–15 (domain only). Everything else is free tier.
- Operational simplicity: 6 services to manage instead of 12.
- Performance: Cloudflare edge serves Nepal POP well; mobile-first audience well-served.
- Type safety: end-to-end TypeScript with Zod boundaries; hallucination structurally harder.
- Visual moat: Recharts + D3 + Tailwind cover the entire data-viz surface.

### Negative
- Free-tier limits will eventually bite (500MB Supabase, 10GB R2, 2K GitHub Actions minutes). Need active quota monitoring.
- Cloudflare Pages has some Next.js App Router edge cases (image optimization, certain ISR patterns). Vercel fallback ready.
- Drizzle is less mature than Prisma; some patterns are less-trodden.
- D3 has a learning curve; first Money Map will take longer than subsequent visualizations.

### Neutral / unknown
- Long-term editorial sustainability of the 25-hr/week solo cadence — to be tested in practice.
- Bilingual Nepali rendering complexity (Devanagari fonts, locale-aware date formats) — likely tractable, not blocking.

## References

- Strategy plan §"Tech Stack": [../STRATEGY.md](../STRATEGY.md) (canonical, in-repo)
- [docs/CLOUD_STACK.md](../CLOUD_STACK.md) — full free-tier composition reasoning
- [docs/CONVENTIONS.md](../CONVENTIONS.md) — how the chosen stack is used in practice
