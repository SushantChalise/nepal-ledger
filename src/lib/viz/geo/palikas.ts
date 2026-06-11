/**
 * Palika (753 local-level) choropleth geometry loader.
 *
 * Loads the build-generated, federal_code-keyed, Mercator-projected SVG-path
 * asset (`palikas-753.geo.json`) produced by `scripts/geo/build_palika_geo.py`
 * (ADR-0025). The asset is a static, versioned reference geometry — it changes
 * only on federal restructuring — so it is imported (bundled) rather than
 * fetched.
 *
 * We validate the imported JSON once, at module load, with Zod — the sanctioned
 * DB/external-data boundary (CONTEXT_RULES §"Cast Escape Hatches" item (a)) —
 * so feature code consumes a fully-typed `PalikaGeometry` with no `as` cast.
 * Each feature carries the MoFAGA 8-digit `code` (joins to
 * `entities.slug` / `administrative_units.federal_code`), English + Nepali
 * names, district, type, and a ready-to-render SVG path `d` string in the
 * shared `viewBox`.
 */

import { z } from 'zod';

import rawGeometry from './palikas-753.geo.json';

const PalikaFeatureSchema = z.object({
  /** MoFAGA 8-digit federal code — the choropleth join key. */
  code: z.string().regex(/^\d{8}$/),
  nameEn: z.string(),
  nameNe: z.string(),
  district: z.string(),
  type: z.string(),
  /** SVG path `d` string in the shared viewBox (Mercator-projected). */
  d: z.string(),
});

const PalikaGeometrySchema = z.object({
  /** SVG viewBox shared by every feature's `d` path, e.g. "0 0 1000 578". */
  viewBox: z.string(),
  features: z.array(PalikaFeatureSchema),
});

export type PalikaFeature = z.infer<typeof PalikaFeatureSchema>;
export type PalikaGeometry = z.infer<typeof PalikaGeometrySchema>;

/**
 * The validated palika geometry. Parsed once per server process. Throws at
 * module load if the build asset is malformed — a build-time guarantee failure,
 * not a runtime user path, so a hard failure is correct (it can never ship).
 */
export const palikaGeometry: PalikaGeometry = PalikaGeometrySchema.parse(rawGeometry);

/** Count of palika features in the asset (expected 753). */
export const PALIKA_COUNT = palikaGeometry.features.length;
