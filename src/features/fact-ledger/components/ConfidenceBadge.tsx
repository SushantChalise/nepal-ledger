import type { ConfidenceGrade } from '@/lib/db/schema/enums';

/**
 * Confidence grade pill (A / B / C). Server Component.
 *
 * Colours mirror the Pulse KpiCard badge exactly
 * (`src/features/pulse/components/KpiCard.tsx`) so the grade reads
 * identically across lenses. Grade is conveyed by label text, not colour
 * alone (UI_ACCEPTANCE §Accessibility).
 */

const CONFIDENCE_LABEL: Record<ConfidenceGrade, string> = {
  A: 'Grade A',
  B: 'Grade B',
  C: 'Grade C',
};

const CONFIDENCE_COLOR: Record<ConfidenceGrade, string> = {
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-yellow-100 text-yellow-800',
  C: 'bg-orange-100 text-orange-800',
};

export function ConfidenceBadge({ grade }: { grade: ConfidenceGrade }) {
  return (
    <span
      aria-label={`Confidence: ${CONFIDENCE_LABEL[grade]}`}
      className={`inline-block whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium ${CONFIDENCE_COLOR[grade]}`}
    >
      {CONFIDENCE_LABEL[grade]}
    </span>
  );
}
