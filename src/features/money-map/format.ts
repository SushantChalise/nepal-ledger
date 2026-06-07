/**
 * NPR-thousand display formatter, shared by the Money Map server page and the
 * client Sankey component. Lives in its own (non-'use client') module so the
 * Server Component page can call it directly — a function exported from a
 * 'use client' module cannot be invoked from the server.
 *
 * Values are stored in NPR_thousand. At ≥ 1 crore (10,000 K) we switch to
 * "NPR X.XX Cr" for readability; below that, "NPR X,XXX K".
 */
export function formatNprThousand(nprThousand: number): string {
  if (!isFinite(nprThousand)) return 'NPR —';
  const inCrore = nprThousand / 10_000;
  if (inCrore >= 1) {
    return `NPR ${inCrore.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr`;
  }
  return `NPR ${nprThousand.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} K`;
}
