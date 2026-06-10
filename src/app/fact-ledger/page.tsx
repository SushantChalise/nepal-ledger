import type { Metadata } from 'next';
import Link from 'next/link';

import { ConfidenceBadge } from '@/features/fact-ledger/components/ConfidenceBadge';
import { LedgerTable } from '@/features/fact-ledger/components/LedgerTable';
import { CATEGORY_LABELS, FACT_TABLE_LABELS, formatRowCount } from '@/features/fact-ledger/format';
import { getFactLedgerView } from '@/features/fact-ledger/server/queries';
import { formatAppError } from '@/lib/errors';

export const metadata: Metadata = {
  title: 'Fact Ledger — Nepal Ledger',
  description:
    "Every published economic number, browsable with its source and confidence grade. Nepal Ledger's auditable claims database: indicator, value, period, confidence (A/B/C), and source agency.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function FactLedgerPage() {
  const result = await getFactLedgerView();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <LedgerHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load the Fact Ledger
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

  const view = result.value;

  if (view.totalEntries === 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <LedgerHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No approved facts yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            Every published number will appear here once the first ingestion run promotes data to
            production.
          </p>
        </div>
      </main>
    );
  }

  const hasFactTables = view.factTableCounts.length > 0;

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <LedgerHeader
        totalEntries={view.totalEntries}
        indicatorCount={view.indicatorCount}
        sourceCount={view.sourceCount}
      />

      {/* Plain-language interpretation — UI_ACCEPTANCE §"Required Content Elements" */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Every approved number Nepal Ledger
          publishes, listed with the source that produced it and a confidence grade. Grade A is an
          official figure read directly from the source document; Grade B is derived or
          layout-reconstructed. Nothing is shown here that did not pass the validation pipeline.
        </p>
      </div>

      {/* Summary strip: confidence + per-category coverage */}
      <section aria-labelledby="ledger-summary-heading" className="mt-6">
        <h2 id="ledger-summary-heading" className="sr-only">
          Coverage summary
        </h2>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SummaryStat label="Indicator values" value={formatRowCount(view.totalEntries)} />
          <SummaryStat label="Distinct indicators" value={formatRowCount(view.indicatorCount)} />
          <SummaryStat label="Source feeds" value={formatRowCount(view.sourceCount)} />
          <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
            <dt className="text-xs font-medium text-zinc-500 dark:text-zinc-400">By confidence</dt>
            <dd className="mt-1 flex flex-wrap items-center gap-1.5">
              {(['A', 'B', 'C'] as const)
                .filter((g) => view.confidence[g] > 0)
                .map((g) => (
                  <span key={g} className="inline-flex items-center gap-1">
                    <ConfidenceBadge grade={g} />
                    <span className="text-xs tabular-nums text-zinc-600 dark:text-zinc-400">
                      {formatRowCount(view.confidence[g])}
                    </span>
                  </span>
                ))}
            </dd>
          </div>
        </dl>

        {/* Coverage by category */}
        <div className="mt-3 flex flex-wrap gap-2">
          {view.categoryCounts.map((c) => (
            <span
              key={c.category}
              className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400"
            >
              <span className="font-medium text-zinc-700 dark:text-zinc-300">
                {CATEGORY_LABELS[c.category] ?? c.category}
              </span>
              <span className="tabular-nums">{formatRowCount(c.count)}</span>
            </span>
          ))}
        </div>
      </section>

      {/* Category groups — each a semantic table + mobile fallback */}
      <div className="mt-10 flex flex-col gap-10">
        {view.groups.map((group) => (
          <LedgerTable key={group.category} group={group} />
        ))}
      </div>

      {/* Coverage strip: typed dimensional fact tables not in this index */}
      {hasFactTables && (
        <section
          aria-labelledby="ledger-factbase-heading"
          className="mt-12 border-t border-zinc-200 pt-6 dark:border-zinc-700"
        >
          <h2
            id="ledger-factbase-heading"
            className="text-base font-semibold text-zinc-800 dark:text-zinc-200"
          >
            Granular fact tables
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-zinc-500 dark:text-zinc-400">
            Beyond the headline indicators above, Nepal Ledger holds dimensional fact tables —
            millions of granular rows powering the Money Map, district dashboards, and census
            lenses. Row counts below; these are not enumerated individually here.
          </p>
          <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {view.factTableCounts.map((ft) => {
              const meta = FACT_TABLE_LABELS[ft.table];
              return (
                <div
                  key={ft.table}
                  className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900"
                >
                  <dt className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                    {meta?.label ?? ft.table}
                  </dt>
                  <dd className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
                    {formatRowCount(ft.rows)}
                  </dd>
                  {meta?.blurb && (
                    <dd className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{meta.blurb}</dd>
                  )}
                </div>
              );
            })}
          </dl>
        </section>
      )}

      {/* Source attribution + confidence legend — UI_ACCEPTANCE */}
      <footer className="mt-10 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Sources:</dt>
            <dd>{view.sourceCount} registered feeds, each row attributed in the Source column</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="font-medium">A</span> official ·{' '}
              <span className="font-medium">B</span> derived/reconstructed ·{' '}
              <span className="font-medium">C</span> low-confidence
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Data status:</dt>
            <dd>
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-800">
                Approved
              </span>
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Every value here passed the staging → validation → approved pipeline. Click-through to the
          underlying source PDF/XLSX is a planned follow-up.{' '}
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

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
      <dt className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
        {value}
      </dd>
    </div>
  );
}

type LedgerHeaderProps = {
  totalEntries?: number;
  indicatorCount?: number;
  sourceCount?: number;
};

function LedgerHeader({ totalEntries, indicatorCount, sourceCount }: LedgerHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Fact Ledger
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        Nepal Ledger&apos;s auditable claims database — every published number, browsable with the
        source that produced it and a confidence grade. This is the project&apos;s commitment to
        verifiable economic truth made tangible.
      </p>
      {totalEntries !== undefined && indicatorCount !== undefined && sourceCount !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>
            {indicatorCount} indicators · {totalEntries} approved values · {sourceCount} sources
          </span>
        </p>
      )}
    </header>
  );
}
