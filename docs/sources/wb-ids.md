# Source: World Bank — International Debt Statistics (Nepal)

**source_id:** `wb-ids`
**Status:** Active
**Tier:** 2
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11

## What this is

The World Bank's **International Debt Statistics** (IDS), filtered to Nepal. IDS
is the authoritative source for **external debt by creditor** — the dimension
NRB's aggregate BOP/debt figures don't expose. It answers the *Money Out /
Borrowed Time* question: **who does Nepal owe, and how much?**

Nepal 2023 snapshot (from the live API): total external debt **$9.98 bn**
(24.0% of GNI). Multilateral-dominated — **World Bank-IDA $4.37 bn, ADB $2.99 bn**.
Bilateral led by **Japan $411 m > India $304 m > China $262 m**.

## Publication

- API base: `https://api.worldbank.org/v2/sources/6/country/NPL/series/<CODE>/counterpart-area/all/time/all?format=json`
- No authentication. **The IDS creditor breakdown uses the `sources/6` counterpart-area route** — the standard `/v2/country/NPL/indicator/<CODE>?source=6` route 404s for IDS series.
- Frequency: annual (IDS release ~December; ~1-year lag).
- Format: JSON (REST; no OCR required).

## What we extract

12 indicators (slug prefix `ids-`). USD stocks/service stored in `usd_million`
(parser ÷1e6); debt-to-GNI in `percent`. All `observation_type='actual'`, conf A.

### Aggregates (World counterpart, `WLD`)
- `ids-external-debt-total-usd` — `DT.DOD.DECT.CD`
- `ids-external-debt-pct-gni` — `DT.DOD.DECT.GN.ZS`
- `ids-debt-service-total-usd` — `DT.TDS.DECT.CD`
- `ids-short-term-debt-usd` — `DT.DOD.DSTC.CD`
- `ids-ppg-bilateral-total-usd` — `DT.DOD.BLAT.CD` (World)
- `ids-ppg-multilateral-total-usd` — `DT.DOD.MLAT.CD` (World)

### Bilateral creditors (`DT.DOD.BLAT.CD`, counterpart id)
- `ids-debt-bilateral-japan-usd` (701) · `ids-debt-bilateral-india-usd` (646) · `ids-debt-bilateral-china-usd` (730) · `ids-debt-bilateral-korea-usd` (742)

### Multilateral creditors (`DT.DOD.MLAT.CD`, counterpart id)
- `ids-debt-multilateral-worldbank-ida-usd` (905) · `ids-debt-multilateral-adb-usd` (915)

Creditors are **slug-encoded** (no schema change / partner-dimension ADR needed
for this focused set). The ingest CLI runs 6 series queries and extracts the
World aggregate + the named counterparts into pre-resolved slugs; the parser
applies units + the period contract.

## Period convention

IDS years are calendar year-end. For consistency with the other WB-family Nepal
series, the parser maps year `Y` onto Nepal's FY via the shared
`nepal_wb_year_period` helper (`Y → BS Y+57`). IDS 2023 → BS 2080/81. The
~6-month calendar-vs-fiscal nuance is within the system's annual tolerance.

## Provenance

- Confidence default: A
- License: CC BY 4.0
- Reporting period type: annual

## Known breakage modes

- `ids-uses-sources-6-counterpart-area-route-not-indicator-route` — the `/indicator/?source=6` route 404s; must use `sources/6/.../counterpart-area`
- `counterpart-area-names-have-trailing-nbsp-garbage-use-ids` — creditor `value` strings carry trailing non-breaking spaces; the CLI keys on counterpart `id`, not name
- `creditor-coverage-changes-as-loans-are-repaid` — a creditor's series ends when its loans are fully repaid (null thereafter; skipped)

## Revision policy

IDS revises debt stocks as creditors report. Each ingest is a full snapshot;
updated values supersede prior approved rows via `revision_number`.

## Cross-source checks

- `ids-external-debt-pct-gni` sense-checks against NRB external-sector debt ratios and `weo-govt-gross-debt-pct-gdp` (external vs gross public debt — different scopes, not a tolerance check).
- `ids-ppg-bilateral-total-usd + ids-ppg-multilateral-total-usd` ≈ the PPG share of `ids-external-debt-total-usd`.

## Parser

- Path: `scrapers/wb_ids/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: `scrapers/wb_ids/tests/fixtures/ids_npl_2026.json` (values from a live IDS response)

## Ingest CLI

```powershell
# Dry-run against the saved fixture (no DB, no network):
pnpm ingest:ids --dry-run

# Download fresh from the IDS API (6 series, creditor extraction), then ingest:
pnpm ingest:ids --download

# Download/save without ingesting:
pnpm ingest:ids --download --output-dir "C:\IDS"

# Live ingest from a pre-downloaded combined JSON:
pnpm ingest:ids --input "path/to/ids_npl_2026-06-11.json"
```

## Archive policy

- Downloaded files stored under archive key `wb-ids/<yyyy-mm-dd>/<filename>`.
- Hash + URL recorded in `source_documents`. Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
