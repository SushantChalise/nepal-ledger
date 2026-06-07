/**
 * RateSeriesTable — Server Component rendering a percent-valued annual series
 * (real-GDP growth OR CPI inflation) as an accessible, semantic table with a
 * thin decorative magnitude bar.
 *
 * No `'use client'`: a static, sorted table needs no interactivity, so this is
 * a pure Server Component (matching the state-enterprises convention). It pairs
 * with the GdpTrajectoryChart: the chart shows the level (GDP); this shows the
 * rate of change, fully as text.
 *
 * Accessibility:
 *   - Native <table> with <caption>, <th scope="col">, and a <th scope="row">
 *     per fiscal year.
 *   - Percent cells are right-aligned with tabular-nums.
 *   - The magnitude bar is aria-hidden — the percent is stated in the adjacent
 *     cell, so meaning is never carried by colour/width alone (WCAG AA).
 *   - Negative values (a contraction / deflation) are labelled with a "−"
 *     sign in the text, never by colour alone.
 */

import type { SeriesPoint } from '../server/queries';
import { formatPercent } from '../format';

const BAR_FILL = '#0d9488'; // teal-600 — positive
const BAR_FILL_NEGATIVE = '#b45309'; // amber-700 — negative (contraction / deflation)

type RateSeriesTableProps = {
  /** The percent-valued series, ascending by fiscal year. */
  points: SeriesPoint[];
  /** Accessible caption / column header for the rate (e.g. "Real GDP growth"). */
  rateLabel: string;
  /** How many most-recent years to show (the full series lives in the chart's table). */
  limit?: number;
};

export function RateSeriesTable({ points, rateLabel, limit = 12 }: RateSeriesTableProps) {
  // Most-recent `limit` years, newest first (a rate table reads best descending).
  const recent = [...points].slice(-limit).reverse();
  const maxAbs = recent.reduce((m, p) => (Math.abs(p.value) > m ? Math.abs(p.value) : m), 0) || 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">
          {rateLabel} by fiscal year (percent), most recent {recent.length} years, newest first.
        </caption>
        <thead>
          <tr className="border-b border-zinc-300 text-left dark:border-zinc-600">
            <th
              scope="col"
              className="py-2 pr-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Fiscal year
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              {rateLabel}
            </th>
            <th
              scope="col"
              className="hidden py-2 pl-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 sm:table-cell dark:text-zinc-400"
            >
              <span aria-hidden="true">Magnitude</span>
              <span className="sr-only">Magnitude (visual)</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {recent.map((p) => {
            const widthPct = Math.max(2, (Math.abs(p.value) / maxAbs) * 100);
            const isNegative = p.value < 0;
            return (
              <tr key={p.fiscalYearBs} className="border-b border-zinc-100 dark:border-zinc-800">
                <th
                  scope="row"
                  className="py-2 pr-3 text-left font-normal text-zinc-800 dark:text-zinc-200"
                >
                  {p.fiscalYearBs}
                </th>
                <td className="py-2 pl-3 text-right font-medium tabular-nums text-zinc-900 dark:text-zinc-50">
                  {formatPercent(p.value)}
                </td>
                <td className="hidden py-2 pl-3 align-middle sm:table-cell">
                  <div
                    aria-hidden="true"
                    className="h-3 w-40 overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800"
                    title={formatPercent(p.value)}
                  >
                    <div
                      className="h-full"
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: isNegative ? BAR_FILL_NEGATIVE : BAR_FILL,
                      }}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
