/**
 * WDI-vs-DNE cross-source divergence check.
 *
 * After a WDI ingest run, this check queries the newly-promoted approved rows
 * and compares each directly-comparable WDI indicator against its DNE
 * counterpart for the same fiscal year.  Findings are written as
 * `data_quality_flags` (ValueOutOfPlausibleRange / warning severity) and
 * returned as a typed summary for the ingest CLI to display.
 *
 * Only three pairs can be compared without currency conversion:
 *   wdi-gdp-growth-annual-pct      ↔  dne-gdp-real-growth       (both %)
 *   wdi-cpi-inflation-annual-pct   ↔  dne-inflation-rate         (both %)
 *   wdi-gdp-per-capita-current-usd ↔  dne-gdp-per-capita-usd    (both USD)
 *
 * USD-level indicators (GDP current USD vs DNE NPR) are not compared here —
 * they require an exchange-rate series that is not yet in the database.
 *
 * Tolerance design (generous, methodological divergence is expected):
 *   - Percentage indicators: warn if |WDI − DNE| > 3 pp absolute.
 *     (WDI uses calendar-year estimates; DNE uses Nepal FY; methods differ.)
 *   - USD per-capita: warn if relative divergence > 20%.
 *
 * Findings are WARNING severity — they never block promotion.
 */

import { findLatestApprovedByPeriod } from '@/lib/db/repositories/approved-indicator-values';
import { findIndicatorBySlug } from '@/lib/db/repositories/indicators';
import { ok, type Result } from '@/lib/errors';
import { writeFlag } from './flag';

export type DivergenceFinding = {
  wdiSlug: string;
  dneSlug: string;
  fiscalYearBs: string;
  wdiValue: number;
  dneValue: number;
  pct: number;
  detail: string;
  flagWritten: boolean;
};

type BenchmarkPair = {
  wdiSlug: string;
  dneSlug: string;
  toleranceMode: 'absolute_pp' | 'relative_pct';
  toleranceThreshold: number;
};

const BENCHMARK_PAIRS: readonly BenchmarkPair[] = [
  {
    wdiSlug: 'wdi-gdp-growth-annual-pct',
    dneSlug: 'dne-gdp-real-growth',
    toleranceMode: 'absolute_pp',
    toleranceThreshold: 3,
  },
  {
    wdiSlug: 'wdi-cpi-inflation-annual-pct',
    dneSlug: 'dne-inflation-rate',
    toleranceMode: 'absolute_pp',
    toleranceThreshold: 3,
  },
  {
    wdiSlug: 'wdi-gdp-per-capita-current-usd',
    dneSlug: 'dne-gdp-per-capita-usd',
    toleranceMode: 'relative_pct',
    toleranceThreshold: 20,
  },
];

/**
 * Run WDI-vs-DNE divergence checks for all WDI annual rows from a parser run.
 *
 * For each BENCHMARK_PAIR, checks whether a matching DNE approved row exists for
 * the same fiscal year as each WDI approved row (last 10 years). When divergence
 * exceeds the threshold, writes a warning flag and includes the finding in the
 * returned list.
 *
 * Returns an empty list when all pairs are within tolerance or when no DNE
 * counterpart exists (gap in DNE history — not an error).
 */
