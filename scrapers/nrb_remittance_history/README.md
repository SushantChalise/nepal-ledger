# `nrb_remittance_history` — NRB historical Workers' Remittances (BPM5)

Deterministic parser (ADR-0003) for the **long annual remittance series** the
NDRI Migration Atlas's Figure 13 trend is built from.

- **Source:** NRB "Trade and Balance of Payments" workbook
  (`Financial Data/nrb_dne_historical/Trade-and-Balance-of-Payments.xlsx`),
  sheet **`BOP 2000-`**, row **"Workers' remittances"**, unit *In Million Rupees*.
- **Output:** `_common.types.ParserResult` — one annual `StagingRowDraft` per
  fiscal year → indicator slug **`dne-remittance-workers-historical`**
  (`npr_million`, `annual`, confidence **B**).
- **Coverage:** FY **2000/01 → 2020/21** (21 points; AD→BS via +57, ADR-0013).

## The BPM5 ↔ BPM6 boundary (why a separate slug)

This is the **BPM5** "Workers' remittances" line — a *different concept* from the
modern **BPM6** "Personal transfers, Credit" that feeds `dne-remittance-inflow`
(parser `nrb_dne`). The BPM5 line ends at **FY 2020/21** (961,054.6 npr_million);
NRB switched to BPM6 presentation thereafter. The two **dovetail** at the
2020/21 → 2021/22 break to form the full long trend. Per the Data Continuity
Protocol we **never splice across the break** — each is its own labelled series.

## Run

```bash
# from scrapers/ on PYTHONPATH:
PYTHONPATH=scrapers python scrapers/nrb_remittance_history/parser.py \
  "Financial Data/nrb_dne_historical/Trade-and-Balance-of-Payments.xlsx" --verify
```

`--verify` prints the series span + reconciles the BPM5 endpoint
(FY2020/21 ≈ NPR 961 bn). Without `--verify` it emits the `ParserResult` JSON
(the `ParserOutputSchema` shape) on stdout, ready for the staging→approved
ingest.

## Verification

- **Real-file extraction** (manual, the authoritative check): FY2000/01 = 47,216.1
  → FY2020/21 = 961,054.6 npr_million, 21 points, including the FY2019/20 COVID
  dip — matches NRB's published historical remittance.
- **Unit tests** (`tests/`, programmatically-generated fixture — no committed
  binaries, per the nrb_dne convention): header detection, label match, AD→BS
  conversion, the row contract, fail-loud on missing sheet/row, idempotency.

## Ingest (deferred — operator step)

The series ingests through the standard indicator pipeline
(staging → validation → approved `approved_indicator_values`) once a populated
DB is available; the indicator is seeded in `scripts/seed-indicators.ts`. See
`docs/INGEST_RUNBOOK.md`.
