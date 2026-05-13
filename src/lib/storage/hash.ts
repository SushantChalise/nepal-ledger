/**
 * SHA-256 helpers.
 *
 * Source documents are content-addressed: the same NRB CMEFs PDF
 * re-downloaded next month produces the same hash, which keeps the archive
 * idempotent and lets the Fact Ledger prove that a citation has not been
 * tampered with since archival.
 */

import { createHash } from 'node:crypto';

/**
 * Return the lowercase hex SHA-256 digest of the given bytes.
 */
export function sha256OfBuffer(buf: Buffer | Uint8Array): string {
  return createHash('sha256').update(buf).digest('hex');
}
