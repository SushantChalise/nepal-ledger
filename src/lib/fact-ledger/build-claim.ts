/**
 * Fact Ledger — pure helper that mints a `ClaimDraft` from an approved
 * indicator value + its source document.
 *
 * Determinism is the whole point: same inputs → same slug → same prose. The
 * UI just renders; it never has to invent claim text. See
 * docs/STRATEGY.md §"The Visible Fact Ledger".
 *
 * This function performs NO IO. Repositories that wrap it pass in already-
 * fetched rows; tests pass in handcrafted plain objects.
 */

import { err, ok, type Result } from '@/lib/errors';
import { format, parseReportingPeriod } from '@/lib/dates';

import type { ConfidenceGrade } from './types';
import type { ReportingPeriodType } from '@/lib/db/schema/enums';

import { validateClaimDraft } from './schemas';
import type { ClaimDraft } from './types';

export type BuildInput = {
  indicator: {
    id: string;
    slug: string;
    nameEn: string;
    nameNe: string | null;
    unit: string;
    sourceAgency: string;
  };
  value: {
    id: string;
    value: string;
    unit: string;
    reportingPeriodType: ReportingPeriodType;
    reportingPeriodBs: string;
    reportingPeriodAdStart: Date;
    reportingPeriodAdEnd: Date;
    publicationDateAd: Date;
    publicationDateBs: string;
    fiscalYearBs: string;
    confidenceGrade: ConfidenceGrade;
  };
  sourceDocument: { id: string };
  verifiedBy: string;
};

const NUMBER_FORMAT = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

const validation = (field: string, reason: string): Result<ClaimDraft> =>
  err({ kind: 'Validation', field, reason });

/**
 * Build the deterministic kebab-case slug. Indicator slug + FY + period type
 * is collision-resistant within one indicator-year-period; revisions don't
 * collide because revision 0 is the only one a claim is ever minted for
 * (revisions retire-then-replace at the claim layer, not here).
 */
function buildSlug(
  indicatorSlug: string,
  fiscalYearBs: string,
  periodType: ReportingPeriodType,
): string {
  const fyToken = fiscalYearBs.replace(/\//g, '-');
  const periodToken = periodType.replace(/_/g, '-');
  return `${indicatorSlug}-${fyToken}-${periodToken}`.toLowerCase();
}

/**
 * Human-readable reporting-period label per docs/CALENDAR_AND_PERIODS.md
 * §"Display Rules" + the Mother brief's examples:
 *   - nine_months_cumulative  → "FY 2082/83 9M (Shrawan–Chait)"
 *   - monthly                 → "Mid-{Month} {YYYY}"
 *   - annual                  → "FY 2082/83"
 *   - other (quarterly/etc.)  → parsed bsLabel, or raw input as a last resort
 *
 * We canonicalize via `parseReportingPeriod` when it can; if the input is
 * non-standard we fall back to the raw `reportingPeriodBs` rather than fail
 * (the claim is still useful with a slightly less polished label).
 */
function buildReportingPeriodLabel(
  periodType: ReportingPeriodType,
  reportingPeriodBs: string,
): string {
  const parsed = parseReportingPeriod(reportingPeriodBs);
  if (parsed.ok) {
    if (periodType === 'monthly') return `Mid-${parsed.value.bsLabel}`;
    return format.bsLabelEn(parsed.value);
  }
  if (periodType === 'monthly') return `Mid-${reportingPeriodBs}`;
  return reportingPeriodBs;
}

const isProvisionalSource = (agency: string): boolean => /preliminary|provisional/i.test(agency);

export function buildClaimDraftFromIndicatorValue(input: BuildInput): Result<ClaimDraft> {
  const { indicator, value, sourceDocument, verifiedBy } = input;

  if (verifiedBy.trim().length === 0) {
    return validation('verifiedBy', 'must be a non-empty string');
  }

  const parsedValue = Number(value.value);
  if (!Number.isFinite(parsedValue)) {
    return validation('value.value', `cannot parse "${value.value}" as a finite number`);
  }

  const reportingPeriodLabel = buildReportingPeriodLabel(
    value.reportingPeriodType,
    value.reportingPeriodBs,
  );

  const formattedValue = NUMBER_FORMAT.format(parsedValue);
  const provisionalSuffix =
    value.confidenceGrade === 'C' && isProvisionalSource(indicator.sourceAgency)
      ? ' (provisional)'
      : '';

  const textEn = `${indicator.nameEn} for ${reportingPeriodLabel}: ${formattedValue} ${indicator.unit}.${provisionalSuffix}`;

  const textNe =
    indicator.nameNe !== null
      ? `${indicator.nameNe} ${reportingPeriodLabel}: ${formattedValue} ${indicator.unit}।`
      : null;

  const draft: ClaimDraft = {
    slug: buildSlug(indicator.slug, value.fiscalYearBs, value.reportingPeriodType),
    textEn,
    textNe,
    indicatorValueId: value.id,
    indicatorId: indicator.id,
    sourceDocumentId: sourceDocument.id,
    confidenceGrade: value.confidenceGrade,
    verifiedBy,
    reportingPeriodLabel,
    publicationDateAd: value.publicationDateAd,
    publicationDateBs: value.publicationDateBs,
  };

  // Self-validate: catches shape drift before callers persist anything.
  const validated = validateClaimDraft(draft);
  if (!validated.ok) return validated;
  return ok(validated.value);
}
