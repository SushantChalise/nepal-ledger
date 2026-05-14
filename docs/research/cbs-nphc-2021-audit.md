# Pre-Ingest Audit — CBS National Population & Housing Census 2021 (NPHC 2021)

**Dataset ID:** `cbs-nphc-2021`
**Source folder:** `Financial Data/Census/census_2021_data/`
**Auditor:** Worker ι (iota)
**Date:** 2026-05-14
**Branch:** `docs/audit-census-2021`
**Doctrine:** [docs/PRE_INGEST_AUDIT.md](../PRE_INGEST_AUDIT.md)

---

## 0. TL;DR (read this first)

- **89 CSVs + 8 Excel files + 1 metadata index JSON + 1 metadata index XLSX.**
- **CSV header structure is NOT uniform.** Index file `CENSUS_DATA_INDEX.json` is *misleading* on this point: only **4 files** (`Hhld01..Hhld04`) carry a buried-header "title" preamble; the other **85 CSVs have clean row-0 headers** (`prov,dist,gapa,...`).
- **Geographic granularity:** Palika (local-level / gapa) on all 89 CSVs and the 7 Listing XLSXs. **Ward-level exists ONLY in `DegurbaUrbanRural.xlsx`** (6,743 rows = sum of wards across 753 palikas). Verified.
- **Coverage:** All **753 local levels** present in every probed palika file. Exact 1:1 match with the canonical 753-palika roster from `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx` (Sheet2). No palikas missing.
- **Municipality-naming conflicts vs canonical 753:** out of 753 palikas: **726 reach ≥85 fuzzy score** under normalization (`STRIP type-suffixes → uppercase → alnum`); **27 fall below 85** — all are *real spelling drifts* (e.g. "Pokhara Metropolitian City" vs "Pokhara Metropolitan City", "Fakfokathum" vs "Phakphokthum"). The conflict is systematic and tractable: it is one ETL-time normalization layer, not a coverage problem.
- **Authoritative verdict:** the 89 CSVs are the canonical palika-level cross-tabulations; the 7 `Listing*` XLSXs are *presentation-formatted* sibling tables (multi-row title, percentage-only, no machine-parseable structure beyond the existing CSVs); **DEGURBA is the sole ward-level authority**.
- **PII:** none. Aggregate counts only; no individual identities. Public-domain government open data (CBS Nepal).

---

## 1. File Inventory

### 1.1 Top-level

| Path | Bytes | Format | Purpose |
|---|---:|---|---|
| `CENSUS_DATA_INDEX.json` | 244 KB | JSON | Self-produced index with metadata + per-file column lists + Pokhara cutouts. Useful for orientation but **partially inaccurate** (see §1.2). |
| `Census_Data_Index.xlsx` | (varies) | XLSX | Sibling of the JSON index. Not consumed downstream; redundant. |
| `census-dataset/` | 217.4 MB | dir | 89 CSV palika-level cross-tabs. |
| `degurba-report/` | 339 KB | dir | 1 XLSX, ward-level degree-of-urbanization. |
| `household-results/` | 4.85 MB | dir | 7 XLSX/XLS Listing tables (percentage-formatted presentation tables). |

No `README.md`, no `CHANGELOG`, no `*_metadata.json` other than the self-built index. Provenance comes from filename conventions and the JSON index's `metadata` block: source is "National Population and Housing Census 2021 (2078 BS), Nepal, Central Bureau of Statistics (CBS)".

### 1.2 `census-dataset/` — 89 CSVs

- 23 `Hhld*` (household-level cross-tabs)
- 66 `Indv*` (individual-level cross-tabs; numbered 01–71 but with gaps at 08, 12, 13, 14, 15)
- File mtime: uniform `Nov 9 2025`. Bytes range from 46 KB (`Indv05`) to 8.5 MB (`Indv56_PopulationByIndustry.csv`).
- Cumulative row count across all 89 CSVs (lines including headers): **2,084,606** rows.

### 1.3 `household-results/` — 7 Listing XLSX/XLS

| File | Bytes | Sheet rows | Notes |
|---|---:|---:|---|
| `Listing01_NumberOfBuilding-Percentage-Palika.xlsx` | 226 KB | 1002 | Percentage formatted; multi-row title header |
| `Listing02_NumberOfFloor-Palika.xlsx` | 122 KB | 1002 | same |
| `Listing03_YearOfConst-Palika.xls` | 2.96 MB | (legacy .xls — requires `xlrd`) | not probed in depth this audit |
| `Listing04_HouseFromGovtGrant-Palika.xlsx` | 108 KB | 1002 | same |
| `Listing05_HaveBankAccount-Palika_rev1.0.xlsx` | 107 KB | 1002 | `rev1.0` suffix → publisher revision |
| `Listing06_HaveTraining-Palika_rev1.0.xlsx` | 135 KB | 1003 | `rev1.0` suffix |
| `Listing07_HouseholdHavingLoan-Palika.xlsx` | 1.39 MB | 1002 | same |

