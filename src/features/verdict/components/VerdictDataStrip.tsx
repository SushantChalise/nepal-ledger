import type { ApprovedIndicatorWithMeta } from '@/lib/db/repositories/approved-indicator-values';

type Props = {
  rows: ApprovedIndicatorWithMeta[];
};

const UNIT_LABEL: Record<string, string> = {
  NPR_billion: 'NPR B',
  npr_billion: 'NPR B',
  percent_yoy: '%',
  percent: '%',
  months_of_imports: 'months',
  months: 'months',
  usd_million: 'USD M',
  usd: 'USD',
  index_points: 'Gini',
};

function formatStrip(
  rawValue: string,
  unit: string,
): { display: string; suffix: string } {
  const n = parseFloat(rawValue);
  if (isNaN(n)) return { display: rawValue, suffix: unit };

  const suffix = UNIT_LABEL[unit] ?? unit;

  if (unit === 'NPR_billion' || unit === 'npr_billion') {
    return {
      display: n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      suffix,
    };
  }
  if (unit === 'percent_yoy' || unit === 'percent') {
    return {
      display: n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      suffix,
    };
  }
  if (unit === 'months_of_imports' || unit === 'months') {
    return {
      display: n.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
      suffix,
    };
  }
  return {
    display: n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    suffix,
  };
}

const GRADE_STYLE: Record<string, string> = {
  A: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300',
  B: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-950 dark:text-amber-300',
  C: 'bg-zinc-100 text-zinc-600 ring-zinc-500/20 dark:bg-zinc-800 dark:text-zinc-400',
};

export function VerdictDataStrip({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-500">
        No approved indicators yet. Run an ingest first.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
      <table className="min-w-full divide-y divide-zinc-200 text-sm dark:divide-zinc-700">
        <thead className="bg-zinc-50 dark:bg-zinc-900">
          <tr>
            <th
              scope="col"
              className="py-2 pl-4 pr-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
            >
              Indicator
            </th>
            <th
              scope="col"
              className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
            >
              Value
            </th>
            <th
              scope="col"
              className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
            >
              Period
            </th>
            <th
              scope="col"
              className="py-2 pl-3 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
            >
              Grade
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 bg-white dark:divide-zinc-800 dark:bg-zinc-950">
          {rows.map((row) => {
            const { display, suffix } = formatStrip(row.value.value, row.indicator.unit);
            const gradeStyle =
              GRADE_STYLE[row.value.confidenceGrade] ?? GRADE_STYLE['C'];
            return (
              <tr key={row.value.id}>
                <td className="py-2 pl-4 pr-3 font-medium text-zinc-800 dark:text-zinc-200">
                  {row.indicator.nameEn}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {display}{' '}
                  <span className="text-xs text-zinc-400 dark:text-zinc-500">{suffix}</span>
                </td>
                <td className="px-3 py-2 text-zinc-500 dark:text-zinc-400">
                  {row.value.reportingPeriodBs}
                </td>
                <td className="py-2 pl-3 pr-4">
                  <span
                    className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset ${gradeStyle}`}
                  >
                    {row.value.confidenceGrade}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
