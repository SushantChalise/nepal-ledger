import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { getGrowthData } from '@/features/growth/server/queries';
import { GdpTrajectoryChart } from '@/features/growth/components/GdpTrajectoryChart';
import { RateSeriesTable } from '@/features/growth/components/RateSeriesTable';
import {
  formatFiscalYear,
  formatIndex,
  formatNprFromBillion,
  formatPercent,
  formatUsd,
} from '@/features/growth/format';

export const metadata: Metadata = {
  title: 'Growth — Nepal Ledger',
  description:
    "Nepal's headline economy at a glance: nominal and real GDP, the real growth rate, per-capita GDP in US dollars, and consumer-price inflation — roughly fifty fiscal years each. Is the economy growing, and is it becoming wealth per person? Source: Nepal Rastra Bank Database on Nepalese Economy.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function GrowthPage() {
  const result = await getGrowthData();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <GrowthHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load Nepal&apos;s macro data
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

  // The page is anchored on the four headline KPIs. If NONE of them has a
  // latest value, the dataset is effectively empty → render the empty state.
  const anyHeadline =
    data.gdpNominal.latest !== null ||
    data.gdpReal.latest !== null ||
    data.gdpRealGrowth.latest !== null ||
    data.perCapitaUsd.latest !== null;

  if (!anyHeadline) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <GrowthHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No macro data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            Nepal&apos;s GDP, growth, inflation, and per-capita series will appear here once the
            first ingestion run completes.
          </p>
        </div>
      </main>
    );
  }

  const latestNominal = data.gdpNominal.latest;
  const latestReal = data.gdpReal.latest;
  const latestGrowth = data.gdpRealGrowth.latest;
  const latestPerCapita = data.perCapitaUsd.latest;
  const latestCpi = data.cpi.latest;
  const latestInflation = data.inflationRate.latest;

  // Most-recent fiscal year across the headline series, for the header line.
  const latestFy =
    latestNominal?.fiscalYearBs ??
    latestReal?.fiscalYearBs ??
    latestGrowth?.fiscalYearBs ??
    latestPerCapita?.fiscalYearBs ??
    null;

  const sourceAgency = data.gdpNominal.sourceAgency || 'Nepal Rastra Bank';

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <GrowthHeader latestFy={latestFy ?? undefined} sourceAgency={sourceAgency} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Nominal GDP"
          value={latestNominal ? formatNprFromBillion(latestNominal.value) : '—'}
          unit=""
          period={latestNominal ? formatFiscalYear(latestNominal.fiscalYearBs) : 'no data'}
          confidence={data.gdpNominal.confidence}
        />
        <KpiCard
          label="Real GDP growth"
          value={latestGrowth ? formatPercent(latestGrowth.value) : '—'}
          unit=""
          period={latestGrowth ? formatFiscalYear(latestGrowth.fiscalYearBs) : 'no data'}
          confidence={data.gdpRealGrowth.confidence}
        />
        <KpiCard
          label="Per-capita GDP"
          value={latestPerCapita ? formatUsd(latestPerCapita.value) : '—'}
          unit="per person"
          period={latestPerCapita ? formatFiscalYear(latestPerCapita.fiscalYearBs) : 'no data'}
          confidence={data.perCapitaUsd.confidence}
        />
        <KpiCard
          label="Consumer-price inflation"
          value={latestInflation ? formatPercent(latestInflation.value) : '—'}
          unit=""
          period={latestInflation ? formatFiscalYear(latestInflation.fiscalYearBs) : 'no data'}
          confidence={data.inflationRate.confidence}
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md, and the
          mission framing: growth vs. wealth-per-person. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Nepal&apos;s mission question in
          four numbers. <span className="font-medium">Nominal GDP</span> is the size of the economy
          in today&apos;s rupees; <span className="font-medium">real GDP</span> strips out price
          rises, so the gap between the two lines below is inflation&apos;s cumulative bite. The{' '}
          <span className="font-medium">real growth rate</span> says whether the economy is
          genuinely expanding after inflation — but a growing economy only becomes{' '}
          <span className="font-medium">wealth per person</span> if output outpaces population,
          which is exactly what <span className="font-medium">per-capita GDP</span> (
          {latestPerCapita ? formatUsd(latestPerCapita.value) : '—'}
          {latestPerCapita ? ` in ${formatFiscalYear(latestPerCapita.fiscalYearBs)}` : ''})
          measures. Inflation is the headwind: it erodes what each rupee of that wealth can buy.
        </p>
      </div>

      {/* GDP trajectory chart (nominal vs real). */}
      {data.gdpNominal.points.length > 0 && data.gdpReal.points.length > 0 ? (
        <section aria-labelledby="gdp-chart-heading" className="mt-8">
          <h2
            id="gdp-chart-heading"
            className="mb-1 text-base font-semibold text-zinc-700 dark:text-zinc-300"
          >
            GDP trajectory — nominal vs real (NPR trillion)
          </h2>
          <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
            Both lines are gross domestic product. Nominal includes price rises; real holds prices
            constant. The widening gap is the cumulative effect of inflation.
            {latestNominal && latestReal
              ? ` Latest (${formatFiscalYear(latestNominal.fiscalYearBs)}): nominal ${formatNprFromBillion(
                  latestNominal.value,
                )}, real ${formatNprFromBillion(latestReal.value)}.`
              : ''}
          </p>
          <GdpTrajectoryChart nominal={data.gdpNominal.points} real={data.gdpReal.points} />
        </section>
      ) : (
        <SeriesUnavailable
          headingId="gdp-chart-heading"
          title="GDP trajectory — nominal vs real"
          detail="The nominal and real GDP series will be charted here once both are ingested."
        />
      )}

      {/* Inflation rate series (text/table). */}
      {data.inflationRate.points.length > 0 ? (
        <section aria-labelledby="inflation-heading" className="mt-10">
          <h2
            id="inflation-heading"
            className="mb-1 text-base font-semibold text-zinc-700 dark:text-zinc-300"
          >
            Consumer-price inflation — recent fiscal years
          </h2>
          <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
            Year-on-year change in the national consumer price index. This is the headwind that
            decides how much real purchasing power each rupee of growth delivers.
            {latestCpi
              ? ` Latest index level (${formatFiscalYear(latestCpi.fiscalYearBs)}): ${formatIndex(
                  latestCpi.value,
                )} — an index, base year ≈ 2014/15 = 100, not a currency amount.`
              : ''}
          </p>
          <RateSeriesTable points={data.inflationRate.points} rateLabel="CPI inflation" />
        </section>
      ) : (
        <SeriesUnavailable
          headingId="inflation-heading"
          title="Consumer-price inflation"
          detail="The CPI inflation series will appear here once it is ingested."
        />
      )}

      {/* Source attribution + confidence + units — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-10 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>Nepal Rastra Bank — Database on Nepalese Economy</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800">
                Grade {data.gdpNominal.confidence}
              </span>
              <span className="ml-1">— official NRB compilation</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Units:</dt>
            <dd>GDP in NPR (billion at rest, shown as trillion); per-capita in USD; rates in %</dd>
          </div>
          {latestFy && (
            <div className="flex gap-1">
              <dt className="font-medium text-zinc-600 dark:text-zinc-400">Latest:</dt>
              <dd>{formatFiscalYear(latestFy)}</dd>
            </div>
          )}
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Nominal and real GDP are stored in NPR billion and shown as NPR trillion (÷ 1,000).
          Per-capita GDP is a US-dollar, per-person figure. The consumer price index is an index
          level (base year ≈ 2014/15 = 100), not currency.{' '}
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

type GrowthHeaderProps = {
  latestFy?: string | undefined;
  sourceAgency?: string | undefined;
};

function GrowthHeader({ latestFy, sourceAgency }: GrowthHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">Growth</h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        The headline mission numbers: how big Nepal&apos;s economy is, how fast it is really growing
        after inflation, what that amounts to per person in US dollars, and how quickly prices are
        rising. Roughly fifty fiscal years of each, so the trend — not a single year — tells the
        story.
      </p>
      {latestFy !== undefined && sourceAgency !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Latest fiscal year: {formatFiscalYear(latestFy)}</span>
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

/**
 * Typed "section unavailable" placeholder for a single series that returned no
 * rows while the rest of the page has data. Never fabricates a figure to fill
 * the gap (Data Continuity Protocol) — states plainly that the series is not
 * yet available. Referenced unused-prop-free so it satisfies the linter.
 */
function SeriesUnavailable({
  headingId,
  title,
  detail,
}: {
  headingId: string;
  title: string;
  detail: string;
}) {
  return (
    <section aria-labelledby={headingId} className="mt-10">
      <h2 id={headingId} className="mb-3 text-base font-semibold text-zinc-700 dark:text-zinc-300">
        {title}
      </h2>
      <div
        aria-disabled="true"
        className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-6 text-center dark:border-zinc-700 dark:bg-zinc-900/50"
      >
        <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          Series not yet available
        </p>
        <p className="mx-auto mt-1 max-w-md text-xs text-zinc-400 dark:text-zinc-500">{detail}</p>
      </div>
    </section>
  );
}
