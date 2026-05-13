# ADR-0005: Sentry Setup Plan (Deferred to Post-Scaffold)

- **Status:** Proposed (executes during Day 1–3 bootstrap, immediately after Next.js scaffold lands)
- **Date:** 2026-05-13
- **Deciders:** Mother Opus, user
- **Tags:** observability, errors, tracing, replay

## Context

The [Sentry Next.js skill](https://github.com/getsentry/sentry-for-ai/blob/main/skills/sentry-nextjs-sdk/SKILL.md) recommends running `npx @sentry/wizard@latest -i nextjs` against an existing Next.js project to install and configure the SDK. That wizard:
- Logs the user into Sentry via browser
- Selects org + project
- Installs `@sentry/nextjs`
- Generates `instrumentation-client.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`, `instrumentation.ts`
- Wraps `next.config.ts` with `withSentryConfig()`
- Sets up source-map upload
- Adds an `/sentry-example-page` for verification

It requires a real Next.js project to exist (cannot run pre-scaffold) and interactive terminal input (cannot be driven by Mother / an agent).

## Decision

**Two-step Sentry rollout:**

### Step A (now — pre-bootstrap, browser, ~60s)
- Sign up at https://sentry.io/signup/ (GitHub OAuth)
- Create a Next.js project — Sentry's project-creation flow auto-names it `javascript-nextjs` (the platform default). Keep that name; do not rename. The org is `nepal-ledger`; the project is `javascript-nextjs`. The two identifiers together are the addressable handle.
- Save the DSN to `.env.local` locally (NEVER paste DSN into chat — DSN includes the org+project identifiers)

### Step B (Day 1–3 — after `pnpm create` scaffolds Next.js, user runs)
```powershell
npx @sentry/wizard@latest -i nextjs --saas --org nepal-ledger --project javascript-nextjs
```
Wizard prompts:
- Login: browser (same Sentry account)
- Org/project: pre-selected by the flags above (`nepal-ledger` / `javascript-nextjs`)
- Features: select **Error Monitoring + Tracing + Session Replay**
- Runtimes: select **All three** (browser + Node.js server + Edge)
- Source maps: Yes (creates a `SENTRY_AUTH_TOKEN` for builds; lands in `.env.sentry-build-plugin` which gets gitignored)

After the wizard, Mother (this session) writes a follow-up commit:
- Verifies the generated config files match the skill's recommended init options
- Adds `SENTRY_AUTH_TOKEN`, `SENTRY_ORG=nepal-ledger`, `SENTRY_PROJECT=javascript-nextjs` to GitHub Actions secrets
- Updates `.env.example` with the new vars
- Adds `.env.sentry-build-plugin` to `.gitignore`
- Promotes this ADR's status from Proposed → Accepted

## Feature Selection (Per the Skill's Recommendation Logic)

### Enabled at launch
| Feature | Why |
|---------|-----|
| **Error Monitoring** | Skill says "always — non-negotiable baseline." Captures server, client, server-action, edge-runtime errors. |
| **Tracing** | Skill says "always for Next.js" — server route tracing + client navigation are high value, especially given ISR + Server Actions in our stack. Sample rate: 1.0 in dev, 0.1 in production. |
| **Session Replay** | Recommended for user-facing apps. Records sessions around errors. Sample rates: 0.1 of all sessions, 1.0 of error sessions. Privacy: default Sentry masking on. |

### Enabled later (when triggered)
| Feature | Trigger to enable |
|---------|-------------------|
| **Logging** | When we adopt a structured logging library (`pino` or `winston`) for the data pipeline |
| **AI Monitoring** | When/if we add API-based parsing (currently NO per [ADR-0003](0003-ai-assisted-parsing-policy.md)); also relevant for the Digital Export Boom vertical's Phase 2 AI-tools coverage |
| **Crons** | When monthly NRB scrapers move from GitHub Actions cron to Cloudflare Workers Cron Triggers — Sentry Crons can monitor either |
| **Metrics** | When we have business metrics worth tracking (e.g., newsletter signup rate, calculator usage) — likely Phase 2 |

### Skipped (decided not to enable)
- **Profiling** — requires `Document-Policy: js-profiling` HTTP header which adds Worker-routing complexity. Marginal value at our scale. Re-evaluate at 10K+ MAU.

## `next.config.ts` Wrapping — Cloudflare Workers Compatibility Note

Per [ADR-0002](0002-cloudflare-workers-opennext.md), we deploy via `@opennextjs/cloudflare`. The skill notes one Turbopack/Webpack consideration: `withSentryConfig`'s tree-shaking options are webpack-only. OpenNext for Cloudflare uses esbuild internally, not webpack — verify with the wizard's output whether the tree-shake config it emits is compatible. If it isn't, strip the `webpack.treeshake.*` options from `next.config.ts` and document the change here.

## Tunnel Route (Ad-Blocker Bypass)

The skill recommends `tunnelRoute: "/monitoring"` in `withSentryConfig()` so Sentry events can bypass ad-blockers via a same-origin Next.js route. We adopt this. If we add middleware later, exclude `/monitoring` from auth/redirect logic (the skill provides the matcher pattern).

## Verification (Day 1–3 Acceptance)

After wizard runs and Mother's follow-up commit lands:
- [ ] `@sentry/nextjs` in `package.json` dependencies
- [ ] `instrumentation-client.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`, `instrumentation.ts` exist with skill-recommended init options
- [ ] `app/global-error.tsx` created (App Router error boundary)
- [ ] `next.config.ts` wrapped with `withSentryConfig()`
- [ ] `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` documented in `.env.example`
- [ ] `.env.sentry-build-plugin` in `.gitignore`
- [ ] GitHub Actions secrets set (`SENTRY_AUTH_TOKEN`)
- [ ] Test error thrown in `/sentry-example-page` appears in Sentry dashboard within 30s
- [ ] Source maps resolve readable filenames in the test error's stack trace
- [ ] Session Replay tab shows the test session

## Alternatives Considered

### A. Skip Sentry, use Cloudflare-only error logging
- **Pro:** zero additional account
- **Con:** Cloudflare Workers logs are line-based, no replay, no source maps, no aggregation across error frequencies. Inadequate for a publication where editorial credibility depends on debugging quickly.
- Rejected.

### B. Self-hosted error tracking (GlitchTip, etc.)
- **Pro:** open source, no SaaS dependency
- **Con:** ops burden we don't have time for; replay support is weaker
- Rejected.

### C. Sentry via wizard (chosen)
- **Pro:** skill-recommended; handles all three runtimes; replay + source maps + tracing included; free tier 5K events/mo
- **Con:** another vendor in the stack
- Accepted.

## Consequences

### Positive
- Errors across browser, Node server, Edge runtime captured in one dashboard
- Source-map-resolved stack traces for production debugging
- Session replays around errors — game-changer for client-side bug repro
- Tracing spans across the full request path (browser → Worker → Supabase)
- Free tier (5K events/mo) sufficient for a niche publication's Year 1

### Negative
- Extra ~50KB shipped to client (Session Replay is the biggest piece)
- Source-map upload on every build adds ~10s to build time
- One more secret to manage (`SENTRY_AUTH_TOKEN`)

### Neutral / unknown
- Whether OpenNext for Cloudflare bundles `@sentry/nextjs` cleanly — verified post-wizard

## References

- [Sentry Next.js skill (canonical)](https://github.com/getsentry/sentry-for-ai/blob/main/skills/sentry-nextjs-sdk/SKILL.md)
- [docs.sentry.io/platforms/javascript/guides/nextjs/](https://docs.sentry.io/platforms/javascript/guides/nextjs/)
- [ADR-0001](0001-tech-stack.md) — Sentry chosen as error layer
- [ADR-0002](0002-cloudflare-workers-opennext.md) — hosting target (informs `instrumentation.ts` runtime dispatch)
- [CLOUD_STACK.md §"Sentry (errors)"](../CLOUD_STACK.md) — free-tier capacity