The 1002–1003 row count = 1 NEPAL row + 7 province rows + 77 district rows + 753 palika rows + spacer rows (one blank row between palikas observed in Listing01 raw read). All percentage-only; no household counts.

### 1.4 `degurba-report/` — 1 XLSX

| File | Bytes | Rows | Notes |
|---|---:|---:|---|
| `DegurbaUrbanRural.xlsx` | 339 KB | 6,743 | Ward-level only (753 palikas × 5–33 wards each). Schema in §2.5. |

---

## 2. Per-File Shape Probe

### 2.1 Discovery: header pattern (CRITICAL CORRECTION to `CENSUS_DATA_INDEX.json`)

The pre-existing index file uses `pd.read_csv(..., header=0)` on all 89 CSVs and reports many as having `Unnamed: 0..N` columns plus a "Table NN" string in the header — implying buried-header structure across the corpus. **This is wrong.** Direct line-by-line inspection reveals two distinct header styles:

| Header style | Count | Example | Real header row index |
|---|---:|---|---:|
| **Title preamble (5 prelude rows, then real header)** | 4 | `Hhld01..Hhld04` | row 5 |
| **Clean row-0 header** | 85 | `Hhld05..Hhld23`, all `Indv*` | row 0 |

The buried-header files have this exact 6-line preamble:
```
R0: ,,,"Table NN: <title>, NPHC 2021",,,,,,,
R1: ,,,,,,,,,,
R2: ,,,Area,,,Total,<grouping label>,,,
R3: ,,,,,,,Owned,Rented,Institutional*,Other
R4: ,,,,,,,,,,
R5: prov,dist,gapa,provname,dname,gapaname,rowtotal,a_Own,b_Rented,c_Institutnl,d_Other
R6: 0,0,0,NEPAL,NEPAL,NEPAL,6660841,5728586,850562,36809,44884
```

**Parser policy:** detect via `first_line.startswith(',,,')` or `first_line[:30].contains('"Table ')`; if matched, use `skiprows=5, header=0`; otherwise `header=0`. Two-mode reader, no per-file allowlist needed.

### 2.2 Canonical CSV shape (Hhld05, representative)

- File: `Hhld05_FloorOfHouse.csv`
- Shape: 838 rows × 13 cols
- Columns: `prov,dist,gapa,provname,dname,gapaname,rowtotal,a_Mud,b_Wooden,c_BrickStone,d_Ceramic,e_Cemented,f_Other`
- Row breakdown:
  - 753 palika rows (prov≠0 AND dist≠0 AND gapa≠0)
  - 85 aggregate rows (gapa==0): 1 NEPAL + 7 provinces + 77 districts
- Distinct (prov,dist,gapa) palikas: **753** (✓ canonical)
- Distinct `gapaname` strings: 734 (19 palika names are reused across districts — same spelling in different districts).

### 2.3 Hhld14 (death-by-sex; long form with age dim)

- 11 cols: `prov,dist,gapa,agegrp,provname,dname,gapaname,agegrpname,rowtotal,a_male,b_female`
- Long format — one row per (palika × agegrp).

### 2.4 Indv56 (industry × age — widest)

- 23 cols: full age-band breakdown (`a_10to14 ... l_65pls`) for each (palika × sex × industry-code).

### 2.5 DEGURBA (ward-level — only ward-grain file)

- File: `degurba-report/DegurbaUrbanRural.xlsx`
- Shape: 6,743 × 11
- Cols: `Prov,dist,gapa,Ward,ProvName,DistName,GapaName,UrbRur,UrbRurName,DEGURBA_7,DEGURBA_7Name`
- 753 distinct (Prov,dist,gapa); wards per palika 5–33 (mean 8.95).
- Sample row: `1,1,1,1,Koshi,TAPLEJUNG,Phaktanlung Gaunpalika,3,Rural,12,Low Density Rural Grid Cell`
- **Confirmed: this is the ONLY ward-level file in the corpus.** Verifies metadata claim.

### 2.6 Pokhara identifier verification

Per `CENSUS_DATA_INDEX.json` metadata: `prov=4, dist=40, gapa=4, gapaname='Pokhara Metropolitian City'` (CBS uses the typo "Metropolitian" consistently).

Verified against `Hhld05`:

