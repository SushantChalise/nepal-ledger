/**
 * Pure classification helpers for the palika choropleth (View B).
 *
 * Kept in a plain (non-`'use client'`, no-JSX) module so they can be unit
 * tested without pulling in React, and reused by any future choropleth. The
 * scale is a 6-class **quantile** classification: each colour band holds
 * roughly the same number of palikas, which reads better than equal-interval
 * for the heavily right-skewed migration distribution.
 */

/** Number of colour classes (matches the 6-colour ramp in PalikaChoropleth). */
export const CHOROPLETH_CLASSES = 6;

/**
 * The 5 internal break points (→ 6 classes) at the 1/6…5/6 quantiles of the
 * positive values. Returns `[]` when there are no positive values (the caller
 * then renders everything as "no data"). Breaks are non-decreasing.
 */
export function quantileBreaks(values: readonly number[]): number[] {
  const sorted = values.filter((v) => v > 0).sort((a, b) => a - b);
  if (sorted.length === 0) return [];
  const at = (q: number): number => {
    const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor(q * sorted.length)));
    return sorted[idx] ?? 0;
  };
  const breaks: number[] = [];
  for (let i = 1; i < CHOROPLETH_CLASSES; i += 1) {
    breaks.push(at(i / CHOROPLETH_CLASSES));
  }
  return breaks;
}

/**
 * Class index 0…(CHOROPLETH_CLASSES-1) for `value` given the internal `breaks`.
 * A value equal to a break falls in the lower class; values above the last
 * break land in the top class.
 */
export function classOf(value: number, breaks: readonly number[]): number {
  let i = 0;
  while (i < breaks.length && value > (breaks[i] ?? Infinity)) i += 1;
  return i;
}
