'use client';

/**
 * DestinationBarChart — client component that renders the absent-population
 * ranking as an accessible horizontal bar chart (one bar per destination
 * region, longest at the top).
 *
 * Measure: PEOPLE (absent-population headcount), NOT remittance/currency. The
 * bars encode person counts from the CBS 2021 census (see queries.ts semantic
 * note). A horizontal layout is used because the region labels are long and a
 * ranked bar chart reads top-to-bottom.
 *
 * D3 usage: only the numeric x-scale is needed (count → pixel width), supplied
 * by `buildLinearScale` from `src/lib/viz/adapters/d3-shape.ts` (ADR-0012 —
 * the sanctioned cast location). Row positions are a plain arithmetic band, so
 * this component has zero `as` casts.
 *
 * Accessibility (UI_ACCEPTANCE.md):
 *   - SVG has role="img" + an aria-label describing the data shape.
 *   - A visually-hidden <table> exposes every row for screen readers and is
 *     the non-visual fallback at every viewport.
 *   - <640px: a flex bar list replaces the SVG (labels stack above each bar),
 *     because long region labels do not fit a narrow SVG gutter.
 *   - prefers-reduced-motion: bar grow-in transition is disabled.
 *   - Colour is never the sole carrier of meaning — every bar is labelled.
 */

import { useId, useState, useSyncExternalStore } from 'react';

import { buildLinearScale } from '@/lib/viz/adapters/d3-shape';

import type { DestinationCount } from '../server/queries';
import { formatPeople, formatPeopleFull, formatSharePct } from '../format';

const SVG_ROW_HEIGHT = 34;
const MARGIN = { top: 8, right: 64, bottom: 28, left: 220 } as const;
const DEFAULT_WIDTH = 800;
const BAR_FILL = '#0d9488';

type DestinationBarChartProps = {
  destinations: DestinationCount[];
};

export function DestinationBarChart({ destinations }: DestinationBarChartProps) {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const reducedMotion = usePrefersReducedMotion();

  // Reactive width via ResizeObserver — same approach as the sibling charts.
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
      {/* ≥640px: SVG bar chart. <640px: stacked bar list. */}
      <div ref={attachResizeObserver} className="hidden w-full sm:block">
        <ChartSvg destinations={destinations} width={width} reducedMotion={reducedMotion} />
      </div>
      <div className="sm:hidden">
        <NarrowBarList destinations={destinations} />
      </div>
      <AccessibleTableFallback destinations={destinations} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SVG bar chart (≥640px)
// ---------------------------------------------------------------------------

function ChartSvg({
  destinations,
  width,
  reducedMotion,
}: {
  destinations: DestinationCount[];
  width: number;
  reducedMotion: boolean;
}) {
  const descId = useId();
  const innerW = Math.max(1, width - MARGIN.left - MARGIN.right);
  const innerH = destinations.length * SVG_ROW_HEIGHT;
  const svgHeight = innerH + MARGIN.top + MARGIN.bottom;

  const maxPeople = destinations.reduce((m, d) => (d.people > m ? d.people : m), 0);
  // x: count → pixel width. Top-padded 2% so the longest bar leaves room for
  // its end label. Total scale guards an all-zero series (caller rules this out).
  const xScale = buildLinearScale([0, maxPeople * 1.02 || 1], [0, innerW]);

  const transition = reducedMotion ? undefined : 'width 700ms ease-out';

  return (
    <svg
      viewBox={`0 0 ${width} ${svgHeight}`}
      width="100%"
      height={svgHeight}
      role="img"
      aria-labelledby={descId}
      className="overflow-visible text-zinc-500 dark:text-zinc-400"
    >
      <desc id={descId}>
        Horizontal bar chart ranking the destinations of Nepal&apos;s absent population (people
        living abroad) recorded in the 2021 census. The Middle East and India are the two largest
        destinations, together accounting for most of the absent population; remaining regions
        follow in descending order.
      </desc>

      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        {destinations.map((d, i) => {
          const y = i * SVG_ROW_HEIGHT;
          const barH = SVG_ROW_HEIGHT - 10;
          const barW = Math.max(0, xScale(d.people));
          return (
            <g key={d.code}>
              {/* Destination label in the left gutter */}
              <text
                x={-12}
                y={y + barH / 2}
                dy="0.32em"
                textAnchor="end"
                fontSize={12}
                fill="currentColor"
              >
                {d.label}
              </text>
              {/* Track (faint) for visual baseline */}
              <rect x={0} y={y} width={innerW} height={barH} fill="currentColor" opacity={0.06} />
              {/* Value bar */}
              <rect
                x={0}
                y={y}
                width={barW}
                height={barH}
                fill={BAR_FILL}
                rx={2}
                style={transition ? { transition } : undefined}
              >
                <title>
                  {d.label}: {formatPeopleFull(d.people)} people ({formatSharePct(d.sharePct)})
                </title>
              </rect>
              {/* End label: count + share */}
              <text
                x={barW + 8}
                y={y + barH / 2}
                dy="0.32em"
                textAnchor="start"
                fontSize={11}
                fill="currentColor"
                className="tabular-nums"
              >
                {formatPeople(d.people)} · {formatSharePct(d.sharePct)}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Narrow (<640px) bar list — labels stack above each bar
// ---------------------------------------------------------------------------

function NarrowBarList({ destinations }: { destinations: DestinationCount[] }) {
  const maxPeople = destinations.reduce((m, d) => (d.people > m ? d.people : m), 0) || 1;
  return (
    <ul className="flex flex-col gap-3">
      {destinations.map((d) => {
        const widthPct = Math.max(1, (d.people / maxPeople) * 100);
        return (
          <li key={d.code}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {d.label}
              </span>
              <span className="text-xs tabular-nums text-zinc-500 dark:text-zinc-400">
                {formatPeopleFull(d.people)} · {formatSharePct(d.sharePct)}
              </span>
            </div>
            <div className="mt-1 h-3 w-full overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800">
              <div
                className="h-full rounded"
                style={{ width: `${widthPct}%`, backgroundColor: BAR_FILL }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Accessible table fallback (visually hidden, always present)
// ---------------------------------------------------------------------------

function AccessibleTableFallback({ destinations }: { destinations: DestinationCount[] }) {
  return (
    <div className="sr-only">
      <table>
        <caption>
          Nepal&apos;s absent population by destination region, 2021 census (people)
        </caption>
        <thead>
          <tr>
            <th scope="col">Destination region</th>
            <th scope="col">Absent population (people)</th>
            <th scope="col">Share</th>
          </tr>
        </thead>
        <tbody>
          {destinations.map((d) => (
            <tr key={d.code}>
              <td>{d.label}</td>
              <td>{formatPeopleFull(d.people)}</td>
              <td>{formatSharePct(d.sharePct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
