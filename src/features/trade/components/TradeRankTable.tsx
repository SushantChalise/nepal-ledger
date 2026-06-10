/**
 * TradeRankTable — server component rendering one ranked customs-trade
 * breakdown (top commodities or top partner countries, import or export side)
 * as an accessible, semantic table.
 *
 * No `'use client'`: a sorted, static table needs no interactivity, so this is a
 * pure Server Component (matching the state-enterprises / Pulse convention).
 *
 * Each row is one dimension member — a commodity (HS code + description) or a
 * partner country (name) — with its trade value (converted NPR thousand → NPR
 * billion via `format.ts`) and its share of the side total. A thin bar visualises
 * the share, but it is decorative: every figure is also printed as text, so
 * meaning is never carried by colour/width alone (UI_ACCEPTANCE.md / WCAG AA).
 *
 * Accessibility:
 *   - Native <table> with <caption>, <th scope="col"> headers, and a
 *     <th scope="row"> per member.
 *   - Numeric cells right-aligned with tabular-nums; the share bar is
 *     aria-hidden (the share % is stated in an adjacent cell).
 *   - A horizontal scroll container keeps the table usable on narrow viewports.
 */

import type { TradeMember } from '../server/queries';
import { formatNprBillion, formatSharePct } from '../format';

type MemberKind = 'commodity' | 'country';

type TradeRankTableProps = {
  members: TradeMember[];
  /** Whether members are HS-code commodities or partner countries. */
  memberKind: MemberKind;
  /** Bar fill colour (import vs export side). */
  barColor: string;
  /** Accessible caption describing the table. */
  caption: string;
  /** Column header for the member column (e.g. 'Commodity', 'Partner country'). */
  memberHeader: string;
  /** Column header for the value column (e.g. 'Import value'). */
  valueHeader: string;
};

export function TradeRankTable({
  members,
  memberKind,
  barColor,
  caption,
  memberHeader,
  valueHeader,
}: TradeRankTableProps) {
  const maxAmount = members.reduce((m, x) => (x.amount > m ? x.amount : m), 0) || 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-zinc-300 text-left dark:border-zinc-600">
            <th
              scope="col"
              className="py-2 pr-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              <span className="sr-only">Rank, </span>
              {memberHeader}
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              {valueHeader}
            </th>
            <th
              scope="col"
              className="py-2 pl-3 text-right text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
            >
              Share
            </th>
            <th
              scope="col"
              className="hidden py-2 pl-3 text-xs font-semibold uppercase tracking-wide text-zinc-500 sm:table-cell dark:text-zinc-400"
            >
              <span aria-hidden="true">Share of total</span>
              <span className="sr-only">Share of total (visual bar)</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {members.map((m, i) => {
            const barWidthPct = Math.max(2, (m.amount / maxAmount) * 100);
            return (
              <tr key={m.value} className="border-b border-zinc-100 align-top dark:border-zinc-800">
                <th
                  scope="row"
                  className="max-w-md py-2 pr-3 text-left font-normal text-zinc-800 dark:text-zinc-200"
                >
                  <span className="mr-1.5 tabular-nums text-zinc-400 dark:text-zinc-500">
                    {i + 1}.
                  </span>
                  <span className="font-medium">{m.label}</span>
                  {memberKind === 'commodity' && (
                    <span className="mt-0.5 block text-xs text-zinc-400 dark:text-zinc-500">
                      HS {m.value}
                    </span>
                  )}
                </th>
                <td className="py-2 pl-3 text-right font-medium tabular-nums text-zinc-900 dark:text-zinc-50">
                  {formatNprBillion(m.amount)}
                </td>
                <td className="py-2 pl-3 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatSharePct(m.sharePct)}
                </td>
                <td className="hidden py-2 pl-3 align-middle sm:table-cell">
                  {/* Decorative share bar. aria-hidden: the share % is stated in
                      the adjacent text cell, so colour/width is never the only
                      carrier of meaning (WCAG AA). */}
                  <div
                    aria-hidden="true"
                    className="h-3 w-40 overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800"
                    title={`${formatSharePct(m.sharePct)} of total`}
                  >
                    <div
                      className="h-full rounded"
                      style={{ width: `${barWidthPct}%`, backgroundColor: barColor }}
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
