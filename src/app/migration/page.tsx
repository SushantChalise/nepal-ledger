import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import {
  getMigrationByCountrySeries,
  getAbsenteeShareByPalika,
} from '@/features/migration-source/server/queries';
import { DestinationBarChart } from '@/features/migration-source/components/DestinationBarChart';
import { PalikaChoropleth } from '@/features/migration-source/components/PalikaChoropleth';
import { formatPeopleFull, formatSharePct } from '@/features/migration-source/format';

export const metadata: Metadata = {
  title: 'Migration — Where Nepal’s Absent Population Is | Nepal Ledger',
  description:
    "Nepal's absent population — the people living abroad on census night — ranked by destination region, from the 2021 census. A Money-OUT view of labour migration: counts of people, not remittance rupees. Source: CBS National Population & Housing Census 2021.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function MigrationPage() {
  const result = await getMigrationByCountrySeries(15);

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <MigrationHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load absent-population data
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
  // Independent of the destination ranking — the origin choropleth has its own
  // typed fallback and must never break the page if the census slice is absent.
  const palikaResult = await getAbsenteeShareByPalika();

  if (data.destinations.length === 0 || data.totalPeople <= 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <MigrationHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No absent-population data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            The destination ranking will appear here once the census table is ingested.
          </p>
        </div>
      </main>
    );
  }

  const top = data.destinations[0]!;
  const second = data.destinations[1];

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <MigrationHeader censusYearAd={data.censusYearAd} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. Confidence A. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          label="Absent population abroad"
          value={formatPeopleFull(data.totalPeople)}
          unit="people"
          period={`Census ${data.censusYearAd}`}
          confidence="A"
        />
        <KpiCard
          label="Top destination"
          value={top.label}
          unit=""
          period={`${formatPeopleFull(top.people)} people · ${formatSharePct(top.sharePct)}`}
          confidence="A"
        />
        <KpiCard
          label="Local levels covered"
          value={data.palikaCount.toLocaleString('en-IN')}
          unit="palikas"
          period="All 753 local governments"
          confidence="A"
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Where Nepal&apos;s{' '}
          <span className="font-medium">absent population</span> — household members living abroad
          on census night — was located in {data.censusYearAd}, ranked by destination region. This
          is a headcount of <span className="font-medium">people</span>, the labour-migration side
          of Money OUT; it is <span className="font-medium">not</span> remittance and carries no
          rupee figure. The largest destination is <span className="font-medium">{top.label}</span>{' '}
          ({formatSharePct(top.sharePct)})
          {second ? (
            <>
              , followed by <span className="font-medium">{second.label}</span> (
              {formatSharePct(second.sharePct)})
            </>
          ) : null}
          . The census groups destinations by region — individual Gulf states fall under the Middle
          East and Malaysia under ASEAN — so labels are regions, not single countries.
        </p>
      </div>

      {/* Chart */}
      <section aria-labelledby="destinations-chart-heading" className="mt-8">
        <h2
          id="destinations-chart-heading"
          className="mb-4 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Absent population by destination region — {data.censusYearAd} census
        </h2>
        <DestinationBarChart destinations={data.destinations} />
      </section>

      {/* View B — where the absent population comes FROM, by palika (choropleth). */}
      <section aria-labelledby="origin-map-heading" className="mt-10">
        <h2
          id="origin-map-heading"
          className="mb-1 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Migration intensity — share of each local level&apos;s population abroad
        </h2>
        <p className="mb-4 max-w-2xl text-sm text-zinc-500 dark:text-zinc-400">
          The same {data.censusYearAd} census, mapped to each of Nepal&apos;s 753 local levels: the{' '}
          <span className="font-medium">share of the local population living abroad</span> on census
          night (absent population ÷ total population). Darker means a larger share of the community
          is away. Still a count of <span className="font-medium">people</span> underneath — not
          remittance.
        </p>
        {palikaResult.ok ? (
          <PalikaChoropleth
            byCode={palikaResult.value.byCode}
            nationalPct={palikaResult.value.nationalPct}
            censusYearAd={palikaResult.value.censusYearAd}
            palikaCount={palikaResult.value.palikaCount}
          />
        ) : (
          <div
            role="status"
            aria-live="polite"
            className="rounded-lg border border-zinc-200 bg-zinc-50 p-8 text-center dark:border-zinc-700 dark:bg-zinc-900"
          >
            <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
              Per-palika map not available yet
            </p>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-500">
              The 753-local-level choropleth appears here once the census origin slice is loaded.
            </p>
          </div>
        )}
      </section>

      {/* Where the money lands — coming soon (disabled placeholder; no fabricated data). */}
      <section aria-labelledby="remittance-map-heading" className="mt-10">
        <h2
          id="remittance-map-heading"
          className="mb-3 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Where the remittance rupee lands
        </h2>
        <div
          aria-disabled="true"
          className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-6 text-center dark:border-zinc-700 dark:bg-zinc-900/50"
        >
          <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
            Remittance by recipient district — coming soon
          </p>
          <p className="mx-auto mt-1 max-w-md text-xs text-zinc-400 dark:text-zinc-500">
            A district choropleth of where remittance rupees are received. This view is not yet
            available — the census table on this page counts people by destination, not money by
            recipient district, and we will not show a rupee estimate until the underlying flow data
            is ingested and verified.
          </p>
        </div>
      </section>

      {/* Source attribution + confidence — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>CBS National Population &amp; Housing Census 2021</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-800">
                Grade A
              </span>
              <span className="ml-1">— official census enumeration</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>Absent population (people / count)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Reference:</dt>
            <dd>Census {data.censusYearAd}</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Counts are the absent population by destination region, summed across all{' '}
          {data.palikaCount.toLocaleString('en-IN')} local levels (sex = total, all ages — a single
          non-overlapping census slice).{' '}
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

type MigrationHeaderProps = {
  censusYearAd?: string;
};

function MigrationHeader({ censusYearAd }: MigrationHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Migration — Where Nepal&apos;s Absent Population Is
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        On census night in 2021, more than two million Nepalis were living abroad. This lens ranks
        their destinations by region — the labour-migration side of Money OUT. It counts{' '}
        <span className="font-medium">people</span>, not remittance rupees.
      </p>
      {censusYearAd !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reference: Census {censusYearAd}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              CBS National Population &amp; Housing Census 2021
            </span>
          </span>
        </p>
      )}
    </header>
  );
}
