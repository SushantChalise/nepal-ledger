# nrb-dne-xlsx — NRB Database on Nepalese Economy (XLSX corpus)

| Field | Value |
|-------|-------|
| `source_id` | `nrb-dne-xlsx` |
| `agency` | Nepal Rastra Bank (NRB) |
| `dataset_name` | Database on Nepalese Economy — structured time-series XLSX (all sectors) |
| `source_url` | <https://www.nrb.org.np/database-on-nepalese-economy/> |
| `publication_frequency` | monthly (varies by series) |
| `reporting_period_type` | monthly / annual (mixed; per-series) |
| `file_format` | xlsx |
| `requires_table_extraction` | false (structured XLSX) |
| `historical_coverage` | Varies by series across Real / External / Fiscal / Monetary / Financial sectors |
| `license_status` | gov_open |
| `parser_owner` | `scrapers/nrb_dne/parser.py` |
| `parser_version` | 0.1.0 |
| `confidence_default` | B |
| `status` | active |
| `tier` | 1 |

## What this is

The umbrella ingest source for NRB's **Database on Nepalese Economy** — the
structured time-series XLSX corpus (BoP, forex reserves, remittance, trade,
tourist arrivals, money supply, government finance, etc.). The #1 gap from the
2026-05 NRB catalog audit: plug-and-play XLSX that needs no PDF extraction.

## Identity / reconciliation (ADR-0010)

The parser `scrapers/nrb_dne` declares `SOURCE_ID = "nrb-dne-xlsx"`. This row is
its `source_documents` FK target. The finer-grained catalog rows
`nrb-db-external-sector`, `nrb-db-fiscal-sector`, `nrb-db-real-sector`,
`nrb-db-financial-sector` describe the individual sectoral pages; a DNE ingest
is tagged with this umbrella `source_id` and the sector is captured in the
indicator slug (`dne-<label>`) / `parser_notes`. (Option A in the DNE wiring
reconciliation: one ingest source per data product, matching the CMEFs pattern.)

## Status (2026-06)

- Parser written, 28 tests passing, wired via `ingest:dne` (dry-run verified).
- **No real DNE XLSX downloaded yet** — live ingest pending a download pass
  (URLs embed upload dates; scrape the sector page for the current link — see
  `knownBreakageModes`).

## Known breakage modes

- `upload-url-embeds-date-not-hardcodeable` — download URLs carry the upload
  date; resolve the current link from the sector page rather than hardcoding.
- `sector-page-layout-shift` — the listing page layout can change.

## Cross-reference

- Parser: [`scrapers/nrb_dne/README.md`](../../scrapers/nrb_dne/README.md)
- [ADR-0010](../decisions/0010-ingest-cli-conventions.md) — ingest CLI conventions
- Audit: [`docs/research/NRB_CATALOG_AUDIT_2026-05.md`](../research/NRB_CATALOG_AUDIT_2026-05.md)
