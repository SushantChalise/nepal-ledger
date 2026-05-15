# Worker P2 follow-up — NRB BFI monthly XLSX, remaining 48 months

**Status:** brief stub
**Predecessor:** Worker P2 (this PR)
**Source id:** `nrb-bfi-monthly-xlsx`

## Goal

Extend the BFI parser to cover the remaining 48 months of the corpus
(Shrawan 2078 → Saun 2082, excluding the canonical Bhadau 2082 already
shipped). Batch by structural similarity rather than chronology — the
schema-discovery probe at `docs/research/nrb-bfi-schema-probe.md` is the
input.

## Shape

Spawn one Worker brief per **schema group** identified in the probe report
("G1", "G2", …). The probe groups files by sheet count + key-sheet
dimensions; files within a group share parser logic.

Typical batch:

- Read the group's sample header excerpt in the probe report.
- Extend `_LATEST_VALUE_COL_BY_CLASS` and `_C5_INDICATORS` in
  `scrapers/nrb_bfi/parser.py` (or fork a group-specific parser module if
  drift is too large — discuss with Mother).
- Add per-month period metadata (do not hardcode Bhadau 2082).
- Extend `scripts/ingest-bfi-monthly.ts` to walk a directory rather than
  single file when `--input` points at a folder.
- Tests: one fixture per group, schema-faithful trimmed XLSX.

## Acceptance per batch

- [ ] All files in the group parse without "PageLayoutChanged" errors.
- [ ] Row count per file matches `(indicator count) × 4 bank classes`.
- [ ] Idempotent re-ingestion produces zero new rows on second run.
- [ ] Tests green; `pnpm` gates green.

## Out of scope

- Sheets beyond C5/C6/C7 (Phase 2 of BFI coverage; needs ADR if scope
  is widened).
- Per-bank entity dimension (currently `bank_entity_id = NULL`; per-bank
  rows require the `entities` table to carry NRB-licensed bank names —
  separate ingest path, follow-up brief).
- BS↔AD calendar refinement (period dates use mid_month_ad placeholders;
  TS validator refines them — see `docs/CALENDAR_AND_PERIODS.md`).

## Sequencing

After this PR lands and the probe report is reviewed by Mother, file
one brief per top-3 schema groups. Smaller / one-off groups parked until
the schema-discovery output has been audited end to end.
