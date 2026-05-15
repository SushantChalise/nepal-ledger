# Source: Nepal Rastra Bank — Banking & Financial Statistics (monthly XLSX corpus)

**source_id:** `nrb-bfi-monthly-xlsx`
**Status:** active (canonical month parsed; remaining 48 months batched in follow-up)
**Tier:** Tier 1
**Registered at:** 2026-05-14
**Last verified:** 2026-05-15

## Publication

- URL: https://www.nrb.org.np/category/banking-and-financial-statistics/
- Frequency: monthly
- Format: xlsx
- Reporting period type: monthly
- Requires table extraction: yes (multi-sheet, multi-block per sheet)

## Corpus

- On-disk location: `Financial Data/nrb_monthly_statistics/` (gitignored; pre-staged)
- File count: 49 XLSX snapshots, Shrawan 2078 → Bhadau 2082
- Canonical month: `Bhadau_2082_Publish.xlsx` (most recent at parser ship)
- Companion: `metadata.json`, `bfi_niyamabali.pdf` (regulatory; not parsed)

## Provenance

- Confidence default: A
- License: gov_open
- Ingestion mode: manual_upload

## Schema layout (Bhadau 2082 canonical)

Each XLSX carries **25 sheets** named `C1`..`C25`. The high-value sheets for
Money Captured + Collateral State are:

- **C5** — Statement of Assets & Liabilities
- **C6** — Profit & Loss statement
- **C7** — Loans & advances by economic sector

Each of these sheets has **four side-by-side sub-tables**, one per bank
class: BFI total (system_total), Commercial, Development, Finance. Each
sub-table has a stride of 8 value columns; the descriptive indicator label
lives in **column 2** (0-indexed) for all four sub-tables (the label is
shared across blocks).

For the canonical month, value column indices (0-based) for the latest
snapshot (Mid-Sept 2025) are:

| Bank class    | C5 value col | C6 value col | C7 value col |
|---------------|-------------:|-------------:|-------------:|
| system_total  | 7            | 7            | 7            |
| commercial    | 15           | 15           | 15           |
| development   | 23           | 23           | 23           |
| finance       | 31           | 31           | 31           |

Other months drift on:
- sheet name casing/whitespace
- header row text ("Mid-July " vs "Mid-July", year labels)
- max_row counts (varying numbers of sub-rows under each balance heading)
- a small number of files include extra sheets (rare; flagged by schema probe)

See `docs/research/nrb-bfi-schema-probe.md` for the full per-file inventory
and structural-similarity grouping.

## Parser status

- v0.1.0 (this ship): parses **C5 only** for the canonical month
  (Bhadau 2082) — ~9 indicators × 4 bank classes = ~36 rows per ingestion.
- Schema probe output groups the remaining 48 months for follow-up batches.
- See `docs/tasks/worker-P2-followup-bfi-batches.md`.

## Known breakage modes

- XLSX files with embedded drawings can crash openpyxl in non-`read_only`
  mode (encountered in Bhadau 2082). Parser uses `read_only=True` to
  bypass; do not change.
- Older 2078 files use slightly different sheet naming. Schema probe will
  surface these; parsers must dispatch on sheet name presence, not assume.
- Column 1 sometimes holds an ordinal number and sometimes a descriptive
  label (drift across the corpus). The canonical parser reads from
  **col 2** (descriptive label) — confirm in the probe before extending.

## Revision policy

NRB occasionally republishes a month with restated values (the `-V1`,
`-V2`, `-V3` suffixes in filenames). The ingest CLI relies on the
natural-key unique index + `onConflictDoNothing` — re-ingesting the same
filename is a no-op; a republished file with the same period gets
flagged when the validation job sees a value delta. See
`docs/DATA_PIPELINE.md` §"Revision detection".

## Related sources

- `nrb-banking-stats` (quarterly bulletin PDF) — partial overlap with this
  corpus; canonicalise to the monthly XLSX where present.
- `nrb-cmefs-monthly` (NRB CMEFs PDF) — complementary macro tables;
  separate parser pipeline.
