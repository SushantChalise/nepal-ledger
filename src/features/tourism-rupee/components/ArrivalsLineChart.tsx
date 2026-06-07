'use client';

/**
 * ArrivalsLineChart — client component that renders the monthly tourist-
 * arrivals series as an accessible inline SVG line chart.
 *
 * Time axis: every point is plotted on its AD month-end (`point.x`), never on
 * the BS label — see queries.ts GOTCHA and docs/research/DATA_BUILDOUT_PLAN.md
 * §#27. The BS labels skew near COVID; the AD end date is the trustworthy axis.
 *
 * D3 type-bridging lives in `src/lib/viz/adapters/d3-shape.ts` (ADR-0012); this
 * component imports only the typed wrappers and has zero `as` casts.
 *
 * Accessibility (UI_ACCEPTANCE.md):
 *   - SVG has role="img" + an aria-label describing the data shape + argument.
 *   - A visually-hidden <table> exposes every observation for screen readers.
 *   - A COVID reference marker is labelled in text, not by colour alone.
 *   - prefers-reduced-motion: the draw-in transition is disabled.
 *   - <640px: the SVG still renders (it is a single hero viz that scales via
 *     viewBox); the sr-only table is the non-visual fallback.
 */

import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react';

import {
  buildLinePath,
  buildLinearScale,
  buildTimeScale,
  type TimePoint,
} from '@/lib/viz/adapters/d3-shape';

import type { ArrivalsPoint } from '../server/queries';
import { formatCount, formatCountFull, formatMonthLabel } from '../format';

// The COVID border-closure trough: Nepal sealed entry late March 2020 and the
// April-2020 month recorded ~14 arrivals (annotation anchor per the spec). We
// mark the calendar instant and let the chart place it on the time axis.
const COVID_TROUGH = new Date('2020-04-15T00:00:00Z');
const COVID_LABEL = 'COVID-19 border closure (Apr 2020)';

const SVG_HEIGHT = 380;
const MARGIN = { top: 24, right: 20, bottom: 36, left: 56 } as const;
const DEFAULT_WIDTH = 800;

type ArrivalsLineChartProps = {
  points: ArrivalsPoint[];
};

