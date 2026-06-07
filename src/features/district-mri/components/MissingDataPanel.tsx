import type { MissingPillarField } from '../server/queries';

/**
 * Honest disclosure of Pillar fields that are part of the District MRI vision
 * but have NO ingested source yet. We list them explicitly rather than
 * zero-filling or fabricating placeholder numbers (Data Continuity Protocol;
 * UI_ACCEPTANCE.md §"Never fabricate").
 *
 * Server Component.
 */
export function MissingDataPanel({ fields }: { fields: readonly MissingPillarField[] }) {
  if (fields.length === 0) return null;

  return (
    <section
      aria-labelledby="district-missing-heading"
      className="rounded-lg border border-amber-200 bg-amber-50 p-5 dark:border-amber-900 dark:bg-amber-950"
    >
      <h2
        id="district-missing-heading"
        className="text-sm font-semibold text-amber-800 dark:text-amber-200"
      >
        Not yet measured
      </h2>
      <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
        These indicators belong in the district picture but have no ingested data source yet. We
        show what is missing rather than guessing.
      </p>
      <ul className="mt-3 space-y-2">
        {fields.map((field) => (
          <li key={field.label} className="text-xs text-amber-800 dark:text-amber-200">
            <span className="font-medium">{field.label}</span>
            <span className="ml-1.5 rounded bg-amber-100 px-1.5 py-0.5 text-[0.65rem] font-medium text-amber-700 dark:bg-amber-900 dark:text-amber-300">
              {field.pillar}
            </span>
            <span className="mt-0.5 block text-amber-700 dark:text-amber-400">{field.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
