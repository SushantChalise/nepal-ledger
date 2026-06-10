/**
 * Display formatters for the Fact Ledger index.
 *
 * PLAIN module — NOT `'use client'`. It is imported by the Server Component
 * page and could be imported by any client child; a `'use client'` module
 * imported by a Server Component 500s the page at render time (see the
 * money-map feature CLAUDE.md "Gotchas"). Keep this free of React imports.
 *
 * Mirrors the unit vocabulary handled inline in the Pulse page
 * (`src/app/pulse/page.tsx` `formatValue`): the canonical unit strings from
 * `indicator_units`. Unknown units fall back to the raw number + the unit
 * slug as a trailing label, so a new unit never renders blank.
 */

/** Formatted value split into the number string and a trailing unit label. */
export type FormattedValue = { display: string; unit: string };

export function formatIndicatorValue(rawValue: string, unitSlug: string): FormattedValue {
  const num = Number(rawValue);
  if (!Number.isFinite(num)) return { display: rawValue, unit: unitSlug };

  switch (unitSlug) {
    case 'NPR_billion':
    case 'npr_billion':
      return {
        display: `NPR ${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} B`,
        unit: '',
      };
    case 'percent_yoy':
    case 'percent':
      return {
        display: num.toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
        unit: '%',
      };
    case 'months_of_imports':
    case 'months':
      return {
        display: num.toLocaleString('en-IN', {
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        }),
        unit: 'months',
      };
    case 'count':
      return {
        display: num.toLocaleString('en-IN', { maximumFractionDigits: 0 }),
        unit: '',
      };
    default:
      return {
        display: num.toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
        unit: unitSlug,
      };
  }
}

/** Compact integer for the coverage strip (e.g. 531618 → "531,618"). */
export function formatRowCount(rows: number): string {
  if (!Number.isFinite(rows)) return '—';
  return Math.trunc(rows).toLocaleString('en-IN');
}

/** Human label for each indicator category present in the ledger. */
export const CATEGORY_LABELS: Record<string, string> = {
  price: 'Prices',
  monetary: 'Monetary',
  fiscal: 'Fiscal',
  external_sector: 'External Sector',
  real_sector: 'Real Sector',
  banking: 'Banking',
  capital_markets: 'Capital Markets',
  labour: 'Labour',
  tourism: 'Tourism',
  agriculture: 'Agriculture',
  energy: 'Energy',
  land: 'Land',
  demographic: 'Demographic',
  composite: 'Composite',
};

/** Short one-line description per category, shown under each group heading. */
export const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  price: 'Consumer price inflation across NCPI commodity groups and the headline rate.',
  external_sector: 'Cross-border flows — remittances, balance of payments, and reserves.',
  tourism: 'Monthly international tourist arrivals.',
};

/** Human label for each typed fact table in the coverage strip. */
export const FACT_TABLE_LABELS: Record<string, { label: string; blurb: string }> = {
  dne_facts: {
    label: 'Foreign trade (by commodity)',
    blurb: 'Dimensional import/export facts from NRB Database on Nepalese Economy.',
  },
  banking_sector_facts: {
    label: 'Banking balance sheets',
    blurb: 'Monthly BFI balance-sheet facts (NRB Banking & Financial Statistics).',
  },
  local_government_fiscal_transfers: {
    label: 'Fiscal transfers',
    blurb: 'Federal-to-local intergovernmental grants (Ministry of Finance).',
  },
  census_facts: {
    label: 'Census 2021',
    blurb: 'NPHC 2021 household & individual facts across 753 local levels.',
  },
};
