'use client';

/**
 * GdpTrajectoryChart — client component that renders Nepal's nominal vs real
 * GDP trajectory as two accessible inline SVG lines on a shared axis.
 *
 * Nominal grows with both output AND prices; real strips out inflation, so the
 * widening gap between the two lines IS the cumulative price effect. Both are
 * `npr_billion` at rest; the y-axis is labelled in NPR trillion (format.ts).
 *
 * Time axis: each point is plotted on its AD fiscal-year-end instant (`adEnd`)
 * for correct chronological spacing, but x-ticks are labelled with the BS
 * fiscal-year string (the canonical annual period for these series).
 *
 * D3 type-bridging lives in `src/lib/viz/adapters/d3-shape.ts` (ADR-0012); this
 * component imports only the typed wrappers and has zero `as` casts.
 *
 * Accessibility (UI_ACCEPTANCE.md):
 *   - SVG carries role="img" + a <desc> describing both series and the gap.
 *     The whole figure is decorative: the page also renders every value in a
 *     visible table, so this chart adds nothing meaning-bearing on its own.
 *   - A visually-hidden <table> still exposes both series per fiscal year for
 *     screen readers reaching the SVG directly.
 *   - The two lines are distinguished by an in-SVG text label at each line's
 *     end (not by colour alone); the legend below repeats name + colour.
 *   - prefers-reduced-motion disables the draw-in transition.
 */

import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react';

import {
  buildLinePath,
  buildLinearScale,
  buildTimeScale,
  type TimePoint,
} from '@/lib/viz/adapters/d3-shape';

import type { SeriesPoint } from '../server/queries';
import { formatNprTrillionCompact } from '../format';

const NOMINAL_FILL = '#0d9488'; // teal-600 — nominal GDP
const REAL_FILL = '#7c3aed'; // violet-600 — real GDP

const SVG_HEIGHT = 380;
const MARGIN = { top: 24, right: 64, bottom: 36, left: 64 } as const;
const DEFAULT_WIDTH = 800;

type GdpTrajectoryChartProps = {
  /** Nominal GDP series (npr_billion), ascending. */
  nominal: SeriesPoint[];
  /** Real GDP series (npr_billion), ascending. */
  real: SeriesPoint[];
};

export function GdpTrajectoryChart({ nominal, real }: GdpTrajectoryChartProps) {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const reducedMotion = usePrefersReducedMotion();
  const nominalPathRef = useRef<SVGPathElement | null>(null);
  const realPathRef = useRef<SVGPathElement | null>(null);

  // Reactive width via ResizeObserver, same approach as ArrivalsLineChart.
  const attachResizeObserver = (el: HTMLDivElement | null) => {
    if (!el) return;
    setWidth(el.clientWidth > 0 ? el.clientWidth : DEFAULT_WIDTH);
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const w = entry.contentRect.width;
        if (w > 0) setWidth(w);
      }
    });
    observer.observe(el);
    // Page-level component; observer GC'd when the element unmounts.
  };

  return (
    <div>
      <div ref={attachResizeObserver} className="w-full">
        <ChartSvg
          nominal={nominal}
          real={real}
          width={width}
          reducedMotion={reducedMotion}
          nominalPathRef={nominalPathRef}
          realPathRef={realPathRef}
        />
      </div>
      {/* Visible legend — text + colour, never colour alone. */}
      <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-zinc-600 dark:text-zinc-400">
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: NOMINAL_FILL }}
          />
          Nominal GDP (includes price rises)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: REAL_FILL }}
          />
          Real GDP (inflation stripped out)
        </span>
      </div>
      <AccessibleTableFallback nominal={nominal} real={real} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SVG chart
// ---------------------------------------------------------------------------

