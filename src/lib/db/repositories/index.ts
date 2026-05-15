/**
 * Repository barrel. Feature code imports from `@/lib/db/repositories`,
 * never reaches into individual modules and never imports `@/lib/db/client`.
 */

export * from './source-registry';
export * from './source-documents';
export * from './indicators';
export * from './parser-runs';
export * from './staging-indicator-values';
export * from './approved-indicator-values';
export * from './data-quality-flags';
export * from './banking-sector-facts';
export * from './local-government-fiscal-transfers';
export * as censusFactsRepo from './census-facts';
