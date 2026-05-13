# Source Registry

The platform's core asset is **auditable economic truth**, not "data". Every external data feed gets a registry entry before a scraper is written, before a row hits production. Without this discipline, the Fact Ledger silently mixes A-tier and C-tier inputs and the credibility moat dies.

This document defines:
1. The schema of the source registry
2. The workflow for adding a new source
3. The list of sources committed to ingest in Year 1

---

## Schema

Every source gets a row in `source_registry` (database table) and a Markdown profile in `docs/sources/<source-id>.md`. The database row is the live truth; the Markdown is the human-readable companion.

### Required fields

| Field | Type | Example |
|-------|------|---------|
| `source_id` | string (kebab) | `nrb-cmefs-monthly` |
| `agency` | string | `Nepal Rastra Bank` |
| `agency_short` | string | `NRB` |
| `dataset_name` | string | `Current Macroeconomic and Financial Situation` |
| `source_url` | URL | `https://www.nrb.org.np/category/current-macroeconomic-situation/` |
| `publication_frequency` | enum | `monthly`, `quarterly`, `annual`, `daily`, `seasonal`, `ad-hoc` |
| `expected_release_window` | string | `25th–30th of the month following the reporting period` |
| `reporting_period_type` | enum | `monthly`, `quarterly`, `annual`, `nine-months`, `cumulative-ytd` |
| `file_format` | enum | `pdf`, `csv`, `xlsx`, `xls`, `html`, `json`, `xml` |
| `requires_table_extraction` | boolean | `true` if PDF tables need pdfplumber |
| `historical_coverage` | string | `FY 2073/74 onward (~2016)` |
| `license_status` | enum | `public-domain`, `gov-open`, `cc-by`, `proprietary`, `unclear` |
| `parser_owner` | string (kebab) | `scrapers/parse_cmefs.py` |
| `parser_version` | semver | `1.0.0` |
| `revision_policy` | string | `Provisional values revised in next release; historical values stable after 2 cycles` |
| `known_breakage_modes` | string[] | `["url-changes-each-fy", "pdf-format-shifts-at-fy-boundary"]` |
| `confidence_default` | enum | `A`, `B`, `C` |
| `notes` | string | freeform |
| `registered_at` | timestamp | auto |
| `last_verified_at` | timestamp | manual, monthly |

### Computed/derived

- `indicators_produced` — array of indicator slugs this source feeds (joined via `indicator_source_map`)
- `last_successful_ingest_at` — joined from `parser_runs`
- `last_failed_ingest_at` — joined from `parser_runs`
- `confidence_grade_observed` — most-recent ingest's confidence label (may differ from `confidence_default` for one cycle)

---

## Workflow for Adding a New Source

**No scraper is written until the source is registered.** This is non-negotiable.

1. Identify the source. Open its publication page in a browser. Verify it actually publishes what you expect.
2. Write the Markdown profile at `docs/sources/<source-id>.md` (template below).
3. Insert the row into `source_registry` via a Drizzle migration (`migrations/NNNN_add_source_<id>.sql`).
4. Identify which indicators this source produces. Either:
   - Add new rows to `indicators` (also via migration), OR
   - Map to existing indicators via `indicator_source_map`.
5. Write the parser (`scrapers/<source-id>/parser.py`). Parser writes ONLY to `staging_indicator_values` (see [DATA_PIPELINE.md](DATA_PIPELINE.md)).
6. Write at least one parser test against an archived sample.
7. Open PR. Reviewer (Mother) checks: registry row sane, indicators mapped, parser test green, sample archived in Supabase Storage (R2 in Phase 2).
8. After merge: first manual ingest. Verify staging output, promote to approved.

A scraper merged without a source registry entry is reverted on sight.

---

## Markdown Profile Template

`docs/sources/<source-id>.md`:

```markdown
# Source: <Agency> — <Dataset Name>

**source_id:** `<source-id>`
**Status:** Active | Paused | Deprecated
**Last verified:** YYYY-MM-DD

## What this is
<One paragraph: what the dataset reports, why we ingest it>

## Publication
- URL: <link>
- Frequency: <monthly | quarterly | …>
- Expected window: <e.g. "25th–30th of month following">
- Format: <pdf | csv | xlsx | html>

## What we extract
- <indicator slug 1> — <one-line description>
- <indicator slug 2> — <one-line description>

## Provenance
- Confidence default: <A | B | C>
- License: <public-domain | gov-open | …>
- Reporting period type: <monthly | quarterly | …>

## Known breakage modes
- <e.g. "URL changes each fiscal year — search-pattern fallback in parser">
- <e.g. "PDF column headers shifted in FY 2081/82 — handled by parser v1.2">

## Revision policy
<How the source revises historical values; how we handle revisions>

## Parser
- Path: `scrapers/<source-id>/parser.py`
- Version: <semver>
- Owner: <Mother Opus | name>
- Tested against: `docs/sources/<source-id>/samples/`

## Archive policy
- All downloaded files stored in Supabase Storage bucket `source-archive` (Phase 2: migrate to R2 — see [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md)) under key `<source-id>/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`.
- Never overwritten.

## Recent ingests
<auto-populated table or link to monitoring dashboard>
```

