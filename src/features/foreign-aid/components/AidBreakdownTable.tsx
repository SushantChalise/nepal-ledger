/**
 * AidBreakdownTable — server component rendering a ranked foreign-aid breakdown
 * (by donor OR by sector) as an accessible, semantic table.
 *
 * No `'use client'`: a sorted, static table needs no interactivity, so this is a
 * pure Server Component (matching the state-enterprises / Pulse convention).
 *
 * Each row shows one member (donor or recipient ministry, label rendered
 * faithfully) with its GRANT total, LOAN total, and combined aid — ALL ALREADY
 * IN NPR BILLION (the query converts each row from its edition's lakh/thousand
 * unit before summing; see queries.ts / format.ts). A thin grant-vs-loan
 * composition bar accompanies the total, but the bar is decorative: every figure
 * is also printed as text, so meaning is never carried by colour alone
 * (UI_ACCEPTANCE.md / WCAG AA).
 *
 * Accessibility:
 *   - Native <table> with <caption>, column <th scope="col">, and a row-header
 *     <th scope="row"> per member.
 *   - Numeric cells are right-aligned with tabular-nums; the composition bar
 *     carries aria-hidden (the grant/loan split is stated in adjacent cells).
 *   - A horizontal scroll container keeps the table usable on narrow viewports
 *     without truncating any column.
 */

import type { AidBreakdown } from '../server/queries';
import { formatBillion, formatSharePct } from '../format';

const GRANT_FILL = '#0d9488'; // teal-600 — grant (need not be repaid)
const LOAN_FILL = '#b45309'; // amber-700 — loan (must be repaid)

type AidBreakdownTableProps = {
  breakdown: AidBreakdown;
  /** Noun for the member column header / caption, e.g. "Development partner". */
  memberNoun: string;
  /** BS fiscal year label for the caption. */
  fiscalYearBs: string;
  /** Stable id fragment so multiple tables on one page have unique captions. */
  captionId: string;
};

export function AidBreakdownTable({
  breakdown,
  memberNoun,
  fiscalYearBs,
  captionId,
}: AidBreakdownTableProps) {
  const { members, grandTotal } = breakdown;
  const maxTotal = members.reduce((m, x) => (x.total > m ? x.total : m), 0) || 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption id={captionId} className="sr-only">
          Foreign aid to Nepal by {memberNoun.toLowerCase()}, ranked by total aid (grant plus loan)
          for fiscal year {fiscalYearBs}, in NPR billion.
        </caption>
        <thead>
          <tr className="border-b border-zinc-300 text-left dark:border-zinc-600">
            <th
              scope="col"
              className="py-2 pr-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              <span className="sr-only">Rank, </span>
              {memberNoun}
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Grant
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Loan
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Total aid
            </th>
            <th
              scope="col"
              className="hidden py-2 pl-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 sm:table-cell dark:text-zinc-400"
            >
              <span aria-hidden="true">Grant vs loan</span>
              <span className="sr-only">Grant versus loan composition (visual)</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {members.map((m, i) => {
            const grantPctOfRow = m.total > 0 ? (m.grant / m.total) * 100 : 0;
            const loanPctOfRow = m.total > 0 ? (m.loan / m.total) * 100 : 0;
            const rowWidthPct = Math.max(2, (m.total / maxTotal) * 100);
            const shareOfGrand = grandTotal > 0 ? (m.total / grandTotal) * 100 : 0;
            return (
              <tr key={m.slug} className="border-b border-zinc-100 align-top dark:border-zinc-800">
                <th
                  scope="row"
                  className="max-w-xs py-2 pr-3 text-left font-normal text-zinc-800 dark:text-zinc-200"
                >
                  <span className="mr-1.5 tabular-nums text-zinc-400 dark:text-zinc-500">
                    {i + 1}.
                  </span>
                  <span className="font-medium">{m.label}</span>
                  <span className="mt-0.5 block text-xs text-zinc-400 dark:text-zinc-500">
                    {formatSharePct(shareOfGrand)} of total aid
                  </span>
                </th>
                <td className="py-2 pl-3 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatBillion(m.grant)}
                </td>
                <td className="py-2 pl-3 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatBillion(m.loan)}
                </td>
                <td className="py-2 pl-3 text-right font-medium tabular-nums text-zinc-900 dark:text-zinc-50">
                  {formatBillion(m.total)}
                </td>
                <td className="hidden py-2 pl-3 align-middle sm:table-cell">
                  {/* Decorative composition bar. aria-hidden: the grant/loan
                      split and total are already stated in text cells above. */}
                  <div
                    aria-hidden="true"
                    className="h-3 w-40 overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800"
                    title={`Grant ${formatSharePct(grantPctOfRow)} · Loan ${formatSharePct(loanPctOfRow)}`}
                  >
                    <div className="flex h-full" style={{ width: `${rowWidthPct}%` }}>
                      <div
                        className="h-full"
                        style={{ width: `${grantPctOfRow}%`, backgroundColor: GRANT_FILL }}
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
            style={{ backgroundColor: GRANT_FILL }}
          />
          Grant (need not be repaid)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: LOAN_FILL }}
          />
          Loan (must be repaid)
        </span>
      </div>
    </div>
  );
}