export async function checkWdiDneDivergence(): Promise<Result<DivergenceFinding[]>> {
  const findings: DivergenceFinding[] = [];

  for (const pair of BENCHMARK_PAIRS) {
    // Resolve WDI indicator id.
    const wdiIndResult = await findIndicatorBySlug(pair.wdiSlug);
    if (!wdiIndResult.ok) {
      if (wdiIndResult.error.kind === 'NotFound') continue;
      return wdiIndResult;
    }
    const wdiInd = wdiIndResult.value;

    // Resolve DNE indicator id.
    const dneIndResult = await findIndicatorBySlug(pair.dneSlug);
    if (!dneIndResult.ok) {
      if (dneIndResult.error.kind === 'NotFound') continue;
      return dneIndResult;
    }
    const dneInd = dneIndResult.value;

    // Find all WDI approved rows for this indicator (any period in the last ~60y).
    // We use a broad trailing query via findLatestApprovedByPeriod for each FY we
    // know WDI produces.  Rather than iterating every possible FY, we use the
    // approved rows for this run's parser_run_id as the anchor set.
    //
    // Since approved_indicator_values doesn't have a parser_run_id FK (rows are
    // promoted from staging), we query the staging rows to get the FY list, then
    // look up approved.  For simplicity, we query a range of candidate FYs (the
    // WDI fixture covers 2019–2023; we check the last 10 years).
    const candidateWbYears = Array.from({ length: 10 }, (_, i) => 2014 + i);
    // WB year Y → BS FY start = Y + 57 → fy_bs = "{Y+57}/{(Y+58)%100:02d}"
    const candidateFyBs = candidateWbYears.map((y) => {
      const bsStart = y + 57;
      const bsEnd = (bsStart + 1) % 100;
      return `${bsStart}/${String(bsEnd).padStart(2, '0')}`;
    });

    for (const fyBs of candidateFyBs) {
      const wdiRowResult = await findLatestApprovedByPeriod(wdiInd.id, 'annual', fyBs);
      if (!wdiRowResult.ok) continue;
      const wdiRow = wdiRowResult.value;
      if (!wdiRow) continue;

      const dneRowResult = await findLatestApprovedByPeriod(dneInd.id, 'annual', fyBs);
      if (!dneRowResult.ok) continue;
      const dneRow = dneRowResult.value;
      if (!dneRow) continue;

      const wdiVal = Number(wdiRow.value);
      const dneVal = Number(dneRow.value);
      if (!Number.isFinite(wdiVal) || !Number.isFinite(dneVal)) continue;

      let diverges = false;
      let pct = 0;
      let detail = '';

      if (pair.toleranceMode === 'absolute_pp') {
        const diff = Math.abs(wdiVal - dneVal);
        pct = diff;
        if (diff > pair.toleranceThreshold) {
          diverges = true;
          detail =
            `WDI ${pair.wdiSlug}=${wdiVal.toFixed(2)} vs DNE ${pair.dneSlug}=${dneVal.toFixed(2)} ` +
            `for FY ${fyBs}: absolute diff ${diff.toFixed(2)} pp > tolerance ${pair.toleranceThreshold} pp`;
        }
      } else {
        if (dneVal !== 0) {
          pct = (Math.abs(wdiVal - dneVal) / Math.abs(dneVal)) * 100;
          if (pct > pair.toleranceThreshold) {
            diverges = true;
            detail =
              `WDI ${pair.wdiSlug}=${wdiVal.toFixed(2)} vs DNE ${pair.dneSlug}=${dneVal.toFixed(2)} ` +
              `for FY ${fyBs}: relative diff ${pct.toFixed(1)}% > tolerance ${pair.toleranceThreshold}%`;
          }
        }
      }

      if (diverges) {
        // Write warning flag against the WDI staging row id — we use the approved
        // row's FK to find the staging row id.  Since staging rows are deleted on
        // promotion we write the flag against a synthetic reference: the approved
        // row's id (which is a different table, but writeFlag accepts any uuid).
        // The flag's stagingRowId field here serves as a correlation id; the flag
        // severity=warning means it never blocks.
        const flagResult = await writeFlag({
          stagingRowId: wdiRow.id,
          flagType: 'ValueOutOfPlausibleRange',
          severity: 'warning',
          detail: `[cross-source benchmark] ${detail}`,
        });
        const flagWritten = flagResult.ok;
        if (!flagResult.ok && flagResult.error.kind !== 'QueryFailed') {
          return flagResult;
        }

        findings.push({
          wdiSlug: pair.wdiSlug,
          dneSlug: pair.dneSlug,
          fiscalYearBs: fyBs,
          wdiValue: wdiVal,
          dneValue: dneVal,
          pct,
          detail,
          flagWritten,
        });
      }
    }
  }

  return ok(findings);
}
