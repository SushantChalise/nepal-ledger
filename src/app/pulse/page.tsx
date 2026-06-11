import type { Metadata } from 'next';

import { listApprovedWithIndicator } from '@/lib/db/repositories/approved-indicator-values';
import type { ApprovedIndicatorWithMeta } from '@/lib/db/repositories/approved-indicator-values';
import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { KpiGroup } from '@/features/pulse/components/KpiGroup';

export const metadata: Metadata = {
  title: 'Pulse — Nepal Ledger',
  description:
    'Live macro indicators for Nepal: inflation, remittances, trade, fiscal balance, and World Bank structural benchmarks.',
};

// ---------------------------------------------------------------------------
// Group definitions — two sections: Current Flow (NRB CMEFs) + Benchmarks (WDI)
// ---------------------------------------------------------------------------

type FlowGroupKey = 'prices' | 'money-in' | 'money-out' | 'fiscal' | 'banking';
type BenchmarkGroupKey = 'economy' | 'inequality' | 'fiscal-ratios';

// CMEFs (NRB) — current-period flow data (9-months YTD / YoY)
const FLOW_SLUG_TO_GROUP: Record<string, FlowGroupKey> = {
  'cmefs-ncpi-yoy-overall': 'prices',
  'cmefs-m2-yoy': 'banking',
  'cmefs-private-sector-credit-yoy': 'banking',
  'cmefs-bfi-deposits-yoy': 'banking',
  'cmefs-remittance-inflow-ytd': 'money-in',
  'cmefs-bop-surplus-ytd': 'money-in',
  'cmefs-gross-forex-reserves': 'money-in',
  'cmefs-forex-reserves-months-of-import-cover': 'money-in',
  'cmefs-merchandise-exports-ytd': 'money-out',
  'cmefs-merchandise-imports-ytd': 'money-out',
  'cmefs-trade-deficit-ytd': 'money-out',
  'cmefs-govt-revenue-total-ytd': 'fiscal',
  'cmefs-govt-expenditure-total-ytd': 'fiscal',
  'cmefs-govt-fiscal-balance-ytd': 'fiscal',
};

// WDI (World Bank) — latest annual structural benchmarks
const BENCHMARK_SLUG_TO_GROUP: Record<string, BenchmarkGroupKey> = {
  'wdi-gdp-current-usd': 'economy',
  'wdi-gdp-constant-2015-usd': 'economy',
  'wdi-gdp-growth-annual-pct': 'economy',
  'wdi-gdp-per-capita-current-usd': 'economy',
  'wdi-gdp-per-capita-growth-pct': 'economy',
  'wdi-cpi-inflation-annual-pct': 'economy',
  'wdi-remittances-received-usd': 'economy',
  'wdi-remittances-pct-gdp': 'economy',
  'wdi-gni-current-usd': 'economy',
  'wdi-gni-per-capita-current-usd': 'economy',
  'wdi-poverty-headcount-national-pct': 'inequality',
  'wdi-gini-index': 'inequality',
  'wdi-gross-capital-formation-pct-gdp': 'fiscal-ratios',
  'wdi-central-govt-debt-pct-gdp': 'fiscal-ratios',
  'wdi-current-account-balance-pct-gdp': 'fiscal-ratios',
};

const FLOW_GROUP_META: Record<FlowGroupKey, { title: string; description: string }> = {
  prices: {
    title: 'Prices',
    description: 'Consumer price inflation — how fast the cost of living is rising.',
  },
  'money-in': {
    title: 'Money In',
    description: 'Remittances, balance of payments, and foreign-exchange reserves.',
  },
  'money-out': {
    title: 'Money Out / Trade',
    description: 'Exports, imports, and the trade deficit — net flows leaving Nepal.',
  },
  fiscal: {
    title: 'Fiscal',
    description: 'Government revenue, expenditure, and the fiscal balance year-to-date.',
  },
  banking: {
    title: 'Money Supply & Credit',
    description: 'Broad money (M2), private sector credit, and bank deposit growth.',
  },
};

const BENCHMARK_GROUP_META: Record<BenchmarkGroupKey, { title: string; description: string }> = {
  economy: {
    title: 'Economy',
    description: 'GDP, GNI, per-capita income, inflation, and remittances as structural measures.',
  },
  inequality: {
    title: 'Inequality',
    description: 'National poverty headcount and the Gini index of income distribution.',
  },
  'fiscal-ratios': {
    title: 'Fiscal Ratios',
    description:
      'Capital formation, central government debt, and the current account — as a share of GDP.',
  },
};

const FLOW_ORDER: FlowGroupKey[] = ['prices', 'money-in', 'money-out', 'fiscal', 'banking'];
const BENCHMARK_ORDER: BenchmarkGroupKey[] = ['economy', 'inequality', 'fiscal-ratios'];

// ---------------------------------------------------------------------------
// Value formatting
// ---------------------------------------------------------------------------

