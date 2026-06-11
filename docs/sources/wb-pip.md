# Source: World Bank — Poverty and Inequality Platform (Nepal)

**source_id:** `wb-pip`
**Status:** Active
**Tier:** 2
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11

## What this is

The World Bank's **Poverty and Inequality Platform** (PIP, successor to
PovcalNet), filtered to Nepal, via its public REST API. PIP is the authoritative
international source for **distributional** poverty and inequality — multiple
international poverty lines, the Gini coefficient, mean/median consumption, and
decile shares — anchored on Nepal's household surveys.

Ingested as the **distributional poverty layer**. It is the only source that
gives the full shape of Nepal's distribution (not just a single headcount), and
it carries the freshest survey — **NLSS-IV / LSS-IV (2022/23)**, which entered
PIP in October 2024. `pip-gini` is stored on the same 0–100 scale as
`wdi-gini-index` so the two cross-check (WDI's Nepal Gini is itself fed by PIP).

## Publication

- API base: `https://api.worldbank.org/pip/v1/pip?country=NPL&povline=<L>&format=json`
- No authentication. **Intermittently flaky** — transient empty / HTTP 000 responses; the CLI retries.
- `&fill_gaps=true` returns the headcount filled across every year (modelled); the default returns only survey rounds.
- Frequency: ad-hoc — refreshed when a new survey is added or PPPs/methods update.
- Format: JSON (REST; no OCR required).

## What we extract

10 indicators. The 5 survey rounds (1984 MHBS, 1995 LSS-I, 2003 LSS-II, 2010
LSS-III, 2022 LSS-IV) are the only rows PIP populates with distributional detail:

| Slug | PIP field | Unit | Scale | Note |
|------|-----------|------|-------|------|
| `pip-poverty-headcount-215` | headcount @ $2.15 | percent | ×100 | extreme poverty |
| `pip-poverty-headcount-365` | headcount @ $3.65 | percent | ×100 | LMIC line — also the filled trend |
| `pip-poverty-headcount-685` | headcount @ $6.85 | percent | ×100 | UMIC line — post-LDC fragility marker |
| `pip-poverty-gap-365` | poverty_gap @ $3.65 | percent | ×100 | depth |
| `pip-poverty-severity-365` | poverty_severity @ $3.65 | percent | ×100 | FGT2 |
| `pip-gini` | gini | index_points | ×100 | **cross-checks `wdi-gini-index`** |
| `pip-mean-consumption` | mean | intl_dollar_per_day | ×1 | 2017-PPP daily |
| `pip-median-consumption` | median | intl_dollar_per_day | ×1 | 2017-PPP daily |
| `pip-decile1-share` | decile1 | percent | ×100 | captured by poorest 10% |
| `pip-decile10-share` | decile10 | percent | ×100 | captured by richest 10% |

## Observation type (ADR-0025)

PIP is the first source to exercise the full `observation_type` taxonomy:

- **Survey anchors** (`is_interpolated=false`) → `observation_type='actual'`, confidence **A**. The 5 rounds, with full distribution.
- **Filled $3.65 headcount** for non-survey years → confidence **B**, with type from PIP's `estimation_type`:
  - `interpolation` (between two surveys) → `interpolated`
  - forward `extrapolation` (after the last survey) → `projection`
  - backward `extrapolation` (before the first survey) → `estimate`

Survey years come **only** from the anchor block; if the filled series also
contains a survey year, the parser drops it (the anchor is authoritative).

## Period convention

PIP `reporting_year` is a **calendar** AD year, but it labels the same Nepal
survey rounds that the WDI ingest maps onto Nepal's July fiscal year. To keep
`pip-*` aligned with `wdi-*` for the same survey, the parser reuses the WDI
convention: year `Y` → BS FY `(Y+57)`, AD Jul 15 `Y` – Jul 15 `Y+1`. So PIP
2022 → BS 2079/80, matching how WDI labels the same LSS-IV Gini.

## Provenance

- Confidence default: A (survey anchors); B (modelled trend)
- License: CC BY 4.0
- Reporting period type: annual

## Known breakage modes

- `api-intermittently-returns-empty-or-000-retry` — the PIP endpoint is flaky; the CLI retries up to 4×
- `distributional-fields-null-except-survey-years` — gini/mean/median/deciles are null in modelled years (by design)
- `reporting-year-is-calendar-not-fiscal` — unlike WEO/WDI raw dates; mapped onto Nepal FY via the WDI convention
- `welfare-type-differs-income-pre1995-consumption-after` — 1984 MHBS is income-based; later rounds consumption-based

## Revision policy

PIP revises when surveys are re-estimated or PPP/CPI inputs change. Each ingest
is a full snapshot; updated values supersede prior approved rows via
`revision_number`.

## Cross-source checks

- `pip-gini` ↔ `wdi-gini-index` — same 0–100 scale, same underlying surveys (expect close).
- `pip-poverty-headcount-*` complements `wdi-poverty-headcount-national-pct` (national line vs international lines — different definitions, not a tolerance check).

## Parser

- Path: `scrapers/wb_pip/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: `scrapers/wb_pip/tests/fixtures/pip_npl_2026.json` (values from a live PIP response)

## Ingest CLI

```powershell
# Dry-run against the saved fixture (no DB, no network):
pnpm ingest:pip --dry-run

# Download fresh from the PIP API (4 queries, merged), then ingest:
pnpm ingest:pip --download

# Download/save without ingesting:
pnpm ingest:pip --download --output-dir "C:\PIP"

# Live ingest from a pre-downloaded combined JSON:
pnpm ingest:pip --input "path/to/pip_npl_2026-06-11.json"
```

## Archive policy

- Downloaded files stored under archive key `wb-pip/<yyyy-mm-dd>/<filename>`.
- Hash + URL recorded in `source_documents`. Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
