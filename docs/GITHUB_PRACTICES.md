# GitHub Practices

How we use GitHub. This is the practical procedure manual, not opinion. Follow it.

---

## Repository Setup

**Name:** `nepal-ledger` (lowercase, hyphenated)
**Visibility:** **Public from Day 1.** Builds in the open from the first commit; aligns with the open-source-from-Day-1 license intent in `CLAUDE.md` and unlocks unlimited free GitHub Actions minutes.
**Default branch:** `main`
**License:** TBD before any external contributor lands a PR. Recommended: MIT (code) + CC BY-NC-SA (content); add `LICENSE` and `LICENSE-content.md` in a follow-up. Until added, repo is "All Rights Reserved" by default — fine for a solo-bootstrap window.
**Description:** *"Nepal Ledger — tracking whether Nepal's money becomes wealth."*
**Topics:** `nepal`, `economic-data`, `data-journalism`, `nextjs`, `typescript`, `supabase`

---

## Branching Model

**Trunk-based development.** Short-lived feature branches → squash merge to `main`.

| Branch type | Naming | Lifetime | Merged via |
|-------------|--------|----------|-----------|
| `main` | — | Forever | — |
| Feature | `feat/<feature>-<short-desc>` | <3 days | Squash merge PR |
| Fix | `fix/<short-desc>` | <1 day | Squash merge PR |
| Chore | `chore/<short-desc>` | <1 day | Squash merge PR |
| Docs | `docs/<short-desc>` | <1 day | Squash merge PR |
| ADR | `adr/<NNNN>-<title>` | <1 day | Merge with merge commit (preserves the ADR commit) |

**Rules:**
- Never commit directly to `main` (enforced after CI is live)
- Never push force to `main` (always blocked)
- Always delete the branch after merge
- One PR per branch
- One logical change per PR (split if mixed)

---

## Conventional Commits

Every commit message:
```
<type>(<scope>): <imperative summary>

<optional body explaining why>

<optional footer: BREAKING CHANGE, Refs #issue>
```

**Types:**
- `feat` — new user-facing feature
- `fix` — bug fix
- `refactor` — code change without behavior change
- `chore` — infra/config/deps
- `docs` — documentation only
- `test` — adding/changing tests
- `style` — formatting only (no code change)
- `perf` — performance improvement
- `ci` — CI/CD config change
- `revert` — reverting a previous commit

**Scope:** the feature folder or area (e.g., `verdict`, `pulse`, `db`, `ci`).

**Examples:**
```
feat(pulse): add 5-KPI homepage card group
fix(db): correct YoY calculation in indicators repository
chore(deps): bump Drizzle ORM to 0.40.0
docs(adr): add ADR-0007 for Cloudflare R2 archival policy
test(verdict): add Vitest cases for 5-pillar prose validator
```

This format is read by the auto-changelog tool and by future humans grepping git log.

---

## Pull Requests

Every change goes through a PR. Even solo work. Reasons:
- Forces a moment of review (Mother always reviews her own diff one more time)
- CI runs against the PR
- Creates a permanent record with title + body
- Auto-changelog ingests PR titles

### PR Template

`.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## What
<one paragraph: what changed, user-visible>

## Why
<one paragraph: which plan section this implements; which ADR it follows>

## How
<bullets: the approach; any non-obvious decisions>

## Testing
<what was tested, what new tests were added>

## Screenshots / Demo
<for UI changes; before/after if reasonable>

## Checklist
- [ ] Scope fence respected (files changed are in the planned scope)
- [ ] `pnpm typecheck` clean
- [ ] `pnpm test` passing
- [ ] `pnpm lint` clean
- [ ] `pnpm build` succeeds
- [ ] Tests added for new behavior
- [ ] ADR added if architectural decision was made
- [ ] Change log entry added if scope shifted
- [ ] CLAUDE.md updated if a new pattern was established
- [ ] No new dependencies added (or explicitly approved)
- [ ] No secrets committed
- [ ] Screenshots attached for UI changes
```

A PR missing checklist items is not merged.

### PR Size

- Target: <300 lines of diff (additions + deletions, ignoring lockfile)
- Soft cap: 500 lines
- Hard cap: 800 lines (any larger triggers a "split this PR" comment from Mother)

Large PRs are split because review quality collapses past ~500 lines.

---

## CI/CD (GitHub Actions)

### Workflow files

```
.github/workflows/
├── ci.yml                # On PR and push to main: typecheck, lint, test, build
├── deploy-preview.yml    # On PR: build + deploy to Cloudflare Pages preview URL
├── deploy-production.yml # On push to main: deploy to production
├── scraper-monthly.yml   # Cron: monthly NRB CMEFs ingestion
├── scraper-customs.yml   # Cron: monthly customs data
└── doc-audit.yml         # Weekly: check for broken links, stale docs, missing ADR references
```

