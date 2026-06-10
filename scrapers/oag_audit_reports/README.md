# OAG Audit Reports — acquisition scraper

`source_id: oag-audit-reports` · doctrine: [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md) (deterministic Python), [ADR-0024](../../docs/decisions/0024-government-audit-fact-domain.md) (audit fact domain) · recon: [docs/research/oag-audit-reports-audit.md](../../docs/research/oag-audit-reports-audit.md)

Acquires the Office of the Auditor General's consolidated **Annual Report** PDFs, content-addresses them, and writes an append-only provenance manifest. This is the **acquisition** stage only — it downloads + hashes + provenances; it does **not** parse PDFs (that's the future parser PR).

## Why a curated catalog, not a crawler

The new OAG site (`oag.gov.np`) is a **JS SPA** with no stable report-URL pattern, and the legacy site (`old.oag.gov.np`) serves an **expired TLS certificate** — so there is no reliable crawl. Acquisition is therefore **curated** (`ingestion_mode = manual_upload`): report PDF URLs are recorded in [`sources.py`](sources.py) as `ReportRef`s, and the archiver downloads them deterministically. This mirrors how `nso_archive` archives, minus the HTML discovery step.

## Usage

```bash
# from repo root, with the scrapers Python env active (httpx required)
python -m scrapers.oag_audit_reports.cli --output-dir source-data/oag --dry-run   # list selection
python -m scrapers.oag_audit_reports.cli --output-dir source-data/oag             # download + archive
python -m scrapers.oag_audit_reports.cli --output-dir source-data/oag --edition 58 --language en
```

Each successful run writes, under `--output-dir`:

- `<sha256>.pdf` — the report, content-addressed (dedup + integrity).
- `<sha256>.json` — a sidecar: the `ReportRef` + archived metadata (url, bytes, content-type, fetched-at).
- `manifest.jsonl` — append-only events: `archived | skipped_duplicate | discovery_only | error`.

Idempotent: re-running skips reports whose content hash is already archived. `--max-docs` caps a run. Downloads are polite (1s sleep between fetches by default).

## Adding a report to the catalog

1. Open the report on `oag.gov.np`, copy the `/site_uploads/<...>.pdf` URL.
2. Append a `ReportRef` to `KNOWN_REPORTS` in [`sources.py`](sources.py). Record the **edition**, the **audited fiscal year** (read it from the report's foreword — the title year is the BS submission year, **not** the audited FY), the **language** (`en`/`ne`), and `doc_kind`.
3. Set `verified=True` only after a successful fetch.

**English vs Nepali:** the English edition carries tier/class **aggregates** + major observations only; **per-entity** detail (ministries, provinces, local levels) is **only in the Nepali edition**. Acquire both when both grains are needed (see the recon doc §4).

**Legacy historical URLs** live on `old.oag.gov.np/uploads/...` (e.g. older Report Summaries). That domain's TLS cert is expired — fetch those via a browser and re-host, or add explicit insecure handling before scripting them. The default scraper does **not** disable TLS verification.

## Layout

| File | Role |
|---|---|
| `sources.py` | `ReportRef` + the curated `KNOWN_REPORTS` catalog + `select_reports()` |
| `archive.py` | stream-download → sha256 → `<sha256>.pdf` + sidecar; idempotent; `ArchiveError` on 4xx/5xx |
| `manifest.py` | append-only JSONL provenance log |
| `cli.py` | `argparse` entry point (`--output-dir`, `--edition`, `--language`, `--dry-run`, `--max-docs`) |
| `tests/` | pytest (mocked `httpx`, no network) |

## Tests

```bash
cd scrapers && PYTHONPATH=. python -m pytest oag_audit_reports/tests
```

> Note: the Node CI workflow does not yet run the Python scrapers; run `pytest` / `ruff` / `mypy` locally (per `scrapers/pyproject.toml`). Wiring Python into CI is tracked separately.
