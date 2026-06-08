/**
 * TradeBalanceBar — server component visualising the imports-vs-exports gap
 * (Nepal's structural merchandise deficit) as two proportional bars.
 *
 * No `'use client'`: static proportions, no interactivity. The bars are
 * decorative (`aria-hidden`); the imports, exports, and deficit figures are all
 * stated as text beside them, so meaning is never carried by width/colour alone
 * (UI_ACCEPTANCE.md / WCAG AA). Widths are computed relative to the larger side
 * (imports), so exports render as the visibly small fraction it is.
 */

import { formatNprMagnitude, formatSharePct } from '../format';

const IMPORTS_FILL = '#b45309'; // amber-700 — money leaving (imports)
const EXPORTS_FILL = '#0d9488'; // teal-600 — money returning (exports)

type TradeBalanceBarProps = {
  /** Total imports, NPR thousand. */
  totalImports: number;
  /** Total exports, NPR thousand. */
  totalExports: number;
};

export function TradeBalanceBar({ totalImports, totalExports }: TradeBalanceBarProps) {
  const max = Math.max(totalImports, totalExports) || 1;
  const importPct = (totalImports / max) * 100;
  const exportPct = (totalExports / max) * 100;
  const coverage = totalImports > 0 ? (totalExports / totalImports) * 100 : 0;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-700 dark:bg-zinc-900">
      <div className="space-y-4">
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Imports</span>
            <span className="text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
              {formatNprMagnitude(totalImports)}
            </span>
          </div>
          <div
            aria-hidden="true"
            className="mt-1.5 h-4 w-full overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800"
          >
            <div
              className="h-full rounded"
              style={{ width: `${importPct}%`, backgroundColor: IMPORTS_FILL }}
            />
          </div>
        </div>
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Exports</span>
            <span className="text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
              {formatNprMagnitude(totalExports)}
            </span>
          </div>
          <div
            aria-hidden="true"
            className="mt-1.5 h-4 w-full overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800"
          >
            <div
              className="h-full rounded"
              style={{ width: `${exportPct}%`, backgroundColor: EXPORTS_FILL }}
            />
          </div>
        </div>
      </div>
      <p className="mt-4 text-xs text-zinc-500 dark:text-zinc-400">
        Exports cover just <span className="font-medium">{formatSharePct(coverage)}</span> of the
        import bill. The rest is the merchandise trade deficit —{' '}
        <span className="font-medium">{formatNprMagnitude(totalImports - totalExports)}</span>{' '}
        flowing out on goods.
      </p>
    </div>
  );
}
