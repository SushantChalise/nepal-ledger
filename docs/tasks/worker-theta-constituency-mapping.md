# Worker θ — Constituency Table Ingest + Admin-Hierarchy Constituency Fix

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** soft 300 / hard 500 non-test source lines

---

## Goal

Two related deliverables:

1. **Parse `Financial Data/Constituency/Combined_Constituency_Master_Table.csv`** — the canonical federal-constituency → local-level mapping. Emit staging JSON for ingest.
2. **Fix the broken constituency coverage in the admin-hierarchy** — the source CSV (`administrative_hierarchy_FINAL.csv`) has constituency mapping on only 10% of rows. Join with the constituency master table to populate the missing 90%.

Done = staging JSON at `staging-data/constituency-mapping/` covers ALL 753 local levels with their federal constituency assignments, plus 165 constituency entities for ingest.

## Why

Constituencies are the federal political units that overlay onto the local-level geography. Required for:
- Vertical 10 (Budget Watch + Local Ledger) — election results × budget execution overlays
- Story #1 ("How Nepal's Economy Actually Works") — federal-spending-by-constituency analysis
- District MRI — constituency-level election results × economic indicators
- Future Phase-2: election-result ingestion needs the canonical constituency mapping

## Setup state

- Working dir: `C:\Users\ACER\Projects\Economy`
- Branch: create `feat/constituency-mapping` from main yourself
- Sources:
  - `Financial Data/Constituency/Combined_Constituency_Master_Table.csv` (24KB)
  - `Financial Data/Constituency/Constituency_Table.csv` (30KB; possibly older version)
  - `Financial Data/Constituency/Constituency Narrative.txt` (28KB; explanatory)
  - `Financial Data/Administrative Division/administrative_hierarchy_FINAL.csv` (the broken one)
  - `Financial Data/Constituency/Province to Election booth table.txt` (2MB; very long)
- Worker ε's `_common/municipality_resolver.py` (you'll need it for the join)

## Schema target

Two ingest targets:

1. **`entities`** (kind=`constituency`) — 165 constituency entities for the federal parliament. Each with:
   - `slug` like `kathmandu-1`, `kaski-2`
   - `parent_entity_id` → the district entity
   - `metadata` like `{ "constituency_no": 1, "constituent_district": "Kathmandu" }`

2. **Update `administrative_units.constituency_no`** for the 753 local levels by joining the constituency master table against the canonical fiscal-transfer XLSX local-level table.

## Investigation phase first

Before writing code:
1. Read `Combined_Constituency_Master_Table.csv` columns and 10 sample rows
2. Read `Constituency_Table.csv` to understand if it's the same data in a different shape
3. Read the first 100 lines of `Constituency Narrative.txt` for context
4. Confirm the join key: is it (district_en + local_level_en)? (district_en + ward_no)? Federal code?
5. Document findings in `docs/research/constituency-mapping-findings.md` BEFORE writing the parser

## Parser shape

`scripts/ingest-constituency-mapping.ts` (TypeScript, mirroring the other ingest scripts):

```typescript
// Step 1: parse Combined_Constituency_Master_Table.csv → 165 constituency entities
// Step 2: parse the admin-hierarchy CSV → for each local level, look up its constituency
// Step 3: emit staging JSON merging both — ready for the apply-all wrapper to ingest

// Output: staging-data/constituency-mapping/constituencies.json
//         staging-data/constituency-mapping/local-level-constituency.json
```

## Acceptance criteria

- [ ] Files only in `scripts/` + `staging-data/constituency-mapping/` (gitignored)
- [ ] `docs/research/constituency-mapping-findings.md` documents the source-CSV columns + join key BEFORE the script is written
- [ ] `pnpm typecheck` clean
- [ ] Output JSON covers all 165 constituencies + at least 700 of 753 local-level mappings (some may genuinely have no constituency assignment per the source — note them)
- [ ] No untracked files outside scope on commit
- [ ] Branch `feat/constituency-mapping`. Commit message: `feat(data): constituency mapping + admin-hierarchy constituency fix`
- [ ] **Use git stash before branch switches** — other workers in the filesystem; do NOT `git add -A`

## What to return

≤12 bullets:
- Source-CSV column structure (which CSV is canonical)
- Join key used
- Stats: 165 constituencies / how many of 753 local levels mapped / unmapped count + reasons
- Branch SHA
- Any anomalies in the source data flagged for Mother's attention

Begin.