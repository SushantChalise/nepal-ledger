/**
 * Vitest suite for the Supabase Storage wrapper.
 *
 * The Supabase JS client is mocked via a hand-rolled stub passed in as the
 * `clientOverride` argument the wrapper accepts for testability. No network,
 * no real bucket. The only env vars these tests touch are SUPABASE_URL /
 * SUPABASE_SERVICE_ROLE_KEY / SUPABASE_STORAGE_BUCKET, stubbed below.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// `server-only` is a React marker module that throws at runtime in a
// non-RSC environment (Vitest is plain Node). Stub it out so the wrapper's
// own server-only assertion does not abort the suite.
vi.mock('server-only', () => ({}));

import {
  downloadSourceDocument,
  getPublicUrl,
  getSignedUrl,
  sha256OfBuffer,
  uploadSourceDocument,
} from './index';
import { sanitizeFileName } from './upload';
import type {
  DownloadResp,
  SignedUrlResp,
  StorageClientLike,
  StorageFileApiLike,
  UploadResp,
} from './types';

// Hand-rolled stub matching the narrowed StorageClientLike contract.
// Each test wires up exactly the methods it exercises; the rest throw so
// that an unexpected SDK call surfaces immediately instead of silently
// returning undefined.

function makeClient(parts: {
  download?: () => Promise<DownloadResp>;
  upload?: () => Promise<UploadResp>;
  createSignedUrl?: () => Promise<SignedUrlResp>;
}): StorageClientLike {
  const api: StorageFileApiLike = {
    download: vi.fn(parts.download ?? (() => Promise.reject(new Error('download not stubbed')))),
    upload: vi.fn(parts.upload ?? (() => Promise.reject(new Error('upload not stubbed')))),
    createSignedUrl: vi.fn(
      parts.createSignedUrl ?? (() => Promise.reject(new Error('createSignedUrl not stubbed'))),
    ),
  };
  return { storage: { from: () => api } };
}

const VALID_INPUT_BASE = {
  sourceId: 'nrb-cmefs',
  downloadedAtIso: '2026-05-13T10:00:00.000Z',
  fileName: 'cmefs-nine-months.pdf',
  contentType: 'application/pdf',
};

beforeEach(() => {
  vi.stubEnv('SUPABASE_URL', 'https://example.supabase.co');
  vi.stubEnv('SUPABASE_ANON_KEY', 'anon-test-key');
  vi.stubEnv('SUPABASE_SERVICE_ROLE_KEY', 'service-test-key');
  vi.stubEnv('DATABASE_URL', 'postgres://test:test@localhost:5432/test');
  vi.stubEnv('SUPABASE_STORAGE_BUCKET', 'source-archive');
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('sha256OfBuffer', () => {
  it('returns the lowercase hex SHA-256 of a known fixture', () => {
    // Standard fixture: sha256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
    const out = sha256OfBuffer(Buffer.from('hello'));
    expect(out).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
  });

  it('is deterministic across runs', () => {
    const a = sha256OfBuffer(Buffer.from([1, 2, 3, 4, 5]));
    const b = sha256OfBuffer(Buffer.from([1, 2, 3, 4, 5]));
    expect(a).toBe(b);
  });
});

describe('sanitizeFileName', () => {
  it('replaces spaces and unicode with underscores', () => {
    expect(sanitizeFileName('My Report Q1 2026.pdf')).toBe('My_Report_Q1_2026.pdf');
    expect(sanitizeFileName('रिपोर्ट.pdf')).toBe('_______.pdf');
  });

  it('preserves safe characters', () => {
    expect(sanitizeFileName('file-name_1.0.csv')).toBe('file-name_1.0.csv');
  });
});

describe('uploadSourceDocument', () => {
  const body = Buffer.from('pdf-bytes');
  const bodyHash = sha256OfBuffer(body);

  it('happy path: returns StorageObject with the expected shape and hash', async () => {
    const client = makeClient({
      download: () => Promise.resolve({ data: null, error: { message: 'not found', status: 404 } }),
      upload: () =>
        Promise.resolve({
          data: {
            id: 'obj-1',
            path: 'nrb-cmefs/2026-05-13/cmefs-nine-months.pdf',
            fullPath: 'source-archive/…',
          },
          error: null,
        }),
    });

    const result = await uploadSourceDocument({ ...VALID_INPUT_BASE, body }, client);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toEqual({
      storageKey: 'nrb-cmefs/2026-05-13/cmefs-nine-months.pdf',
      fileHashSha256: bodyHash,
      fileSizeBytes: body.byteLength,
      contentType: 'application/pdf',
      storageProvider: 'supabase',
    });
  });

  it('idempotent: same key + same hash → ok with existing metadata', async () => {
    const existingBlob = new Blob([body], { type: 'application/pdf' });
    const client = makeClient({
      download: () => Promise.resolve({ data: existingBlob, error: null }),
    });

    const result = await uploadSourceDocument({ ...VALID_INPUT_BASE, body }, client);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.fileHashSha256).toBe(bodyHash);
    expect(result.value.storageKey).toBe('nrb-cmefs/2026-05-13/cmefs-nine-months.pdf');
  });

  it('conflict: same key + different hash → Conflict error', async () => {
    const differentBlob = new Blob([Buffer.from('totally-different-bytes')], {
      type: 'application/pdf',
    });
    const client = makeClient({
      download: () => Promise.resolve({ data: differentBlob, error: null }),
    });

    const result = await uploadSourceDocument({ ...VALID_INPUT_BASE, body }, client);

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('Conflict');
  });

  it('validation: bad sourceId → Validation error', async () => {
    const client = makeClient({});
    const result = await uploadSourceDocument(
      { ...VALID_INPUT_BASE, sourceId: 'BadID!', body },
      client,
    );
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('Validation');
    if (result.error.kind === 'Validation') {
      expect(result.error.field).toBe('sourceId');
    }
  });

  it('validation: empty body → Validation error', async () => {
    const client = makeClient({});
    const result = await uploadSourceDocument(
      { ...VALID_INPUT_BASE, body: Buffer.alloc(0) },
      client,
    );
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('Validation');
    if (result.error.kind === 'Validation') {
      expect(result.error.field).toBe('body');
    }
  });

  it('sanitization: filename with spaces and unicode is underscored in the key', async () => {
    const client = makeClient({
      download: () => Promise.resolve({ data: null, error: { message: 'not found', status: 404 } }),
      upload: () =>
        Promise.resolve({
          data: { id: 'obj-2', path: 'p', fullPath: 'p' },
          error: null,
        }),
    });

    const result = await uploadSourceDocument(
      { ...VALID_INPUT_BASE, fileName: 'My Report रिपोर्ट.pdf', body },
      client,
    );

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.storageKey).toBe('nrb-cmefs/2026-05-13/My_Report________.pdf');
  });

  it('external: upload error → External error', async () => {
    const client = makeClient({
      download: () => Promise.resolve({ data: null, error: { message: 'not found', status: 404 } }),
      upload: () => Promise.resolve({ data: null, error: { message: 'bucket full', status: 507 } }),
    });
    const result = await uploadSourceDocument({ ...VALID_INPUT_BASE, body }, client);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('External');
  });
});

describe('downloadSourceDocument', () => {
  it('returns body bytes + size + content type on success', async () => {
    const blob = new Blob([Buffer.from('contents')], { type: 'application/pdf' });
    const client = makeClient({
      download: () => Promise.resolve({ data: blob, error: null }),
    });

    const result = await downloadSourceDocument('nrb-cmefs/2026-05-13/a.pdf', client);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.sizeBytes).toBe(8);
    expect(result.value.contentType).toBe('application/pdf');
  });

  it('translates 404 to NotFound', async () => {
    const client = makeClient({
      download: () => Promise.resolve({ data: null, error: { message: 'not found', status: 404 } }),
    });
    const result = await downloadSourceDocument('missing/key.pdf', client);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('NotFound');
  });
});

describe('getPublicUrl', () => {
  it('composes the public URL from env + bucket + key', () => {
    const url = getPublicUrl('nrb-cmefs/2026-05-13/a.pdf');
    expect(url).toBe(
      'https://example.supabase.co/storage/v1/object/public/source-archive/nrb-cmefs/2026-05-13/a.pdf',
    );
  });
});

describe('getSignedUrl', () => {
  it('returns the signed URL on success', async () => {
    const client = makeClient({
      createSignedUrl: () =>
        Promise.resolve({
          data: { signedUrl: 'https://example.supabase.co/storage/v1/object/sign/x?token=abc' },
          error: null,
        }),
    });
    const result = await getSignedUrl('nrb-cmefs/2026-05-13/a.pdf', 60, client);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value).toContain('token=abc');
  });

  it('rejects non-positive expiresSec as Validation', async () => {
    const client = makeClient({});
    const result = await getSignedUrl('a/b/c.pdf', 0, client);
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe('Validation');
  });
});
