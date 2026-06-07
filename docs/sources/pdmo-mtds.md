# Source: Public Debt Management Office — Medium-Term Debt Management Strategy (MTDS)

**source_id:** `pdmo-mtds`
**Status:** Paused
**Tier:** null (reference-only)
**Registered at:** 2026-06-07
**Last verified:** 2026-05-20 (Worker B catalog audit)

## What this is

PDMO's Medium-Term Debt Management Strategy (MTDS) is a 3-year forward-looking policy
document setting targets for the composition and cost of public debt. It is not a time-series
statistical feed — it is a strategy document that provides context for the Borrowed Time
vertical and can be cited from editorial stories. Four editions confirmed (FY 2078/79–2080/81
through FY 2082/83–2084/85). Published in both Nepali and English.

## Publication

- URL: https://pdmo.gov.np/pages/debtsteategy (note: URL has a typo — "steategy" not "strategy")
- Frequency: annual (updated each FY with a new 3-year window)
- Expected window: Typically Ashadh–Shrawan (June–August)
- Format: pdf

## What we extract

No indicators ingested — reference-only. Cite from stories:

- Debt composition target (domestic vs. external split %)
- Benchmark interest rate target for new borrowings (%)
- Planned T-bill vs. bond issuance mix

## Provenance

- Confidence default: A
- License: gov-open
- Reporting period type: annual (3-year forward window)
- Ingestion mode: reference_only

## Known breakage modes

- `url-typo-on-pdmo-site-debtsteategy-not-debtstrategy` — The PDMO page URL contains a typo:
  `debtsteategy` (not `debtstrategy`). Do not attempt to correct the URL; use the typo'd form
  as published. If PDMO fixes the typo, update this profile and the seed row.

## Revision policy

Annual; 3-year forward window. Each edition supersedes the prior. Not a time-series feed;
not ingested into `approved_indicator_values`.

## Parser

Not applicable — reference_only. Cited from stories via source document link.

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  (Phase 2: migrate to R2 — see [ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md))
  under key `pdmo-mtds/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests

Not applicable — reference_only source.
