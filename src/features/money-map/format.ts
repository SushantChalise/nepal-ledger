/**
 * NPR fiscal-amount display formatter, shared by the Money Map server page
 * and the client Sankey component.
 *
 * Values in the fiscal-transfer table are stored in NPR crore
 * (1 crore = 10 million NPR = 1,00,00,000). The formatter uses Nepali
 * financial convention:
 *   ≥ 100 crore  → "NPR X.XX arab"  (1 arab = 100 crore = 1 billion)
 *   ≥ 1 crore    → "NPR X.XX crore"
 *   < 1 crore    → "NPR X.XX lakh"  (1 lakh = 0.01 crore = 100,000)
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
