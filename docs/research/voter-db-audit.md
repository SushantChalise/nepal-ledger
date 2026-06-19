# Pre-Ingest Audit — Voter DB Corpus (PII)

**Auditor:** Worker λ (Sonnet)
**Date:** 2026-05-14
**Branch:** `docs/audit-voter-db`
**Status:** DO NOT INGEST without explicit user sign-off. This is the most sensitive dataset in the Nepal Ledger corpus.

> Sections follow the seven-part Pre-Ingest Audit template referenced in worker brief. The doctrine doc `docs/PRE_INGEST_AUDIT.md` was not present in the tree at audit time; the section headings below mirror the template described in the brief (Inventory / Schema / PII / Provenance / License & Ethics / Risk & Verdict / Handling Recommendation).

---

## 1. Inventory

### Files audited (NOT read line-by-line — sampled only)

| Path | Size | Notes |
|---|---|---|
| `Financial Data/Voter DB/voters_db_backup_20251111_085859.sql` | 546,201,639 B (~521 MB) | Plain-text `pg_dump` dump, 2,092,344 lines, 11-Nov-2025 08:58 |
| `Financial Data/Voter DB/voters_db_backup_20251111_090306.sql` | 546,201,639 B (~521 MB) | **Byte-identical size** to the 08:58 dump; almost certainly a second copy of the same logical dump (timestamps differ by ~4 min, probably a re-export of an unchanged DB). Should be deduped before any further handling. |
| `Financial Data/Voter DB scrape/` | — | Python scraper toolkit (50+ scripts, multiple test/debug variants). Source URL: `https://voterlist.election.gov.np/`. |
| `Financial Data/Voter DB scrape/.env` | 122 B | **Credentials. NOT read by this auditor.** Filename existence confirmed only. Catch-all `.env*` is matched by repo `.gitignore` line `.env*` (with `!.env.example` allow). |
| `Financial Data/Voter DB scrape/data/complete_scraping/` | ~10 GB across 115 JSON files | Per-batch raw voter records (100–200 locations per file). **Contains individual voter records.** |
| `Financial Data/Voter DB scrape/data/voter_scraping/` | 654 MB | Earlier-pass voter JSON batches. Same shape. |
| `Financial Data/Voter DB scrape/data/constituency_mapping/` | 13 MB, 4 files | **Aggregate/derived only** — no individual voter records. Safe-by-construction. |
| `Financial Data/Voter DB scrape/data/full_extraction_test_*.csv` | — | Test extract; assume PII row-level until verified. |
| `Financial Data/Voter DB scrape/data/*.png`, `*.html`, `*.json` (root) | — | Debug screenshots / form discovery output. Probably no PII but assume risk. |

### Already-derived non-PII files (safe-by-construction)

- `Administrative Division/.../administrative_hierarchy_FINAL.csv` (polling-station counts) — referenced in worker brief; **not part of this dataset directory** but is the canonical non-PII derivative.
- `data/constituency_mapping/complete_location_mapping.json` (10,812 records) — location_id → constituency mapping with GPS, **`voter_count` aggregate** (no individuals).
- `data/constituency_mapping/constituency_summary_by_district.json` — per-district constituency lists.
- `data/constituency_mapping/hierarchical_location_mapping.json` — province → district → municipality → ward tree with counts.

---

## 2. Schema

### Database: `voters_db` (PostgreSQL, dumped via `pg_dump`)

`grep -ao "CREATE TABLE public\.[a-z_0-9]*" | sort -u` returned **123 tables**. By family:

- **Census 2021 (NSO):** 78 tables, prefix `census_2021_*` (household and individual census tabulations). NOT PII — these are pre-aggregated census tabulations by ward/municipality.
- **Population projection:** 3 tables (`population_projection_age_groups`, `population_projection_by_year`, `population_projection_single_age`). Aggregate.
- **Election results / electoral geography:** ~25 tables (`election_results_2022`, `election_results_2074_*`, `election_results_2079*`, `local_elections_*`, `provincial_*`, `constituent_assembly_2064_fptp`, `dcc_elections_2074`, `executive_elections_2074`, `unified_local_elections`, `vote_transfer_matrix`, `party_vote_flow_analysis*`). Aggregate.
- **Reference / translation:** `district_classification`, `district_name_translations`, `party_name_translations`, `polling_stations`. Non-PII.
- **`public.voters` — THE PII TABLE.** Schema:

  ```sql
  CREATE TABLE public.voters (
      province  text,
      district  text,
      gapa      text,   -- gaupalika / municipality
      ward      text,
      centre    text,   -- voting centre
      sn        text,   -- serial number within centre
      voter_no  text,   -- voter ID number
      name      text,   -- full name
      age       text,
      gender    text,
      spouse    text,   -- spouse name (relational PII)
      parent    text,   -- parent name (relational PII)
      detail    text    -- free-text remarks
  );
  ```

  No primary key, no indices, no foreign keys in the dump — this is a flat scrape table.

### Row count estimate — voters table

