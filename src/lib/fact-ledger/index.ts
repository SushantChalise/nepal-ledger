/**
 * Public surface for `src/lib/fact-ledger`. Import from here, not from the
 * individual module files.
 */

export { buildClaimDraftFromIndicatorValue, type BuildInput } from './build-claim';
export { ClaimDraftSchema, ConfidenceGradeSchema, validateClaimDraft } from './schemas';
export type { ClaimDraft, ConfidenceGrade } from './types';
