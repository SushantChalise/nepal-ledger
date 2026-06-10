/**
 * Fact Ledger view-model builder.
 *
 * Composes the typed repository reads (`listFactLedgerEntries`,
 * `getFactTableCounts`) into a grouped, summary-annotated shape the Server
 * page renders directly. No raw DB access here — features read through
 * `@/lib/db/repositories` (docs/CONVENTIONS.md §"Repository pattern"); the
 * SQL + Zod-at-boundary lives in the repo, this module only reshapes typed
 * data into the presentation model.
 *
 * SCOPE: only the fact-ledger feature.
 */

import {
  getFactTableCounts,
  listFactLedgerEntries,
  type FactLedgerEntry,
  type FactTableCount,
} from '@/lib/db/repositories';
import type { ConfidenceGrade } from '@/lib/db/schema/enums';
import { ok, type Result } from '@/lib/errors';

/** One category section: a heading + its rows (already category-sorted). */
export type LedgerCategoryGroup = {
  category: string;
  entries: FactLedgerEntry[];
};

/** Count of rows at each confidence grade, for the summary header. */
export type ConfidenceBreakdown = Record<ConfidenceGrade, number>;

export type FactLedgerView = {
  /** Category groups in DB order (category asc, slug asc within). */
  groups: LedgerCategoryGroup[];
  /** Total approved indicator-value rows. */
  totalEntries: number;
  /** Distinct indicator count (a slug may have multiple periods/revisions). */
  indicatorCount: number;
  /** Distinct source feeds (source_registry rows) backing the ledger. */
  sourceCount: number;
  /** Rows per category, ordered like `groups`. */
  categoryCounts: { category: string; count: number }[];
  /** Rows per confidence grade. */
  confidence: ConfidenceBreakdown;
  /** Roll-up counts of the typed dimensional fact tables (coverage strip). */
  factTableCounts: FactTableCount[];
};

/**
 * Build the full Fact Ledger view model. Returns a typed error if either
 * underlying read fails; the coverage strip is best-effort — if only the
 * fact-table counts fail we still render the indicator ledger (the counts
 * become an empty array, and the page hides the strip).
 */
export async function getFactLedgerView(): Promise<Result<FactLedgerView>> {
  const entriesResult = await listFactLedgerEntries();
  if (!entriesResult.ok) return entriesResult;
  const entries = entriesResult.value;

  // Coverage strip is non-critical: degrade to [] rather than failing the page.
  const countsResult = await getFactTableCounts();
  const factTableCounts = countsResult.ok ? countsResult.value : [];

  // Group by category preserving the DB sort order (entries arrive sorted by
  // category then slug, so first-seen order is the display order).
  const groupMap = new Map<string, FactLedgerEntry[]>();
  const confidence: ConfidenceBreakdown = { A: 0, B: 0, C: 0 };
  const indicatorSlugs = new Set<string>();
  const sourceIds = new Set<string>();

  for (const entry of entries) {
    const bucket = groupMap.get(entry.category);
    if (bucket) {
      bucket.push(entry);
    } else {
      groupMap.set(entry.category, [entry]);
    }
    confidence[entry.confidence] += 1;
    indicatorSlugs.add(entry.indicatorSlug);
    sourceIds.add(entry.sourceId);
  }

  const groups: LedgerCategoryGroup[] = [];
  const categoryCounts: { category: string; count: number }[] = [];
  for (const [category, groupEntries] of groupMap) {
    groups.push({ category, entries: groupEntries });
    categoryCounts.push({ category, count: groupEntries.length });
  }

  return ok({
    groups,
    totalEntries: entries.length,
    indicatorCount: indicatorSlugs.size,
    sourceCount: sourceIds.size,
    categoryCounts,
    confidence,
    factTableCounts,
  });
}