- COPY block starts at line **4639**, terminator `\.` at line **207577** → **≈ 202,938 rows** in the `voters` table within the dump.
- The 17.8M figure in the worker brief refers to the **total voter universe** (Nepal's registered electorate). The dump itself holds a **~1.1% sample**, not the full roll. The full data is *not* on disk in this dump — but the **scraper toolkit is functional and intended to fetch the full universe**, and `data/complete_scraping/` already holds **~10 GB** of additional batched JSON whose rows count toward the real PII exposure.
- Both `.sql` files are the same size; effectively one dump.

### `complete_scraping/*.json` file shape (sampled — `complete_batch_1_to_10_20251227_215651.json`)

Top-level: JSON array, one element per **voting location** (location_id, province, district, municipality, ward, voting_center, GPS, federal_constituency, provincial_constituency, **`voter_count`**, and **`voters: [...]`** — a nested array of individual voter rows). Per-voter fields:

```
voter_id, name, name_english, age, gender, address
```

Field mapping appears scrambled in the sample (numeric strings in `name`, age strings in `gender`, "महिला"/"पुरुष" in `address`) — likely a scraper column-order bug — but regardless, **these are individual-row records** and must be treated as PII.

So `complete_scraping/` is **per-voting-centre, with individual voter rows nested**. NOT pre-aggregated.

---

## 3. PII Enumeration

### `public.voters` (SQL dump) — every column is contextual PII

| Column | PII class |
|---|---|
| `name` | **Direct identifier** |
| `voter_no` | **Direct identifier** (national voter ID) |
| `age` | Quasi-identifier |
| `gender` | Quasi-identifier |
| `spouse` | **Relational PII** (links a second person) |
| `parent` | **Relational PII** (links a third person) |
| `detail` | Free-text — unknown contents, assume PII |
| `province`, `district`, `gapa`, `ward`, `centre` | Geographic quasi-identifier — at ward+centre level, k-anonymity is low |
| `sn` | Within-centre serial; not PII alone |

Combination of (ward, centre, age, gender, parent-name) is near-uniquely identifying. **The whole table is PII.**

### `complete_scraping/*.json` — every nested `voters[*]` object is PII

| Field | PII class |
|---|---|
| `voter_id` | Direct identifier (per-centre serial; in combination with centre → unique) |
| `name` / `name_english` | Direct identifier |
| `age` | Quasi-identifier |
| `gender` | Quasi-identifier |
| `address` | Quasi-identifier / direct (depending on actual contents) |
| Parent record's `voting_center_id`, `municipality_id`, `district_id`, `province_id` | Geographic |
| Parent record's `voting_center_lat`/`lng` | **Precise geo-coordinates** of where the voter votes (high-resolution quasi-PII) |

### `voter_scraping/*.json` — same shape, assume same PII set.

### Non-PII derivatives confirmed safe

- `constituency_mapping/*.json` — no per-voter rows; only `voter_count` aggregate per location_id.
- All `census_2021_*` tables — pre-tabulated census from NSO.
- All `election_results_*`, `local_elections_*`, `polling_stations`, `population_projection_*`, `vote_transfer_matrix`, `party_vote_flow_analysis*` — aggregates.

---

## 4. Provenance

- **Origin:** Government of Nepal Election Commission — `https://voterlist.election.gov.np/view_ward.php`.
- **Method:** Async HTTPS POST scrape (aiohttp + BeautifulSoup) per `SCRAPING_COMPLETE.md` and `SCRAPING_PROGRESS.md`. ~3–5 locations/sec, 10 concurrent connections, 100/batch.
- **Acquisition date:** Initial constituency pass Dec 27 2024; voter rows scraped late Dec 2024; DB dumped 2025-11-11 08:58 / 09:03.
- **Storage at acquisition:** Local Postgres DB named `voters_db`.
- **Auditor of this DB ≠ Nepal Ledger team** in any verified way — the scraper appears to predate the project and was inherited.

### Continuity / archival risk

- The Election Commission website may change schema or remove public-list access at any time. Dump is therefore *valuable* as a historical snapshot — but it does not have a publishable provenance chain (no ToS check on record, no notice to data subjects).
- Source Registry: **the voter list site is NOT yet registered** under `docs/SOURCE_REGISTRY.md`. Any aggregate ingest must add a registry entry first per doctrine.

---

## 5. License & Ethical Considerations

- **Terms of use:** The Election Commission's voter-search page is *technically* a public-facing lookup (one ward at a time), but bulk scraping was performed without explicit ToS review. Bulk extraction + redistribution materially exceeds the disclosed lookup purpose.
- **Re-publishing individual rows:** Almost certainly impermissible — would re-identify Nepali citizens at ward+centre granularity. **Hard no.**
- **Re-publishing aggregates:** Voter counts by polling station / ward / age-band / sex are arguably derivable from a public source and equivalent in granularity to what the EC itself publishes. Re-publishing **k-anonymized aggregates** (e.g., suppress any cell where count < 10) is the only ethically defensible output.
- **Nepal's data-protection regime:** The Individual Privacy Act 2075 (2018) defines personal information broadly and restricts processing without consent or lawful basis. Bulk voter-roll analysis for journalism is a grey area — defensible for aggregate statistics, not for individual disclosure.
- **Journalistic public-interest test:** Nepal Ledger's mission ("does Nepal's money become wealth?") does not require individual voter records. The headline questions answerable from this corpus — turnout patterns, electoral geography, polling-station distribution — are ALL answerable from aggregates.

---

## 6. Risk & Credential Assessment

### Credential leak risk

- `.env` file at `Financial Data/Voter DB scrape/.env` exists, **122 bytes**, NOT read by this auditor. Catch-all `.env*` rule in repo `.gitignore` (verified line: `.env*` with `!.env.example` exception) means it will be ignored by git — but **the file is sitting in a tracked folder path**, so it is excluded only because the catch-all matches, not because the folder is excluded. Recommend explicit reinforcement: add `Financial Data/Voter DB scrape/.env` to a `.gitignore`-adjacent enforcement check, OR move the file outside the repo tree entirely.
- **`git log --all -- Financial Data/Voter DB scrape/.env` should be run to confirm the file was never historically committed.** Not done in this audit — flag for Mother.
- SQL dump credential scan: the dump is plain pg_dump output (no embedded passwords, no `\connect` with creds visible in the schema-prelude region). Dumps in pg_dump format do not embed connection credentials. Considered low-risk for credential leakage.

### Dataset-on-disk risk

- ~11 GB of PII sits unencrypted in a project subdirectory.
- The folder `Financial Data/` should be confirmed to be in `.gitignore` (the `.gitignore` excerpt shows `source-data/` excluded but **does not show `Financial Data/`** in the snippet read). **Action item:** verify `Financial Data/` is git-ignored OR move dumps + scraped JSON to a path that IS ignored (e.g., a top-level `source-data/` or out-of-repo `~/data/`).
- Backup hygiene: byte-identical duplicate dump should be deleted to halve the on-disk footprint and reduce accidental-leak surface.

---

## 7. Handling Verdict and Recommendation

### Decision: **Option B — ingest only pre-aggregated, k-anonymized derivatives. No individual records ever leave local disk.**

Concretely:

1. **Supabase / production DB receives:** ONLY counts. Allowed shape examples:
   - `voters_by_centre`: (province, district, gapa, ward, centre_name, voter_count_total, voter_count_male, voter_count_female).
   - `voters_by_age_band`: (province, district, age_band_5y, count) — *suppress any cell where count < 10*.
   - `polling_station_geo`: (centre_id, lat, lng, federal_constituency, provincial_constituency) — geo of *centres*, not of individuals.
2. **The SQL dumps + `complete_scraping/*.json` + `voter_scraping/*.json` stay local-only.** Never copied to Supabase, never committed, never uploaded to any cloud service. Aggregation is done on a local Postgres restored from the dump, the aggregate output (likely <10 MB total) is what gets registered in the Fact Ledger.
3. **The aggregation pipeline must live in `scripts/` under the repo and be reviewable**, but the input directory and output directory paths must be configurable (so the pipeline runs against an out-of-repo data dir).
4. **Source Registry entry first.** Per doctrine, no ingest until `docs/sources/ec-voter-list.md` (or similar) is registered with provenance metadata, license stance ("Public source page; bulk extraction predates project; aggregate-only re-publication"), and confidence band.
5. **ADR required** documenting why this dataset is treated specially (PII gate). Suggest ADR-0008 or next available number: "Voter-list corpus: aggregate-only ingest with k-anonymity ≥ 10".

### Why not A (stay entirely off Supabase)?

A is *safer* but throws away genuine journalistic value (turnout patterns, polling-station density vs. census population, geographic constituency analysis). Option B retains that value at no PII cost.

### Why not C (RLS-isolated PII tables on Supabase)?

C is wrong on three grounds: (i) doctrine ADR-0004 keeps us on Supabase free-tier Year 1 — 11 GB of PII would blow the quota; (ii) RLS protects against *application reads*, not against *ops/admin reads or breach* — Supabase staff can still see the rows; (iii) we have **zero business need** for individual rows. Don't store what you don't need.

### Immediate follow-ups (for Mother, not for this audit)

- [ ] Confirm `Financial Data/` is gitignored OR move corpus out of repo tree.
- [ ] Delete byte-identical duplicate dump.
- [ ] Run `git log --all -- "Financial Data/Voter DB scrape/.env"` to confirm `.env` was never committed.
- [ ] Add Source Registry entry for `voterlist.election.gov.np`.
- [ ] Author ADR for aggregate-only voter ingest policy.
- [ ] Draft aggregation SQL (centre/ward-level counts with k≥10 suppression) under `scripts/voter-aggregates/`.

---

**Auditor confidence:** Medium-high. The dump schema and scraped JSON shape are sampled rather than fully parsed; row counts are line-count estimates not true `SELECT COUNT(*)`. No actual PII values are reproduced in this document.
