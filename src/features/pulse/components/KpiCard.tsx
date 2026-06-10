import type { ConfidenceGrade } from '@/lib/db/schema/enums';

type KpiCardProps = {
  label: string;
  value: string;
  unit: string;
  period: string;
  confidence: ConfidenceGrade;
};

const CONFIDENCE_LABEL: Record<ConfidenceGrade, string> = {
  A: 'Grade A',
  B: 'Grade B',
  C: 'Grade C',
};

const CONFIDENCE_COLOR: Record<ConfidenceGrade, string> = {
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-yellow-100 text-yellow-800',
  C: 'bg-orange-100 text-orange-800',
};

export function KpiCard({ label, value, unit, period, confidence }: KpiCardProps) {
  return (
    <article
      aria-label={label}
      className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900"
    >
      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {value}
        {unit && (
          <span className="ml-1 text-sm font-normal text-zinc-500 dark:text-zinc-400">{unit}</span>
        )}
      </p>
      <div className="flex items-center gap-2">
        <p className="text-xs text-zinc-500 dark:text-zinc-400">{period}</p>
        <span
          aria-label={`Confidence: ${CONFIDENCE_LABEL[confidence]}`}
          className={`rounded px-1.5 py-0.5 text-xs font-medium ${CONFIDENCE_COLOR[confidence]}`}
        >
          {CONFIDENCE_LABEL[confidence]}
        </span>
      </div>
    </article>
  );
}
