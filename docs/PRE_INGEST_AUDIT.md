# Pre-Ingest Data Audit — Mandatory Doctrine

**Status:** Established 2026-05-14 after a real failure: the admin-hierarchy ingest used `administrative_hierarchy_FINAL.csv` as if it were canonical when the same folder contained 6 alternative files, two of which were partial scrapes and one of which had broken `municipality_type` and `constituency_no` fields throughout. The "FINAL" naming was misleading; the folder's actual canonical source was elsewhere.

**Rule:** No external dataset is ingested into `staging_*` or any production-shape table until a data audit has been written, reviewed, and committed.

---

## Why this rule exists

External datasets routinely arrive with:

- Multiple files in the same folder representing **iterations** of an extract (`administrative_hierarchy.csv`, `..._COMPLETE.csv`, `..._FINAL.csv`) — naming alone is unreliable
- **Partial scrapes** that look complete but cover only some districts/provinces
- **Broken classifications** (e.g. `Municipality Type` populated by an English-only suffix matcher that fails on Devanagari)
- **Sparse joinable columns** (`Constituency No.` populated on only 10% of rows)
- **A separate folder with the canonical version** that the obvious file silently shadows

The result without audit: parsers get written against the wrong file, ingest produces incorrect data, and the Fact Ledger inherits the lie. Discovering this AFTER ingestion costs:

- Migration rollback or per-row backfill
- Source-of-truth confusion in downstream stories
- Reviewer trust in the platform

Auditing BEFORE ingest costs 15–60 minutes per dataset. It is non-negotiable.

---

## The audit (mandatory checklist before ANY ingest brief is written)

For each new external dataset, produce `docs/research/<dataset-id>-audit.md` covering:

### 1. File inventory
- Recursively list every file in the source folder
- For each: filename, byte size, row count (if structured), file format, file age (mtime), file purpose (inferred from name)
- Note "variants": files with similar names (`X.csv`, `X_COMPLETE.csv`, `X_FINAL.csv`) and READMEs that explain them
- Note any README, CHANGELOG, or `*_metadata.json` files that document provenance

### 2. Per-file shape probe
For each candidate file:
- Open it
- List exact column names + types
- Row count
- Distinct value count for key dimensional columns (province / district / municipality / etc.)
- Coverage statistics: how many rows have each column populated?
- Spot-check 5–10 sample rows for sanity

### 3. Variant comparison
If multiple files in the folder look similar, **diff them**:
- Row count delta
- Column delta (do all variants have the same columns?)
- For shared columns: do the values match? Which variant has more populated cells?
- Compute "coverage percent" per column per file
- Identify which variant is the most complete + most correct, AND which fields each variant gets right vs. wrong

### 4. Authority assessment
For each field needed downstream:
- Which file (if any) has the **authoritative** version of this field?
- Which fields are **broken** in all variants and need a different source entirely?
- Which fields are **derived** (computed from other fields, not raw data)?
- Cross-reference against canonical reference tables when they exist (e.g. the MoF chart-of-accounts for fiscal-transfer; the canonical 753-local-level table from the Cleaned/ XLSX)

### 5. Gap surface
What fields/rows/coverage are MISSING and would need a different source or a manual fix:
- Specific count of missing rows
- Identifiable patterns (e.g. "only 52 of 77 districts covered")
- Mitigations available now vs. needing a future scrape/manual upload

### 6. Authoritative decision (one paragraph)
Conclude with a **single explicit verdict**:
- "**Canonical source**: `<filename>` for fields X, Y, Z"
- "**Discarded**: `<other filenames>` — superseded; do NOT use"
- "**Gaps**: `<list>` — accept as known limitation, OR queue follow-up scrape"
- "**Ingest brief**: WRITE only after this verdict is reviewed"

### 7. PII & licensing check
- Does any file contain PII (names, addresses, IDs, phone, location data with privacy implications)?
- What's the license? Public-domain, gov-open, CC-BY, proprietary?
- Are credentials embedded anywhere (`.env`, `config.yaml`)?
- The PII verdict determines whether the data crosses into Supabase or stays local-only

---

## Process

1. **Mother reads** the user-flagged "here's a new dataset folder" message
2. **Mother spawns an audit worker** (`general-purpose` Sonnet; sometimes Opus for messy folders) with the scope: read the folder, write the audit, return findings. No parser is written by this worker.
3. **Audit lands in `docs/research/<dataset-id>-audit.md`** via a separate PR
4. **User reviews the audit** and signs off on the authoritative-source verdict
5. **Then and only then**: Mother writes the parser/ingest brief based on the audit's verdict
6. **Then**: parser worker spawns

This adds one PR cycle (~15 min) per dataset. It saves a multi-hour rollback when "canonical" turned out to be wrong.

---

## The cautionary case (concretely)

`Financial Data/Administrative Division/` contained:

| File | Rows | Status |
|------|------:|---|
| `administrative_hierarchy.csv` | 953 | Early attempt; covers only 11 of 77 districts |
| `administrative_hierarchy_COMPLETE.csv` | 10,263 | Full 77 districts, but 0% constituency populated |
| `administrative_hierarchy_FINAL.csv` | 10,263 | 10% constituency populated, all 4 values; municipality_type all wrong |
| `Constituency/nepal_admin_hierarchy_*.json` | 953 | Sample-sized; has voting-center lat/lng |
| `Constituency/province_[1-7]_*.json` (aggregated) | 4,037 | Correct constituency + types BUT only 52/77 districts and 450/753 municipalities — scrape incomplete |
| `Constituency/municipality_ward_count.csv` | ? | Ward counts; un-audited |

Mother (without audit) used `..._FINAL.csv` because the filename signalled "use me". The actual canonical source for the **753 local levels** is `mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx` (different folder entirely). The Administrative Division/ files are partial/wrong derivatives.

**Verdict, reached only AFTER ingest (one wasted cycle):** discard the Administrative Division/ files entirely; use the MoF fiscal-transfer XLSX as the canonical local-level catalog.

This document exists so that doesn't happen again.

---

## Cross-Reference

- [CONTEXT_RULES.md](CONTEXT_RULES.md) — the Six Rules workers operate under (this audit becomes Rule 7 for any worker spawning a new-dataset parser)
- [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) §"Workflow for Adding a New Source" — formal source-registry workflow that now begins with this audit
- [DATA_PIPELINE.md](DATA_PIPELINE.md) — production-pipeline conventions assuming the audit has passed