function ChartSvg({
  nominal,
  real,
  width,
  reducedMotion,
  nominalPathRef,
  realPathRef,
}: {
  nominal: SeriesPoint[];
  real: SeriesPoint[];
  width: number;
  reducedMotion: boolean;
  nominalPathRef: React.RefObject<SVGPathElement | null>;
  realPathRef: React.RefObject<SVGPathElement | null>;
}) {
  const descId = useId();
  const innerW = Math.max(1, width - MARGIN.left - MARGIN.right);
  const innerH = SVG_HEIGHT - MARGIN.top - MARGIN.bottom;

  const nominalPoints: TimePoint[] = nominal.map((p) => ({ x: new Date(p.adEnd), y: p.value }));
  const realPoints: TimePoint[] = real.map((p) => ({ x: new Date(p.adEnd), y: p.value }));

  // Shared domain spans the union of both series' time range and a common
  // y-max (nominal is always ≥ real, so nominal's peak bounds the axis).
  const allPoints = [...nominalPoints, ...realPoints];
  const firstMs = allPoints.reduce((m, p) => Math.min(m, p.x.getTime()), Number.POSITIVE_INFINITY);
  const lastMs = allPoints.reduce((m, p) => Math.max(m, p.x.getTime()), Number.NEGATIVE_INFINITY);
  const maxValue = allPoints.reduce((m, p) => (p.y > m ? p.y : m), 0);

  const hasData = allPoints.length > 0 && Number.isFinite(firstMs) && Number.isFinite(lastMs);
  const domainStart = hasData ? new Date(firstMs) : new Date(0);
  const domainEnd = hasData ? new Date(lastMs) : new Date(0);

  const xScale = buildTimeScale([domainStart, domainEnd], [0, innerW]);
  // y domain top-padded 8% so the peak does not touch the top border.
  const yScale = buildLinearScale([0, maxValue * 1.08 || 1], [innerH, 0]);

  const nominalPath = buildLinePath(nominalPoints, xScale, yScale);
  const realPath = buildLinePath(realPoints, xScale, yScale);

  // Draw-in animations (called unconditionally to satisfy rules-of-hooks; each
  // self-guards on a null path element / empty path).
  useDrawIn(nominalPathRef, reducedMotion, nominalPath);
  useDrawIn(realPathRef, reducedMotion, realPath);

  if (!hasData) return null;

  const yTicks = makeTicks(0, maxValue * 1.08 || 1, 5);
  // X ticks: pick ~6 evenly spaced source points and label them with the BS FY.
  const labelledPoints = pickFiscalYearTicks(nominal.length >= real.length ? nominal : real, 6);

  const lastNominal = nominalPoints[nominalPoints.length - 1];
  const lastReal = realPoints[realPoints.length - 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${SVG_HEIGHT}`}
      width="100%"
      height={SVG_HEIGHT}
      role="img"
      aria-labelledby={descId}
      className="overflow-visible text-zinc-500 dark:text-zinc-400"
    >
      <desc id={descId}>
        Line chart of Nepal&apos;s nominal versus real gross domestic product by fiscal year, in NPR
        trillion. The nominal line (which includes price rises) climbs faster than the real line
        (inflation stripped out); the widening gap between them is the cumulative effect of
        inflation. Every value is also listed in the data table on this page.
      </desc>

      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        {/* Y gridlines + labels (NPR trillion) */}
        <g aria-hidden="true">
          {yTicks.map((t) => {
            const y = yScale(t);
            return (
              <g key={`y-${t}`}>
                <line
                  x1={0}
                  x2={innerW}
                  y1={y}
                  y2={y}
                  stroke="currentColor"
                  strokeOpacity={0.15}
                  strokeWidth={1}
                />
                <text
                  x={-8}
                  y={y}
                  dy="0.32em"
                  textAnchor="end"
                  fontSize={10}
                  fill="currentColor"
                  className="tabular-nums"
                >
                  {formatNprTrillionCompact(t)}
                </text>
              </g>
            );
          })}
        </g>

        {/* X axis labels (BS fiscal years) */}
        <g aria-hidden="true">
          {labelledPoints.map((p) => {
            const x = xScale(new Date(p.adEnd));
            return (
              <text
                key={`x-${p.fiscalYearBs}`}
                x={x}
                y={innerH + 20}
                textAnchor="middle"
                fontSize={10}
                fill="currentColor"
                className="tabular-nums"
              >
                {p.fiscalYearBs}
              </text>
            );
          })}
        </g>

        {/* Real GDP line (drawn first, under nominal) */}
        <path
          ref={realPathRef}
          d={realPath}
          fill="none"
          stroke={REAL_FILL}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Nominal GDP line */}
        <path
          ref={nominalPathRef}
          d={nominalPath}
          fill="none"
          stroke={NOMINAL_FILL}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* End-of-line text labels so the two series are told apart without
            relying on colour alone. */}
        {lastNominal && (
          <text
            x={xScale(lastNominal.x) + 6}
            y={yScale(lastNominal.y)}
            dy="0.32em"
            fontSize={10}
            fontWeight={600}
            fill={NOMINAL_FILL}
            className="select-none"
          >
            Nominal
          </text>
        )}
        {lastReal && (
          <text
            x={xScale(lastReal.x) + 6}
            y={yScale(lastReal.y)}
            dy="0.32em"
            fontSize={10}
            fontWeight={600}
            fill={REAL_FILL}
            className="select-none"
          >
            Real
          </text>
        )}

        {/* Latest-point dots with native tooltips. */}
        {lastNominal && (
          <circle cx={xScale(lastNominal.x)} cy={yScale(lastNominal.y)} r={3.5} fill={NOMINAL_FILL}>
            <title>Nominal GDP: {formatNprTrillionCompact(lastNominal.y)}</title>
          </circle>
        )}
        {lastReal && (
          <circle cx={xScale(lastReal.x)} cy={yScale(lastReal.y)} r={3.5} fill={REAL_FILL}>
            <title>Real GDP: {formatNprTrillionCompact(lastReal.y)}</title>
          </circle>
        )}
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// prefers-reduced-motion subscription
// ---------------------------------------------------------------------------

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

/**
 * Subscribe to the OS reduced-motion preference via useSyncExternalStore — the
 * idiomatic way to read an external store (matchMedia) without a
 * setState-in-effect cascade. SSR snapshot is `true` (motion-free first paint).
 */
function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => true,
  );
}

function subscribeReducedMotion(onChange: () => void): () => void {
  const mq = window.matchMedia(REDUCED_MOTION_QUERY);
  mq.addEventListener('change', onChange);
  return () => mq.removeEventListener('change', onChange);
}

// ---------------------------------------------------------------------------
// Draw-in animation hook (reduced-motion aware)
// ---------------------------------------------------------------------------

function useDrawIn(
  pathRef: React.RefObject<SVGPathElement | null>,
  reducedMotion: boolean,
  linePath: string,
) {
  useEffect(() => {
    const el = pathRef.current;
    if (!el) return;

    if (reducedMotion) {
      // Ensure no residual dash offset when motion is disabled.
      el.style.strokeDasharray = '';
      el.style.strokeDashoffset = '';
      return;
    }

    const length = el.getTotalLength();
    el.style.transition = 'none';
    el.style.strokeDasharray = `${length}`;
    el.style.strokeDashoffset = `${length}`;
    // Force reflow so the starting offset is applied before transitioning.
    void el.getBoundingClientRect();
    el.style.transition = 'stroke-dashoffset 900ms ease-out';
    el.style.strokeDashoffset = '0';
  }, [pathRef, reducedMotion, linePath]);
}

// ---------------------------------------------------------------------------
// Accessible table fallback (visually hidden, always present)
// ---------------------------------------------------------------------------

function AccessibleTableFallback({
  nominal,
  real,
}: {
  nominal: SeriesPoint[];
  real: SeriesPoint[];
}) {
  // Join both series on fiscal year so each row carries nominal + real.
  const realByFy = new Map(real.map((p) => [p.fiscalYearBs, p.value]));
  return (
    <div className="sr-only">
      <table>
        <caption>Nepal nominal vs real GDP by fiscal year (NPR billion) — full series</caption>
        <thead>
          <tr>
            <th scope="col">Fiscal year (BS)</th>
            <th scope="col">Nominal GDP (NPR billion)</th>
            <th scope="col">Real GDP (NPR billion)</th>
          </tr>
        </thead>
        <tbody>
          {nominal.map((p) => (
            <tr key={p.fiscalYearBs}>
              <td>{p.fiscalYearBs}</td>
              <td>{p.value.toLocaleString('en-IN')}</td>
              <td>{(realByFy.get(p.fiscalYearBs) ?? NaN).toLocaleString('en-IN')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tick helpers
// ---------------------------------------------------------------------------

/** Evenly spaced numeric ticks across [min, max], inclusive, `count` steps. */
function makeTicks(min: number, max: number, count: number): number[] {
  if (count < 1 || max <= min) return [min];
  const step = (max - min) / count;
  const ticks: number[] = [];
  for (let i = 0; i <= count; i++) {
    ticks.push(min + step * i);
  }
  return ticks;
}

/**
 * Pick roughly `count` evenly spaced points from an ascending series, always
 * including the first and last, to use as labelled x-axis ticks. Annual series
 * have ~50 points; ~6 labels keep the axis legible.
 */
function pickFiscalYearTicks(points: readonly SeriesPoint[], count: number): SeriesPoint[] {
  if (points.length === 0) return [];
  if (points.length <= count) return [...points];
  const step = (points.length - 1) / (count - 1);
  const picked: SeriesPoint[] = [];
  const seen = new Set<number>();
  for (let i = 0; i < count; i++) {
    const idx = Math.round(i * step);
    if (!seen.has(idx)) {
      const p = points[idx];
      if (p) {
        picked.push(p);
        seen.add(idx);
      }
    }
  }
  return picked;
}
