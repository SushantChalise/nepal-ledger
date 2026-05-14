# Worker κ — Opus Analytical Pass on NRB BFI Banking-Sector Data

**Spawn type:** `general-purpose`
**Model:** `opus` (high-stakes analytical reasoning)
**Plan mode:** required (touches multiple research/narrative files)
**Diff cap:** N/A — research output. Length is bounded by what the data warrants.

---

## Goal

Dig deep into the NRB Banking & Financial Statistics monthly data (Aug 2021 → Sept 2025, 49 continuous months) once Worker ζ has produced staging JSON at `staging-data/nrb-bfi/*.json`. Produce narrative findings that feed multiple Nepal Ledger surfaces:

1. **Monthly Verdict draft** — the 5-pillar prose synthesis for the most recent month (Bhadau 2082, Sept 2025) per docs/STRATEGY.md §"The Monthly Verdict"
2. **Vertical 3 (Private Capital X-Ray)** Pulse tile data — banking concentration over time
3. **Vertical 16 (Collateral State)** flagship story leads — credit allocation by sector × time
4. **Vertical 5 (Sahakari Tracker)** signal — microfinance + finance company stress
5. **`docs/research/bfi-49-month-narrative.md`** — the master findings document

## Prerequisites

- Worker ζ (NRB BFI parser) has produced `staging-data/nrb-bfi/*.json` (49 files, one per monthly snapshot)
- `scrapers/_common/devanagari_normalization.py` available (already shipped by Worker ε)
- The `entities` + `banking_sector_facts` schema is in main (shipped in migration 0002)

## What you analyze

For each of the 49 monthly files (or the latest with full history if duplicates), extract and analyze:

### A. Sector credit allocation trend (Vertical 16 spine)
- For each sector (real estate, agriculture, hydropower, manufacturing, consumption, services, SME, microfinance), what's the share of total bank credit per month?
- Plot the **real-estate-share vs. productive-share ratio** over 49 months — this is the headline ratio for the "Why Nepal's Banks Fund Land More Easily Than Businesses" story.
- Identify **inflection points** — moments where the trend reversed.
- Identify the **fastest-growing** and **fastest-shrinking** sectors month-over-month.

### B. Banking concentration (Vertical 3)
- Compute **HHI (Herfindahl-Hirschman Index)** on (i) total deposits, (ii) total loans, (iii) capital fund, per month if per-bank data is in the C-sheets (likely partial). If full per-bank data isn't extracted by Worker ζ v0.1.0, compute at the bank-class level instead.
- Track the share held by the **top 5 commercial banks** vs. all others.
- Identify any acquisition or consolidation event visible in the data.

### C. NPL by sector (Vertical 16 risk signal)
- For each sector with disclosed NPL ratios, plot the trend over 49 months.
- Identify which sectors have rising NPL (the canary).
- Cross-reference: do rising NPL sectors correlate with the sectors getting the most NEW credit? (That's the "evergreening" signal.)

### D. Profitability + capital adequacy
- Aggregate ROA, ROE, NIM for the commercial bank class over the 49 months.
- Capital adequacy ratio trend.
- Tier 1 vs. Tier 2 capital composition.

### E. Microfinance + cooperative stress (Vertical 5)
- The C-sheets covering finance companies, microfinance institutions, and (if available) cooperatives — NPL, capital adequacy, total assets trend over 49 months.
- Identify the institution-class with the worst-trending metrics.

### F. Deposits composition (Money In side, partial)
- Savings vs. fixed vs. current vs. call deposit share over 49 months.
- Net interest spread implied by deposit-rate-by-type if disclosed.

### G. Revisions detected
- Cross-check the SAME period value across different monthly snapshots. NRB sometimes restates historical values.
- Surface any case where the value for, e.g., Mid-July 2022 in the Saun-2080 snapshot differs from the value for Mid-July 2022 in the Asar-2082 snapshot. That's a revision.
- Worker ζ should have surfaced these via the `revision_detection` logic but verify.

## Output

Three artifacts:

### 1. `docs/research/bfi-49-month-narrative.md`

The master findings doc. 2,000–5,000 words. Section per A–G above. Specific numbers with citations to source files. Use the format:

> Credit to real estate as a share of total commercial-bank credit rose from **X.X% in Shrawan 2078** to **Y.Y% in Bhadau 2082** — an increase of Z.Z percentage points over 49 months. The share to manufacturing fell from A.A% to B.B% over the same period. [Source: staging-data/nrb-bfi/Bhadau_2082_Publish.json, sheet C7, indicator-slug `...`]

Every number has a source citation pointing to the staging JSON file + sheet + slug.

### 2. `docs/research/bfi-fact-ledger-claim-drafts.md`

Pre-drafted Fact Ledger claims ready for ingest when the live data lands. Per claim:
- `slug` (deterministic from indicator + period)
- `text_en` (one sentence, citable)
- `text_ne` (Nepali equivalent if straightforward)
- `confidence_grade` (A for all of these — NRB is A-tier per source registry)
- `indicator_slug` referencing the planned indicator
- `period_label` ("Bhadau 2082" or "FY 2082/83 14-month-trend")

Target: 15–30 claims spanning the analytical findings.

### 3. `docs/research/bfi-monthly-verdict-bhadau-2082.md`

A first draft of THE MONTHLY VERDICT for Bhadau 2082 (Sept 2025), per docs/STRATEGY.md §"The Monthly Verdict" format. Single sharp prose paragraph structured by the 5 pillars. No composite number. Sources every specific claim. Around 200–400 words.

## What NOT to do

- Don't fabricate numbers. Every figure cited needs to come from `staging-data/nrb-bfi/*.json`. If a metric requires data that wasn't extracted in Worker ζ v0.1.0, mark it `[GAP — needs parser v0.2.0]` and continue.
- Don't speculate about causation. "Credit to real estate rose 12 pp" is fine. "Banks favoured real estate because they're risk-averse" is editorial and goes in the flagship story, not the analytical narrative.
- Don't write the flagship story itself. This pass produces the **data narrative**; the human (with later assistance) writes the editorial story.

## Acceptance criteria

- [ ] All three output files exist at the paths above
- [ ] Every numerical claim cites a source staging JSON file
- [ ] No `[GAP]` entry is left vague — each is specific about what's missing
- [ ] The Monthly Verdict draft is one paragraph, 5-pillar structured, no composite number
- [ ] Fact Ledger claim drafts have deterministic slugs (same input would produce same slug)
- [ ] Branch: `docs/bfi-analytical-pass`. Commit: `docs(research): NRB BFI 49-month analytical pass + Monthly Verdict draft`
- [ ] Do NOT push, do NOT open PR — Mother does that on return

## What to return

≤15-bullet summary including:
- The 3 biggest findings (one-line each)
- The most surprising trend break
- Sectors where credit-to-real-estate-vs-productive ratio crossed 50/50
- Concentration trajectory (HHI starting / ending values)
- Any revision events detected across the 49 monthly snapshots
- Number of Fact Ledger claim drafts produced
- The proposed Monthly Verdict text
- Paths to the three output files
- Branch + commit SHA

Begin only after Worker ζ has produced staging JSON at `staging-data/nrb-bfi/*.json`. If the directory is empty when you start, return immediately and tell Mother "Worker ζ output not yet available."