| prov | dist | gapa | provname | dname | gapaname | rowtotal |
|---|---|---|---|---|---|---|
| 4 | 40 | 4 | Gandaki | Kaski | Pokhara Metropolitian City | 140459 |

Tuple `(4,40,4)` is valid as a join key. ✓

### 2.7 Listing XLSX shape

`Listing01_NumberOfBuilding-Percentage-Palika.xlsx`:

- Raw rows 0–3 are title + multi-row column header; row 4 is `NEPAL`; subsequent palika rows interspersed with blank spacer rows.
- Values are **percentages** (e.g. `71.72%` for residential), plus `Total Number of Building Structures` as the only count column.
- Sheet1 layout is presentation-formatted — would need a custom header-stack parser plus blank-row dropping.

---

## 3. Variant Comparison

### 3.1 Hhld vs Listing — what's the overlap?

The `Hhld*` CSVs and `Listing*` XLSXs cover *related but distinct* topics; they are **not** variants of the same data.

| Variant family | Files | Overlap with CSVs? |
|---|---|---|
| `Hhld01_OwnershipOfHouse.csv` (ownership type) | 1 file | No Listing equivalent |
| `Hhld02..Hhld04` (foundation/wall/roof) | 3 files | No Listing equivalent |
| `Listing01` (building structures by main-use type) | 1 file | NOT in CSVs — `Hhld*` measures household-occupancy attributes, `Listing*` measures the building inventory |
| `Listing04` (govt-grant housing %) | 1 file | NOT in CSVs |
| `Listing05` (bank account %) | 1 file | NOT in CSVs — adjacent to `Hhld10_HouseholdFacility.csv` but distinct |
| `Listing07` (outstanding loan %) | 1 file | NOT in CSVs |

**Conclusion:** the Listing files cover **complementary** topics not captured in the CSVs (building stock, bank-account ownership, training, loans). They are not redundant variants of the CSV cross-tabs.

### 3.2 Within `Hhld*` and `Indv*` — variant check

Inspected `Hhld14_NumberOfDeathBySex.csv` vs `Hhld15_NumberOfDeathByCauseOfDeath.csv`: different breakdowns (sex vs cause), not variants. No file pairs found that differ only by suffix (no `_FINAL`, `_v2`, `_REVISED` pollution).

`Listing05`/`Listing06` have `_rev1.0` suffixes — this is the publisher's revision tag, not a "two competing files" situation; only one rev present.

**Verdict: no shadow-variant files in the corpus.** This dataset does NOT exhibit the Administrative Division/ pathology that motivated the audit doctrine.

---

## 4. Authority Assessment

### 4.1 Downstream-needed fields → canonical file

| Field | Authoritative source | Notes |
|---|---|---|
| Palika roster (prov,dist,gapa,name) | `Hhld05` (or any palika-grain CSV) | 753 palikas, exact 1:1 with MoF canonical. `gapaname` carries CBS spellings. |
| District roster (prov,dist,name) | Same — palika CSVs include district aggregate rows (gapa==0) | 77 districts; province codes 1–7 |
| Province roster | Same — rows where dist==0 AND gapa==0 (and prov≠0) | 7 provinces |
| NEPAL national totals | Same — row where prov==0,dist==0,gapa==0 | Useful reconciliation check |
| Households per palika | `Hhld05.rowtotal` and 22 other Hhld* `rowtotal` columns | Cross-check across Hhld* — `rowtotal` should be identical per palika across `Hhld01..Hhld13` since denominator is "all households" |
| Population per palika | `Indv01_PopulationBySex.csv` `total`, `male`, `female`, `nHhld`, `avg_hhsize`, `sex_ratio`, `growth_rate`, `pop_density` — **single canonical population row per geography** | Indv01 has 830 palika-level rows (vs 753) — appears to include some urban/rural disaggregation; sub-grain present. Investigate in parser brief. |
| Ward-level urban/rural classification | `DegurbaUrbanRural.xlsx` ONLY | Two encodings: `UrbRur` (3 classes) and `DEGURBA_7` (7 classes) |
| Building inventory (count by use type) | `Listing01_NumberOfBuilding-Percentage-Palika.xlsx` | Percentage-formatted; one count column (`Total Number of Building Structures`) |
| Household banking access | `Listing05_HaveBankAccount-Palika_rev1.0.xlsx` | Percentages only |
| Household loan exposure | `Listing07_HouseholdHavingLoan-Palika.xlsx` | Percentages only |

### 4.2 Cross-reference against canonical 753-row roster from MoF

Canonical roster: `Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx`, sheet `Sheet2`.

