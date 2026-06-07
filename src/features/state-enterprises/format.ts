/**
 * Display formatters for the state-enterprises (Public Enterprise X-Ray) view.
 *
 * Shared by the Server page and the server table component. MUST remain a plain
 * (non-`'use client'`) module — a module exported from a `'use client'` file and
 * imported by a Server Component 500s the page at render time (the
 * money-map/tourism-rupee gotcha). No React here.
 *
 * UNIT CONTRACT (ADR-0011): the underlying values are NPR THOUSAND
 * (`unit = 'npr_thousand'`, from the Annex-1 header "(रु. हजारमा)"). Raw
 * thousands are NEVER shown. The canonical display unit is NPR billion:
 *
 *     NPR billion = value_thousand / 1_000_000
 *
 * because 1 billion NPR = 1,000,000 thousand NPR. Worked example (Nepal
 * Electricity Authority government share): 181,330,245 thousand / 1e6 =
 * 181.330245 → "NPR 181.33 bn".
 */

/** Divisor converting NPR thousand → NPR billion (1 bn = 1,000,000 thousand). */
const THOUSAND_PER_BILLION = 1_000_000;

/**
 * Convert a raw NPR-thousand value to NPR billion (numeric). Exposed so call
 * sites can compute bar widths / shares on the converted magnitude rather than
 * re-deriving the divisor.
 */
export function thousandToBillion(valueThousand: number): number {
  if (!Number.isFinite(valueThousand)) return 0;
  return valueThousand / THOUSAND_PER_BILLION;
}

/**
 * Format a raw NPR-thousand value as "NPR X.XX bn".
 *
 * Uses 2 decimals by default for the per-enterprise figures (the smallest
 * enterprises are well under NPR 1 bn, so 2 decimals keep them legible);
 * en-IN grouping is applied to the billions integer part for very large SOEs
 * (e.g. "NPR 1,81,330.25 thousand" is never shown — only the bn form).
 * Returns a null-safe "—" when the input is not finite.
 */
export function formatNprBillion(valueThousand: number, decimals = 2): string {
  if (!Number.isFinite(valueThousand)) return '—';
  const bn = thousandToBillion(valueThousand);
  const formatted = bn.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `NPR ${formatted} bn`;
}

/**
 * Compact NPR-billion label for tight contexts (e.g. an inline bar end label).
 * Drops the decimals for values ≥ 100 bn (where two decimals add noise) and
 * keeps one decimal otherwise. Always carries the "NPR" + "bn" unit so a figure
 * is never ambiguous.
 */
export function formatNprBillionCompact(valueThousand: number): string {
  if (!Number.isFinite(valueThousand)) return '—';
  const bn = thousandToBillion(valueThousand);
  const decimals = Math.abs(bn) >= 100 ? 0 : 1;
  return `NPR ${bn.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} bn`;
}

/**
 * Percentage share (e.g. "36.7%") for an enterprise's slice of a total.
 * Returns a null-safe "—" when the input is not finite.
 */
export function formatSharePct(pct: number): string {
  if (!Number.isFinite(pct)) return '—';
  return `${pct.toFixed(1)}%`;
}
