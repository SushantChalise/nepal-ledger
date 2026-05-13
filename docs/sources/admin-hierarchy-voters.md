# Source: Election Commission (derived) — Administrative Hierarchy from Voter DB

**source_id:** `admin-hierarchy-voters`
**Status:** Active (one-shot ingest from pre-extracted CSV; refresh on next EC voter-roll publication)
**Last verified:** 2026-05-14

## What this is

The complete Nepal administrative hierarchy aggregated from the **voter database** (17.8 million voter records). Extracted via the `extract_with_constituencies.py` script (in `Financial Data/Administrative Division/`) and shipped as `administrative_hierarchy_FINAL.csv` with 10,263 rows.

Granularity: down to **polling-station level** with **actual registered voter counts**.

The most authoritative spatial dataset we have, because the voter roll is legally mandated to cover every adult Nepali citizen with an address. By contrast, the MoF fiscal-transfer XLSX has only 753 local levels (no wards/polling stations).

## Publication

- URL: not directly published; derived from the EC's voter-DB Postgres dump at `Financial Data/Voter DB/voters_db_backup_*.sql` (546 MB; PII; never shared)
- Frequency: One-shot extract per voter-roll refresh (EC publishes refreshed rolls every few years; next anticipated around election cycle)
- Expected window: irregular
- Format: CSV (derived); SQL dump (source — PII; not for our DB)

## Data shape

10,263 rows × 9 columns:
- Province (Nepali) — 7 distinct
- District (Nepali) — 77 distinct
- Constituency No. — sparse (10% coverage; rest fixed by `Combined_Constituency_Master_Table.csv` per Worker θ)
- Municipality/Rural Municipality (Nepali) — 719 distinct (canonical 753 — gap reveals name variants)
- Municipality Type — currently misclassified (all "Rural Municipality"; fixed via canonical join)
- Rural/Urban
- Ward No.
- Polling Station name (Nepali)
- Voter Count (integer)

## Local processing results

| Aggregate | Count |
|---|---:|
| Provinces | 7 |
| Districts | 77 |
| Distinct local levels (in this CSV) | 736 (vs. canonical 753 — 17 not represented by polling stations) |
| Ward rollups | 6,285 |
| Polling stations | 10,203 |
| Total voters | 17,800,330 |

## What we extract

- `entities` rows for: 7 provinces, 77 districts, ~736 local levels (joined to canonical 753), ~6,176 wards, ~10,203 polling stations
- `administrative_units` rows for each entity with: federal_code, local_level_type (fixed via canonical join), constituency_no (fixed via Worker θ), ward_no, rural_urban, voter_count
- This is a **one-shot ingest** — re-runs on the same source are idempotent via `entities` upsert + `administrative_units` upsert

## Provenance

- Confidence default: **A** (voter roll is the legally authoritative spatial source)
- License: gov_open (voter roll is public; PII excluded from our derivative)
- Reporting period type: annual (rolls refresh; not time-series — this is reference geography)

## Known breakage modes

- **Municipality types misclassified** by the source CSV's English-only suffix matcher. Fixed at ingest by joining to the canonical 753-row local-level table from MoF fiscal-transfer FY 2082/83.
- **Constituency mapping sparse** (10% coverage). Fixed by Worker θ via `Combined_Constituency_Master_Table.csv`.
- Polling-station names have OCR-typo variations even within the CSV. Worker ε's `_common/devanagari_normalization.py` handles common ones.
- 17 local levels canonical-but-not-in-CSV — typically very small or remote rural municipalities with consolidated polling stations elsewhere.

## Revision policy

When EC publishes a refreshed voter roll, we re-extract via the script and re-ingest. The `entities` upsert preserves IDs; new wards/polling stations get inserted; departed ones get `retired_at` (TBD column addition; not in migration 0002 yet).

## Parser

- Path: `scripts/ingest-admin-hierarchy.ts` (Mother-owned)
- Version: 0.1.0 (XLSX path confirmed)
- Owner: Mother Opus

## Archive policy

Original SQL dump is PII; **NEVER** ingested into our Supabase. Stays local-only at `Financial Data/Voter DB/voters_db_backup_*.sql`. The DERIVED CSV (no PII; just aggregates per polling station) is the only thing that crosses into our DB.

## Recent ingests

Staged at `staging-data/admin-hierarchy/wards-and-polling-stations.json`. Awaiting `pnpm exec tsx scripts/apply-all.ts` for live ingest.