export function ArrivalsLineChart({ points }: ArrivalsLineChartProps) {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const reducedMotion = usePrefersReducedMotion();
  const pathRef = useRef<SVGPathElement | null>(null);

  // Reactive width via ResizeObserver, same approach as SankeyDiagram.
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
        <ChartSvg points={points} width={width} reducedMotion={reducedMotion} pathRef={pathRef} />
      </div>
      <AccessibleTableFallback points={points} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SVG chart
// ---------------------------------------------------------------------------

function ChartSvg({
  points,
  width,
  reducedMotion,
  pathRef,
}: {
  points: ArrivalsPoint[];
  width: number;
  reducedMotion: boolean;
  pathRef: React.RefObject<SVGPathElement | null>;
}) {
  const descId = useId();
  const innerW = Math.max(1, width - MARGIN.left - MARGIN.right);
  const innerH = SVG_HEIGHT - MARGIN.top - MARGIN.bottom;

  // Map ArrivalsPoint → {x: Date, y: number}.
  const timePoints: TimePoint[] = points.map((p) => ({
    x: new Date(p.adEnd),
    y: p.arrivals,
  }));

  const first = timePoints[0];
  const last = timePoints[timePoints.length - 1];
  const maxArrivals = timePoints.reduce((m, p) => (p.y > m ? p.y : m), 0);

  // Scales degrade gracefully on an empty series (caller guarantees non-empty,
  // but we keep these total so the hooks below run unconditionally — see the
  // rules-of-hooks note: no hook may sit behind the `first/last` guard).
  const domainStart = first?.x ?? new Date(0);
  const domainEnd = last?.x ?? new Date(0);
  const xScale = buildTimeScale([domainStart, domainEnd], [0, innerW]);
  // y domain top-padded 8% so the peak does not touch the top border.
  const yScale = buildLinearScale([0, maxArrivals * 1.08 || 1], [innerH, 0]);

  const linePath = buildLinePath(timePoints, xScale, yScale);

  // Draw-in animation: stroke-dash trick, disabled under reduced motion.
  // Called unconditionally (before the empty-series guard) to satisfy
  // rules-of-hooks; it self-guards on a null path element / empty path.
  useDrawIn(pathRef, reducedMotion, linePath);

  if (!first || !last) return null;

  // Y gridlines / ticks (5 evenly spaced).
  const yTicks = makeTicks(0, maxArrivals * 1.08 || 1, 5);
  // X ticks: ~6 year markers across the domain.
  const xTicks = makeYearTicks(first.x, last.x, 6);

  // COVID reference marker — only drawn if it falls within the domain.
  const covidInRange =
    COVID_TROUGH.getTime() >= first.x.getTime() && COVID_TROUGH.getTime() <= last.x.getTime();
  const covidX = covidInRange ? xScale(COVID_TROUGH) : null;

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
        Line chart of monthly tourist arrivals to Nepal from {formatMonthLabel(first.x)} to{' '}
        {formatMonthLabel(last.x)}. Arrivals grow from the 1990s to a pre-pandemic peak, collapse to
        near zero during the 2020 COVID-19 border closure, then recover. Latest month:{' '}
        {formatCountFull(last.y)} arrivals.
      </desc>

      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        {/* Y gridlines + labels */}
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
                  {formatCount(t)}
                </text>
              </g>
            );
          })}
        </g>

        {/* X axis labels (years) */}
        <g aria-hidden="true">
          {xTicks.map((d) => {
            const x = xScale(d);
            return (
              <text
                key={`x-${d.getTime()}`}
                x={x}
                y={innerH + 20}
                textAnchor="middle"
                fontSize={10}
                fill="currentColor"
                className="tabular-nums"
              >
                {d.getUTCFullYear()}
              </text>
            );
          })}
        </g>

        {/* COVID reference marker — dashed vertical line + text label */}
        {covidX !== null && (
          <g aria-hidden="true">
            <line
              x1={covidX}
              x2={covidX}
              y1={0}
              y2={innerH}
              stroke="#dc2626"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              strokeOpacity={0.8}
            />
            <text
              x={covidX + 5}
              y={10}
              fontSize={10}
              fontWeight={600}
              fill="#dc2626"
              className="select-none"
            >
              {COVID_LABEL}
            </text>
          </g>
        )}

        {/* The series line */}
        <path
          ref={pathRef}
          d={linePath}
          fill="none"
          stroke="#0d9488"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Latest-point dot + label */}
        <g>
          <circle cx={xScale(last.x)} cy={yScale(last.y)} r={3.5} fill="#0d9488">
            <title>
              {formatMonthLabel(last.x)}: {formatCountFull(last.y)} arrivals
            </title>
          </circle>
        </g>
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

function AccessibleTableFallback({ points }: { points: ArrivalsPoint[] }) {
  return (
    <div className="sr-only">
      <table>
        <caption>Monthly tourist arrivals to Nepal — full series</caption>
        <thead>
          <tr>
            <th scope="col">Month (AD)</th>
            <th scope="col">Period (BS)</th>
            <th scope="col">Arrivals</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.adEnd}>
              <td>{formatMonthLabel(new Date(p.adEnd))}</td>
              <td>{p.periodBs}</td>
              <td>{formatCountFull(p.arrivals)}</td>
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
 * Roughly `count` year-boundary Date ticks across [start, end]. Picks whole
 * years at an interval that yields ≈count labels, so the axis stays legible
 * across a 30+ year domain.
 */
function makeYearTicks(start: Date, end: Date, count: number): Date[] {
  const startYear = start.getUTCFullYear();
  const endYear = end.getUTCFullYear();
  const span = Math.max(1, endYear - startYear);
  const step = Math.max(1, Math.round(span / count));
  const ticks: Date[] = [];
  for (let y = startYear; y <= endYear; y += step) {
    const d = new Date(Date.UTC(y, 0, 1));
    if (d.getTime() >= start.getTime() && d.getTime() <= end.getTime()) {
      ticks.push(d);
    }
  }
  return ticks;
}
