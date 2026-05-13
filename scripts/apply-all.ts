/**
 * Apply migrations and run all staged ingests in the correct order.
 *
 * This is the SINGLE COMMAND the user runs after waking up to land the
 * overnight pipeline's outputs into the live Supabase database. It
 * sequences the per-step scripts, prints row counts after each, and
 * stops on the first failure with a clear diagnostic.
 *
 * Sequence:
 *   1. Apply Drizzle migrations 0001 + 0002 (idempotent)
 *   2. Seed source_registry (idempotent)
 *   3. Ingest fiscal-transfer-canonical FY 2082/83 (idempotent)
 *   4. Ingest admin-hierarchy wards + polling stations (idempotent)
 *   5. (When their staging JSON exists:) BFI banking facts, Census facts,
 *      constituency mapping fix
 *   6. Print final per-table row counts
 *
 * Each step is idempotent; re-runs are safe. Failure at any step exits
 * non-zero with a description; the user can fix and re-run.
 *
 * Usage:
 *   pnpm exec tsx scripts/apply-all.ts           # full sequence
 *   pnpm exec tsx scripts/apply-all.ts --from=4  # resume from step 4
 *   pnpm exec tsx scripts/apply-all.ts --only=1  # just migrations
 *   pnpm exec tsx scripts/apply-all.ts --dry-run # print plan, no DB writes
 */

import 'dotenv/config';

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { argv } from 'node:process';

import { config as dotenvConfig } from 'dotenv';

dotenvConfig({ path: '.env.local', override: true });

// ─── CLI arg parsing ──────────────────────────────────────────────

function getArg(flag: string): string | undefined {
  const eq = argv.find((a) => a.startsWith(`${flag}=`));
  if (eq) return eq.slice(flag.length + 1);
  const idx = argv.indexOf(flag);
  if (idx >= 0 && idx + 1 < argv.length) return argv[idx + 1];
  return undefined;
}

const fromArg = getArg('--from');
const onlyArg = getArg('--only');
const dryRun = argv.includes('--dry-run');

const fromStep = fromArg ? parseInt(fromArg, 10) : 1;
const onlyStep = onlyArg ? parseInt(onlyArg, 10) : null;

// ─── Step definitions ─────────────────────────────────────────────

type Step = {
  num: number;
  name: string;
  script: string | null; // null = built-in (e.g. final verify)
  args: string[];
  precondition?: () => boolean;
  preconditionMessage?: string;
  optional?: boolean; // optional steps just warn and skip if precondition fails
};

const steps: Step[] = [
  {
    num: 1,
    name: 'Apply Drizzle migrations 0001 + 0002',
    script: 'scripts/apply-migrations.ts',
    args: [],
  },
  {
    num: 2,
    name: 'Seed source_registry (idempotent)',
    script: 'scripts/seed-source-registry.ts',
    args: [],
  },
  {
    num: 3,
    name: 'Ingest fiscal-transfer-canonical (FY 2082/83)',
    script: 'scripts/ingest-fiscal-transfer-canonical.ts',
    args: ['--fiscal-year=2082/83'],
    precondition: () =>
      existsSync('Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx'),
    preconditionMessage:
      'Financial Data/mof_documents/Cleaned/Fiscal Transfer_2082_82.xlsx missing',
  },
  {
    num: 4,
    name: 'Ingest admin-hierarchy wards + polling stations',
    script: 'scripts/ingest-admin-hierarchy.ts',
    args: [],
    precondition: () =>
      existsSync('Financial Data/Administrative Division/administrative_hierarchy_FINAL.csv'),
    preconditionMessage:
      'Financial Data/Administrative Division/administrative_hierarchy_FINAL.csv missing',
  },
  {
    num: 5,
    name: 'Ingest NRB BFI banking-sector facts (Worker ζ output)',
    script: 'scripts/ingest-nrb-bfi.ts',
    args: [],
    precondition: () => existsSync('scripts/ingest-nrb-bfi.ts'),
    preconditionMessage: 'Worker ζ has not yet produced scripts/ingest-nrb-bfi.ts',
    optional: true,
  },
  {
    num: 6,
    name: 'Ingest Census 2021 facts (Worker η output)',
    script: 'scripts/ingest-census-2021.ts',
    args: [],
    precondition: () => existsSync('scripts/ingest-census-2021.ts'),
    preconditionMessage: 'Worker η has not yet produced scripts/ingest-census-2021.ts',
    optional: true,
  },
  {
    num: 7,
    name: 'Fix admin-hierarchy constituency mapping (Worker θ output)',
    script: 'scripts/fix-admin-constituency.ts',
    args: [],
    precondition: () => existsSync('scripts/fix-admin-constituency.ts'),
    preconditionMessage: 'Worker θ has not yet produced scripts/fix-admin-constituency.ts',
    optional: true,
  },
];

