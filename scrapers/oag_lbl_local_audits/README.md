# OAG Local-Body Audit Reports — acquisition scraper

`source_id: oag-lbl-local-audits` · doctrine: [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md), [ADR-0024](../../docs/decisions/0024-government-audit-fact-domain.md) · recon: [docs/research/oag-lbl-local-audits-audit.md](../../docs/research/oag-lbl-local-audits-audit.md)

Discovers and archives the **753 local levels' individual final audit reports** (~6,000+ documents across fiscal years). Acquisition only — download + content-address + provenance; no PDF parsing.

## Discovery via the backend API (not HTML scraping)

The OAG site is a JS SPA, but its backend exposes a clean **Laravel-paginated JSON API**:

```
GET https://oag.gov.np/api/front/local-level-report?page=N
→ { "reports": { "data": [...], "last_page": 601, "total": 6008, "per_page": 10 },
    "provinces": [7], "fiscal_years": [8] }
```

Each row carries the **municipality / district / province**, the fiscal-year label `"2083 (2081/82)"` (publish BS year + the **audited FY in parens** — so no title-year guesswork), and a `files[].location` PDF URL. `discover.py` paginates this endpoint and yields a typed `LocalReportRef` per file. No TLS bypass, no headless browser.

## Usage

```bash
# Discover-only (default): harvest the URL catalog into manifest.jsonl, no downloads
python -m scrapers.oag_lbl_local_audits.cli --output-dir source-data/oag-lbl

# Discover a subset
python -m scrapers.oag_lbl_local_audits.cli --output-dir source-data/oag-lbl \
    --province Bagmati --fiscal-year "2081/82"

# Actually download (narrow it — there are thousands)
python -m scrapers.oag_lbl_local_audits.cli --output-dir source-data/oag-lbl \
    --province Karnali --fiscal-year "2081/82" --archive --max-docs 50
```

**Default is discover-only** (writes `discovered` events with municipality/FY/URL — the catalog) because the full corpus is GBs. Use `--archive` with `--province` / `--fiscal-year` / `--max-docs` to download narrowly. Idempotent (content hash); polite (sleeps between fetches).

Outputs under `--output-dir`: `<sha256>.pdf` + `<sha256>.json` sidecar (the `LocalReportRef` + archived metadata) + append-only `manifest.jsonl` (`discovered | archived | skipped_duplicate | error`).

## Layout

| File | Role |
|---|---|
| `discover.py` | paginate `/api/front/local-level-report` → `LocalReportRef` (+ `parse_audited_fy`) |
| `archive.py` | stream-download → `<sha256>.pdf` + sidecar; idempotent |
| `manifest.py` | append-only JSONL provenance |
| `cli.py` | `argparse` entry (`--province`, `--fiscal-year`, `--archive`, `--max-docs`, `--page-from/to`) |
| `tests/` | pytest (mocked `httpx`, no network) |

## Next (parser, PR E)

Most local reports are Nepali scans → **Tier 2 Surya OCR** (the harness is now on `main`). The parser resolves the `municipality` name to the seeded 753 `entities` via `_common/municipality_resolver.py`, extracts beruju per the audit schema (`audit_subject_class='local_government'`, `source_precedence=2`), and runs the reconciliation gate. See the recon doc.

> CI note: the Node workflow does not run the Python scrapers; run `pytest` / `ruff` / `mypy` locally.
