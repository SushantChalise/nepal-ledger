# UI Acceptance Standard

Every UI change passes this checklist before merging. "Manual eyeball" was the placeholder; this is the actual gate.

The checklist is part of the [PR template](../.github/PULL_REQUEST_TEMPLATE.md). Reviewers (Mother) verify each item.

---

## Required Viewports

A screenshot of the change is attached for each of these viewports:

| Name | Dimensions | Used by |
|------|-----------|---------|
| **Mobile** | 390 × 844 (iPhone 12-class) | Primary audience — Nepal mobile-heavy |
| **Tablet** (optional unless layout differs) | 768 × 1024 | iPad / Nepali mid-range Android tablet |
| **Desktop** | 1440 × 900 | Diaspora professionals + researchers |

Use Playwright's `page.screenshot()` in scripts under `scripts/screenshots/`, or DevTools device mode for one-offs.

---

## Required States

Every component that fetches data or accepts input has screenshots for all four states:

1. **Loading** — skeleton or spinner; never blank screen
2. **Empty** — no data; helpful copy explains why (not "Error" — "Awaiting Chait 2082 release")
3. **Error** — typed error message; not a generic "Something went wrong"; tells the user what to do (retry, refresh, report)
4. **Populated (default)** — the happy path with real data

Components with input (calculators, forms) additionally need:

5. **Invalid input** — field-level error; submit disabled or surfaces the issue
6. **Submitted / pending** — feedback that something is happening
7. **Success** — confirmation state

---

## Required Content Elements

Every data-display surface (chart, KPI card, table, Money Map node, etc.) MUST include:

- **Source citation** visible without click (e.g., "Source: NRB CMEFs Chait 2082")
- **Confidence badge** visible (A / B / C)
- **Last updated timestamp** visible (e.g., "Updated 2026-05-08")
- **Data status label** if applicable (`Fresh`, `Lagged`, `Preliminary`, `Estimated`, `Partial`, `Disputed`, `Archived` — see [STRATEGY.md](STRATEGY.md) §"Data Governance")
- **Plain-language interpretation** for every chart (the sentence that the chart argues — never a chart without prose context)

A chart without source/confidence is rejected on sight. Always.

---

## Accessibility

- **Color contrast ≥ 4.5:1** for body text, ≥ 3:1 for large text (WCAG AA)
- **Alt text** on every chart image and infographic — describes the data shape AND the argument
- **Keyboard navigable** — every interactive element reachable by Tab; visible focus ring
- **No information conveyed by color alone** — direction indicators have arrows/labels, not just up-green/down-red
- **Reduced motion** respected — `prefers-reduced-motion: reduce` disables non-essential animations
- **Screen-reader-friendly** — semantic HTML, aria labels for icon-only buttons, chart data exposed as accessible table fallback

Validate with axe DevTools or Lighthouse Accessibility audit on the page before PR.

---

## Performance Gates

The mobile target audience is on metered, often-slow connections. Performance is correctness, not polish.

| Metric | Target | Hard fail |
|--------|--------|-----------|
| First Contentful Paint (mobile, 3G) | <2.5s | >4s |
| Largest Contentful Paint (mobile, 3G) | <3s | >5s |
| Total Blocking Time | <300ms | >800ms |
| Cumulative Layout Shift | <0.1 | >0.25 |
| JS shipped to a typical article page | <100KB gzipped | >250KB |

Run Lighthouse mobile audit on the deployed preview URL for any PR that ships visible UI changes. Attach the score in the PR body if any metric is borderline.

---

## Bilingual / i18n Gates

For any text content:

- English copy uses sentence case, plain language, no jargon without explanation
- Nepali copy is conversational (tea-shop tone — see [STRATEGY.md](STRATEGY.md) §"Nepali Tone Rules"), NOT direct translation
- Date displays follow [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md) display rules
- Currency: NPR symbol or "Rs" — never "$" without explicit context
- Devanagari rendering tested in actual Nepali — use Mukta, Noto Sans Devanagari, or Hind for the font

For monthly recurring artifacts (Monthly Verdict, Pulse), the Nepali version ships 1 week after the English. Exception: **Cost of Leaving Nepal calculator ships bilingual Day 1.**

---

## Mobile-First Rules (from STRATEGY.md §"The Lenses System")

These are reminders embedded in this acceptance doc so PR reviewers don't have to chase:

- One hero visualization per screen on mobile — no more
- KPI cards condense to a horizontal scrollable strip on phones (max 3 visible)
- Sankey diagrams (Money Map) render as a simplified stacked-bar on phones; "view full diagram" link to expanded view
- Stories load reading-mode by default on mobile (large type, no sidebar)
- Newsletter signup is one persistent button — not an interstitial that blocks reading

If a desktop layout looks great but the mobile screenshot is broken, the PR doesn't ship.

---

## PR Checklist Snippet

The [PR template](../.github/PULL_REQUEST_TEMPLATE.md) includes a UI acceptance section. For UI PRs, the author confirms:

```
## UI Acceptance
- [ ] Mobile screenshot (390×844) attached
- [ ] Desktop screenshot (1440×900) attached
- [ ] All states screenshotted (Loading / Empty / Error / Populated) for data-driven components
- [ ] All input states screenshotted (Invalid / Submitting / Success) for input components
- [ ] Source citation + confidence badge visible on every data element
- [ ] Plain-language interpretation included for every chart
- [ ] Accessibility audit (axe or Lighthouse) passed; alt text on all images/charts
- [ ] Lighthouse mobile score recorded (or N/A for non-page changes)
- [ ] No information conveyed by color alone
- [ ] Bilingual: applicable language versions present, or follow-up issue filed
```

A UI PR missing screenshots is not reviewed. A UI PR with screenshots but failing one of the gates above gets a follow-up task brief, not in-line fixes.

---

## Cross-Reference

- Chart Doctrine: [STRATEGY.md](STRATEGY.md) §"Chart Doctrine"
- Content formats (what should appear where): [CONTENT_FORMATS.md](CONTENT_FORMATS.md)
- Date display rules: [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md) §"Display Rules"
- Conventions for React components: [CONVENTIONS.md](CONVENTIONS.md) §"React + Next.js"
