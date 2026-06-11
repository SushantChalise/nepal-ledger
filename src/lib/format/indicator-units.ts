/**
 * Format a raw numeric indicator value for display.
 *
 * Unit slugs are the canonical vocabulary from the `indicator_units` enum.
 * Returns a [display, unit] pair: display is the formatted number string;
 * unit is the label to show alongside it (empty string when unit is already
 * embedded in display, e.g. "NPR 1,234.56 B").
 */
export function formatIndicatorValue(
  rawValue: string,
  unitSlug: string,
): { display: string; unit: string } {
  const num = parseFloat(rawValue);
  if (isNaN(num)) return { display: rawValue, unit: unitSlug };

  switch (unitSlug) {
    case 'NPR_billion':
    case 'npr_billion': {
      const formatted = num.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return { display: `NPR ${formatted} B`, unit: '' };
    }
    case 'percent_yoy':
    case 'percent': {
      return {
        display: num.toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
        unit: '%',
      };
    }
    case 'months_of_imports':
    case 'months': {
      return {
        display: num.toLocaleString('en-IN', {
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        }),
        unit: 'months',
      };
    }
    default: {
      return {
        display: num.toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
        unit: unitSlug,
      };
    }
  }
}