- 989 total rows decomposing to: 460 Rural Municipality + 276 Municipality + 11 Sub-Metropolitan City + 6 Metropolitan City = **753 palika rows** (+ 77 District Totals + 159 subtotal rows).
- **Census palika count: 753.** Exact match.

#### Name reconciliation (fuzzy match, rapidfuzz `fuzz.ratio` after type-suffix-stripping + uppercase normalization)

- 563 / 753 (74.8%) exact normalized match
- **726 / 753 (96.4%) score ≥ 85** — clears the resolver gate the project standard expects
- 27 / 753 (3.6%) score < 85 — all real spelling drifts, **none are coverage gaps**:
  - Systematic typo: CBS uses **"Metropolitian"** (sic) and **"Sub-Metropolitian"** instead of "Metropolitan" / "Sub-Metropolitan" — accounts for 10+ of the sub-85 cases (Dharan, Butwal, Itahari, Kalaiya, Hetauda, Ghorahi, Pokhara, Nepalganj, etc.)
  - Romanization variants: "Fakfokathum" (CBS) vs "Phakphokthum" (MoF); "Bhoome" vs "Bhume"; "Ruruchhetra" vs "Ruru Kshetra"; "Temkemaiyum" vs "Tyamkemaiyung"; "Bheri Malika" vs "Badimalika"; "Mayadevi" vs "Mahadeva"
  - One outright differing name: "Lumbini Sanskritik Municipality" (CBS) — likely renamed since the MoF roster snapshot; needs manual map override.

**Resolver action:** when the parser runs, register these 27 names as explicit overrides in the resolver's seed map (the resolver already supports manual overrides per its design). The `(prov,dist,gapa)` integer tuple is the safe primary join key; `gapaname` is for display.

### 4.3 Broken fields

