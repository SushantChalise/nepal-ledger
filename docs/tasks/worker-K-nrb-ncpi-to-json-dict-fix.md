# Worker K — NRB NCPI parser direct-invoke `to_json_dict` fix

**Spawn type:** general-purpose
**Diff cap:** 100 code-only non-test source lines (tiny PR)

## Goal

Fix the same latent bug Worker P1 surfaced and fixed in `scrapers/mof_fiscal_transfers/parser.py`: when a Python parser is invoked as a subprocess directly (`python -m scrapers.nrb_ncpi.parser <path> <id>`), the `_common.types.ParserError` class identity differs between the direct-invoke context and the imported context. Bound methods like `to_json_dict()` aren't reliably visible across this boundary.

**The fix:** in `scrapers/nrb_ncpi/parser.py`'s `__main__` block, serialize the `ParserResult` using `dataclasses.asdict(result)` rather than `result.to_json_dict()`. Datetime fields need explicit `.isoformat()` handling.

## Why

Today, the bug is masked because `src/lib/ingestion/index.test.ts` uses mocked subprocesses. The real subprocess invocation (production code path) has never been integration-tested end-to-end. The first time it runs against a real DB, the parser stdout would be malformed JSON and the Zod schema would fail-closed.

Worker P1's `scrapers/mof_fiscal_transfers/parser.py` uses the corrected pattern. Mirror that.

## Scope Fence

Edit:
- `scrapers/nrb_ncpi/parser.py` — the `__main__` block ONLY. Do not change the `parse()` function or any data classes.

Optionally:
- `scrapers/_common/types.py` — consider deprecating `to_json_dict()` on the dataclasses if no caller uses it (grep for usages first). If still referenced from importable Python contexts, leave alone.

**Out of scope:**
- `parse()` function changes
- Any TS changes (the Zod schema on the Node side is correct)
- The orchestrator (Worker H's output, already shipped)

## Acceptance Criteria

- [ ] `python -m scrapers.nrb_ncpi.parser <fixture> <fake-id>` produces valid JSON on stdout
- [ ] `pnpm test --run` — 131/131 still pass
- [ ] `python -m pytest scrapers/nrb_ncpi/tests` — still passes
- [ ] Under 100 code-only non-test source lines

## What to Return

Standard 6-section report. This is a tiny PR; expect 20-30 lines of actual change.
