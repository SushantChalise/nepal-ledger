import type { Metadata } from 'next';

import { listApprovedWithIndicator } from '@/lib/db/repositories/approved-indicator-values';
import type { ApprovedIndicatorWithMeta } from '@/lib/db/repositories/approved-indicator-values';
import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { KpiGroup } from '@/features/pulse/components/KpiGroup';
import { formatIndicatorValue } from '@/lib/format/indicator-units';

export const metadata: Metadata = {
  title: 'Pulse — Nepal Ledger',
  description:
    'Live macro indicators for Nepal: inflation, remittances, trade balance, forex reserves. Data sourced from Nepal Rastra Bank CMEFs.',
};

// ---------------------------------------------------------------------------
// Pulse groups — ordered for page presentation.
// Slugs that do not match any bucket fall into "Other Indicators".
// ---------------------------------------------------------------------------

type PulseGroupKey = 'prices' | 'money-in' | 'money-out' | 'government' | 'monetary';

const SLUG_TO_GROUP: Record<string, PulseGroupKey> = {
  // Prices
  'cmefs-ncpi-yoy-overall': 'prices',
  // Money In
  'cmefs-remittance-inflow-ytd': 'money-in',
  'cmefs-merchandise-exports-ytd': 'money-in',
  'cmefs-bop-surplus-ytd': 'money-in',
  'cmefs-gross-forex-reserves': 'money-in',
  'cmefs-forex-reserves-months-of-import-cover': 'money-in',
  // Money Out / Trade
  'cmefs-merchandise-imports-ytd': 'money-out',
  'cmefs-trade-deficit-ytd': 'money-out',
  // Government Finance
  'cmefs-govt-revenue-total-ytd': 'government',
  'cmefs-govt-expenditure-total-ytd': 'government',
  'cmefs-govt-fiscal-balance-ytd': 'government',
  // Monetary
  'cmefs-m2-yoy': 'monetary',
  'cmefs-private-sector-credit-yoy': 'monetary',
  'cmefs-bfi-deposits-yoy': 'monetary',
};

const GROUP_META: Record<PulseGroupKey, { title: string; description: string }> = {
  prices: {
    title: 'Prices',
    description: 'Consumer price inflation measures how fast the cost of living is rising.',
  },
  'money-in': {
    title: 'Money In',
    description:
      'Remittances, exports, balance of payments surplus, and foreign-exchange reserves flowing into Nepal.',
  },
  'money-out': {
    title: 'Money Out / Trade',
    description: 'Merchandise imports and the trade deficit represent money leaving Nepal.',
  },
  government: {
    title: 'Government Finance',
    description:
      'Fiscal position: government revenue, expenditure, and the resulting surplus or deficit.',
  },
  monetary: {
    title: 'Monetary',
    description:
      'Money supply growth (M2), private-sector credit, and BFI deposit trends on a year-on-year basis.',
  },
};

const GROUP_ORDER: PulseGroupKey[] = ['prices', 'money-in', 'money-out', 'government', 'monetary'];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function PulsePage() {
  const result = await listApprovedWithIndicator();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <PulseHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load indicators
          </p>
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">
            {formatAppError(result.error)}
          </p>
        </div>
      </main>
    );
  }

  const rows = result.value;

  if (rows.length === 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <PulseHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">No data yet</p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            Approved indicators will appear here once the first ingestion run completes.
          </p>
        </div>
      </main>
    );
  }

  // Group rows into display buckets.
  const buckets: Record<PulseGroupKey, ApprovedIndicatorWithMeta[]> = {
    prices: [],
    'money-in': [],
    'money-out': [],
    government: [],
    monetary: [],
  };
  const overflow: ApprovedIndicatorWithMeta[] = [];

  for (const row of rows) {
    const group = SLUG_TO_GROUP[row.indicator.slug];
    if (group !== undefined) {
      buckets[group].push(row);
    } else {
      overflow.push(row);
    }
  }

  // Use the first row's reporting period label and source for the header.
  const firstRow = rows[0];
  const reportingPeriod = firstRow?.value.reportingPeriodBs ?? 'Unknown period';
  const sourceAgency = firstRow?.indicator.sourceAgency ?? 'Nepal Rastra Bank';

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <PulseHeader reportingPeriod={reportingPeriod} sourceAgency={sourceAgency} />

      <div className="mt-10 flex flex-col gap-10">
        {GROUP_ORDER.map((groupKey) => {
          const groupRows = buckets[groupKey];
          if (groupRows.length === 0) return null;
          const meta = GROUP_META[groupKey];
          return (
            <KpiGroup key={groupKey} title={meta.title} description={meta.description}>
              {groupRows.map((row) => {
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
            </KpiGroup>
          );
        })}

        {overflow.length > 0 && (
          <KpiGroup
            title="Other Indicators"
            description="Additional approved indicators not yet categorised into a Pulse group."
          >
            {overflow.map((row) => {
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
          </KpiGroup>
        )}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type PulseHeaderProps = {
  reportingPeriod?: string;
  sourceAgency?: string;
};

function PulseHeader({ reportingPeriod, sourceAgency }: PulseHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">Pulse</h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        Live macro indicators tracking how Nepal&apos;s money moves — prices, external flows, and
        reserves. Updated when the Nepal Rastra Bank publishes new data.
      </p>
      {reportingPeriod !== undefined && sourceAgency !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reporting period: {reportingPeriod}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {sourceAgency} — Current Macroeconomic and Financial Situation (CMEFs)
            </span>
          </span>
        </p>
      )}
    </header>
  );
}
