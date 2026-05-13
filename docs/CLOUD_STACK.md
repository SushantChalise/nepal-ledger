# Cloud Stack — Free-Tier Composition

Nepal Ledger runs on a deliberately composed free-tier stack. Every service is chosen for: (a) generous free tier, (b) credible upgrade path when we outgrow it, (c) clean DX. Total monthly cost target for Year 1 prototype: **$0–$15** (domain only).

---

## The Stack at a Glance

| Concern | Service | Free tier | Upgrade signal | Migration path |
|---------|---------|-----------|----------------|----------------|
| Hosting (Next.js, full-stack) | **Cloudflare Workers via @opennextjs/cloudflare** | 100K req/day; generous CPU; same edge network | Sustained >80K req/day | Workers Paid ($5/mo flat for 10M reqs) |
| Hosting (static fallback) | Cloudflare Pages | Unlimited bandwidth, 500 builds/month | Used only if a route is provably static-only | n/a |
| Hosting (emergency fallback) | Vercel | 100GB bandwidth/month | If OpenNext blocks a feature we need | Vercel Pro ($20/mo) |
| Database (Postgres) | **Supabase** | 500MB DB, 1GB file, 50K MAU, 5GB egress | DB approaching 400MB | Supabase Pro ($25/mo) / self-host on Fly |
| Object storage | **Supabase Storage** (primary; no card needed) | 1GB storage; 5GB egress shared with DB | Approaching 800MB | Cloudflare R2 (10GB, zero egress) once a payment method is on file |
| Email | **Resend** | 3K emails/mo, 100/day | >2.5K emails/mo or 80/day | Resend Pro ($20/mo for 50K) |
| Analytics | **Cloudflare Web Analytics** | Unlimited, privacy-first | Need event-level tracking | Plausible ($9/mo) |
| Error tracking | **Sentry** | 5K errors/mo | >4K errors/mo | Sentry Team ($26/mo) |
| Search | **Pagefind** | Free (static, no service) | Never (static index scales) | — |
| CI/CD | **GitHub Actions** | 2K min/mo private, unlimited public | Approaching 1.5K min | Buy more minutes (cheap) |
| Cron (scrapers) | **GitHub Actions Cron** | Same pool as CI | Same | Cloudflare Workers Cron Triggers (free) |
| DNS + Registrar | **Cloudflare** | DNS free; registrar at cost (~$10/yr `.com`) | — | — |
| Image optimization | **Next.js Image** on Cloudflare Pages | Built-in | Heavy image workload | Cloudflare Images ($5/mo) |
| Source-of-truth backups | **R2 + GitHub** | Both | — | Add Backblaze B2 redundancy |
| Auth (Phase 2) | **Supabase Auth** | Included with DB free tier | >50K MAU | Supabase Pro |

**Year 1 baseline cost: ~$10–15** (domain only). Everything else is free tier.

---

## Why This Combination

### Cloudflare Workers + OpenNext adapter (hosting — primary)

