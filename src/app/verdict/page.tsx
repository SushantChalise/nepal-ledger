import type { Metadata } from 'next';

import { listApprovedWithIndicator } from '@/lib/db/repositories/approved-indicator-values';
import { formatAppError } from '@/lib/errors';
import { VerdictDataStrip } from '@/features/verdict/components/VerdictDataStrip';
import { VerdictPillar } from '@/features/verdict/components/VerdictPillar';

export const metadata: Metadata = {
  title: 'Monthly Verdict — Nepal Ledger',
  description:
    "Nepal Ledger's monthly synthesis of Nepal's macro data: what moved, who it affected, and whether money is becoming wealth.",
};

// ---------------------------------------------------------------------------
// Edition type — one object per monthly release.
// ---------------------------------------------------------------------------

type Bullet = { text: string; source: string };
type Callout = { name: string; body: string };

type VerdictEdition = {
  editionNumber: number;
  headline: string;
  periodBs: string;
  publishedBs: string;
  pillars: {
    moneyIn: string;
    moneyOut: string;
    moneyCaptured: string;
    moneyWasted: string;
    whereWealthForms: string;
  };
  whatChanged: Bullet[];
  institutionToWatch: Callout;
  householdImpact: Callout;
  projectDebtUpdate: Callout;
  productiveEscape: Callout;
  closingLine: string;
};

// ---------------------------------------------------------------------------
// Edition 1 — 9-months FY 2082/83 (Magh 2082 / January 2026 NRB CMEFs)
// ---------------------------------------------------------------------------

const EDITION_1: VerdictEdition = {
  editionNumber: 1,
  headline: 'Money entered. Most did not compound.',
  periodBs: '9 months of FY 2082/83 (up to Magh 2082)',
  publishedBs: 'Chaitra 2082',
  pillars: {
    moneyIn:
      'Remittances continued as Nepal\'s primary external income, keeping the balance of payments in surplus and forex reserves above the import-cover threshold. External inflows remain strong in aggregate — the structural dependency on labour migration, however, means the country is importing wages rather than producing them.',
    moneyOut:
      'The merchandise trade deficit widened as imports outpaced exports. Nepal continues to import manufactured goods and fuel while exporting only primary commodities at low value-addition. The gap between what enters as remittances and what leaves through imports is narrowing.',
    moneyCaptured:
      'Credit growth remained concentrated in the real estate and consumer lending segments. Productive-sector lending — manufacturing, agriculture, technology — continued to receive a disproportionately small share of bank credit relative to its employment share. Business-group concentration in formal banking, cooperatives, and land has not materially changed.',
    moneyWasted:
      'Capital expenditure execution remained below target in the first eight months of the fiscal year, consistent with the multi-year pattern of front-loaded budget announcements and back-loaded (or failed) disbursements. Revenue mobilisation tracked estimates, but the quality of spend — infrastructure completing on time and on budget — remains weak.',
    whereWealthForms:
      'Hydropower generation capacity continued its slow expansion. IT services exports showed modest growth. Agricultural exports (cardamom, tea, ginger) held steady in volume terms. These remain Nepal\'s three credible conversion sectors — energy, digital services, and high-value agriculture — but their aggregate share of GDP is still far below what is required to offset import dependency.',
  },
  whatChanged: [
    {
      text: 'NRB gross forex reserves remained above 10 months of import cover, the highest sustained level since the 2022 liquidity crisis.',
      source: 'NRB CMEFs 9-months FY 2082/83',
    },
    {
      text: 'NCPI headline inflation moderated, driven by lower food prices; non-food inflation (housing, education, health) held firm.',
      source: 'NRB CMEFs 9-months FY 2082/83',
    },
    {
      text: 'BOP surplus remained positive, though the current-account component narrowed as trade deficit widened.',
      source: 'NRB CMEFs 9-months FY 2082/83',
    },
  ],
  institutionToWatch: {
    name: 'Nepal Rastra Bank (NRB)',
    body: "NRB's monetary policy stance and its credit-growth directives for the coming quarter will determine whether the current forex stability translates into investment momentum or stagnates at the banking-system level. Watch the next MPC meeting minutes.",
  },
  householdImpact: {
    name: 'Food prices and import cost',
    body: 'Lower global commodity prices passed through to domestic food inflation, giving households modest relief. Energy prices (fuel, LPG) remain sensitive to import costs and NOC subsidy policy — any reversal in global oil prices will transmit quickly to household budgets.',
  },
  projectDebtUpdate: {
    name: 'Pokhara International Airport',
    body: "Nepal's largest recent infrastructure project continues to operate below designed passenger capacity. Loan repayments on the Chinese EXIM bank-financed construction remain on the federal debt service schedule. Revenue generation from the airport has not yet offset operational costs, making it a live test of whether debt-financed infrastructure can generate returns.",
  },
  productiveEscape: {
    name: 'Hydropower + IT services exports',
    body: 'Combined electricity export revenue and IT/BPO services exports represent the two non-remittance income streams growing consistently. Both are structurally different from commodity exports — they involve domestic value-addition and create technical employment. Tracking their share of total export earnings is the clearest signal of conversion progress.',
  },
  closingLine: 'Nepal did not lack money this month. It lacked conversion.',
};

