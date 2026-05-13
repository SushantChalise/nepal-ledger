# Nepal Ledger

> Nepal's first money-and-land intelligence platform. Tracks whether Nepal's money becomes wealth.

This repository contains:
- The Next.js web app (`src/`)
- Python data scrapers (`scrapers/`)
- Engineering doctrine and decision records (`docs/`)
- Bootstrap and operational scripts (`scripts/`)

---

## Mission

Every month, money enters Nepal — from migrants, tourists, loans, grants, taxes, and trade. Some leaks out. Some is captured. Some is wasted or destroyed. Some becomes wealth. Nepal Ledger tracks all five and asks one question:

> Did Nepal grow this month, or did it survive another month?

Full strategy: [`/.claude/plans/ok-i-want-to-mossy-dragonfly.md`](../.claude/plans/ok-i-want-to-mossy-dragonfly.md) (location outside the repo for now; will move to `docs/STRATEGY.md` at first commit).

---

## Engineering Doctrine

Read these in order before contributing or running an agent:

1. [`CLAUDE.md`](CLAUDE.md) — agent doctrine entry point
2. [`docs/BACKEND_PLAN.md`](docs/BACKEND_PLAN.md) — umbrella engineering plan
3. [`docs/AGENT_OPS.md`](docs/AGENT_OPS.md) — Mother Opus + Sonnet workers loop
4. [`docs/CONTEXT_RULES.md`](docs/CONTEXT_RULES.md) — anti-hallucination + anti-scope-drift
5. [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — code conventions
6. [`docs/CHANGE_CONTROL.md`](docs/CHANGE_CONTROL.md) — ADR + change log protocol
7. [`docs/CLOUD_STACK.md`](docs/CLOUD_STACK.md) — free-tier services
8. [`docs/GITHUB_PRACTICES.md`](docs/GITHUB_PRACTICES.md) — branching, PRs, CI

Architectural decisions: [`docs/decisions/`](docs/decisions/).

---

## Quick Start

```powershell
# Run bootstrap (idempotent — safe to re-run)
.\scripts\bootstrap.ps1

# After completing the user-action checklist printed by bootstrap:
pnpm dev      # local dev
pnpm test     # run tests
pnpm build    # production build
```

---

## Repository Status

**Day 0 — Doctrine phase.** Engineering operating model is written and committed. Next.js app not yet scaffolded. Cloud services not yet wired. See [`docs/BACKEND_PLAN.md` §First Actions](docs/BACKEND_PLAN.md).

---

## License

All rights reserved until public beta launch. License to be decided before going public.