// ─── Runner ───────────────────────────────────────────────────────

function runScript(script: string, args: string[]): Promise<number> {
  return new Promise((resolve, reject) => {
    const allArgs = ['exec', 'tsx', script, ...args];
    const child = spawn('pnpm', allArgs, { stdio: 'inherit', shell: true });
    child.on('error', reject);
    child.on('exit', (code) => resolve(code ?? 0));
  });
}

async function main(): Promise<void> {
  const url = process.env['DIRECT_URL'] ?? process.env['DATABASE_URL'];
  if (!url) {
    console.error('[apply-all] No DIRECT_URL / DATABASE_URL in .env.local.');
    process.exit(1);
  }

  console.log('=== Nepal Ledger — apply-all ===');
  console.log(`mode: ${dryRun ? 'DRY-RUN' : 'LIVE'}`);
  console.log(`from-step: ${fromStep}${onlyStep !== null ? ` only-step: ${onlyStep}` : ''}`);
  console.log();

  for (const step of steps) {
    if (onlyStep !== null && step.num !== onlyStep) continue;
    if (step.num < fromStep) continue;

    console.log(`────────────────────────────────────────────────────`);
    console.log(`Step ${step.num}: ${step.name}`);
    console.log(`────────────────────────────────────────────────────`);

    if (step.precondition && !step.precondition()) {
      const msg = step.preconditionMessage ?? 'precondition not met';
      if (step.optional) {
        console.log(`SKIP (optional): ${msg}`);
        continue;
      }
      console.error(`FAIL: ${msg}`);
      process.exit(1);
    }

    if (!step.script) {
      console.log('(built-in step — no script)');
      continue;
    }

    if (dryRun) {
      console.log(`would run: pnpm exec tsx ${step.script} ${step.args.join(' ')}`);
      continue;
    }

    const exitCode = await runScript(step.script, step.args);
    if (exitCode !== 0) {
      console.error(`[apply-all] Step ${step.num} FAILED with exit code ${exitCode}.`);
      console.error(`Fix the issue and re-run with --from=${step.num}`);
      process.exit(exitCode);
    }
    console.log(`Step ${step.num}: OK`);
  }

  console.log();
  console.log('=== apply-all OK ===');
  console.log('Verify in Supabase dashboard: 21 user tables in public schema.');
  console.log('Run row-count verification:');
  console.log('  SELECT (SELECT count(*) FROM entities) AS entities,');
  console.log('         (SELECT count(*) FROM administrative_units) AS admin_units,');
  console.log(
    '         (SELECT count(*) FROM local_government_fiscal_transfers) AS fiscal_transfers,',
  );
  console.log('         (SELECT count(*) FROM banking_sector_facts) AS banking_facts,');
  console.log('         (SELECT count(*) FROM census_facts) AS census_facts;');
}

main().catch((e: unknown) => {
  console.error('[apply-all] FAILED:', e instanceof Error ? e.stack : String(e));
  process.exit(1);
});
