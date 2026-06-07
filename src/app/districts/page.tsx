import type { Metadata } from 'next';
import Link from 'next/link';

import { LAUNCH_DISTRICTS } from '@/features/district-mri/launch-districts';

export const metadata: Metadata = {
  title: 'District MRI — Nepal Ledger',
  description:
    "Per-district economic dashboards for Nepal's launch districts — fiscal transfers received and 2021 census wealth indicators (home ownership, internet access, female asset ownership, household entrepreneurship).",
};

export default function DistrictsIndexPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          District MRI
        </h1>
        <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
          A per-district economic dashboard — the &ldquo;MRI&rdquo; of where Nepal&apos;s money
          lands and whether it becomes wealth. Each district rolls up federal fiscal transfers (FY
          2082/83) and 2021 census household indicators. Five launch districts; more to follow.
        </p>
      </header>

      <section aria-label="Launch districts" className="mt-10">
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {LAUNCH_DISTRICTS.map((d) => (
            <li key={d.slug}>
              <Link
                href={`/districts/${d.slug}`}
                className="block rounded-lg border border-zinc-200 bg-white p-5 shadow-sm transition-colors hover:border-teal-400 hover:bg-teal-50/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-teal-600 dark:hover:bg-teal-950/30"
              >
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  {d.nameEn}
                </h2>
                <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
                  {d.province} Province
                </p>
                <p className="mt-3 text-sm font-medium text-teal-700 dark:text-teal-400">
                  View dashboard &rarr;
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-10 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Sources: Ministry of Finance — Intergovernmental Fiscal Transfer Schedule (FY 2082/83);
          Central Bureau of Statistics — National Population &amp; Housing Census 2021. All figures
          aggregate the district&apos;s local levels.{' '}
          <Link
            href="/money-map"
            className="text-teal-700 underline hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300"
          >
            See the national Money Map &rarr;
          </Link>
        </p>
      </footer>
    </main>
  );
}
