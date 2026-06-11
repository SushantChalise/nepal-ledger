# Verdict — feature context

**Monthly Verdict** is Nepal Ledger's editorial habit loop: one structured prose release per
month, timed with the NRB CMEFs drop, that synthesises what the data means in plain language.

Template spec: [docs/CONTENT_FORMATS.md §1 "Monthly Verdict"](../../../docs/CONTENT_FORMATS.md)

Route(s): `/verdict`
Status: v1 — static first edition; KPI strip auto-populated from `approved_indicator_values`

## Architecture

Editions are `VerdictEdition` objects defined in `src/app/verdict/editions/` (one TS file per
edition). The page imports the latest edition and renders it alongside live DB data. No CMS in
Year 1 — content is just TypeScript.

## Data in
- `approved_indicator_values` via `listApprovedWithIndicator()` — auto-populates the KPI strip
- Edition objects (static TS imports) — supply the prose sections

## Components
- `components/VerdictPillar.tsx` — renders one pillar (label + prose paragraph)
- `components/VerdictDataStrip.tsx` — compact table of latest KPI values from the DB

## Invariants
- No `'use client'` anywhere in this feature — pure Server Components
- KPI strip is driven entirely from the DB; editorial prose never hard-codes indicator values
- Edition objects are versioned via `editionNumber`; never mutate a published edition
- Empty DB state (`rows.length === 0`) renders the strip with a "no data" message, not an error

## Content format (from CONTENT_FORMATS.md §1)
1. Headline
2. Pillar summaries × 5 (Money In / Out / Captured / Wasted / Where Wealth Forms)
3. What changed this month (3–5 sourced bullets)
4. Institution to watch
5. Household impact
6. Project / debt update
7. Productive escape
8. Closing line

## Gotchas
- `reportingPeriod` header label is taken from the first KPI row; if the DB has multiple
  periods it will be misleading — acceptable for v1, fix when multi-source Pulse lands
- The `VerdictDataStrip` receives pre-filtered rows (PULSE_SLUGS only); do not pass all
  approved rows to it or the table grows unwieldy as indicators accumulate
