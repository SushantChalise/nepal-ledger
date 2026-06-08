import type { Metadata } from 'next';
import Link from 'next/link';

import { formatAppError } from '@/lib/errors';
import { KpiCard } from '@/features/pulse/components/KpiCard';
import { getTradeOverview, type TradeBreakdown } from '@/features/trade/server/queries';
import { TradeRankTable } from '@/features/trade/components/TradeRankTable';
import { TradeBalanceBar } from '@/features/trade/components/TradeBalanceBar';
import {
  formatCoverageRatio,
  formatImportMultiple,
  formatNprMagnitude,
  formatSharePct,
} from '@/features/trade/format';

export const metadata: Metadata = {
  title: 'Trade — Imports, Exports & the Deficit | Nepal Ledger',
  description:
    'What Nepal imports and exports, and from whom — merchandise trade by commodity (HS code) and partner country for fiscal year 2081/82. Imports run ~6.5× exports: the structural trade deficit is Money Out on goods. Source: Department of Customs Foreign Trade Statistics.',
};

const IMPORTS_BAR = '#b45309'; // amber-700 — imports (money out)
const EXPORTS_BAR = '#0d9488'; // teal-600 — exports (money in)

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function TradePage() {
  const result = await getTradeOverview();

  if (!result.ok) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <TradeHeader />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load customs trade data
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

  if (data.totalImports <= 0 && data.totalExports <= 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <TradeHeader />
        <div
          role="status"
          aria-live="polite"
          className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
        >
          <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
            No customs trade data yet
          </p>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
            The imports/exports breakdown will appear here once the Department of Customs Foreign
            Trade Statistics workbook is ingested.
          </p>
        </div>
      </main>
    );
  }

  const topImportCommodity = data.importCommodities.members[0];
  const topImportPartner = data.importCountries.members[0];
  const topExportPartner = data.exportCountries.members[0];
  const otherPeriods = data.availablePeriods.filter((p) => p.periodBs !== data.periodBs);

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <TradeHeader periodBs={data.periodBs} />

      {/* KPI strip — reuse Pulse KpiCard for consistency. Confidence A. */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total imports"
          value={formatNprMagnitude(data.totalImports)}
          unit=""
          period={`FY ${data.periodBs} · ${data.importCommodities.totalMembers.toLocaleString('en-IN')} commodities`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Total exports"
          value={formatNprMagnitude(data.totalExports)}
          unit=""
          period={`FY ${data.periodBs} · ${data.exportCommodities.totalMembers.toLocaleString('en-IN')} commodities`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Trade deficit"
          value={formatNprMagnitude(Math.abs(data.tradeBalance))}
          unit=""
          period={`Imports ${formatImportMultiple(data.totalImports, data.totalExports)} exports`}
          confidence={data.confidence}
        />
        <KpiCard
          label="Export coverage"
          value={formatCoverageRatio(data.totalExports, data.totalImports)}
          unit=""
          period="Exports ÷ imports"
          confidence={data.confidence}
        />
      </div>

      {/* Plain-language interpretation — required by UI_ACCEPTANCE.md. */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> Nepal&apos;s merchandise trade for
          fiscal year {data.periodBs} — what it buys from the world (
          <span className="font-medium">imports</span>) versus what it sells (
          <span className="font-medium">exports</span>), broken down by commodity and partner
          country. Imports total{' '}
          <span className="font-medium">{formatNprMagnitude(data.totalImports)}</span> against just{' '}
          <span className="font-medium">{formatNprMagnitude(data.totalExports)}</span> of exports —
          a structural deficit of{' '}
          <span className="font-medium">{formatNprMagnitude(Math.abs(data.tradeBalance))}</span>,
          with imports running{' '}
          <span className="font-medium">
            {formatImportMultiple(data.totalImports, data.totalExports)}
          </span>{' '}
          exports. This gap is the <span className="font-medium">Money Out</span> on goods: rupees
          that leave the country to pay for what Nepal does not produce at home.
        </p>
      </div>

      {/* Trade-balance bar — the headline gap. */}
      <section aria-labelledby="balance-heading" className="mt-8">
        <h2
          id="balance-heading"
          className="mb-4 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Imports versus exports — FY {data.periodBs}
        </h2>
        <TradeBalanceBar totalImports={data.totalImports} totalExports={data.totalExports} />
      </section>

      {/* Top import commodities */}
      <RankSection
        id="import-commodities"
        heading={`What Nepal imports most — top ${data.importCommodities.members.length} commodities`}
        breakdown={data.importCommodities}
        memberKind="commodity"
        barColor={IMPORTS_BAR}
        memberHeader="Commodity"
        valueHeader="Import value"
        memberNoun="commodities"
        sideTotal={data.totalImports}
        caption={`Nepal's top import commodities by value for fiscal year ${data.periodBs}, in NPR billion, with each commodity's share of total imports.`}
      />

      {/* Top export commodities */}
      <RankSection
        id="export-commodities"
        heading={`What Nepal exports most — top ${data.exportCommodities.members.length} commodities`}
        breakdown={data.exportCommodities}
        memberKind="commodity"
        barColor={EXPORTS_BAR}
        memberHeader="Commodity"
        valueHeader="Export value"
        memberNoun="commodities"
        sideTotal={data.totalExports}
        caption={`Nepal's top export commodities by value for fiscal year ${data.periodBs}, in NPR billion, with each commodity's share of total exports.`}
      />

      {/* Top import partners */}
      <RankSection
        id="import-partners"
        heading={`Where imports come from — top ${data.importCountries.members.length} partners`}
        breakdown={data.importCountries}
        memberKind="country"
        barColor={IMPORTS_BAR}
        memberHeader="Partner country"
        valueHeader="Import value"
        memberNoun="partner countries"
        sideTotal={data.totalImports}
        caption={`Nepal's top import partner countries by value for fiscal year ${data.periodBs}, in NPR billion, with each partner's share of total imports.`}
      />

      {/* Top export partners */}
      <RankSection
        id="export-partners"
        heading={`Where exports go — top ${data.exportCountries.members.length} partners`}
        breakdown={data.exportCountries}
        memberKind="country"
        barColor={EXPORTS_BAR}
        memberHeader="Partner country"
        valueHeader="Export value"
        memberNoun="partner countries"
        sideTotal={data.totalExports}
        caption={`Nepal's top export partner countries by value for fiscal year ${data.periodBs}, in NPR billion, with each partner's share of total exports.`}
      />

      {/* Concentration prose — the structural reads. */}
      <div className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 px-5 py-4 dark:border-zinc-700 dark:bg-zinc-900/50">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {topImportPartner ? (
            <>
              Imports are heavily concentrated:{' '}
              <span className="font-medium">{topImportPartner.label}</span> alone supplies{' '}
              <span className="font-medium">{formatSharePct(topImportPartner.sharePct)}</span> of
              everything Nepal buys abroad.{' '}
            </>
          ) : null}
          {topExportPartner ? (
            <>
              Exports lean even harder on one market —{' '}
              <span className="font-medium">{topExportPartner.label}</span> takes{' '}
              <span className="font-medium">{formatSharePct(topExportPartner.sharePct)}</span> of
              what Nepal sells.{' '}
            </>
          ) : null}
          {topImportCommodity ? (
            <>
              The single largest import line is{' '}
              <span className="font-medium">{topImportCommodity.label}</span> (
              {formatNprMagnitude(topImportCommodity.amount)}) — a reminder that much of the deficit
              is energy and industrial inputs Nepal cannot source at home.
            </>
          ) : null}
        </p>
      </div>

      {/* Source attribution + confidence — required by UI_ACCEPTANCE.md. */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Source:</dt>
            <dd>Department of Customs — Foreign Trade Statistics (ASYCUDA World)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-800">
                Grade {data.confidence}
              </span>
              <span className="ml-1">— official customs-declaration records</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Unit:</dt>
            <dd>NPR billion / trillion (converted from the source&apos;s NPR thousand)</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Reference:</dt>
            <dd>FY {data.periodBs} (annual workbook)</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          Commodity and country labels are shown exactly as recorded by Customs (HS-code
          descriptions verbatim). Source values are in NPR thousand; we display NPR billion (value ÷
          1,000,000) or NPR trillion for totals. Each ranked table shows only the highest-value
          members — the long tail of smaller lines is not displayed.
          {otherPeriods.length > 0 ? (
            <>
              {' '}
              Other periods available in the customs data:{' '}
              {otherPeriods.map((p) => p.periodBs).join(', ')} (this page shows the FY{' '}
              {data.periodBs} annual file).
            </>
          ) : null}{' '}
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

type RankSectionProps = {
  id: string;
  heading: string;
  breakdown: TradeBreakdown;
  memberKind: 'commodity' | 'country';
  barColor: string;
  memberHeader: string;
  valueHeader: string;
  memberNoun: string;
  sideTotal: number;
  caption: string;
};

function RankSection({
  id,
  heading,
  breakdown,
  memberKind,
  barColor,
  memberHeader,
  valueHeader,
  memberNoun,
  sideTotal,
  caption,
}: RankSectionProps) {
  const headingId = `${id}-heading`;
  const shownTotal = breakdown.members.reduce((s, m) => s + m.amount, 0);
  const shownSharePct = sideTotal > 0 ? (shownTotal / sideTotal) * 100 : 0;

  if (breakdown.members.length === 0) {
    return (
      <section aria-labelledby={headingId} className="mt-10">
        <h2
          id={headingId}
          className="mb-3 text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          {heading}
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No {memberNoun} recorded for this period.
        </p>
      </section>
    );
  }

  return (
    <section aria-labelledby={headingId} className="mt-10">
      <h2 id={headingId} className="mb-1 text-base font-semibold text-zinc-700 dark:text-zinc-300">
        {heading}
      </h2>
      <p className="mb-4 text-xs text-zinc-500 dark:text-zinc-400">
        Showing the top {breakdown.members.length} of{' '}
        {breakdown.totalMembers.toLocaleString('en-IN')} {memberNoun} —{' '}
        {formatSharePct(shownSharePct)} of the total. The remainder is not shown.
      </p>
      <TradeRankTable
        members={breakdown.members}
        memberKind={memberKind}
        barColor={barColor}
        caption={caption}
        memberHeader={memberHeader}
        valueHeader={valueHeader}
      />
    </section>
  );
}

type TradeHeaderProps = {
  periodBs?: string;
};

function TradeHeader({ periodBs }: TradeHeaderProps) {
  return (
    <header>
      <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Trade — Imports, Exports &amp; the Deficit
      </h1>
      <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
        What Nepal buys from the world and what it manages to sell back — merchandise trade by
        commodity and partner country. Imports dwarf exports several times over; that gap is the{' '}
        <span className="font-medium">Money Out</span> on goods.
      </p>
      {periodBs !== undefined && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          <span>Reference: FY {periodBs}</span>
          <span className="mx-2" aria-hidden="true">
            ·
          </span>
          <span>
            Source:{' '}
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              Department of Customs — Foreign Trade Statistics
            </span>
          </span>
        </p>
      )}
    </header>
  );
}