function formatValue(rawValue: string, unitSlug: string): { display: string; unit: string } {
  const num = parseFloat(rawValue);
  if (isNaN(num)) return { display: rawValue, unit: unitSlug };

  switch (unitSlug) {
    case 'NPR_billion':
    case 'npr_billion': {
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        unit: 'NPR B',
      };
    }
    case 'percent_yoy':
    case 'percent': {
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        unit: '%',
      };
    }
    case 'months_of_imports':
    case 'months': {
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: 'months',
      };
    }
    case 'usd_million': {
      if (Math.abs(num) >= 1000) {
        return {
          display: (num / 1000).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }),
          unit: 'USD B',
        };
      }
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: 'USD M',
      };
    }
    case 'usd': {
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }),
        unit: 'USD',
      };
    }
    case 'index_points': {
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: 'Gini',
      };
    }
    default: {
      return {
        display: num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        unit: unitSlug,
      };
    }
  }
}

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

  // Bucket rows into flow and benchmark groups.
  const flowBuckets = Object.fromEntries(FLOW_ORDER.map((k) => [k, [] as ApprovedIndicatorWithMeta[]])) as Record<FlowGroupKey, ApprovedIndicatorWithMeta[]>;
  const benchmarkBuckets = Object.fromEntries(BENCHMARK_ORDER.map((k) => [k, [] as ApprovedIndicatorWithMeta[]])) as Record<BenchmarkGroupKey, ApprovedIndicatorWithMeta[]>;
  const overflow: ApprovedIndicatorWithMeta[] = [];

  for (const row of rows) {
    const slug = row.indicator.slug;
    const flowGroup = FLOW_SLUG_TO_GROUP[slug];
    const benchmarkGroup = BENCHMARK_SLUG_TO_GROUP[slug];
    if (flowGroup !== undefined) {
      flowBuckets[flowGroup].push(row);
    } else if (benchmarkGroup !== undefined) {
      benchmarkBuckets[benchmarkGroup].push(row);
    } else {
      overflow.push(row);
    }
  }

  // Derive period labels per section from representative rows.
  const firstFlowRow = FLOW_ORDER.flatMap((k) => flowBuckets[k]).find(Boolean);
  const firstBenchmarkRow = BENCHMARK_ORDER.flatMap((k) => benchmarkBuckets[k]).find(Boolean);

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <PulseHeader />

      {/* Section 1: NRB CMEFs — current flow */}
      {firstFlowRow !== undefined && (
        <section aria-labelledby="flow-heading" className="mt-10">
          <div className="mb-6">
            <h2
              id="flow-heading"
              className="text-lg font-semibold text-zinc-900 dark:text-zinc-50"
            >
              Current Flow
            </h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              NRB Current Macroeconomic &amp; Financial Situation (CMEFs) ·{' '}
              {firstFlowRow.value.reportingPeriodBs}
            </p>
          </div>
          <div className="flex flex-col gap-10">
            {FLOW_ORDER.map((groupKey) => {
              const groupRows = flowBuckets[groupKey];
              if (groupRows.length === 0) return null;
              const meta = FLOW_GROUP_META[groupKey];
              return (
                <KpiGroup key={groupKey} title={meta.title} description={meta.description}>
                  {groupRows.map((row) => {
                    const { display, unit } = formatValue(row.value.value, row.indicator.unit);
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
          </div>
        </section>
      )}

      {/* Divider */}
      {firstFlowRow !== undefined && firstBenchmarkRow !== undefined && (
        <hr className="my-12 border-zinc-200 dark:border-zinc-800" />
      )}

      {/* Section 2: World Bank WDI — structural benchmarks */}
      {firstBenchmarkRow !== undefined && (
        <section aria-labelledby="benchmark-heading">
          <div className="mb-6">
            <h2
              id="benchmark-heading"
              className="text-lg font-semibold text-zinc-900 dark:text-zinc-50"
            >
              Structural Benchmarks
            </h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              World Bank WDI (annual) · {firstBenchmarkRow.value.reportingPeriodBs}
            </p>
          </div>
          <div className="flex flex-col gap-10">
            {BENCHMARK_ORDER.map((groupKey) => {
              const groupRows = benchmarkBuckets[groupKey];
              if (groupRows.length === 0) return null;
              const meta = BENCHMARK_GROUP_META[groupKey];
              return (
                <KpiGroup key={groupKey} title={meta.title} description={meta.description}>
                  {groupRows.map((row) => {
                    const { display, unit } = formatValue(row.value.value, row.indicator.unit);
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
          </div>
        </section>
      )}

      {/* Overflow — slugs not yet mapped to a display group */}
      {overflow.length > 0 && (
        <>
          {(firstFlowRow !== undefined || firstBenchmarkRow !== undefined) && (
            <hr className="my-12 border-zinc-200 dark:border-zinc-800" />
          )}
          <KpiGroup
            title="Other Indicators"
            description="Additional approved indicators not yet assigned to a display group."
          >
            {overflow.map((row) => {
              const { display, unit } = formatValue(row.value.value, row.indicator.unit);
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
        </>
      )}
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
        Nepal&apos;s macro indicators — current flow data from the Nepal Rastra Bank and annual
        structural benchmarks from the World Bank.
      </p>
      {reportingPeriod !== undefined && sourceAgency !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reporting period: {reportingPeriod}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">{sourceAgency}</span>
          </span>
        </p>
      )}
    </header>
  );
}
