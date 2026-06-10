/**
 * Unit normalization + display formatting for the national money-flow Sankey.
 *
 * THE WHOLE POINT OF THIS FILE (ADR-0011): the three live macro flows are each
 * stored in a DIFFERENT unit. A Sankey that mixes units is meaningless, so every
 * flow is converted to ONE display unit — **NPR billion** — before the diagram
 * is built. The converters below are the single, audited place that conversion
 * happens; the query and the component both call them, never an inline divisor.
 *
 *   Source                 At-rest unit   → NPR billion        Worked example
 *   ─────────────────────  ─────────────    ──────────────     ───────────────────────────
 *   Remittance inflow      npr_million      ÷ 1,000            1,731,270 → 1,731 bn
 *   Foreign aid (grant+loan) npr_lakh       ÷ 10,000           3,600,270 → 360 bn
 *   Merchandise trade      npr_thousand     ÷ 1,000,000        1,804,122,731 → 1,804 bn
 *
 * (1 bn = 1,000 million = 10,000 lakh = 1,000,000 thousand.)
 *
 * MUST remain a plain (non-`'use client'`) module — a module exported from a
 * `'use client'` file and imported by a Server Component 500s the page at render
 * time (the money-map / growth / trade gotcha). No React here.
 */

/** 1 NPR billion = 1,000 NPR million. */
const MILLION_PER_BILLION = 1_000;
/** 1 NPR billion = 10,000 NPR lakh. */
const LAKH_PER_BILLION = 10_000;
/** 1 NPR billion = 1,000,000 NPR thousand. */
const THOUSAND_PER_BILLION = 1_000_000;
/** 1 NPR trillion = 1,000 NPR billion. */
const BILLION_PER_TRILLION = 1_000;
/** At/above this many billion, the headline label switches to trillions. */
const TRILLION_THRESHOLD_BILLION = 1_000;

// ---------------------------------------------------------------------------
// Unit normalizers — every flow goes through exactly one of these.
// ---------------------------------------------------------------------------

/** npr_million → NPR billion. Remittance (`dne-remittance-inflow`). */
export function millionToBillion(valueMillion: number): number {
  if (!Number.isFinite(valueMillion)) return 0;
  return valueMillion / MILLION_PER_BILLION;
}

/** npr_lakh → NPR billion. Foreign aid (`foreign_aid_facts`, npr_lakh edition). */
export function lakhToBillion(valueLakh: number): number {
  if (!Number.isFinite(valueLakh)) return 0;
  return valueLakh / LAKH_PER_BILLION;
}

/** npr_thousand → NPR billion. Customs merchandise trade (`dne_facts`). */
export function thousandToBillion(valueThousand: number): number {
  if (!Number.isFinite(valueThousand)) return 0;
  return valueThousand / THOUSAND_PER_BILLION;
}

// ---------------------------------------------------------------------------
// Display formatters — operate on an ALREADY-NORMALIZED NPR-billion magnitude.
// ---------------------------------------------------------------------------

/**
 * Format an NPR-billion magnitude as "NPR X.XX bn". en-IN grouping is applied to
 * the integer part. Returns "—" when not finite. Use for per-flow labels.
 */
export function formatNprBillion(valueBillion: number, decimals = 0): string {
  if (!Number.isFinite(valueBillion)) return '—';
  return `NPR ${valueBillion.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} bn`;
}

/**
 * Magnitude-aware NPR label for headline totals: flows run to NPR ~1.8 trillion,
 * where a bare "NPR 1,804 bn" reads poorly. Values ≥ 1,000 bn render as
 * "NPR X.XX tn"; everything else falls back to `formatNprBillion`. Always carries
 * "NPR" + unit so a figure is never ambiguous. Returns "—" when not finite.
 */
export function formatNprMagnitude(valueBillion: number): string {
  if (!Number.isFinite(valueBillion)) return '—';
  if (Math.abs(valueBillion) >= TRILLION_THRESHOLD_BILLION) {
    const tn = valueBillion / BILLION_PER_TRILLION;
    return `NPR ${tn.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} tn`;
  }
  return formatNprBillion(valueBillion);
}

/**
 * Percentage share (e.g. "73.1%") of a value within a total. Returns "—" when
 * the input is not finite.
 */
export function formatSharePct(pct: number): string {
  if (!Number.isFinite(pct)) return '—';
  return `${pct.toFixed(1)}%`;
}
