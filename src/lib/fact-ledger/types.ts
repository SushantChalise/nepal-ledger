/**
 * Fact Ledger — derived TypeScript types.
 *
 * Single source of truth lives in `schemas.ts`. Types here are `z.infer`-derived
 * so a schema edit propagates to every consumer without manual sync.
 */

import type { z } from 'zod';

import type { ClaimDraftSchema, ConfidenceGradeSchema } from './schemas';

export type ConfidenceGrade = z.infer<typeof ConfidenceGradeSchema>;
export type ClaimDraft = z.infer<typeof ClaimDraftSchema>;
