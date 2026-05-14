/**
 * Read a file from disk OR fetch from a URL. Returns the raw bytes as a
 * Buffer; the caller hashes + uploads them.
 *
 * `fetch` is retried once on network failure (TypeError) only. HTTP errors
 * (non-2xx) surface immediately — they almost always indicate a stable
 * problem (404, 403, 410) that retry can't fix and the source registry
 * needs to learn about.
 */

import { readFile } from 'node:fs/promises';

import { err, ok, type Result } from '@/lib/errors';

import type { IngestionFileSource } from './types';

const HTTP_SERVICE = 'http';

export async function downloadOrRead(input: IngestionFileSource): Promise<Result<Buffer>> {
  if ('filePath' in input) return readFromDisk(input.filePath);
  return fetchOnce(input.url);
}

async function readFromDisk(filePath: string): Promise<Result<Buffer>> {
  try {
    const buf = await readFile(filePath);
    if (buf.byteLength === 0) {
      return err({ kind: 'Validation', field: 'filePath', reason: `empty file at ${filePath}` });
    }
    return ok(buf);
  } catch (e) {
    return err({
      kind: 'External',
      service: 'filesystem',
      cause: `read ${filePath}: ${e instanceof Error ? e.message : String(e)}`,
    });
  }
}

async function fetchOnce(url: string): Promise<Result<Buffer>> {
  const first = await tryFetch(url);
  if (first.ok) return first;
  // Retry network errors once; do NOT retry HTTP non-2xx.
  if (first.error.kind === 'External' && first.error.cause.startsWith('network:')) {
    return tryFetch(url);
  }
  return first;
}

async function tryFetch(url: string): Promise<Result<Buffer>> {
  try {
    const resp = await globalThis.fetch(url);
    if (!resp.ok) {
      return err({
        kind: 'External',
        service: HTTP_SERVICE,
        cause: `http ${resp.status}: ${resp.statusText} (${url})`,
      });
    }
    const arr = await resp.arrayBuffer();
    if (arr.byteLength === 0) {
      return err({
        kind: 'External',
        service: HTTP_SERVICE,
        cause: `empty body from ${url}`,
      });
    }
    return ok(Buffer.from(arr));
  } catch (e) {
    return err({
      kind: 'External',
      service: HTTP_SERVICE,
      cause: `network: ${e instanceof Error ? e.message : String(e)} (${url})`,
    });
  }
}
