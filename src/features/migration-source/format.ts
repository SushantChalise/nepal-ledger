/**
 * Display formatters for the migration-source (absent-population) view.
 *
 * Shared by the Server page and the `'use client'` DestinationBarChart.
 * MUST remain a plain (non-`'use client'`) module — a module exported from a
 * `'use client'` file and imported by a Server Component 500s the page at
 * render time (the money-map/tourism-rupee gotcha). No React here.
 *
 * The measure is PEOPLE (absent-population headcount), never currency. Format
 * helpers are named accordingly so call sites cannot drift into rupee phrasing.
 */

/**
 * Compact people-count for axis ticks and inline figures. Absent-population
 * counts span four orders of magnitude (hundreds for South America → ~800k for
 * the Middle East), so a compact form keeps a horizontal axis legible.
 *
 *   ≥ 1,000,000 → "1.2M"
 *   ≥ 1,000     → "804.6K"
 *   < 1,000     → exact integer (e.g. "810")
 */
export function formatPeople(value: number): string {
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
 * Full grouped people-count for the accessible table and prose (e.g.
 * "8,04,614"). Uses en-IN grouping to match the rest of the app's number
 * presentation (lakh/crore digit grouping).
 */
export function formatPeopleFull(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return Math.round(value).toLocaleString('en-IN');
}

/**
 * Percentage share for the destination ranking (e.g. "36.7%"). Returns a
 * null-safe "—" when the input is not finite.
 */
export function formatSharePct(pct: number): string {
  if (!Number.isFinite(pct)) return '—';
  return `${pct.toFixed(1)}%`;
}
