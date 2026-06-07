import type { CensusMetric } from '../server/queries';
import { formatCount, formatPercent } from '../format';

/**
 * One census ratio rendered as a labelled horizontal bar + caption.
 * Server Component (no `'use client'`). Color encodes nothing load-bearing —
 * the percentage and label are always shown (no color-only information).
 */
export function MetricBar({ metric }: { metric: CensusMetric }) {
  const hasData = metric.ratio !== null && metric.denominator > 0;
  const pct = hasData ? Math.max(0, Math.min(100, metric.ratio! * 100)) : 0;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{metric.label}</span>
        <span className="text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
          {hasData ? formatPercent(metric.ratio!) : '—'}
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
        role="img"
        aria-label={
          hasData ? `${metric.label}: ${formatPercent(metric.ratio!)}` : `${metric.label}: no data`
        }
      >
        <div
          className="h-full rounded-full bg-teal-600 dark:bg-teal-500"
          style={{ width: `${pct.toFixed(1)}%` }}
        />
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        {metric.description}
        {hasData && (
          <span className="ml-1 text-zinc-400 dark:text-zinc-500">
            ({formatCount(metric.numerator)} of {formatCount(metric.denominator)} households)
          </span>
        )}
      </p>
    </div>
  );
}
