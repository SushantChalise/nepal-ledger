# Worker Task Brief — "Hello, Nepal Ledger" Static Landing Page

**Spawn type:** `general-purpose` Sonnet worker (or `feature-dev:code-architect` if a deeper exploration is preferred)
**Plan mode:** **REQUIRED** — this task touches more than 3 files
**Worktree:** optional; safe to run in main checkout because the scope fence is fully isolated (only `src/app/...` and `public/...`)
**Diff cap:** 300 lines (additions + deletions combined)

---

## Goal

Replace the default Next.js scaffold homepage with a production-quality static landing page that:

1. Declares the Nepal Ledger mission (one paragraph)
2. Lists the **5 Public Pillars** (Money In / Money Out / Money Captured / Money Wasted / Where Money Becomes Wealth)
3. Captures email signups via a Server Action that **stubs** persistence (writes to a typed in-memory log for now — Supabase wiring lands in the Day 11–28 milestone). The form validates with Zod and returns a typed `Result<{ id: string }>`.
4. Links to the 90-day roadmap section of `docs/BACKEND_PLAN.md` (on GitHub, since docs aren't served from the site)
5. Passes Lighthouse mobile ≥ 90 on Performance, Accessibility, Best Practices, SEO

Done = the route at `/` renders all five pillar cards, the signup form posts successfully against the stub, and the page is fully responsive on a 360×640 viewport.

---

## Why

This is the Day 7–10 momentum-win milestone from `docs/BACKEND_PLAN.md`. It establishes the first public URL **before** the data-provenance core (Day 11–28) so the project has a live artefact from week 2. Per the tightened sequence in BACKEND_PLAN, this landing page must not be data-driven — every value is hard-coded copy. Pulse + Verdict + KPIs come later.

---

## Scope Fence (files this worker MAY touch)

**Edit:**
- `src/app/page.tsx` — currently the Next.js scaffold homepage; replace contents
- `src/app/layout.tsx` — update metadata only (title, description, og:image). Do not change the body structure.
- `src/app/globals.css` — add design tokens for the Nepal Ledger palette if the inline-style approach proves limiting; keep changes minimal

**Create:**
- `src/app/_components/Hero.tsx` — server component
- `src/app/_components/PillarCard.tsx` — server component (pure props)
- `src/app/_components/PillarGrid.tsx` — server component composing 5 PillarCards
- `src/app/_components/SignupForm.tsx` — client component (one `'use client'` island)
- `src/app/_components/RoadmapLink.tsx` — server component
- `src/app/actions/subscribe.ts` — Server Action with `'use server'` + Zod input schema
- `src/app/actions/__tests__/subscribe.test.ts` — Vitest covering happy path + Zod failure path
- `public/og-default.png` — open-graph image; if not generated, leave a `public/og-default.txt` placeholder noting "to be generated"

**Do NOT touch:**
- `package.json`, `pnpm-lock.yaml`, `tsconfig.json`, `next.config.ts`, `wrangler.jsonc`, `open-next.config.ts`, `eslint.config.mjs`, `postcss.config.mjs`, `.github/`, `docs/`, `scripts/`, `CLAUDE.md`, anything outside `src/app/` or `public/`
- Any `src/lib/`, `src/features/`, or `src/components/` paths (those land in later milestones)
- Server Action persistence: the stub is the contract for this task

If you need a dependency, **stop and report** — Mother adds it in a separate step.

---

## Context to Read First (in order)

1. `docs/STRATEGY.md` §"The Master Thesis" + §"5 Public Pillars" — to copy mission language faithfully (do not invent)
2. `docs/CONVENTIONS.md` — TypeScript strict, component shape, Server Action shape, named exports, error handling, comments policy
3. `docs/CONTEXT_RULES.md` — the Six Rules; specifically pattern-match-first and no silent failure
4. `docs/UI_ACCEPTANCE.md` — viewport, state, accessibility, performance gates this page must clear
5. `docs/BACKEND_PLAN.md` §"90-Day Sequence" rows for Days 7–10 and Days 11–28 — confirm what is in scope here vs. later
6. `src/app/page.tsx` and `src/app/layout.tsx` — the scaffold defaults; understand them before replacing
7. `src/app/globals.css` — Tailwind v4 + CSS custom properties pattern

---

## Acceptance Criteria

- [ ] Scope fence respected — only files listed above touched (`git diff --name-only main` matches)
- [ ] `pnpm typecheck` clean (no `any`, no `as` casts outside sanctioned locations, no `@ts-ignore`)
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` includes the new `subscribe.test.ts` and passes
- [ ] `pnpm build` succeeds and the `/` route is statically prerendered
- [ ] Zod schema in `subscribe.ts` validates: `email` (RFC-compliant), optional `source` (URL), implicit timestamp
- [ ] Server Action returns `Result<{ id: string }>` (use the local pattern from `docs/CONVENTIONS.md` §"Error Handling" — define `Result<T>` inline in `src/app/actions/subscribe.ts` for now; the shared `src/lib/errors.ts` lands in Day 4–6)
- [ ] Signup form: HTML5 validation + JS-driven Zod validation on submit; success state shows a confirmation; error state shows the Zod message inline (accessible — `aria-invalid` + `aria-describedby`)
- [ ] All five pillar cards render on viewport 360×640 without horizontal scroll
- [ ] All focusable elements have visible focus indicators (Tailwind `focus-visible:ring-*`)
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 for body text, 3:1 for large)
- [ ] `layout.tsx` metadata sets `title`, `description`, `openGraph`, `twitter`
- [ ] No client component beyond `SignupForm.tsx` — everything else is RSC
- [ ] Diff under 300 lines combined
- [ ] No comments restating code; only non-obvious WHY comments
- [ ] No console errors in `pnpm dev` browser load
- [ ] No new dependencies added

---

## What to Return

1. Summary of changes (≤10 bullets)
2. Acceptance-criteria checklist with checkmarks
3. Output of `git diff --stat main` proving scope-fence respected
4. Any deviations from this brief and why
5. Open questions for Mother
6. Suggested conventional-commits commit message (e.g. `feat(landing): "Hello, Nepal Ledger" static landing page with 5 pillars and signup stub`)

---

## Pattern Notes

- **Pillars data:** define a local `const PILLARS: readonly { slug: string; titleEn: string; titleNe: string; oneliner: string }[]` inline at the top of `page.tsx`. Five entries. Mark `as const`.
- **Server Action stub:** persistence is `console.info({ email, source, ts })` for now. Return a stub id with `crypto.randomUUID()`. Add a `// TODO: replace with Supabase insert when Day 11–28 lands the lead schema` comment — this is one of the sanctioned WHY comments.
- **Form library:** use the platform form + Server Action — no React Hook Form yet (RHF lands when the Calculator does, Day 76–90).
- **Styling:** Tailwind v4 utility classes only. Do not introduce shadcn primitives — they land with the Knowledge Base UI (Day 11–28+).
- **Bilingual:** include each pillar's Nepali title in the data, but do not implement locale routing — that lands Day 29–45 with next-intl.

---

## Pre-merge checks Mother will run

Beyond the worker's own checks, Mother will:

- Read the diff line-by-line
- Run `pnpm dev` and load `/` in a real browser (Chrome) on a 360×640 viewport
- Submit the form once with a valid email; verify the `console.info` payload shape
- Submit once with an invalid email; verify the inline error
- Verify `pnpm build` + `pnpm exec opennextjs-cloudflare build` both succeed
- Confirm no Sentry-related code lands here (Sentry instrumentation is wizard-driven; that's a separate commit on `chore/sentry-config`)
- Confirm no `src/lib/` paths created (they're reserved for Day 4–6+)
