/**
 * Schema barrel. Imported by Drizzle Kit (`drizzle.config.ts`) and by
 * `src/lib/db/client.ts`. Every new table file must re-export from here.
 */

export * from './enums';
export * from './source-registry';
export * from './source-documents';
export * from './parser-runs';
export * from './indicators';
export * from './indicator-values';
export * from './fact-ledger';
export * from './leads';
// Added in migration 0002
export * from './entities';
export * from './administrative-units';
export * from './fiscal-transfers';
export * from './census-facts';
export * from './banking-sector-facts';
export * from './ocr-tracking';
