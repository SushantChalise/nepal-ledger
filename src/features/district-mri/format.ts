/**
 * Display formatters for the District MRI dashboard.
 *
 * INVARIANT: this MUST remain a plain (non-`'use client'`) module with no React
 * imports. It is imported by Server Components (the page) and could be imported
 * by future client components. A module exported from a `'use client'` file that
 * is then imported by a Server Component 500s the page at render time — this bit
 * the Money Map feature (see src/features/money-map/CLAUDE.md §"Gotchas").
 *
 * Fiscal amounts in `local_government_fiscal_transfers` are stored in NPR crore
 * (1 crore = 10 million NPR), verified for the launch districts. The formatter
 * mirrors the Nepali financial convention used by Money Map's `formatNprCrore`.
 */

/**
 * Format an NPR-crore amount using Nepali financial convention:
 *   ≥ 100 crore → "NPR X.XX arab"  (1 arab = 100 crore = 1 billion)
 *   ≥ 1 crore   → "NPR X.XX crore"
 *   < 1 crore   → "NPR X lakh"      (1 lakh = 0.01 crore = 100,000)
 */
export function formatNprCrore(nprCrore: number): string {
  if (!isFinite(nprCrore)) return 'NPR —';
  const abs = Math.abs(nprCrore);
  const sign = nprCrore < 0 ? '-' : '';
  if (abs >= 100) {
    const arab = abs / 100;
    return `${sign}NPR ${arab.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} arab`;
  }
  if (abs >= 1) {
    return `${sign}NPR ${abs.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} crore`;
  }
  const lakh = abs * 100;
  return `${sign}NPR ${lakh.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} lakh`;
}

/** Format a ratio in [0,1] as a percentage with one decimal, e.g. 0.776 → "77.6%". */
export function formatPercent(ratio: number): string {
  if (!isFinite(ratio)) return '—';
  return `${(ratio * 100).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

/** Format an integer household/person count with Indian-grouping separators. */
export function formatCount(n: number): string {
  if (!isFinite(n)) return '—';
  return Math.round(n).toLocaleString('en-IN');
}
