# ADR-0010: Shared-Infrastructure Mutations — Ask Then Execute

- **Status:** Accepted (effective 2026-05-14)
- **Deciders:** User (explicit instruction), Mother Opus
- **Supersedes:** Earlier autonomy framing that said "modifying shared infrastructure is user-only" (in HANDOFF docs, BOOTSTRAP_USER_ACTIONS.md, ADR-0008)
- **Tags:** autonomy, permissions, agent-ops, supabase, deploy

## Context

The original autonomy framing (Day 0 session brief) said Mother does NOT autonomously perform actions that modify shared infrastructure: migration application, deploys, Cloudflare API changes, Sentry wizard. These had to be run from the user's terminal.

Through three overnight sessions this rule caused two pain points:

1. **Workflow friction.** The user wakes up, finds 105K rows of banking data staged in JSON, then has to run two commands themselves. The Mother→User→Mother handoff costs hours when the user is asleep and the Mother is otherwise idle.
2. **Wasted Mother session time.** Mother session was effectively "done" when it reached the migration step; the autonomous backend pipeline stalled at a gate that's now-clearly intended to be small (one command).

The user's explicit instruction on 2026-05-14:

> "remove the user-gate with ask user for permission and if they say yes execute and execute"

## Decision

**New policy for shared-infrastructure mutations:**

1. **Mother asks in chat** before initiating any shared-infrastructure mutation (live DB schema change, deploy, Cloudflare API write, Sentry config write). The ask includes:
   - The exact command
   - The blast radius (which tables / which environment / what's reversible)
   - The rollback steps
2. **On explicit user "yes" / "go" / "execute" / equivalent** in chat → Mother runs the command immediately.
3. **On absence of response or ambiguity** → Mother waits or stages and reports.

Shared-infrastructure mutations covered:
- Drizzle migrations against the live Supabase
- Live data ingestions into Supabase (`apply-all.ts`, `ingest-nrb-bfi.ts`, etc.)
- `gh secret set` for any Production environment secret
- `vercel deploy --prod` (when Vercel ever enters the stack)
- `wrangler deploy --env production`
- Anything that writes to a `:owner/:repo/...` resource on shared GitHub branches

NOT covered (Mother executes freely — already in scope):
- Local file edits, code commits to feature branches
- Local Python venv setup
- PR creation (visible but reversible)
- Reading `.env.local` for runtime config

## Sandbox-enforcement gap

Claude Code's permission classifier currently treats live-Supabase mutation as a sandbox-enforced rule that chat-turn authorization does not override. **This is the floor below the doctrine.** Even with this ADR in place, the classifier may block Mother's attempts at migration application.

**The user-facing mitigation:** add Bash permission rules in `/permissions` (Claude Code settings.json) for the specific commands Mother needs to run:

```
Bash(pnpm exec tsx scripts/apply-migrations.ts:*)
Bash(pnpm exec tsx scripts/apply-all.ts:*)
Bash(pnpm exec tsx scripts/ingest-nrb-bfi.ts:*)
Bash(pnpm exec tsx scripts/ingest-fiscal-transfer-canonical.ts:*)
Bash(pnpm exec drizzle-kit migrate:*)
Bash(gh secret set:*)
```

Once these rules are in place, Mother's "ask then execute" pattern works end-to-end without the classifier intervening.

## Alternatives Considered

### A. Keep the strict user-gate
- **Pro:** Maximum safety; user runs every shared-infra mutation manually.
- **Con:** Hours of Mother→User→Mother handoff for trivial one-command steps.
- Rejected per the user's explicit instruction.

### B. Mother runs all shared-infra mutations autonomously, no ask
- **Pro:** Zero friction.
- **Con:** No user awareness of when production state changed; harder to audit.
- Rejected — the user explicitly wants the "ask" step preserved.

### C (chosen). Ask in chat, execute on yes
- **Pro:** Preserves user awareness; eliminates the terminal-round-trip; matches user's stated workflow.
- **Con:** Requires sandbox permission rules to be configured once.

## Consequences

### Positive
- Mother's autonomy extends to live data application after a single in-chat "yes"
- Cleaner audit trail: each shared-infra mutation has a chat-message authorization right before it
- Doctrine matches user's actual operational preference

### Negative
- Requires one-time Claude Code permissions setup (the `/permissions` allow-list rules above)
- Until the rules are set, the classifier blocks Mother's attempts even after explicit chat yes — confusing for the user the first time

### Neutral / unknown
- Whether future Claude Code releases tighten the classifier further; the doctrine survives either way (worst case Mother just asks the user to run the command themselves)

## Implementation handles

- **HANDOFF docs**: stop saying "Mother could not apply because she shouldn't" — say "Mother asks, then runs". Update on next Mother session.
- **BOOTSTRAP_USER_ACTIONS.md**: similar — reframe migration-apply / deploy-secret-set as "Mother asks, you say yes, Mother runs" instead of "you do it".
- **`docs/HANDOFF_2026-05-14-morning.md`** (this overnight session's handoff) — needs the policy change reflected.
- **AGENT_OPS.md §"Escalate to User When"** — keeps "deploy fails on production" + "secret leak detected" as user-confirmation triggers, but adds the "ask then execute" pattern for routine shared-infra mutations.

## References

- [`docs/AGENT_OPS.md`](../AGENT_OPS.md) — escalation triggers (will be amended)
- [`docs/BOOTSTRAP_USER_ACTIONS.md`](../BOOTSTRAP_USER_ACTIONS.md) — user-action checklist (will be amended)
- ADR-0008 — Surya routing (older language about "user-side step" will be cross-referenced to this ADR)
- Claude Code permissions docs (external): the `/permissions` allow-list mechanism
