# OAG Audit Reports — acquisition scraper

`source_id: oag-audit-reports` · doctrine: [ADR-0003](../../docs/decisions/0003-ai-assisted-parsing-policy.md) (deterministic Python), [ADR-0024](../../docs/decisions/0024-government-audit-fact-domain.md) (audit fact domain) · recon: [docs/research/oag-audit-reports-audit.md](../../docs/research/oag-audit-reports-audit.md)

Acquires the Office of the Auditor General's consolidated **Annual Report** PDFs, content-addresses them, writes an append-only provenance manifest, **and** parses the English edition's headline aggregate tables into the audit fact-domain contract.

- **Acquisition** (`discover.py` / `sources.py` / `archive.py` / `cli.py`): downloads + hashes + provenances report PDFs.
- **Parsing** (`parser.py`): deterministic Tier-0 extraction of the English edition's class aggregates (audited amounts, beruju by category × tier, settlement/cumulative) → `AuditParserOutput` JSON.

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

## Parser (English edition, Tier 0)

`parser.py` extracts the report's headline **class aggregates** (the English edition carries no per-entity detail — that needs the Nepali edition) and emits the [`AuditParserOutput`](../../src/lib/ingestion/audit-types.ts) contract:

```bash
# prints AuditParserOutput JSON to stdout; pdfplumber required
python -m oag_audit_reports.parser <report.pdf> <source_document_id> [--]
```

Three printed tables are located **by content** (robust to page-number drift), not by fixed page:

| Source table | → contract rows |
|---|---|
| Ch.1 "Details of Audited Entities" (NRs **billions**) | per-class `audited_amount` + entity count |
| Ch.2 "Status of Irregularity" — classification × tier (NRs **millions**) | `audit_beruju_lines`, `amount_basis=current_year_raised`, per class × `beruju_category` |
| Ch.2 settlement/lifecycle table | per-class `settled_this_year` + `cumulative_outstanding` |

Design notes (ADR-0027 model):

- **Audited FY** comes from the title's **edition ordinal** (spelled-out "Fifty-Eighth" or "58th") via `discover.audited_fy_for_edition` — never the cover/publish year (title-year trap). The orchestrator may pass `fiscal_year_bs` to override.
- **Category → lookup codes:** `beruju_category` is a code into the `beruju_categories` lookup table, not an enum. Labels map to the OAG taxonomy: `Recoverable → recoverable`, `Irregular → tbr_irregular`, `Evidence/documents not submitted → tbr_evidence_not_submitted`, `Balance not brought forward → tbr_balance_not_brought_forward`, `Reimbursement not received → tbr_reimbursement_not_received`, `3.1/3.2/3.3 → adv_staff/adv_mobilization/adv_other_institutional`.
- **Parents are STORED, not skipped:** "2. To be regularized" and "3. Advance" are emitted with `aggregation_role='subtotal'`; the leaves are `detail`. Default analytical sums filter `detail`; the subtotals enable the printed-subtotal == Σ-leaves check.
- **Whitespace normalization:** pdfplumber emits in-cell line breaks (`Mobilization\nAdvance`); labels are whitespace-collapsed before matching so multi-word needles still hit (else a leaf falls through to the generic `advance` subtotal — a real 58th-edition bug).
- **Raw-when-amount:** every `*_npr` is canonical full NPR and carries its printed `*_raw`. Summary `source_unit` is null because the row mixes billions (audited) with millions (beruju) — per-amount scale is implicit in `npr`/`raw`.
- **Reconciliation (level-aware, 3-way):** per tier, (1) `detail` leaves sum to the printed "Total irregularity" exactly, (2) leaves sum to each printed `subtotal` exactly, and (3) the settlement table's current-year column cross-checks the classification total within a NRs 0.1M rounding tolerance (two independent printed tables). Any failure → a `ReconciliationFailed` entry + `status='partial'`. The 58th reconciles to the rupee (federal 44,392.1 / provincial 6,499.7 / local 40,834.7 / committee 12,657.8 M; cumulative = NRs 418.85 bn).

Per ADR-0003 this is **deterministic** Python (no LLM at parse time). The pure table-row functions are unit-tested without a PDF (`tests/test_parser.py`, fixtures are the real 58th-edition rows, incl. an in-cell-newline regression).

## Layout

| File | Role |
|---|---|
| `sources.py` | `ReportRef` + the curated `KNOWN_REPORTS` catalog + `select_reports()` |
| `discover.py` | fetch the `/api/front/annual-reports` JSON API → `ReportRef`; edition-ordinal → audited FY |
| `archive.py` | stream-download → sha256 → `<sha256>.pdf` + sidecar; idempotent; `ArchiveError` on 4xx/5xx |
| `manifest.py` | append-only JSONL provenance log |
| `cli.py` | `argparse` entry point (`--output-dir`, `--edition`, `--language`, `--dry-run`, `--max-docs`) |
| `parser.py` | deterministic Tier-0 PDF → `AuditParserOutput`; pure table-row logic + `pdfplumber` wrapper |
| `tests/` | pytest (mocked `httpx` / real-row fixtures, no network) |

## Tests

```bash
cd scrapers && PYTHONPATH=. python -m pytest oag_audit_reports/tests
```

> Note: the Node CI workflow does not yet run the Python scrapers; run `pytest` / `ruff` / `mypy` locally (per `scrapers/pyproject.toml`). Wiring Python into CI is tracked separately.
