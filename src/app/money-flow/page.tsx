import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { getMoneyFlowData } from '@/features/money-flow/server/queries';
import { MoneyFlowSankey } from '@/features/money-flow/components/MoneyFlowSankey';
import { formatNprBillion, formatNprMagnitude, formatSharePct } from '@/features/money-flow/format';

export const metadata: Metadata = {
  title: 'Money Flow — Nepal Ledger',
  description:
    "Nepal's money in one picture: remittance, foreign aid, and merchandise exports flow into the economy and out to pay for imports. Remittance is the dominant inflow and roughly funds the entire merchandise trade deficit — Nepal's defining macro story. A Sankey of national flows in NPR billion.",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function MoneyFlowPage() {
  const result = await getMoneyFlowData();

  if (!result.ok) {
    // NotFound (no remittance AND no trade) renders the same calm empty state as
    // a genuinely-empty dataset; every other AppError is a real error.
    if (result.error.kind === 'NotFound') {
      return (
        <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
          <MoneyFlowHeader />
          <div
            role="status"
            aria-live="polite"
            className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
          >
            <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
              No money-flow data yet
            </p>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
              Nepal&apos;s remittance, trade, and foreign-aid flows will appear here once the
              ingestion runs complete.
            </p>
          </div>
        </main>
      );
    }

    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <MoneyFlowHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load Nepal&apos;s money-flow data
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

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <MoneyFlowHeader periodBs={data.periodBs} totalInflows={data.totalInflowsBillion} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total inflows"
          value={formatNprMagnitude(data.totalInflowsBillion)}
          unit=""
          period={`FY ${data.periodBs}`}
          confidence={data.remittance?.confidence ?? data.tradeConfidence}
        />
        <KpiCard
          label="Remittance"
          value={data.remittance ? formatNprMagnitude(data.remittance.valueBillion) : '—'}
          unit=""
          period={data.remittance ? `FY ${data.remittance.fiscalYearBs}` : 'no data'}
          confidence={data.remittance?.confidence ?? 'B'}
        />
        <KpiCard
          label="Merchandise trade deficit"
          value={formatNprMagnitude(data.tradeDeficitBillion)}
          unit=""
          period={`FY ${data.periodBs}`}
          confidence={data.tradeConfidence}
        />
        <KpiCard
          label="Remittance share of inflows"
          value={data.remittanceSharePct !== null ? formatSharePct(data.remittanceSharePct) : '—'}
          unit=""
          period={`FY ${data.periodBs}`}
          confidence={data.remittance?.confidence ?? 'B'}
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md, and the
          mission framing: remittance funds the trade deficit. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Where Nepal&apos;s money comes
          from and where it goes, in one flow.{' '}
          {data.remittance ? (
            <>
              <span className="font-medium">Remittance</span> sent home by workers abroad —{' '}
              {formatNprMagnitude(data.remittance.valueBillion)}, the single largest inflow
              {data.remittanceSharePct !== null
                ? ` (${formatSharePct(data.remittanceSharePct)} of all inflows)`
                : ''}{' '}
              — is the engine.{' '}
            </>
          ) : null}
          Set against the <span className="font-medium">merchandise trade deficit</span> of{' '}
          {formatNprMagnitude(data.tradeDeficitBillion)} (imports{' '}
          {formatNprMagnitude(data.importsBillion)} versus exports{' '}
          {formatNprMagnitude(data.exportsBillion)}), the story is stark:{' '}
          {data.remittance ? (
            <>
              remittance alone{' '}
              {data.remittance.valueBillion >= data.tradeDeficitBillion
                ? 'more than covers'
                : 'largely covers'}{' '}
              the gap between what Nepal buys from the world and what it sells. Goods exports pay
              for only a fraction of the import bill; it is money earned abroad — not exports — that
              keeps the books roughly level.
            </>
          ) : (
            <>goods exports pay for only a fraction of the import bill.</>
          )}
        </p>
      </div>

      {/* Diagram */}
      <section aria-labelledby="money-flow-diagram-heading" className="mt-8">
        <h2
          id="money-flow-diagram-heading"
          className="mb-1 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Nepal money flow — FY {data.periodBs} (NPR billion)
        </h2>
        <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
          Left: money entering Nepal. Centre: the economy. Right: money paid out for imports, and
          the remainder retained. Wider bands mean larger flows. Every figure is also listed in the
          table read by screen readers.
        </p>
        <MoneyFlowSankey data={data} />
      </section>

      {/* Honest accounting note on the residual + the fiscal-year mismatch. */}
      <div className="mt-6 rounded-lg border border-amber-100 bg-amber-50 px-5 py-4 dark:border-amber-900/60 dark:bg-amber-950/40">
        <p className="text-xs text-amber-800 dark:text-amber-200">
          <span className="font-semibold">How to read the balance.</span>{' '}
          {data.outflowsExceedInflows ? (
            <>
              Merchandise imports ({formatNprMagnitude(data.importsBillion)}) exceed the inflows
              shown here ({formatNprMagnitude(data.totalInflowsBillion)}). The shortfall is met by
              financing not pictured (external borrowing, reserve drawdown, services income). No
              balancing band is drawn.{' '}
            </>
          ) : (
            <>
              Inflows ({formatNprMagnitude(data.totalInflowsBillion)}) exceed merchandise imports (
              {formatNprMagnitude(data.importsBillion)}); the difference —{' '}
              {formatNprBillion(data.retainedBillion)} — is shown as &ldquo;retained in the
              economy&rdquo;. It is a residual, not a measured figure: it lumps together everything
              not spent on imported goods (services, savings, other payments), so treat it as an
              honest remainder rather than a precise account.{' '}
            </>
          )}
          These are not all the same year:{' '}
          <span className="font-medium">remittance and trade are FY {data.periodBs}</span>
          {data.aidFiscalYearBs ? (
            <>
              , but the latest available{' '}
              <span className="font-medium">foreign-aid edition is FY {data.aidFiscalYearBs}</span>{' '}
              — so the aid band reflects an earlier year and is indicative of scale, not a
              same-period comparison
            </>
          ) : null}
          . This is merchandise (goods) trade only — it excludes services and income, so it is not
          the full current account.
        </p>
      </div>

      {/* Source attribution + confidence + units — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Sources:</dt>
            <dd>
              NRB Database on Nepalese Economy (remittance); Department of Customs — Foreign Trade
              Statistics (trade)
              {data.aid ? '; Ministry of Finance — Source Book / White Book (aid)' : ''}
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-800">
                Grade {data.tradeConfidence}
              </span>
              <span className="ml-1">trade ·</span>
              <span className="ml-1 rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800">
                Grade {data.remittance?.confidence ?? 'B'}
              </span>
              <span className="ml-1">remittance{data.aid ? '/aid' : ''}</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>NPR billion (all flows normalized to one unit)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Period:</dt>
            <dd>
              FY {data.periodBs}
              {data.aidFiscalYearBs ? ` (aid: FY ${data.aidFiscalYearBs})` : ''}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Each source is stored in a different unit — remittance in NPR million, foreign aid in NPR
          lakh, trade in NPR thousand — and all are converted to NPR billion so the bands are
          comparable. Figures cover merchandise trade only.{' '}
          <Link
            href="/trade"
            className="text-blue-600 underline hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            Trade detail →
          </Link>{' '}
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

type MoneyFlowHeaderProps = {
  periodBs?: string;
  totalInflows?: number;
};

function MoneyFlowHeader({ periodBs, totalInflows }: MoneyFlowHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Money Flow
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        Nepal&apos;s money in a single picture — what flows in (remittance, foreign aid, exports),
        through the economy, and back out to pay for imports. The defining pattern: money earned
        abroad, not goods sold, is what keeps Nepal&apos;s external books level.
      </p>
      {periodBs !== undefined && totalInflows !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reporting period: FY {periodBs}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Total inflows:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {formatNprMagnitude(totalInflows)}
            </span>
          </span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Unit: <span className="font-medium text-zinc-700 dark:text-zinc-300">NPR billion</span>
          </span>
        </p>
      )}
    </header>
  );
}
