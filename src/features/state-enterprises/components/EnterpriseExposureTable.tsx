/**
 * EnterpriseExposureTable — server component rendering the public-enterprise
 * government-exposure ranking as an accessible, semantic table.
 *
 * No `'use client'`: a sorted, static table needs no interactivity, so this is
 * a pure Server Component (matching the Pulse feature's all-server convention).
 *
 * Each row shows one public enterprise (raw Devanagari name rendered faithfully)
 * with its government EQUITY (`soe-government-share`), outstanding government
 * LOAN principal (`soe-loan-principal`), and combined exposure — all converted
 * from NPR thousand to NPR billion via `format.ts`. A thin equity-vs-loan
 * composition bar accompanies the total, but the bar is decorative: every figure
 * is also printed as text, so meaning is never carried by colour alone
 * (UI_ACCEPTANCE.md / WCAG AA).
 *
 * Accessibility:
 *   - Native <table> with <caption>, column <th scope="col">, and a row-header
 *     <th scope="row"> per enterprise.
 *   - Numeric cells are right-aligned with tabular-nums; the composition bar
 *     carries aria-hidden (the equity/loan split is stated in adjacent cells).
 *   - A horizontal scroll container keeps the table usable on narrow viewports
 *     without truncating any column.
 */

import type { EnterpriseExposure } from '../server/queries';
import { formatNprBillion, formatSharePct } from '../format';

const SHARE_FILL = '#0d9488'; // teal-600 — equity
const LOAN_FILL = '#b45309'; // amber-700 — loan principal

type EnterpriseExposureTableProps = {
  enterprises: EnterpriseExposure[];
  /** Combined government exposure across all enterprises (NPR thousand). */
  grandTotal: number;
  /** BS fiscal year label for the caption. */
  fiscalYearBs: string;
};

export function EnterpriseExposureTable({
  enterprises,
  grandTotal,
  fiscalYearBs,
}: EnterpriseExposureTableProps) {
  const maxTotal = enterprises.reduce((m, e) => (e.total > m ? e.total : m), 0) || 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">
          Nepal&apos;s public enterprises ranked by total government exposure (equity plus loan
          principal) for fiscal year {fiscalYearBs}, in NPR billion.
        </caption>
        <thead>
          <tr className="border-b border-zinc-300 text-left dark:border-zinc-600">
            <th
              scope="col"
              className="py-2 pr-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              <span className="sr-only">Rank, </span>Enterprise
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Gov. equity
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Loan principal
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Total exposure
            </th>
            <th
              scope="col"
              className="hidden py-2 pl-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 sm:table-cell dark:text-zinc-400"
            >
              <span aria-hidden="true">Equity vs loan</span>
              <span className="sr-only">Equity versus loan composition (visual)</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {enterprises.map((e, i) => {
            const sharePctOfRow = e.total > 0 ? (e.governmentShare / e.total) * 100 : 0;
            const loanPctOfRow = e.total > 0 ? (e.loanPrincipal / e.total) * 100 : 0;
            const rowWidthPct = Math.max(2, (e.total / maxTotal) * 100);
            const shareOfGrand = grandTotal > 0 ? (e.total / grandTotal) * 100 : 0;
            return (
              <tr key={e.slug} className="border-b border-zinc-100 align-top dark:border-zinc-800">
                <th
                  scope="row"
                  className="max-w-xs py-2 pr-3 text-left font-normal text-zinc-800 dark:text-zinc-200"
                >
                  <span className="mr-1.5 tabular-nums text-zinc-400 dark:text-zinc-500">
                    {i + 1}.
                  </span>
                  <span className="font-medium">{e.label}</span>
                  <span className="mt-0.5 block text-xs text-zinc-400 dark:text-zinc-500">
                    {e.slug} · {formatSharePct(shareOfGrand)} of total exposure
                  </span>
                </th>
                <td className="py-2 pl-3 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatNprBillion(e.governmentShare)}
                </td>
                <td className="py-2 pl-3 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatNprBillion(e.loanPrincipal)}
                </td>
                <td className="py-2 pl-3 text-right font-medium tabular-nums text-zinc-900 dark:text-zinc-50">
                  {formatNprBillion(e.total)}
                </td>
                <td className="hidden py-2 pl-3 align-middle sm:table-cell">
                  {/* Decorative composition bar. aria-hidden: the equity/loan
                      split and total are already stated in text cells above. */}
                  <div
                    aria-hidden="true"
                    className="h-3 w-40 overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800"
                    title={`Equity ${formatSharePct(sharePctOfRow)} · Loan ${formatSharePct(loanPctOfRow)}`}
                  >
                    <div className="flex h-full" style={{ width: `${rowWidthPct}%` }}>
                      <div
                        className="h-full"
                        style={{ width: `${sharePctOfRow}%`, backgroundColor: SHARE_FILL }}
                      />
                      <div
                        className="h-full"
                        style={{ width: `${loanPctOfRow}%`, backgroundColor: LOAN_FILL }}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Legend for the composition bar — text + colour, never colour alone. */}
      <div className="mt-3 hidden items-center gap-4 text-xs text-zinc-500 sm:flex dark:text-zinc-400">
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: SHARE_FILL }}
          />
          Government equity (share capital)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: LOAN_FILL }}
          />
          Loan principal outstanding
        </span>
      </div>
    </div>
  );
}
