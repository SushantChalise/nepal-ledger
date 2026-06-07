/**
 * d3-shape + d3-scale type adapters for line/area time-series charts.
 *
 * Like `d3-sankey.ts`, this module is the sanctioned home for the type bridges
 * that line charts need — per CONTEXT_RULES.md §"Cast Escape Hatches" item (c)
 * (`src/lib/viz/adapters/*`) and ADR-0012 (D3 viz type-bridges live in
 * `src/lib/viz/adapters/`). Feature components import the thin wrappers below
 * and never call raw `d3-shape`/`d3-scale` functions that require casts.
 *
 * What it wraps:
 *   - `scaleTime`   → x-axis: Date → pixel
 *   - `scaleLinear` → y-axis: number → pixel
 *   - `line()`      → SVG path `d` string from an array of typed points
 *
 * The d3 scale/shape generators carry generic accessor signatures whose
 * TypeScript form diverges from the plain `{ x: Date; y: number }` points we
 * pass; the casts here keep that divergence in one auditable place.
 */

import { scaleLinear, scaleTime } from 'd3-scale';
import { line } from 'd3-shape';

/** A single plotted point: a real Gregorian instant and a numeric value. */
export type TimePoint = {
  x: Date;
  y: number;
};

/** A linear pixel scale: maps a numeric/Date domain value to an x/y pixel. */
export type PixelScale<TDomain> = {
  (value: TDomain): number;
  /** The two-element [min, max] domain currently configured. */
  domain(): TDomain[];
  /** The two-element [start, end] pixel range currently configured. */
  range(): number[];
};

/**
 * Build a time scale (x-axis). `domain` is [earliest, latest] Date; `range`
 * is [leftPx, rightPx]. Returns a callable scale plus `.domain()`/`.range()`.
 */
export function buildTimeScale(
  domain: readonly [Date, Date],
  range: readonly [number, number],
): PixelScale<Date> {
  const scale = scaleTime()
    .domain(domain as [Date, Date])
    .range(range as [number, number]);
  // d3 scales are callable objects; narrowing to our PixelScale<Date> surface
  // is a documented bridge (ADR-0012) — the runtime object satisfies it.
  return scale as unknown as PixelScale<Date>;
}

/**
 * Build a linear scale (y-axis). `domain` is [min, max] numeric; `range` is
 * [bottomPx, topPx] (note: SVG y grows downward, so range is usually
 * [height, 0]). Returns a callable scale plus `.domain()`/`.range()`.
 */
export function buildLinearScale(
  domain: readonly [number, number],
  range: readonly [number, number],
): PixelScale<number> {
  const scale = scaleLinear()
    .domain(domain as [number, number])
    .range(range as [number, number]);
  return scale as unknown as PixelScale<number>;
}

/**
 * Generate an SVG path `d` string for a poly-line through `points`, projecting
 * each point through the supplied x and y pixel scales.
 *
 * Returns `''` when d3 yields `null` (empty input) so callers can pass the
 * result straight to an SVG `<path d=...>` without a null check.
 */
export function buildLinePath(
  points: readonly TimePoint[],
  xScale: PixelScale<Date>,
  yScale: PixelScale<number>,
): string {
  const generator = line<TimePoint>()
    .x((p) => xScale(p.x))
    .y((p) => yScale(p.y));
  return generator(points as TimePoint[]) ?? '';
}
