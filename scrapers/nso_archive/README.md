# NSO Nepal Archive Scraper

Acquisition-only Layer-1 scraper for the National Statistics Office of Nepal
(<https://nsonepal.gov.np>). It walks category index pages, enumerates every
linked PDF, downloads new ones to a content-addressable directory, and emits
an append-only JSONL manifest with provenance.

**This module does not parse PDFs.** Per
[`docs/decisions/0003-ai-assisted-parsing-policy.md`](../../docs/decisions/0003-ai-assisted-parsing-policy.md),
no LLM API is involved at any stage. A future Node-side ingestor will read
`manifest.jsonl` + the sidecar JSON files to upsert rows into
`source_documents`.

## Quick start

```powershell
# From the repo root, with the scrapers workspace installed:
python -m scrapers.nso_archive.cli `
    --category-ids 1058 1059 `
    --output-dir ./.archive/nso
```

The CLI prints a final one-line summary:

```
discovered: 47, archived: 39, skipped: 8, errors: 0
```

Exit code is `0` only when no error event was written.

### Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--category-ids` | (required) | One or more NSO category ids (e.g. `1058`). |
| `--output-dir` | (required) | Where PDFs, sidecars, and `manifest.jsonl` land. |
| `--category-base-url` | `https://nsonepal.gov.np/category/` | Override for tests / staging. |
| `--max-docs` | `100` | Hard cap on PDFs archived per invocation. |
| `--discovery-timeout-s` | `30` | Per-category-page fetch timeout. |
| `--download-timeout-s` | `120` | Per-PDF download timeout. |
| `--dry-run` | off | Discover only; write `discovery_only` events, no downloads. |

## Output layout

```
<output_dir>/
  manifest.jsonl                 # append-only log of every event
  <sha256>.pdf                   # one file per unique-by-hash PDF
  <sha256>.json                  # sidecar with discovered + archived metadata
```

Each line in `manifest.jsonl` has one of these `event_type` values:

| `event_type` | meaning |
| --- | --- |
| `archived` | new PDF downloaded and hashed |
| `skipped_duplicate` | URL re-seen, hash already on disk |
| `discovery_only` | dry-run: discovered, not downloaded |
| `error` | fetch / parse / hash failure (with `repr(exc)` + traceback) |

Every record carries `schema_version: "1"`.

## Adding a new category

1. Browse <https://nsonepal.gov.np> in a real browser, navigate to the
   category you want to mirror (e.g. *Economic Census*), note the numeric id
   from the URL (`/category/<id>/`).
2. Add it to your invocation: `--category-ids 1058 <new-id>`.
3. Optional: capture a fresh HTML fixture (next section) so tests cover the
   new template variant.

## Capturing a real fixture

Tests rely on `tests/fixtures/category_1058.html`. The version checked in is
a **synthetic** hand-crafted mimic — Mother's worker had no network access
when this module was written. To replace it with a verbatim snapshot:

```powershell
curl -A "nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)" `
    https://nsonepal.gov.np/category/1058/ `
    -o scrapers/nso_archive/tests/fixtures/category_1058.html
```

Then re-run the test suite. If `test_discover.py` assertions break, the
real markup uses different selectors than the fixture; adjust either the
fixture expectations or `discover._parse_page` and add an entry to
`docs/CHANGE_CONTROL.md`.

## Politeness contract

- 1 req/sec target (configurable via `polite_sleep_s` on programmatic calls).
- Custom `User-Agent`: `nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)`.
- Streaming downloads in 64 KiB chunks.
- Single retry on transport errors with exponential backoff (1s, 2s).
- No retry on HTTP 4xx.
- Pagination follows `?page=N` up to a cap of 20 pages.

## Testing

```powershell
python -m pytest scrapers/nso_archive/tests
```

All tests use `httpx.MockTransport` — no network calls.

## Public surface

```python
from nso_archive import (
    DiscoveredDocument,
    ArchivedDocument,
    discover_documents,
    archive_document,
)
```