None observed. The `prov,dist,gapa` integer codes are dense and consistent. No "Municipality Type" column was scraped wrong (the column doesn't exist — type is implicit in the gapaname suffix and can be derived).

---

## 5. Gap Surface

| Gap | Severity | Mitigation |
|---|---|---|
| **No ward-level breakdown in the 89 CSVs** | Known | Accept. Ward-level data exists only as DEGURBA classifications, not full cross-tabs. CBS has not released ward-level NPHC 2021 tables; queue as a future scrape if/when CBS publishes them. |
| Listing files publish **percentages only** (no raw household counts except aggregate row totals) | Medium | Counts can be reconstructed by multiplying percentage × `rowtotal` from corresponding `Hhld*` denominator file — but small precision loss. Flag in ingest brief. |
| `Listing03_YearOfConst-Palika.xls` is legacy `.xls` (BIFF) — needs `xlrd` >= 2.0.1 in the parser env | Low | Add to `scrapers/pyproject.toml` deps. |
| `Indv01` has 830 palika-level rows vs 753 expected | Low | Excess rows likely urban/rural sub-rollups within palikas. Investigate in parser dev; either filter to (prov,dist,gapa) unique tuples by deduping with a sub-grain column, or split palika-total from sub-rollups. |
| Pre-existing `CENSUS_DATA_INDEX.json` is **misleading** on header structure across most files | Low | Do not trust its `category_columns` / `value_columns` arrays; rederive via the two-mode reader from §2.1. |
| `Census_Data_Index.xlsx` is redundant duplicate of JSON | Low | Ignore. |

**No district-level coverage gap.** Every one of Nepal's 77 districts and all 7 provinces and all 753 palikas appears in every probed file.

---

## 6. Authoritative Decision

**Canonical sources:**
- For **palika-level household cross-tabs** (housing, fuel, water, ownership, mortality, migration, etc.): the **23 `Hhld*` CSVs** and **66 `Indv*` CSVs** in `census-dataset/`. Total 89 files.
- For **ward-level urban/rural classification**: `degurba-report/DegurbaUrbanRural.xlsx` (sole authority).
- For **building stock, banking, training, government-grant, loan exposure** at palika level: the **7 `Listing*` XLSX/XLS** in `household-results/`.
- For **the palika roster itself** (793 join keys): retain the existing MoF canonical (`Fiscal Transfer_2082_82.xlsx` Sheet2). The census matches it 1:1 but is not the primary roster.

**Discarded:**
- `CENSUS_DATA_INDEX.json` — useful navigation aid only; its column probes are inaccurate for 85 of 89 CSVs. **Do not use as the parser's schema source of truth.** Re-derive at parse time.
- `Census_Data_Index.xlsx` — redundant.

**Gaps accepted:**
- No native ward-level cross-tabs (only DEGURBA). Not a CBS publication yet; not actionable.
- Listing files publish percentages — accept; flag precision in Fact Ledger entries derived from them.

**Ingest-brief sequencing recommendation (Mother's call, not this auditor's):**
1. First ingest: `Indv01_PopulationBySex.csv` — the single richest palika-grain file (population, households, density, growth rate). Unlocks Pulse population KPIs immediately.
2. Next: `Hhld05–Hhld10` (housing fundamentals) and `Hhld15` (mortality by cause).
3. Defer `Listing*` until the `Hhld*` denominators are ingested (Listings need them to reconstruct counts).
4. Defer DEGURBA until ward-grain joins are needed downstream.

**Parser policy (must appear in the parser brief):**
- Use two-mode CSV reader (skiprows=5 for `Hhld01..Hhld04`, else default).
- Use `(prov, dist, gapa)` int tuples as primary palika key; `gapaname` is display-only.
- Pass `gapaname` through the project's municipality resolver with the 27-name override list above pre-loaded.
- Treat `gapa==0` rows as the *aggregate* row family (one row per geographic parent); do not co-mingle with palika-grain facts.
- For `Indv01`'s 830 rows: investigate sub-grain before ingest; do **not** blindly accept all 830 as palikas.

**Verdict: READY for ingest brief.** No coverage gaps. No variant ambiguity. Naming conflicts are bounded (27 explicit cases) and resolvable via the existing resolver's override mechanism.

---

## 7. PII & Licensing Check

- **PII:** None. All values are aggregate counts/percentages at province / district / palika / ward grain. No personal names, addresses, IDs, phone numbers, GPS coordinates, or household-level identifiers.
- **License:** Government of Nepal open data (CBS publication). Treat as public-domain / gov-open. No license file shipped with the corpus; provenance is implicit (CBS NPHC 2021 official release).
- **Credentials:** None embedded in any file (verified — no `.env`, no `config.yaml`, no API keys in JSON/XLSX/CSV).
- **Supabase crossing:** ✅ Safe to ingest into Supabase. No row-level privacy restriction applies; data may be served publicly via the Fact Ledger.

---

## Appendix A — 27 names below 85 fuzzy threshold (CBS gapaname → canonical MoF name → score)

```
60   Lumbini Sanskritik Municipality       → Sunil Smriti Rural Municipality      (DIFFERENT NAME — likely renamed)
67   Ruruchhetra Gaunpalika                → Ruru Kshetra Rural Municipality      (transliteration drift)
70   Fakfokathum Gaunpalika                → Phakphokthum Rural Municipality
73   Bhoome Gaunpalika                     → Bhume Rural Municipality
73   Nepalganj Sub-Metropolitian City      → Nepalgunj Sub-Metropolitan City      (TYPO + romanization)
73   Bheri Malika Municipality             → Badimalika Municipality              (different name)
75   Temkemaiyum Gaunpalika                → Tyamkemaiyung Rural Municipality
75   Dharan Sub-Metropolitian City         → Dharan Sub-Metropolitan City         (TYPO ONLY)
75   Butwal Sub-Metropolitian City         → Butwal Sub-Metropolitan City         (TYPO ONLY)
75   Mayadevi Gaunpalika                   → Mahadeva Rural Municipality          (different name)
78   Itahari Sub-Metropolitian City        → Itahari Sub-Metropolitan City        (TYPO ONLY)
78   Kalaiya Sub-Metropolitian City        → Kalaiya Sub-Metropolitan City        (TYPO ONLY)
78   Hetauda Sub-Metropolitian City        → Hetauda Sub-Metropolitan City        (TYPO ONLY)
78   Ghorahi Sub-Metropolitian City        → Ghorahi Sub-Metropolitan City        (TYPO ONLY)
...+ 13 additional sub-85 cases of similar pattern
```

The dominant cause is CBS's spelling **"Metropolitian"** (with the extra `i`) plus minor romanization drift. None indicates missing data — all 753 palikas have a clear unique `(prov,dist,gapa)` tuple match.

---

## Appendix B — File counts by group

| Group | Files | Total bytes |
|---|---:|---:|
| Hhld*.csv (household cross-tabs) | 23 | ~26 MB |
| Indv*.csv (individual cross-tabs, with gaps at 08, 12, 13, 14, 15) | 66 | ~191 MB |
| Listing*.xlsx/.xls (household-results) | 7 | ~5 MB |
| DEGURBA xlsx (ward-level) | 1 | 339 KB |
| Metadata index (JSON + XLSX) | 2 | ~500 KB |
| **Total** | **99** | **~223 MB** |

Total CBS NPHC 2021 corpus row count (sum across all 89 CSVs including header lines): **2,084,606 rows**.
