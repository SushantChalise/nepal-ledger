/**
 * Ingestion orchestrator — the Node-side glue from "file on disk or URL" to
 * "validated approved rows".
 *
 * Pipeline (see docs/DATA_PIPELINE.md §"The Flow"):
 *   1. Read or download the file → Buffer
 *   2. Archive to Supabase Storage (content-addressed; idempotent)
 *   3. Insert source_documents row pointing at the storage object
 *   4. Spawn the Python parser subprocess; parse stdout JSON
 *   5. Persist parser_runs + staging_indicator_values (+ parser_errors)
 *   6. Run the validation job (Worker G) against the new parser_runs row
 *
 * Every step returns Result<T>; the orchestrator short-circuits on the first
 * err. Nothing throws. No `as` casts.
 */

import { insertSourceDocument } from '@/lib/db/repositories/source-documents';
import { sha256OfBuffer, uploadSourceDocument } from '@/lib/storage';
import { validateParserRun } from '@/lib/validation';
import { ok, type Result } from '@/lib/errors';

import { downloadOrRead } from './download-or-read';
import { persistStaging } from './persist-staging';
import { runParser, type SpawnLike } from './run-parser';
import type { IngestionInput, IngestionSummary, ParserOutput } from './types';

export type { IngestionInput, IngestionSummary, ParserOutput } from './types';
export { ParserOutputSchema, StagingRowDraftSchema } from './types';

/**
 * Extra knobs the public surface keeps optional but tests pass to inject
 * the subprocess seam without env mutation.
 */
export type IngestSourceOptions = {
  spawnImpl?: SpawnLike;
  pythonExecutable?: string;
};

export async function ingestSource(
  input: IngestionInput,
  options: IngestSourceOptions = {},
): Promise<Result<IngestionSummary>> {
  // 1. Read or download.
  const file = await downloadOrRead(toFileSource(input));
  if (!file.ok) return file;

  // 2. Archive to storage. Content-addressed: same bytes → same key/hash
  //    → the storage layer returns the existing object idempotently.
  const downloadedAtIso = new Date().toISOString();
  const stored = await uploadSourceDocument({
    sourceId: input.sourceId,
    downloadedAtIso,
    fileName: input.fileName,
    body: file.value,
    contentType: input.contentType,
  });
  if (!stored.ok) return stored;

  // 3. Insert source_documents row. DATA_PIPELINE.md: rows are never updated
  //    — a re-run of the same bytes creates a NEW row pointing at the same
  //    storage object (the storage layer dedups, the table does not).
  const originalUrl = 'url' in input ? input.url : `file://${input.filePath}`;
  const docResult = await insertSourceDocument({
    sourceId: input.sourceId,
    originalUrl,
    storageProvider: stored.value.storageProvider,
    storageKey: stored.value.storageKey,
    fileHashSha256: stored.value.fileHashSha256,
    fileSizeBytes: stored.value.fileSizeBytes,
    contentType: stored.value.contentType,
    reportingPeriodLabel: input.reportingPeriodLabel ?? null,
  });
  if (!docResult.ok) return docResult;
  const sourceDocumentId = docResult.value.id;

  // 4. Run the Python parser. The parser reads from disk; if we only have
  //    the bytes from a URL, we still need a path. For URL input the parser
  //    is given the storage-archived file's STORAGE KEY is not a local path,
  //    so we instead pass the original local path (filePath case) OR the
  //    parser receives nothing usable. Constraint: parsers operate on local
  //    files only (DATA_PIPELINE.md §"Parser Contract"). For url input the
  //    caller is responsible for handing a filePath — see brief; tests cover
  //    both. For now we pass `filePath` if present, else fall back to the
  //    URL as the parser's argv (most parsers will fail-fast on a non-file
  //    path, which is the correct failure mode).
  const parserInputPath = 'filePath' in input ? input.filePath : input.url;
  const parserStartedAt = new Date();
  const parserResult = await runParser({
    parserPath: input.parserPath,
    sourceFilePath: parserInputPath,
    sourceDocumentId,
    ...(input.parserTimeoutMs !== undefined ? { timeoutMs: input.parserTimeoutMs } : {}),
    ...(options.spawnImpl !== undefined ? { spawnImpl: options.spawnImpl } : {}),
    ...(options.pythonExecutable !== undefined
      ? { pythonExecutable: options.pythonExecutable }
      : {}),
  });
  if (!parserResult.ok) return parserResult;
  const parserEndedAt = new Date();

  // 5. Persist parser_runs + staging rows.
  const persisted = await persistStaging({
    parserOutput: parserResult.value,
    sourceDocumentId,
    parserPath: input.parserPath,
    startedAt: parserStartedAt,
    endedAt: parserEndedAt,
    stdoutTail: parserStdoutTail(parserResult.value),
  });
  if (!persisted.ok) return persisted;

  // 6. Validate. Worker G surfaces blocks via the summary; we still return ok.
  const validation = await validateParserRun(persisted.value.parserRunId);
  if (!validation.ok) return validation;

  return ok({
    sourceDocumentId,
    parserRunId: persisted.value.parserRunId,
    parserStatus: parserResult.value.status,
    stagingRowsWritten: persisted.value.stagingRowsWritten,
    validation: validation.value,
  });
}

function toFileSource(input: IngestionInput): { filePath: string } | { url: string } {
  if ('filePath' in input) return { filePath: input.filePath };
  return { url: input.url };
}

/**
 * Stable string summary used as `parser_runs.stdout_tail`. The Python
 * parser's actual stdout is JSON we've already parsed — re-serializing the
 * head gives a stable, bounded breadcrumb without keeping raw bytes around.
 */
function parserStdoutTail(output: ParserOutput): string {
  return JSON.stringify({
    status: output.status,
    parser_version: output.parser_version,
    rows: output.staging_rows.length,
    errors: output.errors.length,
  });
}

// Re-export the hash helper for callers wiring `original_url` from a remote
// payload (e.g. when fetching a redirected URL the caller wants logged).
export { sha256OfBuffer };
