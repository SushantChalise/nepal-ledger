import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { getTouristArrivalsSeries } from '@/features/tourism-rupee/server/queries';
import { ArrivalsLineChart } from '@/features/tourism-rupee/components/ArrivalsLineChart';
import { formatCountFull, formatMonthLabel, formatYoyPct } from '@/features/tourism-rupee/format';

export const metadata: Metadata = {
  title: 'Tourism Rupee — Nepal Ledger',
  description:
    "Monthly tourist arrivals to Nepal, 1992–2025. Thirty-four years of the tourism economy's leading indicator — from the pre-pandemic peak through the COVID-19 collapse and recovery. Source: Nepal Rastra Bank Database on Nepalese Economy.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function TourismRupeePage() {
  const result = await getTouristArrivalsSeries();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <TourismHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load tourist-arrivals data
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

  const series = result.value;

  if (series.points.length === 0 || series.latest === null) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <TourismHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No tourist-arrivals data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            The monthly arrivals series will appear here once the first ingestion run completes.
          </p>
        </div>
      </main>
    );
  }

  const latest = series.latest;
  const latestMonth = formatMonthLabel(new Date(latest.adEnd));
  const peak = series.points.reduce((m, p) => (p.arrivals > m.arrivals ? p : m), series.points[0]!);
  const yoyLabel = formatYoyPct(series.yoyPct);

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <TourismHeader latestMonth={latestMonth} sourceAgency={series.sourceAgency} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          label="Latest monthly arrivals"
          value={formatCountFull(latest.arrivals)}
          unit="tourists"
          period={latestMonth}
          confidence={series.confidence}
        />
        <KpiCard
          label="Year-over-year change"
          value={yoyLabel}
          unit=""
          period={`vs. same month, prior year`}
          confidence={series.confidence}
        />
        <KpiCard
          label="Record month"
          value={formatCountFull(peak.arrivals)}
          unit="tourists"
          period={formatMonthLabel(new Date(peak.adEnd))}
          confidence={series.confidence}
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Monthly tourist arrivals are the
          tourism economy&apos;s leading indicator — every arrival is a potential inflow of foreign
          currency. The series climbs for three decades to a pre-pandemic peak of{' '}
          <span className="font-medium">{formatCountFull(peak.arrivals)}</span> in{' '}
          {formatMonthLabel(new Date(peak.adEnd))}, collapses to near zero during the 2020 COVID-19
          border closure, and recovers toward {formatCountFull(latest.arrivals)} by {latestMonth}.
          The line is plotted on each month&apos;s Gregorian (AD) end date for an accurate time
          axis.
        </p>
      </div>

      {/* Chart */}
      <section aria-labelledby="arrivals-chart-heading" className="mt-8">
        <h2
          id="arrivals-chart-heading"
          className="mb-4 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Monthly Tourist Arrivals — {formatMonthLabel(new Date(series.points[0]!.adEnd))} to{' '}
          {latestMonth}
        </h2>
        <ArrivalsLineChart points={series.points} />
      </section>

      {/* Corridor leakage — coming soon (disabled placeholder; no fabricated data). */}
      <section aria-labelledby="corridor-leakage-heading" className="mt-10">
        <h2
          id="corridor-leakage-heading"
          className="mb-3 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Where the tourism rupee leaks
        </h2>
        <div
          aria-disabled="true"
          className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-6 text-center dark:border-zinc-700 dark:bg-zinc-900/50"
        >
          <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
            Corridor leakage — coming soon
          </p>
          <p className="mx-auto mt-1 max-w-md text-xs text-zinc-400 dark:text-zinc-500">
            How much of each tourism rupee stays in Nepal versus leaking to foreign-owned airlines,
            booking platforms, and imported goods. This view is not yet available — we will not show
            an estimate until the underlying flow data is ingested and verified.
          </p>
        </div>
      </section>

      {/* Source attribution + confidence — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>Nepal Rastra Bank — Database on Nepalese Economy</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800">
                Grade {series.confidence}
              </span>
              <span className="ml-1">— official NRB compilation</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>Tourist arrivals (count)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Latest:</dt>
            <dd>{latestMonth}</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Arrivals are plotted on each month&apos;s Gregorian (AD) end date. The series spans{' '}
          {series.points.length} monthly observations.{' '}
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

type TourismHeaderProps = {
  latestMonth?: string;
  sourceAgency?: string;
};

function TourismHeader({ latestMonth, sourceAgency }: TourismHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Tourism Rupee
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        Tourism is one of Nepal&apos;s largest sources of foreign currency. This lens tracks monthly
        tourist arrivals — the leading indicator of the tourism economy — over three decades, from
        the pre-pandemic peak through the COVID-19 collapse and the recovery that followed.
      </p>
      {latestMonth !== undefined && sourceAgency !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Latest month: {latestMonth}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {sourceAgency} — Database on Nepalese Economy
            </span>
          </span>
        </p>
      )}
    </header>
  );
}
