import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { formatAppError } from '@/lib/errors';
import {
  LAUNCH_DISTRICTS,
  findLaunchDistrictBySlug,
  type LaunchDistrict,
} from '@/features/district-mri/launch-districts';
import {
  getDistrictMriData,
  MISSING_PILLAR_FIELDS,
  type DistrictMriData,
} from '@/features/district-mri/server/queries';
import { formatNprCrore } from '@/features/district-mri/format';
import { MetricBar } from '@/features/district-mri/components/MetricBar';
import { MissingDataPanel } from '@/features/district-mri/components/MissingDataPanel';

type PageParams = { district: string };

/** Pre-render all 5 launch districts at build time. */
export function generateStaticParams(): PageParams[] {
  return LAUNCH_DISTRICTS.map((d) => ({ district: d.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<PageParams>;
}): Promise<Metadata> {
  const { district } = await params;
  const ld = findLaunchDistrictBySlug(district);
  if (!ld) return { title: 'District not found — Nepal Ledger' };
  return {
    title: `${ld.nameEn} — District MRI — Nepal Ledger`,
    description: `Economic dashboard for ${ld.nameEn} (${ld.province} Province): federal fiscal transfers received and 2021 census household wealth indicators.`,
  };
}

export default async function DistrictPage({ params }: { params: Promise<PageParams> }) {
  const { district } = await params;
  const ld = findLaunchDistrictBySlug(district);

  // Unknown slug → real 404 (not in the launch set).
  if (!ld) notFound();

  const result = await getDistrictMriData(ld.districtEn);

  if (!result.ok) {
    // NotFound here means the district name matched no local levels — render a
    // typed empty state rather than a 404, since the slug IS a launch district.
    if (result.error.kind === 'NotFound') {
      return (
        <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
          <DistrictHeader district={ld} />
          <EmptyState districtName={ld.nameEn} />
        </main>
      );
    }
    return (
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        <DistrictHeader district={ld} />
        <div
          role="alert"
          aria-live="polite"
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-950"
        >
          <p className="text-sm font-medium text-red-700 dark:text-red-300">
            Unable to load district data
          </p>
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">
            {formatAppError(result.error)}
          </p>
          <p className="mt-3 text-xs text-red-500 dark:text-red-400">
            Refresh the page or check back shortly.
          </p>
        </div>
      </main>
    );
  }

  const data = result.value;
  const hasAnyData =
    (data.fiscal && data.fiscal.byGrantType.length > 0) ||
    data.censusMetrics.some((m) => m.ratio !== null);

  if (!hasAnyData) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        <DistrictHeader district={ld} data={data} />
        <EmptyState districtName={ld.nameEn} />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
      <DistrictHeader district={ld} data={data} />

      {/* What this shows — required plain-language interpretation (UI_ACCEPTANCE). */}
      <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 px-5 py-4 dark:border-blue-900 dark:bg-blue-950">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">What this shows:</span> {ld.nameEn}&apos;s{' '}
          {data.palikaCount} local government{data.palikaCount === 1 ? '' : 's'} received{' '}
          {data.fiscal ? (
            <span className="font-medium">{formatNprCrore(data.fiscal.grandTotalNprCrore)}</span>
          ) : (
            <span className="font-medium">no recorded</span>
          )}{' '}
          in federal transfers
          {data.fiscal ? ` in FY ${data.fiscal.fiscalYearBs}` : ''}. The census measures below show
          how households in the district are placed on the path from income to durable wealth.
        </p>
      </div>

      {/* Fiscal transfers */}
      {data.fiscal && data.fiscal.byGrantType.length > 0 && (
        <section aria-labelledby="district-fiscal-heading" className="mt-8">
          <h2
            id="district-fiscal-heading"
            className="text-base font-semibold text-zinc-700 dark:text-zinc-300"
          >
            Federal transfers received — FY {data.fiscal.fiscalYearBs}
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Total {formatNprCrore(data.fiscal.grandTotalNprCrore)} across{' '}
            {data.fiscal.byGrantType.length} grant types, summed over the district&apos;s local
            governments.
          </p>
          <table className="mt-4 w-full text-sm">
            <caption className="sr-only">
              Federal fiscal transfers to {ld.nameEn} by grant type, FY {data.fiscal.fiscalYearBs},
              in NPR
            </caption>
            <thead>
              <tr className="border-b border-zinc-200 text-left dark:border-zinc-700">
                <th scope="col" className="py-2 font-medium text-zinc-600 dark:text-zinc-400">
                  Grant type
                </th>
                <th
                  scope="col"
                  className="py-2 text-right font-medium text-zinc-600 dark:text-zinc-400"
                >
                  Amount
                </th>
                <th
                  scope="col"
                  className="py-2 text-right font-medium text-zinc-600 dark:text-zinc-400"
                >
                  Share
                </th>
              </tr>
            </thead>
            <tbody>
              {data.fiscal.byGrantType.map((g) => {
                const share =
                  data.fiscal!.grandTotalNprCrore > 0
                    ? (g.totalNprCrore / data.fiscal!.grandTotalNprCrore) * 100
                    : 0;
                return (
                  <tr key={g.grantType} className="border-b border-zinc-100 dark:border-zinc-800">
                    <td className="py-2 text-zinc-700 dark:text-zinc-300">{g.label}</td>
                    <td className="py-2 text-right tabular-nums text-zinc-900 dark:text-zinc-50">
                      {formatNprCrore(g.totalNprCrore)}
                    </td>
                    <td className="py-2 text-right tabular-nums text-zinc-500 dark:text-zinc-400">
                      {share.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="font-semibold">
                <td className="py-2 text-zinc-700 dark:text-zinc-300">Total</td>
                <td className="py-2 text-right tabular-nums text-zinc-900 dark:text-zinc-50">
                  {formatNprCrore(data.fiscal.grandTotalNprCrore)}
                </td>
                <td className="py-2 text-right tabular-nums text-zinc-500 dark:text-zinc-400">
                  100%
                </td>
              </tr>
            </tfoot>
          </table>
        </section>
      )}

      {/* Census wealth indicators */}
      {data.censusMetrics.some((m) => m.ratio !== null) && (
        <section aria-labelledby="district-census-heading" className="mt-10">
          <h2
            id="district-census-heading"
            className="text-base font-semibold text-zinc-700 dark:text-zinc-300"
          >
            Household indicators — Census {data.censusYearAd ?? '2021'}
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Each share is computed from that census table&apos;s own household total, summed across
            the district&apos;s local governments.
          </p>
          <div className="mt-5 flex flex-col gap-5">
            {data.censusMetrics.map((m) => (
              <MetricBar key={m.id} metric={m} />
            ))}
          </div>
        </section>
      )}

      {/* Honest gaps */}
      <div className="mt-10">
        <MissingDataPanel fields={MISSING_PILLAR_FIELDS} />
      </div>

      {/* Source attribution + confidence (UI_ACCEPTANCE required elements). */}
      <footer className="mt-8 border-t border-zinc-200 pt-4 dark:border-zinc-700">
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Fiscal source:</dt>
            <dd>Ministry of Finance — Intergovernmental Fiscal Transfer Schedule, FY 2082/83</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Census source:</dt>
            <dd>Central Bureau of Statistics — National Population &amp; Housing Census 2021</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Confidence:</dt>
            <dd>
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-800">
                Grade A
              </span>
              <span className="ml-1">— official government sources</span>
            </dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-zinc-600 dark:text-zinc-400">Units:</dt>
            <dd>Transfers in NPR crore; census shares as % of households</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
          <Link
            href="/districts"
            className="text-teal-700 underline hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300"
          >
            &larr; All districts
          </Link>
        </p>
      </footer>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DistrictHeader({ district, data }: { district: LaunchDistrict; data?: DistrictMriData }) {
  return (
    <header>
      <p className="text-sm font-medium text-teal-700 dark:text-teal-400">District MRI</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        {district.nameEn}
      </h1>
      <p className="mt-2 text-base text-zinc-600 dark:text-zinc-400">
        {district.province} Province
        {data !== undefined && (
          <>
            <span className="mx-2" aria-hidden="true">
              ·
            </span>
            {data.palikaCount} local government{data.palikaCount === 1 ? '' : 's'}
          </>
        )}
      </p>
    </header>
  );
}

function EmptyState({ districtName }: { districtName: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="mt-8 rounded-lg border border-zinc-200 bg-zinc-50 p-10 text-center dark:border-zinc-700 dark:bg-zinc-900"
    >
      <p className="text-base font-medium text-zinc-600 dark:text-zinc-400">
        No data yet for {districtName}
      </p>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
        Fiscal-transfer and census records for this district will appear once the relevant ingestion
        runs complete.
      </p>
    </div>
  );
}
