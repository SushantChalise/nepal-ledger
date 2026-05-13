# Bootstrap — Remaining User Actions

The Day 1–3 bootstrap landed via Mother Opus. A few remaining steps require **your terminal** because they involve secrets (which must never pass through chat) or interactive flows Mother cannot drive.

Status as of bootstrap commit `1084384`:

- [x] Doctrine in repo
- [x] Next.js 16 + Tailwind v4 + OpenNext + Workers scaffold
- [x] `pnpm typecheck` / `lint` / `test` / `build` / OpenNext build all clean
- [x] GitHub repo created: <https://github.com/SushantChalise/nepal-ledger>
- [x] CI green on first run
- [x] Branch protection enabled on `main` (CI required, linear history, no force pushes, no deletions, admins enforced)
- [x] Repo topics + auto-delete-on-merge + auto-merge enabled
- [x] GitHub `production` environment created (empty — needs secrets)
- [ ] **Sentry wizard run** ← you
- [ ] **GitHub Actions secrets set for deploy** ← you
- [ ] First production deploy verified

---

## 1. Run the Sentry wizard (per [ADR-0005](decisions/0005-sentry-setup.md))

From the project root in PowerShell:

```powershell
npx @sentry/wizard@latest -i nextjs --saas --org nepal-ledger --project javascript-nextjs
```

When prompted, select:

- **Login:** browser (same Sentry account from Day 0)
- **Org:** `nepal-ledger` (preselected)
- **Project:** `javascript-nextjs` (preselected — the Sentry default name; **do not rename**)
- **Features:** Error Monitoring + Tracing + Session Replay
- **Runtimes:** all three (browser + Node.js + Edge)
- **Source maps:** Yes (creates `SENTRY_AUTH_TOKEN`, written to `.env.sentry-build-plugin` which is gitignored)

After the wizard completes, tell me. I'll land a follow-up commit on a `chore/sentry-config` branch that:

- Verifies the generated `instrumentation-client.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`, `instrumentation.ts` match the skill's recommended init options
- Strips any webpack-only tree-shake options from `next.config.ts` (OpenNext uses esbuild — see ADR-0005 §"`next.config.ts` Wrapping")
- Updates `.env.example` with `NEXT_PUBLIC_SENTRY_DSN` if missing
- Confirms `.env.sentry-build-plugin` is in `.gitignore` (already covered by `.env*`)
- Promotes ADR-0005 status from Proposed → Accepted

---

## 2. Set GitHub Actions deploy secrets

The `Deploy to Cloudflare Workers` workflow runs on every push to `main` but fails right now because secrets are missing. Set them yourself from a terminal — never paste a real secret into chat:

```powershell
# Repository-level secrets (visible to all workflows)
gh secret set CLOUDFLARE_API_TOKEN --body $env:CLOUDFLARE_API_TOKEN
gh secret set CLOUDFLARE_ACCOUNT_ID --body "dd4ba6fa3338515d59fd40112d0f409c"

# Production-environment secrets (only the deploy workflow sees these)
gh secret set SUPABASE_URL --env production
gh secret set SUPABASE_ANON_KEY --env production
gh secret set SENTRY_AUTH_TOKEN --env production         # after Sentry wizard
```

`gh secret set --env production` prompts for the value interactively if `--body` is not passed — paste at the prompt, the value never appears in your shell history or here.

After Sentry wizard, also set the build-time vars the deploy workflow's `Build` step references:

```powershell
gh variable set NEXT_PUBLIC_SITE_URL --body "https://nepal-ledger.<your-worker-subdomain>.workers.dev" --env production
```

Once secrets are set, re-trigger the deploy:

```powershell
gh workflow run deploy-production.yml --ref main
gh run watch
```

---

## 3. (Optional, near-term) GitHub secret-scanning push protection

GitHub turned this on for the repo automatically (visible at <https://github.com/SushantChalise/nepal-ledger/settings/security_analysis>). Leave it on — it's belt-and-suspenders with our local gitleaks pre-commit hook and the CI gitleaks step.

---

## 4. Install gitleaks locally (recommended)

The pre-commit hook is tolerant of missing gitleaks (prints a notice and continues), but local detection saves a CI round-trip. On Windows:

```powershell
scoop install gitleaks
# OR
go install github.com/zricethezav/gitleaks/v8@latest
```

---

## 5. (Optional) Configure the worker preview URL

Once the production deploy is green, the URL appears in the `Deploy to Cloudflare Workers` workflow log. Visit it. If `Hello, Nepal Ledger` (the landing page we ship in Phase J) is live, the bootstrap is fully verified.

---

## Open follow-ups Mother will pick up in the next session

1. **ADR-0006: Next.js version bump (15 → 16).** Scaffold delivered Next 16.2.6 — doctrine still cites Next 15 in places. Single follow-up ADR + reference updates in BACKEND_PLAN.md.
2. **Sentry post-wizard reconciliation** (after step 1 above).
3. **Day 7–10 landing page worker** — task brief drafted at `docs/tasks/landing-page-worker-brief.md`.
4. **Day 4–6 schema foundation** — Drizzle config, `safeQuery`, calendar/period utilities, first migration. Multiple workers possible (independent schema files).
5. **Local gitleaks install verification** (Mother runs `gitleaks version` next session to confirm).
