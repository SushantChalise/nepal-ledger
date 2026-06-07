/**
 * Display formatters for the Growth (headline macro) view.
 *
 * Shared by the Server page and the `'use client'` GdpTrajectoryChart. MUST
 * remain a plain (non-`'use client'`) module — a module exported from a
 * `'use client'` file and imported by a Server Component 500s the page at
 * render time (the money-map / tourism-rupee gotcha). No React here.
 *
 * UNIT CONTRACT (ADR-0011 — read the indicator's unit, don't fuzzy-match).
 * The six series carry four distinct units; each has ONE honest display form:
 *
 *   - npr_billion (nominal & real GDP) → "NPR X.XX trillion" (value / 1000)
 *       1 trillion NPR = 1,000 billion NPR. Worked example: nominal GDP
 *       6,107 npr_billion / 1000 = 6.107 → "NPR 6.11 trillion". Values under
 *       1,000 billion fall back to "NPR X billion" so a small early-year figure
 *       is never mislabelled as trillions.
 *   - usd (per-capita GDP) → "USD X,XXX" (e.g. 1,496 → "USD 1,496"). This is a
 *       PER-PERSON dollar figure, never NPR — it is the "wealth per person"
 *       denominator central to the mission, so it is always dollar-labelled.
 *   - percent (real-GDP growth, CPI inflation) → "X.XX%".
 *   - index_points (CPI) → a bare index level (e.g. "166.2"), explicitly an
 *       index (base year ≈ 2014/15 = 100), NOT a currency amount.
 *
 * A bare number is never returned without its unit at any call site.
 */

/** Billions of NPR per trillion of NPR (1 tn = 1,000 bn). */
const BILLION_PER_TRILLION = 1_000;

/**
 * Convert an NPR-billion value to NPR trillion (numeric). Exposed so the chart
 * can compute axis ticks on the converted (trillion) magnitude rather than
 * re-deriving the divisor.
 */
export function billionToTrillion(valueBillion: number): number {
  if (!Number.isFinite(valueBillion)) return 0;
  return valueBillion / BILLION_PER_TRILLION;
}

/**
 * Format an NPR-billion value honestly. Values ≥ 1,000 bn render as trillions
 * ("NPR 6.11 trillion"); smaller values render as billions ("NPR 812 billion"),
 * so an early-year GDP is never inflated into a misleading "0.81 trillion".
 * Returns a null-safe "—" when the input is not finite.
 */
export function formatNprFromBillion(valueBillion: number, trillionDecimals = 2): string {
  if (!Number.isFinite(valueBillion)) return '—';
  const abs = Math.abs(valueBillion);
  if (abs >= BILLION_PER_TRILLION) {
    const tn = billionToTrillion(valueBillion);
    return `NPR ${tn.toLocaleString('en-IN', {
      minimumFractionDigits: trillionDecimals,
      maximumFractionDigits: trillionDecimals,
    })} trillion`;
  }
  // Sub-trillion: whole billions read cleanly (e.g. "NPR 812 billion").
  return `NPR ${valueBillion.toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })} billion`;
}

/**
 * Compact NPR label for tight contexts (axis ticks, the chart's latest-point
 * label). Always uses the trillion form with one decimal ("NPR 6.1T") because
 * the GDP trajectory spans into the trillions; carries the unit so no figure
 * is ambiguous.
 */
export function formatNprTrillionCompact(valueBillion: number): string {
  if (!Number.isFinite(valueBillion)) return '—';
  const tn = billionToTrillion(valueBillion);
  return `NPR ${tn.toLocaleString('en-IN', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}T`;
}

/**
 * Per-capita USD figure (e.g. "USD 1,496"). en-IN grouping matches the rest of
 * the app. Always dollar-labelled — this is the per-person wealth denominator,
 * never an NPR amount. Returns "—" when not finite.
 */
export function formatUsd(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return `USD ${Math.round(value).toLocaleString('en-IN')}`;
}

/**
 * Percentage for growth / inflation (e.g. "4.61%"). Unsigned by default —
 * these are levels (a growth *rate*, an inflation *rate*), not deltas, so a
 * leading "+" would be misleading. Returns "—" when not finite.
 */
export function formatPercent(value: number, decimals = 2): string {
  if (!Number.isFinite(value)) return '—';
  return `${value.toFixed(decimals)}%`;
}

/**
 * CPI index level (e.g. "166.2"). Explicitly an index reading, NOT currency;
 * the page labels the base year alongside. Returns "—" when not finite.
 */
export function formatIndex(value: number, decimals = 1): string {
  if (!Number.isFinite(value)) return '—';
  return value.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Fiscal-year label passthrough for axis ticks and prose. The DB already
 * stores the canonical BS form ("2081/82"); we prefix "FY" for clarity in
 * compact contexts. Returns "—" for an empty label.
 */
export function formatFiscalYear(fiscalYearBs: string): string {
  if (!fiscalYearBs) return '—';
  return `FY ${fiscalYearBs}`;
}
