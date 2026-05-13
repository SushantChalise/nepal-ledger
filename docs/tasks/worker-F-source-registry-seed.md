# Worker F — Source Registry Seed Script + Markdown Profiles

**Spawn type:** `general-purpose`
**Plan mode:** required
**Diff cap:** 300 non-test source lines

---

## Goal

Seed the Source Registry for the two Tier-1 starter sources we already have files for: `nrb-cmefs-monthly` and `nrb-ncpi-table`. Per `docs/SOURCE_REGISTRY.md`, **no scraper is written until the source is registered.** This worker creates the seed script (writes to `source_registry`) and the human-readable Markdown profiles.

Done = `pnpm typecheck`, `pnpm lint`, `pnpm test --run` green; running `pnpm exec tsx scripts/seed-source-registry.ts --dry-run` prints what would be inserted; running without `--dry-run` against a reachable Supabase inserts the two rows idempotently (upsert on `source_id`).

## Why

Every Phase 2+ scraper PR is reviewed against the registry. Without the registry rows, the NRB-NCPI parser (Worker C) is technically merge-blocked per doctrine. This worker unblocks future parser PRs and produces the docs/sources/<id>.md files that humans read.

## Scope Fence (files this worker MAY touch)

Create:
- `scripts/seed-source-registry.ts` — Node script: parses args (`--dry-run`), uses `src/lib/db/client` to upsert each row, prints a diff summary
- `docs/sources/nrb-cmefs-monthly.md` — Markdown profile per the SOURCE_REGISTRY template
- `docs/sources/nrb-ncpi-table.md` — Markdown profile per the SOURCE_REGISTRY template
- `scripts/seed-source-registry.test.ts` (optional) — unit test on the data-shape helper, NOT against a live DB

Edit:
- None outside the above. In particular, do NOT modify `src/lib/db/schema/source-registry.ts` (locked in PR #3).

**Out of scope:** package.json, schemas, repository code (not yet written), CI workflow.

## Context to Read First

1. `docs/SOURCE_REGISTRY.md` — schema, workflow, the Tier-1 list
2. `docs/decisions/0004-supabase-storage-instead-of-r2.md` — bucket name, archive policy
3. `docs/decisions/0003-ai-assisted-parsing-policy.md` — parser policy
4. `src/lib/db/schema/source-registry.ts` — the table shape
5. `src/lib/db/client.ts` — how to instantiate the client (note: `db()` requires `serverEnv()` to be valid; the script must fail fast if it isn't)
6. The actual files: `NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv` and `Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf`
7. `https://www.nrb.org.np/category/current-macroeconomic-situation/` — the publication URL (don't actually fetch in tests)

## Seed Data

For both rows fill out the SOURCE_REGISTRY schema completely:

### `nrb-cmefs-monthly`
- `agency`: "Nepal Rastra Bank"
- `agencyShort`: "NRB"
- `datasetName`: "Current Macroeconomic and Financial Situation"
- `sourceUrl`: "https://www.nrb.org.np/category/current-macroeconomic-situation/"
- `publicationFrequency`: 'monthly'
- `expectedReleaseWindow`: "25th–30th of the month following the reporting period"
- `reportingPeriodType`: 'monthly'  (Note: the actual CMEFs document is monthly per release, but cumulative; mark as monthly here, the parser refines)
- `fileFormat`: 'pdf'
- `requiresTableExtraction`: true
- `historicalCoverage`: "FY 2073/74 onward (~2016)"
- `licenseStatus`: 'gov_open'
- `parserOwner`: "scrapers/nrb-cmefs/parser.py"
- `parserVersion`: "0.0.0"  (Worker C will bump to "0.1.0" when the parser shell lands)
- `revisionPolicy`: "Provisional values revised in next release; historical values stable after 2 cycles"
- `knownBreakageModes`: ["url-changes-each-fy", "pdf-format-shifts-at-fy-boundary"]
- `confidenceDefault`: 'A'
- `status`: 'active'
- `notes`: "Starter source — existing PDFs already in repo at Stastical Information/CMEFs_Eng_Nine-Months_2082.83.pdf"

### `nrb-ncpi-table`
- `agency`: "Nepal Rastra Bank"
- `agencyShort`: "NRB"
- `datasetName`: "NCPI Table 2(B)"
- `sourceUrl`: "https://www.nrb.org.np/category/current-macroeconomic-situation/"
- `publicationFrequency`: 'monthly'
- `expectedReleaseWindow`: "Bundled with CMEFs release"
- `reportingPeriodType`: 'nine_months_cumulative'  (the existing CSV is a nine-month table; subsequent monthly releases will be cumulative too)
- `fileFormat`: 'csv'
- `requiresTableExtraction`: false
- `historicalCoverage`: "FY 2073/74 onward (table form available digitally; pre-2016 in PDF)"
- `licenseStatus`: 'gov_open'
- `parserOwner`: "scrapers/nrb-ncpi/parser.py"
- `parserVersion`: "0.0.0"
- `revisionPolicy`: "Aligned with CMEFs cycle"
- `knownBreakageModes`: ["header-row-position-shifts"]
- `confidenceDefault`: 'A'
- `status`: 'active'
- `notes`: "Existing CSV in repo at NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv"

## Script Shape

```typescript
// scripts/seed-source-registry.ts
import { db } from '@/lib/db/client';
import { sourceRegistry } from '@/lib/db/schema/source-registry';
import type { NewSourceRegistryRow } from '@/lib/db/schema/source-registry';
// ...

const ROWS: NewSourceRegistryRow[] = [
  { /* nrb-cmefs-monthly */ },
  { /* nrb-ncpi-table */ },
];

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  if (dryRun) {
    console.log('[dry-run] would upsert:', JSON.stringify(ROWS, null, 2));
    return;
  }
  // upsert via .onConflictDoUpdate by sourceId
  // ...
  console.log(`[seed] inserted/updated ${ROWS.length} source_registry rows`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
```

The Markdown profiles follow `docs/SOURCE_REGISTRY.md` §"Markdown Profile Template" exactly.

## Acceptance Criteria

- [ ] Files in scope only
- [ ] `pnpm typecheck` clean
- [ ] `pnpm lint` clean
- [ ] `pnpm test --run` — existing tests still pass; new tests (if any) pass
- [ ] No new dependencies
- [ ] No `as` casts, no `any`
- [ ] `pnpm exec tsx scripts/seed-source-registry.ts --dry-run` prints both rows in valid JSON
- [ ] Script imports `db` lazily — running with `--dry-run` does NOT require `DATABASE_URL` to be set (i.e., import `db` inside the non-dry-run branch, or guard the import). This lets Mother run dry-run without env in CI.
- [ ] Both Markdown profiles exist with every section the template lists

## What to Return

Standard 6-section report. In §4 "Deviations", explicitly call out anything you had to guess about the NRB publication cadence / format and ask Mother to verify before live-run.
