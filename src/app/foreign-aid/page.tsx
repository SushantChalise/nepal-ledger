import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { getForeignAidBreakdown } from '@/features/foreign-aid/server/queries';
import { AidBreakdownTable } from '@/features/foreign-aid/components/AidBreakdownTable';
import { formatBillion, formatSharePct } from '@/features/foreign-aid/format';

export const metadata: Metadata = {
  title: 'Foreign Aid — Who Funds Nepal | Nepal Ledger',
  description:
    'Foreign aid entering Nepal by development partner and by recipient ministry, split into grants (need not be repaid) and loans (must be repaid), for fiscal year 2020/21. A Money-In external-financing view. Source: MoF White Book (Source Book for Projects Financed with Foreign Assistance).',
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ForeignAidPage() {
  const result = await getForeignAidBreakdown();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <ForeignAidHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load foreign-aid data
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

  if (data.byDonor.members.length === 0 || data.byDonor.grandTotal <= 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <ForeignAidHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No foreign-aid data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            The donor and sector breakdown will appear here once the White Book summary tables are
            ingested.
          </p>
        </div>
      </main>
    );
  }

  const { byDonor, bySector } = data;
  // Ranked by total desc — the first donor is the largest funder.
  const topDonor = byDonor.members[0]!;
  const grantPctOfTotal = (byDonor.totalGrant / byDonor.grandTotal) * 100;
  const loanPctOfTotal = (byDonor.totalLoan / byDonor.grandTotal) * 100;

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <ForeignAidHeader fiscalYearBs={data.fiscalYearBs} fiscalYearAd={data.fiscalYearAd} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. Confidence B. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total foreign aid"
          value={formatBillion(byDonor.grandTotal, 1)}
          unit=""
          period={`grant + loan · FY ${data.fiscalYearAd}`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Total grants"
          value={formatBillion(byDonor.totalGrant, 1)}
          unit=""
          period={`${formatSharePct(grantPctOfTotal)} of aid · need not be repaid`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Total loans"
          value={formatBillion(byDonor.totalLoan, 1)}
          unit=""
          period={`${formatSharePct(loanPctOfTotal)} of aid · must be repaid`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Top development partner"
          value={topDonor.label}
          unit=""
          period={`${formatBillion(topDonor.total, 1)} · ${formatSharePct((topDonor.total / byDonor.grandTotal) * 100)} of aid`}
          confidence={data.confidence}
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Foreign aid flowing{' '}
          <span className="font-medium">into</span> Nepal in fiscal year {data.fiscalYearAd} (BS{' '}
          {data.fiscalYearBs}) — external financing, the &ldquo;Money In&rdquo; story — broken out
          by who provides it (<span className="font-medium">development partner</span>) and which
          ministry receives it (<span className="font-medium">sector</span>). Across{' '}
          {byDonor.memberCount} partners the total is{' '}
          <span className="font-medium">{formatBillion(byDonor.grandTotal, 1)}</span>:{' '}
          {formatSharePct(grantPctOfTotal)} as <span className="font-medium">grants</span> and{' '}
          {formatSharePct(loanPctOfTotal)} as <span className="font-medium">loans</span>. The
          grant-versus-loan split matters: grants need not be repaid, but loans add to Nepal&apos;s
          external debt and must be paid back with interest. The largest single funder is{' '}
          <span className="font-medium">{topDonor.label}</span> ({formatBillion(topDonor.total, 1)}
          ).
          {data.priorDonor !== null && (
            <>
              {' '}
              For comparison, total aid was{' '}
              <span className="font-medium">{formatBillion(data.priorDonor.grandTotal, 1)}</span> in
              FY {data.priorDonor.fiscalYearAd} — FY {data.fiscalYearAd} was a COVID-year surge
              (emergency budget-support loans from the IMF, World Bank and ADB).
            </>
          )}
        </p>
      </div>

      {/* Ranked donor table — the headline breakdown. */}
      <section aria-labelledby="donor-table-heading" className="mt-8">
        <h2
          id="donor-table-heading"
          className="mb-4 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Foreign aid by development partner — grant vs loan, FY {data.fiscalYearAd}
        </h2>
        <AidBreakdownTable
          breakdown={byDonor}
          memberNoun="Development partner"
          fiscalYearBs={data.fiscalYearBs}
          captionId="donor-table-caption"
        />
      </section>

      {/* Sector (ministry) breakdown. */}
      {bySector.members.length > 0 && bySector.grandTotal > 0 && (
        <section aria-labelledby="sector-table-heading" className="mt-10">
          <h2
            id="sector-table-heading"
            className="mb-1 text-base font-semibold text-zinc-700 dark:text-zinc-300"
          >
            Foreign aid by recipient ministry — grant vs loan, FY {data.fiscalYearAd}
          </h2>
          <p className="mb-4 max-w-2xl text-sm text-zinc-500 dark:text-zinc-400">
            The same aid total, viewed by the government ministry that receives and spends it. Grand
            total {formatBillion(bySector.grandTotal, 1)} across {bySector.memberCount} ministries.
          </p>
          <AidBreakdownTable
            breakdown={bySector}
            memberNoun="Recipient ministry"
            fiscalYearBs={data.fiscalYearBs}
            captionId="sector-table-caption"
          />
        </section>
      )}

      {/* Source attribution + confidence — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-10 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>MoF White Book — Source Book for Projects Financed with Foreign Assistance</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800">
                Grade {data.confidence}
              </span>
              <span className="ml-1">— budget-book allocations, revised across editions</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>NPR billion (converted per edition from the source&apos;s lakh / thousand)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Reference:</dt>
            <dd>
              FY {data.fiscalYearAd} (BS {data.fiscalYearBs})
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Figures are the Total Grant and Total Loan columns from the White Book&apos;s
          &ldquo;Development Partnerwise Summary&rdquo; and &ldquo;Summary of Ministrywise
          Development Partners&rdquo; tables. The source money unit{' '}
          <span className="font-medium">varies by edition</span> — NPR lakh (×100,000) for FY{' '}
          {data.fiscalYearAd}, NPR thousand for the older comparison edition — so each figure is
          converted to NPR billion using its own edition&apos;s unit before any total is summed;
          figures from different editions are never added on the raw scale. Donor and ministry names
          are shown as recorded in the source (English &ldquo;unofficial translation&rdquo;).{' '}
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

type ForeignAidHeaderProps = {
  fiscalYearBs?: string;
  fiscalYearAd?: string;
};

function ForeignAidHeader({ fiscalYearBs, fiscalYearAd }: ForeignAidHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Foreign Aid — Who Funds Nepal
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        A large share of Nepal&apos;s development spending is financed from abroad. This lens
        follows that external money in — which{' '}
        <span className="font-medium">development partners</span> fund Nepal, in what form (
        <span className="font-medium">grant</span> versus <span className="font-medium">loan</span>
        ), and which ministries receive it. Grants need not be repaid; loans must.
      </p>
      {fiscalYearAd !== undefined && fiscalYearBs !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>
            Reference: FY {fiscalYearAd} (BS {fiscalYearBs})
          </span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">MoF White Book</span>
          </span>
        </p>
      )}
    </header>
  );
}
