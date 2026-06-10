/**
 * Display formatters for the /trade (customs foreign-trade) view.
 *
 * Shared by the Server page and the server table components. MUST remain a plain
 * (non-`'use client'`) module — a module exported from a `'use client'` file and
 * imported by a Server Component 500s the page at render time (the
 * money-map / tourism-rupee gotcha documented across the other features). No
 * React here.
 *
 * UNIT CONTRACT (ADR-0011): the underlying values are NPR THOUSAND
 * (`unit = 'npr_thousand'`; every customs FTS value sheet states "(figures are
 * in Rs. Thousands)"). Raw thousands are NEVER shown. We convert to:
 *
 *     NPR billion  = value_thousand / 1_000_000   (1 bn = 1,000,000 thousand)
 *     NPR trillion = value_thousand / 1_000_000_000
 *
 * Worked examples (FY 2081/82 annual, verified against the live DB):
 *   - total imports 1,804,122,731 thousand → 1,804.12 bn → "NPR 1.80 tn"
 *   - total exports   277,030,202 thousand →   277.03 bn → "NPR 277.03 bn"
 *   - Diesel (top import commodity) 128,761,649 thousand → "NPR 128.76 bn"
 */

/** Divisor converting NPR thousand → NPR billion (1 bn = 1,000,000 thousand). */
const THOUSAND_PER_BILLION = 1_000_000;
/** Divisor converting NPR thousand → NPR trillion (1 tn = 1,000,000,000 thousand). */
const THOUSAND_PER_TRILLION = 1_000_000_000;
/** At/above this many billion we switch the headline label to trillions. */
const TRILLION_THRESHOLD_BILLION = 1_000;

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
 * Format a raw NPR-thousand value as "NPR X.XX bn". Two decimals keep the
 * per-commodity figures (some well under NPR 1 bn) legible; en-IN grouping is
 * applied to the billions integer part. Returns "—" when not finite.
 */
export function formatNprBillion(valueThousand: number, decimals = 2): string {
  if (!Number.isFinite(valueThousand)) return '—';
  const bn = thousandToBillion(valueThousand);
  return `NPR ${bn.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} bn`;
}

/**
 * Magnitude-aware NPR label for headline totals: trade totals run to NPR ~1.8
 * trillion, where a bare "NPR 1,804.12 bn" reads poorly. Values ≥ 1,000 bn are
 * shown as "NPR X.XX tn"; everything else falls back to `formatNprBillion`.
 * Always carries the "NPR" + unit so a figure is never ambiguous. Returns "—"
 * when not finite.
 */
export function formatNprMagnitude(valueThousand: number): string {
  if (!Number.isFinite(valueThousand)) return '—';
  const bn = thousandToBillion(valueThousand);
  if (Math.abs(bn) >= TRILLION_THRESHOLD_BILLION) {
    const tn = valueThousand / THOUSAND_PER_TRILLION;
    return `NPR ${tn.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} tn`;
  }
  return formatNprBillion(valueThousand);
}

/**
 * Percentage share (e.g. "59.4%") of a value within a total. Returns "—" when
 * the input is not finite.
 */
export function formatSharePct(pct: number): string {
  if (!Number.isFinite(pct)) return '—';
  return `${pct.toFixed(1)}%`;
}

/**
 * Coverage ratio (exports ÷ imports) as a percentage, e.g. "15.4%". This is how
 * much of the import bill exports cover — the standard trade-coverage measure.
 * Returns "—" when not finite.
 */
export function formatCoverageRatio(exportsThousand: number, importsThousand: number): string {
  if (
    !Number.isFinite(exportsThousand) ||
    !Number.isFinite(importsThousand) ||
    importsThousand <= 0
  )
    return '—';
  return `${((exportsThousand / importsThousand) * 100).toFixed(1)}%`;
}

/**
 * Import-to-export multiple (imports ÷ exports), e.g. "6.5×" — the headline
 * framing of the structural deficit (imports are 6.5 times exports). Returns
 * "—" when not finite.
 */
export function formatImportMultiple(importsThousand: number, exportsThousand: number): string {
  if (
    !Number.isFinite(importsThousand) ||
    !Number.isFinite(exportsThousand) ||
    exportsThousand <= 0
  )
    return '—';
  return `${(importsThousand / exportsThousand).toFixed(1)}×`;
}
