/**
 * Fact Ledger — Zod schemas for the typed claim contract.
 *
 * `ClaimDraft` is the deterministic projection of an approved indicator value
 * + its source document into a citable prose claim. The schema lives here so
 * (a) the build helper can validate its own output before returning it, and
 * (b) downstream callers (future UI, future server actions) can validate
 * round-tripped payloads at trust boundaries.
 *
 * See docs/STRATEGY.md §"The Visible Fact Ledger".
 */

import { z } from 'zod';

import { err, ok, type Result } from '@/lib/errors';

export const ConfidenceGradeSchema = z.enum(['A', 'B', 'C']);

export const ClaimDraftSchema = z.object({
  slug: z.string().min(1),
  textEn: z.string().min(1),
  textNe: z.string().min(1).nullable(),
  indicatorValueId: z.string().uuid(),
  indicatorId: z.string().uuid(),
  sourceDocumentId: z.string().uuid(),
  confidenceGrade: ConfidenceGradeSchema,
  verifiedBy: z.string().min(1),
  reportingPeriodLabel: z.string().min(1),
  publicationDateAd: z.date(),
  publicationDateBs: z.string().min(1),
});

export function validateClaimDraft(input: unknown): Result<z.infer<typeof ClaimDraftSchema>> {
  const parsed = ClaimDraftSchema.safeParse(input);
  if (parsed.success) return ok(parsed.data);
  const first = parsed.error.issues[0];
  const field = first ? first.path.join('.') || 'root' : 'root';
  const reason = first ? first.message : 'invalid ClaimDraft';
  return err({ kind: 'Validation', field, reason });
}