// ---------------------------------------------------------------------------
// Slugs shown in the KPI strip — same as Pulse for consistency.
// ---------------------------------------------------------------------------

// All 14 NRB CMEFs slugs (9-months flow data). WDI annual benchmarks are
// excluded from the Verdict strip — their FY label would differ from CMEFs.
const PULSE_SLUGS = new Set([
  'cmefs-ncpi-yoy-overall',
  'cmefs-remittance-inflow-ytd',
  'cmefs-bop-surplus-ytd',
  'cmefs-gross-forex-reserves',
  'cmefs-forex-reserves-months-of-import-cover',
  'cmefs-merchandise-exports-ytd',
  'cmefs-merchandise-imports-ytd',
  'cmefs-trade-deficit-ytd',
  'cmefs-govt-revenue-total-ytd',
  'cmefs-govt-expenditure-total-ytd',
  'cmefs-govt-fiscal-balance-ytd',
  'cmefs-m2-yoy',
  'cmefs-private-sector-credit-yoy',
  'cmefs-bfi-deposits-yoy',
]);

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function VerdictPage() {
  const edition = EDITION_1;

  const dbResult = await listApprovedWithIndicator();

  const kpiRows =
    dbResult.ok
      ? dbResult.value.filter((r) => PULSE_SLUGS.has(r.indicator.slug))
      : [];

  const dbError = !dbResult.ok ? formatAppError(dbResult.error) : null;

  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      {/* Header */}
      <header className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
          Monthly Verdict · Edition {edition.editionNumber} · {edition.publishedBs}
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          {edition.headline}
        </h1>
        <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
          Data period: {edition.periodBs}
        </p>
      </header>

      {/* KPI strip */}
      <section aria-labelledby="kpi-heading" className="mb-10">
        <h2
          id="kpi-heading"
          className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
        >
          The numbers behind this verdict
        </h2>
        {dbError !== null && (
          <p className="mb-2 text-xs text-red-600 dark:text-red-400">
            Could not load live data: {dbError}
          </p>
        )}
        <VerdictDataStrip rows={kpiRows} />
      </section>

      {/* 5-pillar summaries */}
      <section aria-labelledby="pillars-heading" className="mb-10">
        <h2
          id="pillars-heading"
          className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
        >
          The five pillars
        </h2>
        <div className="flex flex-col gap-5">
          <VerdictPillar label="Money In" body={edition.pillars.moneyIn} />
          <VerdictPillar label="Money Out" body={edition.pillars.moneyOut} />
          <VerdictPillar label="Money Captured" body={edition.pillars.moneyCaptured} />
          <VerdictPillar label="Money Wasted" body={edition.pillars.moneyWasted} />
          <VerdictPillar
            label="Where Money Becomes Wealth"
            body={edition.pillars.whereWealthForms}
          />
        </div>
      </section>

      {/* What changed */}
      <section aria-labelledby="changed-heading" className="mb-10">
        <h2
          id="changed-heading"
          className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
        >
          What changed this month
        </h2>
        <ul className="flex flex-col gap-3">
          {edition.whatChanged.map((bullet, i) => (
            <li key={i} className="flex gap-3">
              <span
                aria-hidden="true"
                className="mt-0.5 shrink-0 text-zinc-400 dark:text-zinc-500"
              >
                ·
              </span>
              <span className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                {bullet.text}{' '}
                <span className="text-xs text-zinc-400 dark:text-zinc-500">
                  [{bullet.source}]
                </span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Four callout sections */}
      <div className="mb-10 grid gap-6 sm:grid-cols-2">
        <Callout
          tag="Institution to watch"
          name={edition.institutionToWatch.name}
          body={edition.institutionToWatch.body}
        />
        <Callout
          tag="Household impact"
          name={edition.householdImpact.name}
          body={edition.householdImpact.body}
        />
        <Callout
          tag="Project / debt update"
          name={edition.projectDebtUpdate.name}
          body={edition.projectDebtUpdate.body}
        />
        <Callout
          tag="Productive escape"
          name={edition.productiveEscape.name}
          body={edition.productiveEscape.body}
        />
      </div>

      {/* Closing line */}
      <footer className="border-t border-zinc-200 pt-8 dark:border-zinc-800">
        <p className="text-base font-medium italic text-zinc-700 dark:text-zinc-300">
          &ldquo;{edition.closingLine}&rdquo;
        </p>
        <p className="mt-4 text-xs text-zinc-400 dark:text-zinc-500">
          Sources: NRB Current Macroeconomic and Financial Situation (CMEFs) —{' '}
          {edition.periodBs}. All indicator values from the Nepal Ledger approved data pipeline.
          Grade A = audited outturn; Grade B = provisional; Grade C = estimate.
        </p>
      </footer>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sub-component
// ---------------------------------------------------------------------------

type CalloutProps = { tag: string; name: string; body: string };

function Callout({ tag, name, body }: CalloutProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-900">
      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
        {tag}
      </p>
      <p className="mt-1 text-sm font-semibold text-zinc-800 dark:text-zinc-200">{name}</p>
      <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">{body}</p>
    </div>
  );
}
