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
// Added in migration 0004 (ADR-0015)
export * from './dne-facts';
// Added in migration 0005 (ADR-0017)
export * from './foreign-aid-facts';
// Added in migration 0006 (ADR-0024)
export * from './audit-facts';
// Added in migration 0007 (ADR-0026)
export * from './migration-permit-facts';
