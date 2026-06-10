import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { getStateEnterpriseExposure } from '@/features/state-enterprises/server/queries';
import { EnterpriseExposureTable } from '@/features/state-enterprises/components/EnterpriseExposureTable';
import { formatNprBillion, formatSharePct } from '@/features/state-enterprises/format';

export const metadata: Metadata = {
  title: 'State Enterprises — Public Enterprise X-Ray | Nepal Ledger',
  description:
    "How much capital Nepal's government has tied up in its state-owned enterprises — government equity versus outstanding loan principal, per enterprise, for fiscal year 2080/81. A Money-Captured / Money-Wasted view. Source: MoF / DPM-Office Yellow Book (Annual Performance Review of Public Enterprises), Annex-1.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function StateEnterprisesPage() {
  const result = await getStateEnterpriseExposure();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <StateEnterprisesHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load public-enterprise data
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

  const data = result.value;

  if (data.enterprises.length === 0 || data.grandTotal <= 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <StateEnterprisesHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No public-enterprise data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            The government equity-vs-loan ranking will appear here once the Yellow Book Annex-1
            table is ingested.
          </p>
        </div>
      </main>
    );
  }

  // Ranked by total exposure desc — the first row is the largest stake.
  const topByTotal = data.enterprises[0]!;
  // Largest single loan exposure (independent of total ranking).
  const topByLoan = data.enterprises.reduce(
    (m, e) => (e.loanPrincipal > m.loanPrincipal ? e : m),
    data.enterprises[0]!,
  );
  const sharePctOfGrand = (data.totalShare / data.grandTotal) * 100;
  const loanPctOfGrand = (data.totalLoan / data.grandTotal) * 100;

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <StateEnterprisesHeader fiscalYearBs={data.fiscalYearBs} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. Confidence B. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          label="Total government exposure"
          value={formatNprBillion(data.grandTotal)}
          unit=""
          period={`${data.enterpriseCount} enterprises · FY ${data.fiscalYearBs}`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Largest stake"
          value={topByTotal.label}
          unit=""
          period={`${formatNprBillion(topByTotal.total)} · ${formatSharePct((topByTotal.total / data.grandTotal) * 100)} of total`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Largest loan exposure"
          value={topByLoan.label}
          unit=""
          period={`${formatNprBillion(topByLoan.loanPrincipal)} loan principal`}
          confidence={data.confidence}
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> How much public capital is tied up
          in Nepal&apos;s <span className="font-medium">state-owned enterprises</span> as of the
          close of fiscal year {data.fiscalYearBs}, split into government{' '}
          <span className="font-medium">equity</span> (paid-in share capital) and outstanding
          government <span className="font-medium">loan principal</span>. Across{' '}
          {data.enterpriseCount} enterprises the state has{' '}
          <span className="font-medium">{formatNprBillion(data.grandTotal)}</span> committed —{' '}
          {formatSharePct(sharePctOfGrand)} as equity and {formatSharePct(loanPctOfGrand)} as loans.
          The single largest stake is in <span className="font-medium">{topByTotal.label}</span> (
          {formatNprBillion(topByTotal.total)}). These are the government&apos;s capital exposures,{' '}
          <span className="font-medium">not</span> the enterprises&apos; revenue or profit.
        </p>
      </div>

      {/* Ranked table */}
      <section aria-labelledby="exposure-table-heading" className="mt-8">
        <h2
          id="exposure-table-heading"
          className="mb-4 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Government equity vs loan exposure by enterprise — FY {data.fiscalYearBs}
        </h2>
        <EnterpriseExposureTable
          enterprises={data.enterprises}
          grandTotal={data.grandTotal}
          fiscalYearBs={data.fiscalYearBs}
        />
      </section>

      {/* Performance & subsidy detail — coming soon (disabled; no fabricated data). */}
      <section aria-labelledby="performance-heading" className="mt-10">
        <h2
          id="performance-heading"
          className="mb-3 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Which enterprises return the money — and which burn it
        </h2>
        <div
          aria-disabled="true"
          className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-6 text-center dark:border-zinc-700 dark:bg-zinc-900/50"
        >
          <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
            Profit, loss &amp; subsidy by enterprise — coming soon
          </p>
          <p className="mx-auto mt-1 max-w-md text-xs text-zinc-400 dark:text-zinc-500">
            Net profit, accumulated loss, and operating subsidy per enterprise — the return on this
            capital. This view is not yet available: the Yellow Book&apos;s per-sector profit tables
            use a different (lakh) unit and a ragged layout we have not yet parsed
            deterministically, and we will not show an estimate until those figures are ingested and
            verified.
          </p>
        </div>
      </section>

      {/* Source attribution + confidence — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>MoF / DPM-Office Yellow Book — Annual Performance Review of Public Enterprises</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800">
                Grade {data.confidence}
              </span>
              <span className="ml-1">— government annual review, revised across editions</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>NPR billion (converted from the source&apos;s NPR thousand)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Reference:</dt>
            <dd>FY {data.fiscalYearBs} (Annex-1, balance-sheet close)</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Figures are government equity (paid-in share capital) and outstanding government loan
          principal per enterprise at the close of FY {data.fiscalYearBs}, from Annex-1 of the
          Yellow Book. Enterprise names are shown as recorded in the source (Devanagari). Source
          values are in NPR thousand; we display NPR billion (value ÷ 1,000,000).{' '}
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

type StateEnterprisesHeaderProps = {
  fiscalYearBs?: string;
};

function StateEnterprisesHeader({ fiscalYearBs }: StateEnterprisesHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        State Enterprises — Public Enterprise X-Ray
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        Nepal&apos;s government owns and bankrolls dozens of public enterprises. This lens X-rays
        the capital behind them — how much the state holds as{' '}
        <span className="font-medium">equity</span> versus how much it has lent as{' '}
        <span className="font-medium">loan principal</span>, enterprise by enterprise, at the close
        of the fiscal year.
      </p>
      {fiscalYearBs !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reference: FY {fiscalYearBs}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              MoF / DPM-Office Yellow Book
            </span>
          </span>
        </p>
      )}
    </header>
  );
}