---

## Year 1 Source Commit List (revised per docs/SOURCE_REGISTRY_AUDIT_PROPOSAL.md, accepted 2026-05-14)

The previous Tier 1–4 list was 12 entries. The audit revealed ~30 missing feeds (LMBIS/SuTRA, Census 2078, Yellow Book PE financials, Local Ledger, climate exposure, etc.). The list below is the v2 commit list, reorganized into 5 tiers + a separate "reference-only" category.

### `ingestion_mode`

Every entry now declares one of three ingestion modes (column added to `source_registry` in migration 0002):
- **`automated_cron`** — GitHub Actions cron pulls fresh data; parser runs without human input
- **`manual_upload`** — Human drops a fresh file into `Financial Data/<source-id>/` and runs the parser; Surya OCR usually involved
- **`reference_only`** — Cited in stories and Knowledge Base; NOT parsed into `approved_indicator_values`

### Tier 0 — Already on disk (immediate, no OCR needed)

| ID | Agency | Dataset | Mode | Confidence | Notes |
|----|--------|---------|------|------------|-------|
| `nrb-ncpi-table` | NRB | NCPI Table 2(B) | manual_upload | A | Worker C parser shipped v0.1.0 (CSV) |
| `nrb-cmefs-monthly` | NRB | Current Macroeconomic and Financial Situation | manual_upload | A | Status: Active (PDF parser pending — Phase B per ADR-0008) |
| `nrb-bfi-monthly` | NRB | Banking & Financial Statistics (monthly XLSX, 50 files Aug-2021→Sept-2025) | manual_upload | A | Worker ζ ships v0.1.0 (XLSX, no OCR). See `scrapers/nrb_bfi/`. |
| `mof-intergovernmental-fiscal-transfer` | MoF / NNRFC | Intergovernmental fiscal transfers (annual) | manual_upload | A | FY 2082/83 ingestable from pre-Cleaned XLSX; prior FYs require Surya OCR. |
| `cbs-nphc-2021` | CBS | National Population & Housing Census 2021 (89 CSVs + 8 Excel) | manual_upload | A | Worker η ships v0.1.0 (CSV, no OCR). |
| `admin-hierarchy-voters` | EC (derived) | Administrative hierarchy from voter DB (10,263 rows) | manual_upload | A | Pre-extracted CSV; municipality types need fix on join. |

### Tier 1 — Days 1–28 (the macro spine + first flagship inputs)

