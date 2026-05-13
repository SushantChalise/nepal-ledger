# Nepal Ledger — Python Scrapers

Deterministic Python parsers for external data sources. See
[ADR-0003](../docs/decisions/0003-ai-assisted-parsing-policy.md):
production parsing is Python, never API calls. Claude CLI is a dev assistant
only.

## Install

```sh
cd scrapers
python -m venv .venv
. .venv/Scripts/activate            # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Or with `uv`:

```sh
cd scrapers
uv venv
uv pip install -e ".[dev]"
```

## Run tests

```sh
cd scrapers
pytest -q
```

## Lint / typecheck

```sh
ruff check scrapers/
mypy scrapers/
```

## Layout

```
scrapers/
  pyproject.toml          # Python 3.12 + ruff/mypy/pytest config
  _common/                # shared types, hashing, periods, parser protocol
  nrb_ncpi/               # NRB CMEFs Table 2(B) — NCPI parser
    parser.py             # parse(path, doc_id) -> ParserResult
    tests/                # pytest against the real CSV in the repo
    fixtures/             # placeholder for parametric test fixtures
```

**Naming note:** the on-disk dir is `nrb_ncpi` (underscore) because Python
forbids hyphens in module names. The canonical `source_id` registered in
`docs/SOURCE_REGISTRY.md` keeps the hyphenated form (`nrb-ncpi-table`).

## Parser contract

Every parser exposes:

- `PARSER_VERSION: str` — semver; bump on behavior change
- `SOURCE_ID: str` — matches `source_registry.source_id`
- `parse(source_document_path: str, source_document_id: str) -> ParserResult`

Rules:
- **Idempotent**: same input -> same output, byte-for-byte.
- **No network calls.** Parsers operate on already-downloaded files.
- **No DB writes.** The orchestration layer (TS) consumes `ParserResult`
  and writes to `staging_indicator_values`.
- **Never raise on bad data.** Return `status='partial'` or `'failure'` with
  structured `errors[]`.

See [docs/DATA_PIPELINE.md](../docs/DATA_PIPELINE.md) §"Parser Contract".

## BS<->AD dates

Python parsers use **lightweight mid-month placeholders** (15th of the
corresponding AD month). The authoritative BS<->AD wrapper lives on the TS
side at `src/lib/dates/index.ts` (uses `nepali-date-converter`). The TS
validation layer refines parser-emitted timestamps before promotion. **Do
not install a Python BS<->AD library** without an ADR — see Mother's
guidance in `docs/tasks/worker-C-python-scrapers.md`.
