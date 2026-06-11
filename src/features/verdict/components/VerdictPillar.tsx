type PillarProps = {
  label: string;
  body: string;
};

const PILLAR_ACCENT: Record<string, string> = {
  'Money In': 'border-l-emerald-500 dark:border-l-emerald-400',
  'Money Out': 'border-l-red-400 dark:border-l-red-300',
  'Money Captured': 'border-l-amber-500 dark:border-l-amber-400',
  'Money Wasted': 'border-l-orange-500 dark:border-l-orange-400',
  'Where Money Becomes Wealth': 'border-l-blue-500 dark:border-l-blue-400',
};

export function VerdictPillar({ label, body }: PillarProps) {
  const accent = PILLAR_ACCENT[label] ?? 'border-l-zinc-400 dark:border-l-zinc-600';
  return (
    <div className={`border-l-4 pl-4 ${accent}`}>
      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
        {label}
      </p>
      <p className="mt-1 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">{body}</p>
    </div>
  );
}