- **Why not Pages:** As of 2025+, Cloudflare's own guidance for full-stack Next.js (App Router + RSC + Server Actions + ISR + Middleware) is **Workers via the OpenNext adapter** (`@opennextjs/cloudflare`), not Pages. Pages is positioned for static-first / lightweight-SSR sites. Nepal Ledger uses Server Actions (form submissions, calculator inputs), ISR (regenerate Pulse on data refresh), App Router with RSC, and middleware (i18n routing). Workers+OpenNext is the right home.
- **What it supports** (per Cloudflare's framework guide): App Router, React Server Components, Route Handlers, SSR, ISR, Server Actions, streaming, Middleware, image optimization, PPR.
- **What it doesn't yet support:** Node.js middleware introduced in Next.js 15.2. We work around this by keeping middleware logic in the Edge runtime where applicable.
- **Edge-first:** workers run at every Cloudflare POP — Nepal traffic hits Singapore/Mumbai POP with low latency.
- **Free tier:** 100K requests/day. Generous; an early-stage publication won't approach this.
- **Build/preview:** `wrangler dev` or `pnpm preview` runs the OpenNext-bundled worker locally.
- **Deploy:** `wrangler deploy` from CI; preview deploys per PR auto-generate.
- **Failure mode (most likely):** an upstream Next.js feature lands before OpenNext supports it. Mitigation: pin Next.js minor versions; upgrade only after OpenNext compatibility note is published.
- **Failure mode (less likely):** OpenNext bug breaks a build. Mitigation: Vercel emergency fallback (we keep the `vercel.json` in repo) — switch DNS in <30 min if needed.

### Windows note
OpenNext build/preview is not fully supported on native Windows. See [WINDOWS_DEV.md](WINDOWS_DEV.md): production-like preview runs in WSL2 or GitHub Actions; routine development is fine on Windows.

### Static fallback (rare): Cloudflare Pages
Used only if a specific subroute is provably 100% static. Not the primary host.

### Emergency fallback: Vercel
- 100GB bandwidth/month free
- One-button revert by changing DNS to `vercel-domain.app`
- We commit `vercel.json` so deploy is one command if Workers fails

### Supabase (Postgres)
- **Postgres** — Drizzle ORM works, full SQL power, joins/CTEs for complex queries
- **500MB DB** — enough for 100K+ indicator_values rows, 50K+ fact_ledger claims, all entity profiles
- **Free row-level security** — useful when we add user accounts in Phase 2
- **Realtime channels** — free for live Pulse updates if needed later
- **Edge functions** — backup compute option if Cloudflare Pages limits us
- **Failure mode:** 500MB cap. Mitigation: aggressive use of R2 for blobs (PDFs, images); only structured data in Postgres

### Supabase Storage (object storage — primary for prototype)
- **No card required.** Cloudflare R2 (the originally-planned storage) requires a payment method on file even for the free tier. Supabase Storage is included in the same free tier as the database — same account, same auth keys, no credit card needed.
- **1GB free** — sufficient for ~6–12 months of source documents at current ingestion volume (~10–20 PDFs/month at 5–30MB each). The first existing CMEFs PDF is 0.8MB; the agriculture statistical PDF is 6.8MB.
- **5GB/month egress** shared with the database. Source documents are archived, not constantly re-served — egress is not the binding cost.
- **S3-compatible API** for migration: when we add R2 later, the same parser and Fact Ledger code paths work with a one-line client swap.
- **Use case:** archive every NRB CMEFs PDF, customs Excel, OAG report immediately on download. Hash-named, timestamped, immutable. Source-of-provenance for Fact Ledger.

### Cloudflare R2 (object storage — Phase 2, when payment method is on file)
- **Zero egress fees** — if archive grows past 800MB OR Supabase egress becomes the binding quota, this is the migration target.
- **10GB free** with the same S3-compatible API.
- **Migration path:** copy archive forward to R2; update `source_documents.storage_provider` from `supabase` to `r2`; new ingestions write to R2; Supabase Storage stays as warm read-only backup for ~3 months, then archived.
- **Trigger to migrate:** any one of (a) Supabase Storage >800MB, (b) Supabase egress >3.5GB/mo, (c) need for true zero-egress public PDF serving.

### Resend (email)
- **3K emails/month free** — covers newsletter list up to ~500 subscribers with weekly + 2 monthly emails
- **React Email integration** — write emails in JSX, same dev model as the site
- **Excellent webhooks** — bounce/spam/delivery events available
- **Failure mode:** 100/day rate limit. Mitigation: batched sends, scheduled queueing

### Cloudflare Web Analytics
- **No cookies → no banner** — privacy-friendly default
- **No event budget** — unlike Plausible/Umami free tiers
- **Server-rendered tracker** — works without JS for SEO bots
- **Failure mode:** less granular than paid alternatives. Mitigation: add Plausible later for funnel analysis only if needed

### GitHub Actions (CI + cron)
- **Already there** — no extra service to manage
- **2K min/month private** — comfortable for monthly build + biweekly story PRs
- **Free for public repos** — when we open-source later
- **Cron triggers** — fine for monthly NRB scraper; not great for sub-hourly tasks
- **Failure mode:** cron schedule occasionally drifts by ~15 min. Mitigation: scrapers idempotent, retry safe

---

## Cloudflare CLI Auth — Use API Token, Not `wrangler login`

`wrangler login` uses an OAuth flow that opens a browser and expects a callback on `http://localhost:8976`. On Windows, this commonly fails because:
- Windows Firewall blocks the loopback callback
- Antivirus intercepts the localhost listener
- VPN routing breaks the redirect
- The browser opens but the redirect lands on a 404

**The supported, more secure, and CI-required path:** use a scoped API token.

### One-time token creation (browser, ~60 seconds)

1. Open https://dash.cloudflare.com/profile/api-tokens
2. **Create Token** → template **"Edit Cloudflare Workers"**
3. Recommended additions under Permissions:
   - **Account → Workers R2 Storage → Edit** (for Phase 2)
   - **Account → D1 → Edit** (optional, future)
   - **Account → Account Settings → Read**
4. Account Resources: your account. Zone Resources: All zones (or scope later).
5. **Continue to summary** → **Create Token** → copy once.

### Local use (PowerShell)

```powershell
# Session-only
$env:CLOUDFLARE_API_TOKEN = "<paste-into-terminal-never-into-chat>"

# Persistent (user scope; open new shell after)
[Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "<token>", "User")

# Verify
wrangler whoami
```

`wrangler whoami` will show the authed account + email. From `whoami` output you can also see `CLOUDFLARE_ACCOUNT_ID` (the long hex). Save it; CI deploy workflow needs it.

### CI use (GitHub Actions)

```powershell
gh secret set CLOUDFLARE_API_TOKEN
gh secret set CLOUDFLARE_ACCOUNT_ID
```

The deploy workflow (`.github/workflows/deploy-production.yml`) already references both. No code change.

---

## Account Setup Checklist (Day 1)

Mother Opus runs these checks at the start of bootstrap. User executes (Mother cannot create accounts):

- [ ] **GitHub:** account exists, can create repos, `gh auth login` complete
- [ ] **Cloudflare:** account at https://dash.cloudflare.com, verified email, `wrangler login` complete
- [ ] **Supabase:** account at https://supabase.com, project created, project URL + anon key + service-role key saved
- [ ] **Resend:** account at https://resend.com, verified email, API key generated
- [ ] **Sentry:** account at https://sentry.io, project created, DSN saved
- [ ] **Domain:** decide now (`nepalledger.com` recommended) — buy through Cloudflare Registrar
- [ ] **Vercel (fallback):** account exists, `vercel login` complete (optional, only if Cloudflare Pages limits us)

Secrets land in:
- **GitHub Actions secrets** (for CI access to Cloudflare, Supabase migrations)
- **Cloudflare Pages env vars** (for runtime access at the edge)
- **`.env.local`** (developer machine — gitignored)

Never in `.env` committed to repo. Never in code. Never in Slack/email/docs.

---

## Service Wiring Diagram

```
                       ┌──────────────────────┐
                       │  GitHub Repo (main)  │
                       └──────────┬───────────┘
                                  │ push
                                  ▼
                    ┌─────────────────────────┐
                    │  GitHub Actions         │
                    │  - CI (typecheck/test)  │
                    │  - OpenNext build       │
                    │  - Wrangler deploy      │
                    │  - Scraper Cron         │
                    └──────┬────────────┬─────┘
                           │            │ monthly
                           │ deploy     │ trigger
                           ▼            ▼
              ┌─────────────────────────┐  ┌──────────────────┐
              │ Cloudflare Workers      │  │ Python Scrapers  │
              │ (Next.js via OpenNext)  │  │ (parse NRB PDFs) │
              └──────┬──────────────────┘  └────────┬─────────┘
                     │                          │ writes
                     │ reads/writes             │
                     ▼                          ▼
              ┌──────────────────────────────────────────┐
              │            Supabase                      │
              │  Postgres (indicators, fact ledger,      │
              │   entities, etc.) + Storage (source PDFs,│
              │   archived raw data, exports)            │
              └──────────────────────────────────────────┘
              (R2 replaces Supabase Storage in Phase 2 once a payment method is on file.)
                     │
                     │ user signup, newsletter
                     ▼
              ┌────────────────────┐
              │  Resend            │
              │  (transactional +  │
              │   newsletter)      │
              └────────────────────┘

Cross-cutting:
  Sentry  (error reporting from Pages, Actions, Scrapers)
  Cloudflare Web Analytics  (page-level telemetry)
  Cloudflare Images  (Phase 2 — image CDN if Next/Image isn't enough)
```

---

## Quota Tracking

Mother checks these weekly. Auto-alerts wired via Cloudflare + Supabase email notifications.

| Service | Limit | Current alert at | Hard alert at |
|---------|-------|------------------|---------------|
| Cloudflare Workers requests | 100K/day | 70K (70%) | 90K (90%) |
| Cloudflare Workers CPU time | 10ms / req | n/a (per-req, watch P95) | P95 > 50ms warrants investigation |
| Supabase DB size | 500 MB | 350 MB | 450 MB |
| Supabase egress | 5 GB/mo | 3.5 GB | 4.5 GB |
| Supabase Storage | 1 GB | 700 MB | 900 MB |
| Resend emails | 3K/mo | 2.1K | 2.7K |
| Sentry errors | 5K/mo | 3.5K | 4.5K |
| GitHub Actions min | 2K/mo | 1.4K | 1.8K |

A hard-alert hit triggers an ADR: do we optimize, do we upgrade, or do we change strategy?

---

## Upgrade Decision Matrix

When a service approaches its limit, the order of preference:

1. **Optimize first** — investigate whether usage is necessary. (e.g., R2: do we really need to archive every revision of every PDF? Maybe just monthly snapshots.)
2. **Shift the load** — move a workload to a different free-tier service. (e.g., move image hosting from Supabase to R2.)
3. **Upgrade only when revenue or grant funding covers it** — Year 1 stays free; Phase 2 monetization funds Pro tiers.

---

## Migration Paths (Pre-Documented)

When we outgrow free tiers, here is the order of expense and how we move:

| Service | Year 1 cost | Year 2 cost (estimated) | Migration plan |
|---------|-------------|--------------------------|----------------|
| Supabase Pro | $0 | $25/mo | Free → Pro is one-click; no code change |
| R2 paid | $0 | $0.015/GB/mo | Already on R2; just over free tier |
| Cloudflare Pages (Workers) | $0 | $5/mo flat | Already on Cloudflare; add Workers paid plan |
| Resend Pro | $0 | $20/mo | One-click upgrade |
| Sentry Team | $0 | $26/mo | One-click upgrade |
| Domain renewal | $10/yr | $10/yr | Auto-renew via Cloudflare |

**Worst-case Year 2 fully paid:** ~$90/month. Coverable by ~50 paying subscribers at $5/month — within the monetization ladder.

---

## Service Selection Justifications (Brief)

If you wonder "why not X":

- **Why not AWS?** S3 egress alone would cost more than this entire stack. AWS is for scale, not prototypes.
- **Why not Vercel as primary?** Vercel free tier has bandwidth caps (100GB/mo) that Cloudflare doesn't, and we want zero-egress source-document archive on R2 anyway. Vercel kept as emergency fallback.
- **Why not Cloudflare Pages as primary?** Pages handled Next.js historically via `@cloudflare/next-on-pages`, but Cloudflare's current guidance routes full-stack Next.js apps (App Router + RSC + Server Actions + ISR) to Workers via OpenNext. Pages remains for static-only fallback only.
- **Why not Render/Railway?** Their free tiers got tighter; reliability for solo project no better than what we have.
- **Why not Fly.io?** Strong, but more ops burden than Cloudflare Pages for a Next.js site.
- **Why not Mailgun/SendGrid?** Resend has better DX and the same free tier scale.
- **Why not Algolia for search?** Pagefind handles a content site of this size for free; Algolia is overkill.
- **Why not Plausible/Umami?** Cloudflare Web Analytics is free + unlimited; Plausible's free tier is gone.
- **Why not Mixpanel?** We don't need event analytics in Year 1. Page-level is enough.

Every "why not" should be answerable. If a future contributor asks one not on this list, the answer goes here.

---

## AI-Assisted Parsing Policy (No Production API)

**The Year 1 prototype does not call Claude through an API.** No Anthropic API key is in scope.

Claude Code / Claude CLI (Sonnet 4.6 via the user's Claude.ai subscription) is used as a **local development assistant only**, not as a production runtime dependency. The senior-data-engineer-sitting-beside-you pattern.

### What Claude CLI is used for

- Designing parsers (table structure, regex patterns, edge cases)
- Inspecting parser failures (paste failing output → get diagnosis)
- Generating extraction rules from observed PDF layouts
- Reviewing parser output before promotion to approved tables
- Generating test fixtures from real source documents
- Explaining weird document layouts the parser missed
- One-off data transformations during development
- Writing the boring boilerplate (Drizzle schemas, types from Zod, repository functions)

### What Claude CLI is NOT used for (Year 1)

- Running on the production website
- Being called by Workers at request time
- Being called by GitHub Actions during scheduled scrapes
- Being the parser of record for any ingested value

### Production ingestion stays deterministic

```
Python parser (pdfplumber / pandas / regex)
        ↓
Schema validation (Zod equivalent in Python: pydantic)
        ↓
Staging table (untrusted)
        ↓
Validation job (deterministic checks — see DATA_PIPELINE.md)
        ↓
Approved table (production)
```

A human (with Claude CLI sitting beside them) reviews ambiguous parses. The human's keystroke is what promotes a row. Not an LLM's confidence score.

### If we add API-based parsing later

Requires all of:
1. Anthropic API key with documented budget cap
2. ADR (Architecture Decision Record) approving the change
3. Cost budget per ingestion run, monitored
4. Data-privacy review (NRB PDFs are public; less sensitive sources may not be)
5. Reproducible prompt + model-version logging — every Claude-parsed row stores the exact prompt + model version that produced it, in `parser_runs`

Until then: Claude CLI for development; deterministic Python for production. See [PARSING_WORKFLOW.md](PARSING_WORKFLOW.md) for the day-to-day workflow.

---

## Documented Alternative: Neon Postgres

Supabase is our default Postgres because we may eventually use its Auth + Storage + Realtime layers. But if the first 30 days reveal that Auth/RLS/Realtime aren't on the near roadmap, **Neon Postgres is a strong alternative** specifically for the agentic-development workflow:

- Native Postgres without the Supabase platform overhead
- Excellent branching/preview database workflow — every PR can spin up its own DB branch
- Scale-to-zero (no idle cost) and built-in connection pooling
- Friendly to Drizzle out of the box
- No card required for the free tier

**Decision rule** (set during the Day 1–3 bootstrap):

```
Choose Supabase if Auth, RLS, or Realtime might matter in the first 30 days.
Choose Neon if the first 30 days are mostly: public data + Drizzle + preview branches + Claude CLI iteration.
```

For Nepal Ledger as currently scoped — public data, monthly ingestion, no user accounts until Phase 2 — **Neon is at least as strong as Supabase**. We default to Supabase for now because the Phase 2 user-account path is shorter, but **the switch costs are low**: Drizzle abstracts the connection; storage moves to a different bucket; no schema changes.

This is documented as an alternative, not a decision. The decision sits in [ADR-0001](decisions/0001-tech-stack.md).

---

## Cloudflare Hyperdrive (Future DB Acceleration, Not Day 1)

When the app runs on Cloudflare Workers and the database lives on Supabase (or any Postgres), every request from a Worker to the DB pays the round-trip latency cost. Cloudflare Hyperdrive is a connection-pooling + query-caching proxy that lives at the edge and reduces this cost dramatically.

**Do not enable on Day 1.** Direct Supabase HTTP/JS client calls are fine for the prototype's request volume.

**Trigger to enable:** any of (a) P95 Worker request latency >500ms attributable to DB calls, (b) connection-pool exhaustion under burst load, (c) Supabase egress quota pressure.

Documented here so future-Mother knows the path exists.

---

## The 48-Hour OpenNext Escape Hatch

**The deployment target must not become the project.** Cloudflare Workers + OpenNext is the documented primary host (see [ADR-0002](decisions/0002-cloudflare-workers-opennext.md)) and the right long-term choice. But if it causes friction in the first 48 hours of scaffolding — scaffold failures, image-optimization breakage, Server Action incompatibilities, Node-API gaps that OpenNext doesn't bridge — **switch the prototype to Vercel immediately** and keep everything else (Supabase, Supabase Storage, Resend, Sentry, GitHub Actions scrapers).

### When to invoke the escape hatch

Within the first 48 hours of bootstrap, if any of these happen and resist a single round of debugging:

1. `pnpm exec opennextjs-cloudflare build` fails on a fresh scaffold for non-trivial reasons
2. A Server Action works in `pnpm dev` but breaks in OpenNext preview
3. Image optimization doesn't resolve in preview
4. Middleware (i18n routing) doesn't work as expected
5. A required Node API isn't bridged by OpenNext and the workaround is non-trivial

### How to invoke

1. Mother writes an ADR: `0005-escape-hatch-to-vercel.md` documenting which gate failed.
2. `vercel.json` (already committed at bootstrap) becomes the live deploy config.
3. CI workflow swap: `.github/workflows/deploy-production.yml` switches from `wrangler-action` to `vercel/action`.
4. DNS swap (when domain exists): point to Vercel.
5. Workers + OpenNext stays parked in `wrangler.toml`. Migration back is a future ADR when OpenNext resolves the blocker.

This is not failure. It's a documented contingency. The whole point of the doctrine layer is so that a deployment-target swap is a 1-hour mechanical task, not a 1-week rebuild.

---

## Cross-Reference

- [ADR-0001](decisions/0001-tech-stack.md) — tech stack overall
- [ADR-0002](decisions/0002-cloudflare-workers-opennext.md) — hosting decision
- [ADR-0003](decisions/0003-ai-assisted-parsing-policy.md) — Claude CLI not API
- [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md) — storage decision
- [PARSING_WORKFLOW.md](PARSING_WORKFLOW.md) — day-to-day parser development with Claude CLI
- [DATA_PIPELINE.md](DATA_PIPELINE.md) — staging → validation → approved
- [WINDOWS_DEV.md](WINDOWS_DEV.md) — Windows + WSL2 for OpenNext build/preview
