# Pre-Ingest Data Audit — Constituency Mapping Corpus

**Auditor:** Worker κ2 (kappa-two)
**Date:** 2026-05-14
**Doctrine:** [docs/PRE_INGEST_AUDIT.md](../PRE_INGEST_AUDIT.md) (committed on parallel branch `docs/audit-census-2021`, sha `a05b129`; referenced here pre-merge)
**Dataset ID:** `constituency-mapping`
**Branch:** `docs/audit-constituency`

Two folders share the "Constituency" name and were inspected together because they document the same conceptual object — Nepal's federal electoral geography — through different artefacts:

- `Financial Data/Constituency/` (25 files; structured tables + parser droppings)
- `Financial Data/Administrative Division/Constituency/` (32 files; scrape outputs + scripts)

The canonical 753-row local-level reference table at `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx` is used as ground truth for completeness checks but is NOT under audit here.

---

## 1. File inventory

### 1a. `Financial Data/Constituency/` (25 entries)

| File | Bytes | Rows | Format | Inferred purpose |
|------|------:|-----:|---|---|
| `Constituency_Table.csv` | 29,724 | 632 | CSV (UTF-8) | **165 federal constituencies → municipality + ward composition** |
| `Constituency table.txt` | 4,650 | 166 | TSV (Wikipedia copy-paste) | 165-constituency roster with 2022 electorate counts |
| `Constituency Narrative.txt` | 27,739 | 339 | Prose | Per-constituency prose descriptions (reference, not data) |
| `Combined_Constituency_Master_Table.csv` | 24,361 | 460 | CSV (latin-1) | Partial local-level catalog: Name/Nepali/Province/District/Pop2021/Area/Wards. **76 districts, 460 rows — NOT 753, NOT 165.** Header malformed (first data row is the header). |
| `Final_Election_Table.csv` | 1,742,952 | 10,747 | CSV (UTF-8) | Per-polling-station table for **seat 1 of each district ONLY** — 75 districts × seat 1; not the full 165-constituency electoral coverage |
| `Province to Election booth table.txt` | 2,026,986 | 11,555 | Space-delimited Devanagari | Source of `Final_Election_Table.csv`. Columns: `प्रदेश जिल्ला गाउँपालिका/नगरपालिका वडा मतदान स्थल`. Polling-station list. |
| `Unmatched_Records.csv` | 26,822 | 261 | CSV | Parser dropout: District_Nepali / District_English / Municipality / Ward / Province_Nepali |
| `merge_data.py` | 31,393 | — | Python | Prior-owner parser (DO NOT execute) |
| `__pycache__/` | — | — | dir | Stale Python bytecode |
| `count_analysis.txt`, `output.txt`, `parser_debug.txt`, `prefix_counts.txt`, `rejected_analysis.txt`, `sample_unmatched.txt`, `skipped_samples.txt`, `still_skipped.txt`, `truncated_samples.txt`, `unmatched_districts.txt`, `unmatched_districts2.txt`, `unmatched_districts3.txt`, `unmatched_final.txt`, `unmatched_samples.txt`, `no_ward_samples.txt`, `final_skipped.txt` | <6 KB each | — | Text | Parser logs / debug droppings — DISCARD |

### 1b. `Financial Data/Administrative Division/Constituency/` (32 entries)

| File | Bytes / Rows | Format | Inferred purpose |
|------|---|---|---|
| `nepal_admin_hierarchy_20251225_173346.json` | 953 rows | JSON | **Sample scrape (953 rows)** with voting-center lat/lng, federal_constituency, provincial_constituency, total_voters |
| `nepal_admin_hierarchy_20251225_173346.xlsx` | — | XLSX | Same content as above, Excel form |
| `province_1..7_20251225_194043.json` | 600 / 650 / 500 / 550 / 600 / 681 / 456 = 4,037 rows | JSON | Per-province scrape with `federal_constituency`, `provincial_constituency`, `municipality_type`. **Incomplete.** |
| `province_6_..csv`, `province_7_..csv` | — | CSV | Province 6/7 in CSV form (subset of JSON) |
| `scrape_*.py`, `extract_*.py`, `test_*.py`, `discover_*.py`, `check_*.py`, `show_*.py` | (16 scripts) | Python | Prior-owner scrape rigging (DO NOT execute) |
| `scrape_progress.json`, `test_results_*.xlsx`, `test_submit_v2_*.xlsx`, `results_page_174200.png`, `page_screenshot.png` | — | Misc | Scrape artefacts — DISCARD |

No README, no `*_metadata.json` in either folder.

---

## 2. Per-file shape probe (key candidates)

### `Constituency_Table.csv` (CSV, 632 data rows, 4 cols)

Columns: `Constituency`, `Area Name`, `Area Type`, `Wards`

