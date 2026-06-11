/**
 * PalikaChoropleth — absent-population SHARE by ORIGIN palika (View B, ADR-0025).
 *
 * A Server Component: the geometry is static and the per-palika values are
 * known at render time, so the whole map is server-rendered SVG with **zero
 * client JavaScript**. Hover/focus tooltips use native SVG `<title>` (works on
 * desktop hover and is exposed to assistive tech); a visually-hidden `<table>`
 * is the non-visual equivalent. This keeps the mobile-first budget tiny — no
 * client-side geo library, no hydration cost (UI_ACCEPTANCE.md).
 *
 * The fill is the **share of each local level's population living abroad** —
 * "migration intensity" — matching the NDRI Atlas's headline map. The unit is
 * still PEOPLE underneath (never currency); the tooltip shows both the % and
 * the headcount. Palikas with no census value (or no population denominator)
 * render in the neutral "no data" fill — never zero-filled (Data Continuity
 * Protocol).
 *
 * D3 is intentionally not used here: classification is a plain numeric
 * threshold and projection is precomputed into the asset, so there is nothing
 * to type-bridge (no `src/lib/viz/adapters/*` cast needed; ADR-0012 N/A).
 */

import { palikaGeometry } from '@/lib/viz/geo/palikas';

import { classOf, quantileBreaks } from '../choropleth-scale';
import { formatPeopleFull, formatSharePct } from '../format';
import type { PalikaDatum } from '../server/queries';

// ColorBrewer YlOrRd (6-class) — sequential, print-and-colourblind friendly.
// Low → high migration intensity. Index 0..5; NO_DATA is the neutral fill.
const RAMP = ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026'] as const;
const NO_DATA = '#e5e7eb'; // zinc-200
const STROKE = '#ffffff';

type Props = {
  /** federal_code → { people, population, pct }. Codes absent ⇒ no-data fill. */
  byCode: Record<string, PalikaDatum>;
  /** National share abroad (%), for the legend caption; null if unknown. */
  nationalPct: number | null;
  /** Census reference year (AD). */
  censusYearAd: string;
  /** Number of palikas carrying a value. */
  palikaCount: number;
};

export function PalikaChoropleth({ byCode, nationalPct, censusYearAd, palikaCount }: Props) {
  // Classification runs over the SHARE (%) values that have a denominator.
  const pctValues = Object.values(byCode)
    .map((d) => d.pct)
    .filter((p): p is number => p !== null);
  const breaks = quantileBreaks(pctValues);
  const hasData = breaks.length > 0;

  // Rank for the accessible table (highest migration intensity first).
  const ranked = palikaGeometry.features
    .map((f) => ({ ...f, datum: byCode[f.code] }))
    .filter(
      (f): f is typeof f & { datum: PalikaDatum & { pct: number } } =>
        (f.datum?.pct ?? null) !== null,
    )
    .sort((a, b) => b.datum.pct - a.datum.pct);

  const legendBands: { color: string; label: string }[] = [];
  if (hasData) {
    for (let i = 0; i < RAMP.length; i += 1) {
      const lo = i === 0 ? 0 : (breaks[i - 1] ?? 0);
      const hi = i < breaks.length ? (breaks[i] ?? Infinity) : Infinity;
      // Skip empty classes: when adjacent quantile breaks are equal (common on a
      // right-skewed distribution), that class holds no palika — `classOf` needs
      // lo < value ≤ hi — so its swatch would be a misleading zero-width band.
      if (i < RAMP.length - 1 && lo >= hi) continue;
      const label =
        i === RAMP.length - 1
          ? `≥ ${formatSharePct(lo)}`
          : `${formatSharePct(lo)}–${formatSharePct(hi)}`;
      legendBands.push({ color: RAMP[i] ?? NO_DATA, label });
    }
  }

  return (
    <figure className="m-0">
      <svg
        viewBox={palikaGeometry.viewBox}
        role="img"
        aria-label={`Choropleth map of Nepal's ${palikaGeometry.features.length} local levels, shaded by the share of each one's population living abroad in the ${censusYearAd} census (${palikaCount} with data).`}
        className="h-auto w-full"
        style={{ maxHeight: '70vh' }}
      >
        <desc>
          Each of Nepal&apos;s local levels (palikas) is shaded from light to dark by the share of
          its residents who were living abroad on census night {censusYearAd}. Darker means a larger
          share of the local population is abroad.
        </desc>
        {palikaGeometry.features.map((f) => {
          const d = byCode[f.code];
          const fill = d?.pct == null ? NO_DATA : (RAMP[classOf(d.pct, breaks)] ?? NO_DATA);
          return (
            <path key={f.code} d={f.d} fill={fill} stroke={STROKE} strokeWidth={0.3}>
              <title>
                {f.nameEn} ({f.district}):{' '}
                {d == null
                  ? 'no census value'
                  : d.pct == null
                    ? `${formatPeopleFull(d.people)} abroad (population not available)`
                    : `${formatSharePct(d.pct)} of population abroad · ${formatPeopleFull(d.people)} people`}
              </title>
            </path>
          );
        })}
      </svg>

      {/* Legend */}
      {hasData && (
        <figcaption className="mt-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Share of population abroad
              {nationalPct !== null ? ` (national ${formatSharePct(nationalPct)})` : ''}
            </span>
            <ul className="flex flex-wrap gap-x-3 gap-y-1" aria-hidden="true">
              {legendBands.map((b) => (
                <li key={b.color} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-3 w-3 rounded-sm ring-1 ring-black/10"
                    style={{ backgroundColor: b.color }}
                  />
                  <span className="text-xs text-zinc-500 dark:text-zinc-400">{b.label}</span>
                </li>
              ))}
              <li className="flex items-center gap-1.5">
                <span
                  className="inline-block h-3 w-3 rounded-sm ring-1 ring-black/10"
                  style={{ backgroundColor: NO_DATA }}
                />
                <span className="text-xs text-zinc-500 dark:text-zinc-400">no data</span>
              </li>
            </ul>
          </div>
        </figcaption>
      )}

      {/* Visually-hidden accessible equivalent: highest-intensity origin palikas. */}
      <table className="sr-only">
        <caption>
          Local levels with the highest share of population abroad, {censusYearAd} census.
        </caption>
        <thead>
          <tr>
            <th scope="col">Rank</th>
            <th scope="col">Local level</th>
            <th scope="col">District</th>
            <th scope="col">Share abroad</th>
            <th scope="col">Absent population</th>
          </tr>
        </thead>
        <tbody>
          {ranked.slice(0, 30).map((f, i) => (
            <tr key={f.code}>
              <td>{i + 1}</td>
              <td>{f.nameEn}</td>
              <td>{f.district}</td>
              <td>{formatSharePct(f.datum.pct)}</td>
              <td>{formatPeopleFull(f.datum.people)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
