/**
 * Spawn the deterministic Python parser as a subprocess.
 *
 * Subprocess contract (also documented in the task brief):
 *   - argv: <source_document_path> <source_document_id>
 *   - stdout: ParserResult JSON (single document); read in full
 *   - stderr: human-readable diagnostics; surfaced on non-zero exit
 *   - exit 0  → consumer parses stdout (status may still be 'failure')
 *   - exit 2  → usage error (bad argv) — orchestrator returns External
 *   - exit 1  → catastrophic crash — orchestrator returns External
 *
 * Windows note: `shell: false` is mandatory — passing user-supplied paths
 * through cmd.exe would create a shell-injection risk. The python
 * executable is read from `PYTHON` env var, falling back to `python`
 * which is the standard Windows launcher name.
 *
 * The `spawnImpl` parameter lets tests inject a fake `spawn` without
 * mocking the whole `node:child_process` module.
 */

import { spawn as nodeSpawn } from 'node:child_process';
import type { EventEmitter } from 'node:events';

import { err, ok, type Result } from '@/lib/errors';

import { ParserOutputSchema, type ParserOutput } from './types';

const PYTHON_SERVICE = 'python-parser';
const DEFAULT_TIMEOUT_MS = 60_000;

/**
 * Structural shape of the subset of `ChildProcessWithoutNullStreams` the
 * orchestrator depends on. Production passes node's `spawn` (which
 * structurally satisfies this); tests pass a hand-rolled stub. The narrow
 * interface lets us inject without `as` casts.
 */
export type SpawnedChildLike = EventEmitter & {
  stdout: EventEmitter;
  stderr: EventEmitter;
  kill(signal?: NodeJS.Signals | number): boolean | void;
};

export type SpawnLike = (
  command: string,
  args: readonly string[],
  options: { cwd?: string; shell: false },
) => SpawnedChildLike;

export type RunParserInput = {
  /** Absolute or relative path to the parser .py file (e.g. scrapers/nrb_ncpi/parser.py). */
  parserPath: string;
  /** Path passed as argv[1] to the parser — the file it should read. */
  sourceFilePath: string;
  /** Passed as argv[2] — opaque UUID for traceability. */
  sourceDocumentId: string;
  /** Working directory for the subprocess. Defaults to process.cwd(). */
  cwd?: string;
  /** Override the python executable. Default: $PYTHON or `python`. */
  pythonExecutable?: string;
  /** Hard timeout in ms. Default: 60_000. */
  timeoutMs?: number;
  /** Injection seam for tests. Default: node:child_process spawn. */
  spawnImpl?: SpawnLike;
};

type CapturedProcess = {
  exitCode: number;
  stdout: string;
  stderr: string;
  timedOut: boolean;
};

export async function runParser(input: RunParserInput): Promise<Result<ParserOutput>> {
  const timeoutMs = input.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const python =
    input.pythonExecutable ??
    process.env['PYTHON'] ??
    (process.platform === 'win32' ? 'python' : 'python3');
  const spawnImpl: SpawnLike = input.spawnImpl ?? nodeSpawn;

  const captured = await runSubprocess(
    spawnImpl,
    python,
    [input.parserPath, input.sourceFilePath, input.sourceDocumentId],
    { cwd: input.cwd ?? process.cwd(), timeoutMs },
  );

  if (captured.timedOut) {
    return err({
      kind: 'External',
      service: PYTHON_SERVICE,
      cause: `timeout after ${timeoutMs}ms: ${input.parserPath}`,
    });
  }
  if (captured.exitCode === 2) {
    return err({
      kind: 'External',
      service: PYTHON_SERVICE,
      cause: `usage error (exit 2): ${captured.stderr.trim() || '<no stderr>'}`,
    });
  }
  if (captured.exitCode !== 0) {
    return err({
      kind: 'External',
      service: PYTHON_SERVICE,
      cause: `exit ${captured.exitCode}: ${captured.stderr.trim() || '<no stderr>'}`,
    });
  }

  let parsedJson: unknown;
  try {
    parsedJson = JSON.parse(captured.stdout);
  } catch (e) {
    return err({
      kind: 'ParseFailed',
      field: 'parser stdout',
      reason: `not JSON: ${e instanceof Error ? e.message : String(e)}`,
    });
  }
  const validated = ParserOutputSchema.safeParse(parsedJson);
  if (!validated.success) {
    const issue = validated.error.issues[0];
    return err({
      kind: 'ParseFailed',
      field: `parser stdout.${issue?.path.join('.') ?? '<root>'}`,
      reason: issue?.message ?? 'shape mismatch',
    });
  }
  return ok(validated.data);
}

async function runSubprocess(
  spawnImpl: SpawnLike,
  command: string,
  args: readonly string[],
  options: { cwd: string; timeoutMs: number },
): Promise<CapturedProcess> {
  return new Promise((resolve) => {
    const child = spawnImpl(command, args, { cwd: options.cwd, shell: false });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    let settled = false;
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGKILL');
    }, options.timeoutMs);

    child.stdout.on('data', (chunk: Buffer) => stdoutChunks.push(chunk));
    child.stderr.on('data', (chunk: Buffer) => stderrChunks.push(chunk));

    const settle = (exitCode: number): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({
        exitCode,
        stdout: Buffer.concat(stdoutChunks).toString('utf8'),
        stderr: Buffer.concat(stderrChunks).toString('utf8'),
        timedOut,
      });
    };

    child.on('error', (e: Error) => {
      stderrChunks.push(Buffer.from(`spawn error: ${e.message}\n`));
      settle(1);
    });
    child.on('close', (code: number | null) => {
      settle(code ?? 1);
    });
  });
}