- `Constituency` (string, format `"<District> <SeatNo>"`, e.g. `Jhapa 1`): **165 unique values** spanning **77 districts**.
- `Area Type` distribution: 279 Rural Municipality, 276 Municipality, 35 District, 21 Metropolitan City, 21 Sub-metropolitan City.
- `Wards` examples: `"All"`, `"9, 10"`, `"4, 5, 6, 7"`, `"All (Entire District)"`.
- Coverage: all 165 (district, seat_no) tuples present; max seat per district = 10 (Kathmandu).
- District-row pattern: 35 rows have `Area Type = District` and `Wards = "All (Entire District)"` — these are seat-1 of small districts that span the whole district.
- Notnull: all 4 cols 100% populated.

### `Constituency table.txt` (Wikipedia roster, 165 rows)

Columns: `No., Province, District, Constituency, Electorate (2022)`. Lines 4+: tab-separated. Electorate values present (e.g. Taplejung 1 = 88,285). 165 constituencies enumerated with district + sequential federal No. 1–165.

### `Final_Election_Table.csv` (10,747 rows, 7 cols)

Columns: `Constituency No, Constituency Name, Province, District, Ward, Rural Municipality/Municipality, Election Location`.

- 100% notnull on every column.
- **`Constituency Name` always ends in " 1"** — i.e. **every row is for seat #1 of its district**. This is NOT 165 constituencies; it is **75 of 77 districts × seat 1 only**.
- Unique `Constituency No`: 75 (range 1–163, federal-sequential numbering of seat 1s).
- Unique districts: 75 (missing 2 of 77 — likely Manang + Mustang or similar small districts that map to the booth-table parser's failure list).
- Unique municipalities: 741. Mojibake (encoding damage) is visible in muni and location columns (e.g. `गाउँपाललका` ← `गाउँपालिका`).
- Granularity: per (constituency_no, municipality, ward) — i.e. **polling-station level**, with multiple rows per ward when there are multiple booths.

### `Combined_Constituency_Master_Table.csv` (460 rows, 7 cols, latin-1 with mojibake)

Columns (after fixing malformed header): `Name, Nepali, Province, District, Population_2021, Area_KM2, Wards`.

- Despite the filename it is **NOT a constituency master** — it is a partial **local-level (municipality) catalog**: 460 munis across 76 districts.
- `Wards` populated on only 42/460 rows (9%); other columns 100%.
- No `constituency_no` column at all.
- Province values: `Koshi, Bagmati, Lumbini, Madhesh, Gandaki, Karnali, Sudupashim`. Sudurpashchim is misspelled "Sudupashim".

### Province `*.json` scrapes (4,037 rows total)

Per-row keys: `province_id, province_name, district_id, district_name, municipality_id, municipality_name, municipality_type, ward_id, ward_name, federal_constituency` (Devanagari). No lat/lng. **52 of 77 districts**, 450 of ~753 munis, 108 of 165 (district, federal_constituency) tuples.

### `nepal_admin_hierarchy_20251225_173346.json` (953 rows)

Same keys as province scrape PLUS `voting_center_id, voting_center_name, total_voters, voting_center_lat, voting_center_lng, provincial_constituency`. 953 rows ≈ ward-level (one row per ward, with one representative voting center). Useful as a **lat/lng enrichment side-table** but not a complete electoral map.

### `Province to Election booth table.txt` (11,555 lines)

Space-separated Devanagari header: `प्रदेश जिल्ला गाउँपालिका/नगरपालिका वडा मतदान स्थल`. ~11,554 polling-station rows. **Encoding shows the same character-substitution corruption** as `Final_Election_Table.csv` (e.g. `पालिका` → `पाललका`); this is the upstream source that the prior owner's `merge_data.py` parsed into `Final_Election_Table.csv`. Booth names contain commas, so a clean re-parse needs a Devanagari-aware tokenizer.

---

## 3. Variant comparison

Three candidate files claim "constituency table" status:

| Property | `Constituency_Table.csv` | `Combined_Constituency_Master_Table.csv` | `Final_Election_Table.csv` |
|---|---|---|---|
| Row count | 632 | 460 | 10,747 |
| Granularity | Constituency × (muni/ward) composition | Municipality (partial) | Polling station (seat 1 only) |
| Districts covered | **77** | 76 | 75 |
| Constituency seats | **165** | 0 (no col) | 75 (seat 1 only) |
| Has ward composition? | **Yes (string list)** | Mostly missing (42/460) | No (single ward per row) |
| Has constituency_no? | Derivable (split string) | No | Yes (federal_no) |
| Encoding clean? | **Yes** | latin-1 mojibake | UTF-8 with character corruption |
| Notnull integrity | 100% | 91% missing on Wards | 100% |

**`Constituency_Table.csv` is unambiguously the most complete and least corrupted artefact for the 165-constituency entity catalog.** The other two cover overlapping but partial subsets and have data-quality problems.

### Cross-folder variant: province `*.json` scrapes vs `Constituency_Table.csv`

The province scrapes provide `federal_constituency` AND `provincial_constituency` (the latter NOT present in `Constituency_Table.csv`), but only on 52/77 districts. They are NOT a substitute for `Constituency_Table.csv` for the federal map; they ARE the only source so far for **provincial-assembly** constituencies and `municipality_id`/`ward_id` numeric keys.

---

## 4. Authority assessment

| Field needed downstream | Authoritative source | Notes |
|---|---|---|
| 165 federal constituencies (list with district + district-internal seat #) | **`Constituency_Table.csv`** + cross-check with **`Constituency table.txt`** for the federal sequential No. (1–165) and 2022 electorate | Use the wiki TSV as the ID/electorate column source; use the CSV for the muni/ward composition. |
| Constituency → (municipality, ward-list) composition | **`Constituency_Table.csv`** | 597 muni-level rows + 35 whole-district rows; `Wards` is a comma-joined string that must be parsed (`"4, 5, 6, 7"`, `"All"`). |
| Local-level (753 munis) base catalog | NOT in this folder — `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx` (753 munis with 8-digit `Code`) | This audit confirms the previous admin-hierarchy verdict. |
| Polling-station / booth granularity | **`Province to Election booth table.txt`** (full 11,555 booths) — re-parse from source; `Final_Election_Table.csv` is the prior-owner's PARTIAL parse (seat 1 only) and should NOT be used directly. | Re-parse needed for full coverage. |
| Voting-center lat/lng | `nepal_admin_hierarchy_20251225_173346.json` (953 rows) | Sample only; not complete. Use as enrichment, not authority. |
| Provincial-assembly constituencies | **No clean source.** Province `*.json` scrapes hold `provincial_constituency` but cover only 52/77 districts. | **Gap.** Needs a follow-up scrape from `election.gov.np` or similar. |
| Municipality type (Rural / Municipality / Sub-Metro / Metro) | **Fiscal Transfer XLSX** `Local Level Type` column | Authoritative; NOT the province scrape (incomplete) and NOT the `_FINAL.csv` admin-hierarchy (broken per the cautionary case in PRE_INGEST_AUDIT.md). |

### JOIN feasibility against canonical 753 local levels

**There is no shared key.** Join must be by `(district_en, local_level_en)` after suffix-stripping. Empirical test:

- Canon munis (suffix-stripped, lowercased): 724 unique names
- `Constituency_Table.csv` munis (lowercased): 468 unique non-District names
- Overlap: **375** (~80% of CT's muni names)
- ~93 munis in CT do not match canon — most are spelling variants (`Anbukhaireni` vs canon `Aanbu Khaireni`, etc.).

**Join recommendation:** normalize both sides with a Devanagari + English fuzzy matcher; reconcile the 93 unmatched names against canon manually; preserve `(district_en, seat_no)` as the constituency PK and `(district_en, muni_en_normalized)` as the join key. **No federal 8-digit code in `Constituency_Table.csv`**, so federal Code (canon's `Code` column) must be brought across by the join, not by primary key.

---

## 5. Gap surface

| Gap | Severity | Mitigation |
|---|---|---|
| `Constituency_Table.csv` lacks the federal-sequential constituency number (1–165) | Low | Pull No. 1–165 from `Constituency table.txt` (wiki TSV); join on `(district, seat_no)`. |
| `Constituency_Table.csv` lacks 2022 electorate per constituency | Low | Same: pull from `Constituency table.txt`. |
| ~93 muni name spelling variants vs canonical 753 | Medium | Devanagari normalizer + manual reconciliation table; estimate <1 day of work. |
| Provincial-assembly constituencies not covered for 25/77 districts | High (deferred) | Queue a fresh scrape of `election.gov.np` or `nepalinconstitution.org` after federal map ships. |
| Full polling-station map for all 165 constituencies (only seat 1 covered in `Final_Election_Table.csv`) | High (deferred) | Re-parse `Province to Election booth table.txt` from source with a clean Devanagari tokenizer; expect ~22k-30k booths total. The 10,747-row file represents <40% of booths. |
| Voting-center lat/lng for all booths | Medium (deferred) | Only 953 booths have lat/lng. Need a follow-up scrape (Election Commission has these in their map UI). |
| Districts missing from booth table: 2 of 77 (likely Manang/Mustang or similar) | Low | Manual fill from EC website for the missing district(s). |

---

## 6. Authoritative decision

**Canonical sources (use these, brand them in `source_registry`):**

1. **`Financial Data/Constituency/Constituency_Table.csv`** — authoritative for the **165 federal constituencies and their (municipality, ward-list) composition**. PK: `(district_en, seat_no)` derived from `Constituency` column.
2. **`Financial Data/Constituency/Constituency table.txt`** — authoritative for the **federal sequential No. (1–165) and 2022 electorate**. JOIN to #1 on `(district_en, seat_no)`.
3. **`Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx`** — authoritative for the **753 local levels, 8-digit federal `Code`, and `Local Level Type`**. Already canonical per the admin-hierarchy verdict (PRE_INGEST_AUDIT.md cautionary case). Use this to enrich #1 with federal codes and municipality types.
4. **`Financial Data/Constituency/Constituency Narrative.txt`** — narrative-quality REFERENCE for editorial use; do NOT ingest as structured data, but cite when stories need a constituency description.

**Provisional / use-only-with-caveat:**

5. `Financial Data/Administrative Division/Constituency/nepal_admin_hierarchy_20251225_173346.json` — keep as **lat/lng enrichment side-table** for the 953 voting centers it covers. Tag as "partial, sample-only".

**Discarded (do NOT ingest):**

- `Combined_Constituency_Master_Table.csv` — partial 460-row municipality catalog with malformed header, mojibake, no constituency column, no federal code. Superseded by Fiscal Transfer XLSX.
- `Final_Election_Table.csv` — partial polling-station table covering only seat 1 of 75 districts; encoding corruption. The upstream `Province to Election booth table.txt` is preferable, but re-parse is itself **DEFERRED** until polling-station data is on the roadmap.
- `Unmatched_Records.csv` — prior parser's reject pile.
- `Financial Data/Administrative Division/Constituency/province_[1-7]_*.json` (4,037 rows total) — covers only **52/77 districts, 450/753 munis, 108/165 federal constituencies**. Confirmed incomplete; superseded by `Constituency_Table.csv` for the constituency map.
- `Financial Data/Administrative Division/Constituency/province_6_*.csv`, `province_7_*.csv` — CSV duplicates of subset of above.
- `nepal_admin_hierarchy_20251225_173346.xlsx` — XLSX duplicate of the JSON.
- All `*.py` scripts in both folders — prior-owner rigging; do NOT execute. Keep for archeology; do not commit to `scrapers/`.
- All `__pycache__` directories — bytecode.
- All `*_samples.txt`, `unmatched_*.txt`, `truncated_*.txt`, `still_skipped.txt`, `final_skipped.txt`, `count_analysis.txt`, `output.txt`, `parser_debug.txt`, `prefix_counts.txt`, `rejected_analysis.txt`, `no_ward_samples.txt`, `scrape_progress.json`, `test_results_*.xlsx`, `test_submit_v2_*.xlsx`, `page_screenshot.png`, `results_page_174200.png` — parser droppings / debug.

**Gaps explicitly accepted as known limitations (queue follow-up scrapes; do not block ingest):**

- No provincial-assembly constituency map (gap on 25/77 districts).
- No full polling-station map (only ~40% of booths parsed; seat-1-only).
- No full voting-center lat/lng map (only 953 booths geocoded).

**Ingest brief NOT to be written by this worker.** Mother to draft after user sign-off.

---

## 7. PII & licensing check

- **PII:** `nepal_admin_hierarchy_20251225_173346.json` contains voting-center coordinates and total_voter counts per ward — public-record electoral data, not PII. No personal names, no addresses, no phone numbers, no IDs anywhere in the corpus. Polling-station names refer to buildings (schools, ward offices), not persons.
- **License:** all source data is published by the Election Commission of Nepal (EC) and Nepal government — public-domain / gov-open. The Wikipedia-derived `Constituency table.txt` is CC BY-SA. Cite both: EC for the booth + composition data; Wikipedia (and underlying EC publication date) for the electorate counts.
- **Credentials:** scanned all `*.py` files in `Financial Data/Administrative Division/Constituency/` — no API keys, no embedded passwords, no `.env` references. Scripts use HTTP scraping with public endpoints.
- **Verdict:** **safe to cross into Supabase**. Citation policy: `source = "Election Commission of Nepal, 2022 election"`; lat/lng provenance: "EC voting center registry, scraped 2025-12-25".

---

## Cross-references

- [docs/PRE_INGEST_AUDIT.md](../PRE_INGEST_AUDIT.md) — doctrine (will be on `main` after `docs/audit-census-2021` merges; until then see commit `a05b129`)
- [docs/CONTEXT_RULES.md](../CONTEXT_RULES.md) — Rule 7 (Pre-Ingest Audit)
- [docs/SOURCE_REGISTRY.md](../SOURCE_REGISTRY.md) — to be updated with the four canonical sources above
- The cautionary case (admin-hierarchy ingest failure) — referenced in PRE_INGEST_AUDIT.md §"The cautionary case"; this audit re-validates that the Fiscal Transfer XLSX, NOT any file under `Administrative Division/`, is the 753-canon.
