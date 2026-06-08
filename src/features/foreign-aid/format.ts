/**
 * Display formatters for the foreign-aid ("Money In") view.
 *
 * Shared by the Server page and the server table component. MUST remain a plain
 * (non-`'use client'`) module — a module exported from a `'use client'` file and
 * imported by a Server Component 500s the page at render time (the
 * money-map/tourism-rupee gotcha). No React here.
 *
 * UNIT CONTRACT (ADR-0011 / ADR-0017) — THE CRUX OF THIS PAGE:
 * The White Book's money unit VARIES BY EDITION and is carried per-row in the
 * `unit` column, verbatim and un-normalised:
 *   - FY 2020/21 (BS 2077/78): `(Rs. in '00000')` = lakh   → unit = 'npr_lakh'
 *   - FY 2015/16 (BS 2072/73): `(NRs'000s)`       = thousand → unit = 'npr_thousand'
 *
 * Raw values are NEVER shown and — critically — NEVER summed across editions
 * without converting first. The canonical display unit is NPR billion. The
 * conversion is keyed on the row's own `unit` string:
 *
 *   npr_lakh     : NPR = value × 100,000  → bn = value / 10,000
 *                  (1 lakh = 1e5 NPR; 1 bn = 1e9 NPR; 1e9 / 1e5 = 1e4)
 *   npr_thousand : NPR = value × 1,000    → bn = value / 1,000,000
 *                  (1 thousand = 1e3 NPR; 1e9 / 1e3 = 1e6)
 *
 * Worked examples (donor grant+loan totals, verified against live DB):
 *   FY 2020/21: 3,600,270 npr_lakh     / 10,000    = 360.027 → "NPR 360.0 bn"
 *   FY 2015/16: 205,894,111 npr_thousand / 1,000,000 = 205.894 → "NPR 205.9 bn"
 *
 * An unrecognised unit returns 0 (a typed dead-end, never a fabricated figure):
 * the query layer guarantees only these two units reach here, so an unknown unit
 * means upstream drift and must NOT be silently rescaled.
 */

/** The two White Book money units (ADR-0017), carried verbatim per row. */
export type ForeignAidUnit = 'npr_lakh' | 'npr_thousand';

/** value × 1e5 NPR per lakh → /1e4 to reach NPR billion (1 bn = 1e9 NPR). */
const LAKH_PER_BILLION = 10_000;
/** value × 1e3 NPR per thousand → /1e6 to reach NPR billion. */
const THOUSAND_PER_BILLION = 1_000_000;

/**
 * Convert a raw White Book value to NPR billion (numeric), keyed on the row's
 * own `unit`. This is the single place per-edition rescaling happens; every call
 * site MUST pass the value together with the unit it was stored under so a
 * lakh-edition figure and a thousand-edition figure never combine on the wrong
 * scale.
 */
export function toBillion(value: number, unit: ForeignAidUnit): number {
  if (!Number.isFinite(value)) return 0;
  switch (unit) {
    case 'npr_lakh':
      return value / LAKH_PER_BILLION;
    case 'npr_thousand':
      return value / THOUSAND_PER_BILLION;
    default:
      // Exhaustiveness guard: an unknown unit is upstream drift, not a value to
      // rescale. Return 0 rather than guess a divisor (Data Continuity Protocol).
      return 0;
  }
}

/**
 * Format an already-converted NPR-billion number as "NPR X.XX bn".
 *
 * Used when a total has already been summed in billion terms (the only safe way
 * to add figures that may span editions). en-IN grouping is applied. Returns a
 * null-safe "—" when the input is not finite.
 */
export function formatBillion(valueBillion: number, decimals = 2): string {
  if (!Number.isFinite(valueBillion)) return '—';
  const formatted = valueBillion.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `NPR ${formatted} bn`;
}

/**
 * Convenience: convert a raw value (with its unit) and format it as "NPR X.XX
 * bn" in one step, for single-row figures that are not pre-summed.
 */
export function formatNprBillion(value: number, unit: ForeignAidUnit, decimals = 2): string {
  return formatBillion(toBillion(value, unit), decimals);
}

/**
 * Percentage share (e.g. "36.7%") for a donor/sector slice of a total. Returns a
 * null-safe "—" when the input is not finite.
 */
export function formatSharePct(pct: number): string {
  if (!Number.isFinite(pct)) return '—';
  return `${pct.toFixed(1)}%`;
}
