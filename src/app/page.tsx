import Link from 'next/link';

import type { ApprovedIndicatorWithMeta } from '@/lib/db/repositories/approved-indicator-values';
import { listApprovedWithIndicator } from '@/lib/db/repositories/approved-indicator-values';
import { formatIndicatorValue } from '@/lib/format/indicator-units';
import { KpiCard } from '@/features/pulse/components/KpiCard';

// The 5 headline slugs shown on the homepage — one per pillar.
const HERO_SLUGS: readonly string[] = [
  'cmefs-ncpi-yoy-overall',
  'cmefs-remittance-inflow-ytd',
  'cmefs-gross-forex-reserves',
  'cmefs-trade-deficit-ytd',
  'cmefs-bop-surplus-ytd',
];

const LENSES: readonly { title: string; href: string; description: string }[] = [
  {
    title: 'Pulse',
    href: '/pulse',
    description: 'All approved macro indicators grouped by prices, flows, government, and monetary.',
  },
  {
    title: 'Money Map',
    href: '/money-map',
    description: 'D3 Sankey of flows entering, circulating, leaking, and destroyed.',
  },
  {
    title: 'Growth',
    href: '/growth',
    description: 'GDP, sector contributions, and structural change over time.',
  },
  {
    title: 'Trade',
    href: '/trade',
    description: 'Exports, imports, and the trade deficit by commodity and partner.',
  },
  {
    title: 'Migration',
    href: '/migration',
    description: 'Remittances, worker departures, and the true cost of leaving Nepal.',
  },
  {
    title: 'Tourism Rupee',
    href: '/tourism-rupee',
    description: 'Arrivals, earnings, and how much of each tourist dollar stays in Nepal.',
  },
  {
    title: 'State Enterprises',
    href: '/state-enterprises',
    description: 'SOE profit, loss, government transfers, and consolidated balance sheets.',
  },
];

export default async function HomePage() {
  const result = await listApprovedWithIndicator();

  const heroRows: ApprovedIndicatorWithMeta[] = result.ok
    ? (HERO_SLUGS
        .map((slug) => result.value.find((r) => r.indicator.slug === slug))
        .filter((r): r is ApprovedIndicatorWithMeta => r !== undefined))
    : [];

  const reportingPeriod = heroRows[0]?.value.reportingPeriodBs;

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      {/* Mission */}
      <header className="mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
          Nepal Ledger
        </h1>
        <p className="mt-4 max-w-2xl text-xl text-zinc-600 dark:text-zinc-400">
          Tracks whether Nepal&apos;s money becomes wealth.
        </p>
      </header>

      {/* Monthly Verdict placeholder */}
      <section
        aria-label="Monthly Verdict"
        className="mb-12 rounded-xl border border-zinc-200 bg-zinc-50 p-6 dark:border-zinc-700 dark:bg-zinc-900"
      >
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
          Monthly Verdict
        </p>
        <h2 className="mt-2 text-lg font-semibold text-zinc-700 dark:text-zinc-300">
          Coming soon — the habit loop
        </h2>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
          On the 25th of each month, the Monthly Verdict synthesises the latest NRB data release
          into a five-pillar assessment: Money In, Money Out, Money Captured, Money Wasted, and
          Where Money Becomes Wealth.
        </p>
      </section>

      {/* 5 hero KPI cards */}
      <section aria-label="Key indicators">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200">
            5 numbers that mattered
            {reportingPeriod !== undefined && (
              <span className="ml-2 text-sm font-normal text-zinc-500">— {reportingPeriod}</span>
            )}
          </h2>
          <Link
            href="/pulse"
            className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
          >
            All indicators →
          </Link>
        </div>

        {heroRows.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {heroRows.map((row) => {
              const { display, unit } = formatIndicatorValue(row.value.value, row.indicator.unit);
              return (
                <KpiCard
                  key={row.value.id}
                  label={row.indicator.nameEn}
                  value={display}
                  unit={unit}
                  period={row.value.reportingPeriodBs}
                  confidence={row.value.confidenceGrade}
                />
              );
            })}
          </div>
        ) : (
          <div
            role="status"
            className="rounded-lg border border-zinc-200 bg-zinc-50 p-8 text-center dark:border-zinc-700 dark:bg-zinc-900"
          >
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Data appears here once the first approved ingest run completes.
            </p>
          </div>
        )}
      </section>

      {/* Lenses */}
      <section aria-label="Explore by lens" className="mt-16">
        <h2 className="mb-4 text-lg font-semibold text-zinc-800 dark:text-zinc-200">
          Explore by lens
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {LENSES.map((lens) => (
            <Link
              key={lens.href}
              href={lens.href}
              className="group flex flex-col rounded-lg border border-zinc-200 bg-white p-4 shadow-sm transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-500"
            >
              <span className="font-medium text-zinc-900 group-hover:text-blue-600 dark:text-zinc-100 dark:group-hover:text-blue-400">
                {lens.title}
              </span>
              <span className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                {lens.description}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
