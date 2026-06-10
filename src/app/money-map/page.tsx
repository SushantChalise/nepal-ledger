import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { getFiscalTransferSankeyData } from '@/features/money-map/server/queries';
import { SankeyDiagram } from '@/features/money-map/components/SankeyDiagram';
import { formatNprCrore } from '@/features/money-map/format';

export const metadata: Metadata = {
  title: 'Money Map — Nepal Ledger',
  description:
    "How Nepal's federal government distributes fiscal transfers to 753 local governments. A D3 Sankey of intergovernmental flows by grant type and local-level type, FY 2082/83.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function MoneyMapPage() {
  const result = await getFiscalTransferSankeyData();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <MoneyMapHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load fiscal transfer data
          </p>
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">
            {formatAppError(result.error)}
          </p>
          <p className="mt-3 text-xs text-red-500 dark:text-red-400">
            Refresh the page or check back shortly. If the issue persists, contact the Nepal Ledger
            team.
          </p>
        </div>
      </main>
    );
  }

  const sankeyData = result.value;

  if (sankeyData.nodes.length === 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <MoneyMapHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No fiscal transfer data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            Intergovernmental fiscal transfer records will appear here once the first ingestion run
            completes.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <MoneyMapHeader
        fiscalYearBs={sankeyData.fiscalYearBs}
        grandTotal={sankeyData.grandTotalNprCrore}
      />

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md §"Required Content Elements" */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> The federal government distributed{' '}
          <span className="font-medium">{formatNprCrore(sankeyData.grandTotalNprCrore)}</span> to
          Nepal&apos;s 753 local governments in FY {sankeyData.fiscalYearBs} through{' '}
          {sankeyData.nodes.filter((n) => n.column === 1).length} grant types. Each column shows a
          stage in the flow: who sends → what channel → who receives. Wider bands mean larger
          transfers.
        </p>
      </div>

      {/* Diagram */}
      <section aria-labelledby="money-map-diagram-heading" className="mt-8">
        <h2
          id="money-map-diagram-heading"
          className="mb-4 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Federal Fiscal Transfers — FY {sankeyData.fiscalYearBs}
        </h2>
        <SankeyDiagram data={sankeyData} />
      </section>

      {/* Source attribution + confidence — required by UI_ACCEPTANCE.md */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>
              Ministry of Finance — Intergovernmental Fiscal Transfer Schedule, FY{' '}
              {sankeyData.fiscalYearBs}
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-800">
                Grade A
              </span>
              <span className="ml-1">— official MoF published schedule</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>NPR crore</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Data status:</dt>
            <dd>
              <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-800">
                Preliminary
              </span>
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Transfer amounts are in NPR crore. Figures cover all 753 local governments — metropolitan
          cities, sub-metropolitan cities, municipalities, and rural municipalities — for the fiscal
          year indicated.{' '}
          <Link
            href="/pulse"
            className="text-blue-600 underline hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            View Pulse →
          </Link>
        </p>
      </footer>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type MoneyMapHeaderProps = {
  fiscalYearBs?: string;
  grandTotal?: number;
};

function MoneyMapHeader({ fiscalYearBs, grandTotal }: MoneyMapHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Money Map
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        How Nepal&apos;s federal government distributes funds to local governments — tracking every
        rupee from the national treasury to 753 municipalities and rural municipalities through
        conditional, special, and complementary grants.
      </p>
      {fiscalYearBs !== undefined && grandTotal !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reporting period: FY {fiscalYearBs}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Total transfers:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {formatNprCrore(grandTotal)}
            </span>
          </span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              Ministry of Finance — Intergovernmental Fiscal Transfers
            </span>
          </span>
        </p>
      )}
    </header>
  );
}
