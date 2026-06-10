import type { ReactNode } from 'react';

type KpiGroupProps = {
  title: string;
  description: string;
  children: ReactNode;
};

export function KpiGroup({ title, description, children }: KpiGroupProps) {
  return (
    <section aria-labelledby={`kpi-group-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="mb-3">
        <h2
          id={`kpi-group-${title.toLowerCase().replace(/\s+/g, '-')}`}
          className="text-base font-semibold text-zinc-700 dark:text-zinc-300"
        >
          {title}
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{children}</div>
    </section>
  );
}