| ID | Agency | Dataset | Mode | Priority |
|----|--------|---------|------|----------|
| `nrb-reserves-daily` | NRB | Daily foreign reserves disclosure | automated_cron | High |
| `customs-monthly-trade` | Department of Customs | Monthly trade statistics | automated_cron | High |
| `noc-petroleum-monthly` | Nepal Oil Corporation | Monthly petroleum imports + price revision notices | automated_cron | High |
| `fcgo-daily` | FCGO | Daily revenue + expenditure | automated_cron | High (preliminary; B-tier confidence) |
| `nepse-eod` | NEPSE | EOD quotes + market cap | automated_cron | High |
| `kalimati-daily-prices` | Kalimati Market | Daily wholesale fruit + veg prices | automated_cron | High (Story #2 dependency) |

### Tier 2 — Days 28–60 (quarterly macro + first deep-dives)

| ID | Agency | Dataset | Mode | Priority |
|----|--------|---------|------|----------|
| `pdmo-debt-bulletin` | PDMO | Quarterly debt bulletin | manual_upload | High |
| `nrb-banking-stats` | NRB | Banking & Financial Statistics (quarterly aggregates) | automated_cron | High |
| `nrb-loans-by-sector` | NRB | Quarterly Economic Bulletin — loans & advances by sector | automated_cron | High |
| `dofe-labour-migration` | DoFE | Monthly labour permits + airport records | automated_cron | High |
| `nrb-fdi-bulletin` | NRB | Status of FDI in Nepal (annual) | manual_upload | Medium |
| `nso-gdp` | NSO | Quarterly GDP estimates | automated_cron | Medium |
| `ntb-tourism-monthly` | Nepal Tourism Board | Monthly arrivals + receipts | automated_cron | Medium |

### Tier 3 — Days 60–120 (verticals + utilities deepen)

| ID | Agency | Dataset | Mode | Priority |
|----|--------|---------|------|----------|
| `coops-regulatory-status` | Department of Cooperatives / Sahakari Bibhag | Regulatory status of cooperatives | manual_upload | High |
| `oag-audit-reports` | OAG | Audit reports | manual_upload | High |
| `dpm-public-enterprises-annual` | DPM Office | Public Enterprises Annual Status Reviews (Yellow Books) | manual_upload | High |
| `moald-crop-production` | MoALD | Seasonal crop production | manual_upload | Medium |
| `mof-lmbis` | MoF | Line Ministry Budget Information System (federal capex execution) | automated_cron | Medium |
| `mof-sutra` | MoF | Sub-national Treasury Regulatory Application | automated_cron | Medium |
| `nnrfc-allocations` | NNRFC | Fiscal transfer allocations | manual_upload | Medium |
| `ird-revenue-monthly` | IRD | Revenue dashboard | automated_cron | Medium |
| `nea-generation-monthly` | NEA | Generation + sales monthly bulletins | manual_upload | Medium |
| `doed-project-pipeline` | DoED | Hydropower licence + project registry | manual_upload | Medium |
| `npc-project-bank` | NPC | Project Bank / monitoring | manual_upload | Medium |

### Tier 4 — Days 120–365 (the long-tail of Year 1)

| ID | Agency | Dataset | Mode | Priority |
|----|--------|---------|------|----------|
| `census-2078-district` | CBS | NPHC 2078 district-level disaggregated data | manual_upload | High (District MRI) |
| `moe-noc-student-outflow` | Ministry of Education | No Objection Letters for student outflow | manual_upload | Medium |
| `ird-top-taxpayers` | IRD | Top taxpayers annual disclosure + LTO data | manual_upload | Medium |
| `oag-lbl-local-audits` | OAG | Local Body audit reports | manual_upload | Medium |
| `dohs-hmis` | DoHS | Health Management Information System | automated_cron | Medium |
| `dohs-emis` | CEHRD / DoEd | Education Management Info System | automated_cron | Medium |
| `mof-budget-redbook` | MoF | Budget Red Book (annual line items) | manual_upload | Medium |
| `fepb-manpower-companies` | FEPB | Manpower company licences + recruitment ceilings | manual_upload | Medium |
| `dhm-hydro-met` | DHM | Hydro + meteorology (flood/discharge/precipitation) | automated_cron | Medium |
| `ndrrma-damage-tally` | NDRRMA | Disaster damage tally | manual_upload | Medium |
| `customs-exemptions` | Department of Customs | Duty exemption list | manual_upload | Low |
| `dolm-malpot-stats` | Department of Land Management | Malpot (land transaction) statistics | manual_upload | Low |
| `un-comtrade` | UN | Comtrade trade-partner data | automated_cron | Low |
| `nrn-investment-tracker` | NRN-MoF + IBN | NRN investment disclosures | manual_upload | Low |
| `mof-dfimis` | MoF | Aid Management Platform / DFIMIS | manual_upload | Low |

### Phase 2 (post-Day 365) — `status: paused` registry entries

Per the audit decision, these stay in the registry with `status='paused'` so the doctrine surface tracks them. No parsers planned for Year 1.

| ID | Agency | Why HARD |
|----|--------|----------|
| `ocr-company-register` | Office of Company Registrar | Cross-ownership mapping; mostly PDF, no structured API; manual phase needed |
| `mto-exchange-rates` | IME / Prabhu / Western Union | FX corridor mechanics; fragmented per-MTO scraping |
| `cib-sectoral-credit` | Credit Information Bureau Nepal | Aggregated sectoral credit; partial public release only |
| `dols-cadastral` | Department of Land Survey | Cadastral aggregates; Phase-2 |
| `hansen-gfc` | UMD | Hansen Global Forest Change (geospatial) |
| `esa-worldcover` | ESA | WorldCover (geospatial) |
| `icimod-glacier-inventory` | ICIMOD | Glacier inventory (climate exposure reference) |
| `ecn-results` | Election Commission Nepal | Election results federal/provincial/local |
| `regional-wholesale-prices` | Pokhara / Birgunj / Itahari | Price-chain breadth |

### Reference-only assets (separate `docs/reference-assets/` track — NOT in `source_registry` table)

These are cited in stories and the Knowledge Base but NOT parsed into `approved_indicator_values`. They live as Markdown profile files at `docs/reference-assets/<asset-id>.md` and get cited via Fact Ledger claims when relevant. Per the audit, light registry shape is NOT used for these; the asset profiles + Fact Ledger citations are enough.

| Asset | Use |
|-------|-----|
| MoF Economic Survey (annual) | Macro narrative reference |
| MoF Budget Speech + Red Book (annual) | Budget Watch reference |
| NPC 16th Plan (5-yr) | Reference + project pipeline |
| NLSS (decadal) | Household Ledger reference |
| NDHS (quinquennial) | Health reference |
| Agriculture Census (decennial) | Soil Economy reference |
| DFRS Forest Inventory | Soil Economy reference |
| IMF Article IV | International benchmark |
| ADB ADO Nepal section | International benchmark |
| World Bank WDI | International benchmark |
| Census 2078 (full survey) | Reference + District MRI source |

---

## Cross-Reference

- Schema implementation lives in `src/lib/db/schema/source-registry.ts` (added Day 4–10).
- Parser pipeline conventions: [DATA_PIPELINE.md](DATA_PIPELINE.md).
- Date/period handling: [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md).
- Archival storage: [CLOUD_STACK.md](CLOUD_STACK.md) §"Supabase Storage" (primary); [ADR-0004](decisions/0004-supabase-storage-instead-of-r2.md) for the R2-deferred decision.
- Confidence grading rules: [STRATEGY.md](STRATEGY.md) §"The Visible Fact Ledger".
