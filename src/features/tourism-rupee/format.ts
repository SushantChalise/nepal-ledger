/**
 * Display formatters for the Tourism Rupee arrivals series.
 *
 * Shared by the Server page and the `'use client'` ArrivalsLineChart.
 * MUST remain a plain (non-`'use client'`) module — a module exported from a
 * `'use client'` file and imported by a Server Component 500s the page at
 * render time (the same gotcha money-map/format.ts documents). No React here.
 */

/**
 * Compact tourist-arrivals count for axis ticks, KPI values, and tooltips.
 * Tourist arrivals span 4 orders of magnitude (14 at the COVID trough →
 * ~150k peak months), so a compact representation keeps axes legible.
 *
 *   ≥ 1,000,000 → "1.2M"
 *   ≥ 1,000     → "116.6K"
 *   < 1,000     → exact integer (e.g. "14")
 */
export function formatCount(value: number): string {
  if (!Number.isFinite(value)) return '—';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    return `${sign}${(abs / 1_000).toFixed(1)}K`;
  }
  return `${sign}${Math.round(abs).toString()}`;
}

/**
 * Full grouped count for the accessible table and prose (e.g. "116,553").
 * Uses en-IN grouping to match the rest of the app's number presentation.
 */
export function formatCountFull(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return Math.round(value).toLocaleString('en-IN');
}

/**
 * Signed percentage for the year-over-year delta (e.g. "+12.4%", "-98.7%").
 * Returns null-safe "—" when the input is not finite (e.g. no prior-year row).
 */
export function formatYoyPct(pct: number | null): string {
  if (pct === null || !Number.isFinite(pct)) return '—';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

/**
 * Short month label for an AD month-end Date (e.g. "Nov 2025"). Used on the
 * x-axis and in tooltips. Uses UTC to avoid the month-end timestamp slipping
 * to the previous day in negative-offset render environments.
 */
export function formatMonthLabel(date: Date): string {
  return date.toLocaleDateString('en-GB', {
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}
