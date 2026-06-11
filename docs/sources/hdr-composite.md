# Source: UNDP — Human Development Report Composite Indices (Nepal)

**source_id:** `hdr-composite`
**Status:** Active
**Tier:** 2
**Registered at:** 2026-06-11
**Last verified:** 2026-06-11

## What this is

The UNDP Human Development Report's **Composite Indices — complete time series**,
filtered to Nepal. It is the authoritative source for the **Human Development
Index** and its relatives (inequality-adjusted, gender, planetary-adjusted) plus
the underlying dimension indicators (longevity, schooling, GNI per capita).

Ingested as the **human-development layer** for the "Where Money Becomes Wealth"
pillar — the question of whether Nepal's income is converting into health,
education, and reduced inequality. Nepal HDI 2023 = **0.622** (Medium HD).
`hdr-gii` and the inequality losses complement the `pip-*` / `wdi-gini-index`
distributional series.

## Publication

- CSV URL: `https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv`
- No authentication. Single bulk download (one wide row per country).
- Frequency: annual HDR release (HDR 2025 launched May 2025; data through 2023).
- Format: **CSV, Latin-1 (cp1252) encoded** — NOT UTF-8 (accented country names). The parser reads it as Latin-1.

## What we extract

18 indicators, read from the `NPL` row's `<metric>_<year>` columns:

| Slug | HDR prefix | Unit | Coverage |
|------|-----------|------|----------|
| `hdr-hdi` / `-female` / `-male` | `hdi` / `hdi_f` / `hdi_m` | index_0_1 | 1990– |
| `hdr-ihdi` | `ihdi` | index_0_1 | 2010– |
| `hdr-gii` | `gii` | index_0_1 | 1990– |
| `hdr-gdi` | `gdi` | index_0_1 | 1990– |
| `hdr-phdi` | `phdi` | index_0_1 | 1990– |
| `hdr-life-expectancy` | `le` | years | 1990– |
| `hdr-expected-years-schooling` | `eys` | years | 1990– |
| `hdr-mean-years-schooling` | `mys` | years | 1990– |
| `hdr-gni-per-capita-ppp` | `gnipc` | intl_dollar (2021 PPP) | 1990– |
| `hdr-coefficient-human-inequality` | `coef_ineq` | percent | 2010– |
| `hdr-ihdi-overall-loss` | `loss` | percent | 2010– |
| `hdr-inequality-education` / `-income` / `-life-expectancy` | `ineq_edu` / `ineq_inc` / `ineq_le` | percent | 2010– |
| `hdr-labour-force-participation-female` / `-male` | `lfpr_f` / `lfpr_m` | percent | 1990– |

Prefix matching is **exact** (`^<prefix>_<year>$`) so `hdi` never captures
`hdi_rank` / `hdi_f` / `hdi_m`. All rows are `observation_type='actual'`,
confidence A.

## Period convention

HDR years are calendar years; the parser maps year `Y` onto Nepal's FY via the
WDI convention (`Y → BS Y+57`, AD Jul 15 Y – Jul 15 Y+1) so `hdr-*` aligns with
`wdi-*` / `pip-*` for the same year. (HDI 2023 → BS 2080/81.)

## Publication date

The CSV carries no timestamp, so the parser pins the vintage's publication date
(HDR 2025 launch, 2025-05-06). Bump `_PUBLICATION_DATE_AD` in the parser when the
source CSV vintage changes.

## Provenance

- Confidence default: A
- License: CC BY 3.0 IGO
- Reporting period type: annual

## Known breakage modes

- `csv-is-latin1-not-utf8` — reading as UTF-8 raises a decode error; the parser reads Latin-1
- `wide-format-metric_year-columns` — ~1,112 columns; the parser keys by `<prefix>_<year>`
- `undp-changes-csv-url-path-each-vintage` — the `2025_HDR/HDR25_…` path changes annually; update the CLI + registry URL
- `composite-indices-start-1990-but-ihdi-inequality-from-2010` — IHDI/inequality cells are blank before 2010 (skipped)

## Revision policy

Each annual HDR re-estimates the full back-series. Ingest the new vintage as a
full snapshot; updated values supersede prior approved rows via `revision_number`.

## Cross-source checks

- `hdr-gii` / inequality losses ↔ `pip-gini` / `wdi-gini-index` — different concepts (gender vs consumption inequality) but jointly describe Nepal's distribution.
- `hdr-gni-per-capita-ppp` is a sense-check against `wdi-gdp-per-capita-current-usd` (PPP vs market USD — not a tolerance check).

## Parser

- Path: `scrapers/hdr_composite/parser.py`
- Version: 0.1.0
- Owner: Mother Opus
- Tested against: `scrapers/hdr_composite/tests/fixtures/hdr_composite_npl.csv` (real HDR 2025 Nepal values)

## Ingest CLI

```powershell
# Dry-run against the saved fixture (no DB, no network):
pnpm ingest:hdr --dry-run

# Download the HDR 2025 CSV, then ingest:
pnpm ingest:hdr --download

# Download/save without ingesting:
pnpm ingest:hdr --download --output-dir "C:\HDR"

# Live ingest from a pre-downloaded CSV:
pnpm ingest:hdr --input "path/to/HDR25_Composite_indices_complete_time_series.csv"
```

## Archive policy

- Downloaded files stored under archive key `hdr-composite/<yyyy-mm-dd>/<filename>`.
- Hash + URL recorded in `source_documents`. Never overwritten. Latin-1 bytes preserved verbatim.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
