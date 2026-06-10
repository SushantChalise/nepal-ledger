import { ConfidenceBadge } from '@/features/fact-ledger/components/ConfidenceBadge';
import {
  CATEGORY_DESCRIPTIONS,
  CATEGORY_LABELS,
  formatIndicatorValue,
} from '@/features/fact-ledger/format';
import type { LedgerCategoryGroup } from '@/features/fact-ledger/server/queries';

/**
 * One category section of the Fact Ledger. Server Component.
 *
 * Renders BOTH a semantic `<table>` (visible ≥640px) and a stacked-card
 * fallback (visible <640px) — the UI_ACCEPTANCE mobile rule. Both carry the
 * same data; exactly one is shown per breakpoint via Tailwind `hidden` /
 * `sm:hidden`. Rows arrive pre-sorted by the DB (category, then slug); no
 * client-side sorting — presentation order is DB-driven, matching Pulse.
 */

function periodLabel(periodBs: string): string {
  return periodBs;
}

export function LedgerTable({ group }: { group: LedgerCategoryGroup }) {
  const label = CATEGORY_LABELS[group.category] ?? group.category;
  const description = CATEGORY_DESCRIPTIONS[group.category];
  const headingId = `ledger-cat-${group.category}`;

  return (
    <section aria-labelledby={headingId}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 id={headingId} className="text-base font-semibold text-zinc-800 dark:text-zinc-200">
          {label}
        </h2>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          {group.entries.length} {group.entries.length === 1 ? 'value' : 'values'}
        </span>
      </div>
      {description && (
        <p className="mb-3 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
      )}

      {/* ≥640px: semantic data table */}
      <div className="hidden overflow-x-auto rounded-lg border border-zinc-200 sm:block dark:border-zinc-700">
        <table className="w-full border-collapse text-left text-sm">
          <caption className="sr-only">
            {label} indicators: each row lists the indicator, its latest approved value and unit,
            reporting period, confidence grade, and source.
          </caption>
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400">
              <th scope="col" className="px-4 py-2 font-medium">
                Indicator
              </th>
              <th scope="col" className="px-4 py-2 text-right font-medium">
                Value
              </th>
              <th scope="col" className="px-4 py-2 font-medium">
                Period
              </th>
              <th scope="col" className="px-4 py-2 font-medium">
                Confidence
              </th>
              <th scope="col" className="px-4 py-2 font-medium">
                Source
              </th>
            </tr>
          </thead>
          <tbody>
            {group.entries.map((entry, i) => {
              const { display, unit } = formatIndicatorValue(entry.value, entry.unit);
              return (
                <tr
                  key={`${entry.indicatorSlug}-${entry.reportingPeriodBs}-${i}`}
                  className="border-b border-zinc-100 last:border-0 odd:bg-white even:bg-zinc-50/50 dark:border-zinc-800 dark:odd:bg-zinc-950 dark:even:bg-zinc-900/40"
                >
                  <th
                    scope="row"
                    className="max-w-xs px-4 py-2 font-normal text-zinc-800 dark:text-zinc-200"
                  >
                    {entry.indicatorNameEn}
                  </th>
                  <td className="whitespace-nowrap px-4 py-2 text-right font-medium tabular-nums text-zinc-900 dark:text-zinc-100">
                    {display}
                    {unit && (
                      <span className="ml-1 text-xs font-normal text-zinc-500 dark:text-zinc-400">
                        {unit}
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2 text-zinc-600 dark:text-zinc-400">
                    {periodLabel(entry.reportingPeriodBs)}
                  </td>
                  <td className="px-4 py-2">
                    <ConfidenceBadge grade={entry.confidence} />
                  </td>
                  <td className="px-4 py-2 text-zinc-600 dark:text-zinc-400">
                    <span title={`${entry.sourceAgency} — ${entry.sourceDataset}`}>
                      {entry.sourceAgencyShort} · {entry.sourceDataset}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* <640px: stacked cards (one hero block per row) */}
      <ul className="flex flex-col gap-2 sm:hidden">
        {group.entries.map((entry, i) => {
          const { display, unit } = formatIndicatorValue(entry.value, entry.unit);
          return (
            <li
              key={`${entry.indicatorSlug}-${entry.reportingPeriodBs}-${i}`}
              className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900"
            >
              <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                {entry.indicatorNameEn}
              </p>
              <p className="mt-1 text-lg font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
                {display}
                {unit && (
                  <span className="ml-1 text-xs font-normal text-zinc-500 dark:text-zinc-400">
                    {unit}
                  </span>
                )}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
                <span>{periodLabel(entry.reportingPeriodBs)}</span>
                <ConfidenceBadge grade={entry.confidence} />
                <span>
                  {entry.sourceAgencyShort} · {entry.sourceDataset}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
