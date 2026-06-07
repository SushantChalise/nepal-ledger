/**
 * Launch-district registry for the District MRI dashboard.
 *
 * Year-1 scope is 5 districts (STRATEGY.md §"District MRI"). Each entry binds a
 * URL slug to the EXACT `entities.metadata->>'district_en'` string used to roll
 * palika-grain rows up to the district.
 *
 * LOAD-BEARING INVARIANT (verified against the live DB):
 *   `districtEn` MUST equal `entities.metadata->>'district_en'` byte-for-byte.
 *   The 8-digit `federal_code` does NOT encode district (see
 *   scrapers/cbs_nphc/generate_crosswalk.py), and there are NO `kind='district'`
 *   entities. The ONLY join key from palika → district is this name string.
 *   The canonical spelling is the MoF table spelling carried on every
 *   `kind='local_level'` entity (e.g. "Chitwan", not the CBS "Chitawan").
 *
 * Palika counts in the comment are the live counts confirmed by a DB probe and
 * are documentation only — never used as a denominator.
 */

export type LaunchDistrict = {
  /** URL segment for /districts/[district]. kebab-case, stable. */
  slug: string;
  /** EXACT entities.metadata->>'district_en' value. The join key. */
  districtEn: string;
  /** Human-readable display name (currently identical to districtEn). */
  nameEn: string;
  /** Province name for context (not a query key). */
  province: string;
};

/** The 5 Year-1 launch districts. `districtEn` verified against live entities. */
export const LAUNCH_DISTRICTS: readonly LaunchDistrict[] = [
  { slug: 'kathmandu', districtEn: 'Kathmandu', nameEn: 'Kathmandu', province: 'Bagmati' }, // 11 palikas
  { slug: 'chitwan', districtEn: 'Chitwan', nameEn: 'Chitwan', province: 'Bagmati' }, // 7 palikas
  { slug: 'kaski', districtEn: 'Kaski', nameEn: 'Kaski', province: 'Gandaki' }, // 5 palikas
  { slug: 'jhapa', districtEn: 'Jhapa', nameEn: 'Jhapa', province: 'Koshi' }, // 15 palikas
  { slug: 'morang', districtEn: 'Morang', nameEn: 'Morang', province: 'Koshi' }, // 17 palikas
] as const;

/** Resolve a URL slug to its launch-district entry, or undefined if unknown. */
export function findLaunchDistrictBySlug(slug: string): LaunchDistrict | undefined {
  return LAUNCH_DISTRICTS.find((d) => d.slug === slug);
}