### CI Job: `ci.yml`

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm typecheck
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build
```

Required to pass before merge. (Branch protection enforces this once enabled.)

### Branch Protection on `main`

**Enabled from Day 1 — not Day 90.** The most fragile phase of the project is the first 90 days, not after. Without protection, Mother (and any agent) will "temporarily" commit to `main` and the doctrine becomes ceremonial. Protection is enabled as soon as the first CI workflow lives.

- Require PR before merging
- Require CI to pass (typecheck + lint + test + build + gitleaks + drizzle check)
- Require linear history (squash merge)
- No direct pushes (even by repo owner — yes, even solo)
- No force pushes
- Delete head branch on merge
- Allow auto-merge after checks pass (optional but recommended for solo work — Mother queues, CI gates)

Activation command (after first CI workflow is committed and at least one PR has run green):

```powershell
gh api repos/:owner/:repo/branches/main/protection -X PUT --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["check"] },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
```

For solo work, leave `required_pull_request_reviews` as `null` (no human-approver required), but keep all the other gates. Mother's review is procedural; CI is the enforcement.

If a hotfix genuinely must skip the gate (production-down emergency), the procedure is: disable protection → push → re-enable protection → write an incident note in `docs/changes/incidents.md`. Never silent.

---

## Issue Templates

`.github/ISSUE_TEMPLATE/`:

| Template | Purpose |
|----------|---------|
| `bug.md` | Bug report — repro steps, expected, actual, env |
| `feature.md` | Feature request — user need, proposed solution, alternatives |
| `decision.md` | Architectural decision request — escalates to ADR |
| `data-quality.md` | Source data issue — flagged for Fact Ledger correction |

---

## GitHub Projects

One project: **"Nepal Ledger — Phase 1 (Year 1)"**.

Columns:
- **Backlog** (everything from the 90-day roadmap + later)
- **Planned (this week)** (Mother's current task queue)
- **In Progress** (max 3 — one per parallel worker)
- **In Review** (PR open)
- **Done** (merged this week — auto-archived after 7 days)
- **Blocked** (waiting on user / external service / decision)

TodoWrite in-session maps to "In Progress." Project board reflects the longer view.

---

## Releases

**Tagging:** SemVer with phase prefix.

| Version | Meaning |
|---------|---------|
| `v0.x.y` | Pre-launch (Day 1–90) |
| `v0.1.0` | First milestone (Bootstrap complete) |
| `v0.5.0` | First Pulse + Money Map live |
| `v0.9.0` | All 4 signature features live |
| `v1.0.0` | Public beta launch (Day 90) |
| `v1.x.y` | Post-launch iterations |

Releases auto-generated from conventional commits.

---

## Code Review (Even Solo)

Mother reviews every Sonnet-worker diff before integrating. The review checklist:

1. **Did it stay in scope?** `git diff --stat` against the scope fence
2. **Does it match patterns?** Compare to the cited reference feature
3. **Are types tight?** No `any`, no `as unknown as`, no `@ts-ignore`
4. **Are tests real?** Read the assertions; do they catch the behavior?
5. **Are errors typed?** No swallowed try/catch; no silent fallback
6. **Did it introduce a new pattern?** If so, demand an ADR or reject
7. **Diff size sane?** <300 lines or it's split
8. **CI passes?** All gates green

Anything failing → diff rejected, new task brief written, new worker spawned. **Never** "Mother fixes it inline" — that breaks the orchestration model.

---

## Secrets

Storage hierarchy:

| Where | What goes here | Who reads |
|-------|----------------|-----------|
| `.env.local` (gitignored) | Local dev secrets | Developer only |
| `.env.example` (committed) | Template only, no actual values | Reference |
| GitHub Actions Secrets | CI/CD secrets (Supabase service role, Cloudflare API, Resend API) | CI workflows |
| Cloudflare Pages env vars | Runtime secrets at edge (Supabase anon key, Sentry DSN) | Pages deployment |
| Supabase env vars | DB-side secrets (rare) | Supabase functions |

**Hard rules:**
- Never commit a secret. Period.
- Use `git-secret-scan` or `gitleaks` as a pre-commit hook (set up in bootstrap)
- If a secret leaks → rotate it within 60 minutes; document in `docs/changes/incidents.md`
- `.env.example` is the source of truth for required environment variables

---

## GitHub CLI Cheatsheet (for Mother)

Mother uses `gh` for repo operations:

```powershell
# Create the repo (one-time, Day 1)
gh repo create nepal-ledger --private --description "Nepal's first money-and-land intelligence platform" --source=. --remote=origin

# Create a PR after pushing a branch
gh pr create --title "feat(pulse): add 5-KPI homepage cards" --body "$(cat .pr-body.tmp)"

# View PR status
gh pr status

# Merge a PR (squash)
gh pr merge <num> --squash --delete-branch

# Create an issue
gh issue create --title "Feature: ..." --body "..." --label feature

# View Actions runs
gh run list --limit 10
gh run view <id> --log-failed

# Set a secret
gh secret set SUPABASE_SERVICE_ROLE_KEY --body "$env:SUPABASE_SERVICE_ROLE_KEY"
```

---

## Quarterly Audit

Once per quarter Mother runs a doc audit:

- All ADRs still valid? Mark superseded if not.
- All CLAUDE.md files reflect current patterns?
- Any stale TODOs in code? `grep -rn TODO src/` — convert to issues or remove.
- Any flaky tests? Mark + decide: fix or delete.
- Any abandoned branches? Delete after 30 days inactivity.
- Any open PRs >7 days? Re-decide: merge, close, or escalate.
- Free-tier quotas — any approaching 70%?

Audit output → a single PR titled `chore(audit): Q<n> 2026 doc + repo hygiene`.
