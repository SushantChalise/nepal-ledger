# dofe_migrant_workers — DoFE migrant-worker permit-counts parser

Deterministic parser (ADR-0003: pure `openpyxl`, no LLM, no network,
byte-identical output for identical input) that extracts **Department of Foreign
Employment (DoFE) labour-permit COUNTS** from the NRB
`Migrant-Workers-Remittance.xlsx` workbook into rows matching the
`migration_permit_facts` schema (**ADR-0026**).

> The source filename says "Remittance" but every sheet holds migrant-worker
> permit **counts** (headcount of permits issued), not rupees.

This is **parser + verification + test only** — it does **not** ingest to any DB.
The parser's stdout is the JSON the (future) typed ingest orchestrator consumes;
its rows are shaped to satisfy `MigrationPermitFactInputSchema`
(`src/lib/ingestion/migration-permit-types.ts`).

## Source layout (three sheets, verified on the real file)

| sheet | cut | col0 | output dimension |
|---|---|---|---|
| `district` | permits by **origin district** | district name (e.g. `Achham`) | `originDistrict` |
| `Country` | permits by **destination country** | country name (e.g. `Afghanistan`) | `destinationCountry` |
| `Migrant Worker` | monthly New / Renew / Total outflow series | AD month date | `permitCategory` (`new_individual` / `reentry`) |

The two wide sheets share a 3-level header:

```
r2  : SPARSE AD fiscal-year banner — one "2021/22" label at each 36-col block head
r3  : month labels — "Mid-<AD-month>" at each 3-col group's ANCHOR column
      (a stray BS month name sometimes sits in the +1 / Female slot — ignored)
r4  : "Male" / "Female" / "Total" repeating per 3-col group
r5+ : one row per district / country (col0 = name)
```

Within a month group: **anchor = Male, anchor+1 = Female, anchor+2 = Total**.
A trailing `Total` national-aggregate row (and an all-zero `Nepal` placeholder)
are excluded as dimensions; footnote rows are skipped. The `total` sex value is
the explicit **Total column we read** — never a sum the parser computes.

## Calendar (ADR-0013)

- **Fiscal year:** the sheet's AD fiscal year `2021/22` → BS `2078/79` by **+57**
  on the start year (same convention as `scrapers/nrb_remittance_history`).
- **Month:** per the source's own note, *"August corresponds to Shrawan"*, so
  `Mid-Aug → 1 (Shrawan)`, `Mid-Sep → 2 (Bhadra)`, …, `Mid-Jul → 12 (Ashar)`.
  Detected from the `Mid-<AD-month>` header at each group anchor (abbreviated or
  full spelling). The `Migrant Worker` sheet keys on an AD calendar date and maps
  via the inverse of the same Aug-anchored cycle.

We key month numbering off the clean `Mid-<AD-month>` AD labels rather than the BS
month names in r3, because the BS names sit one column off (in the Female slot)
and are mislabelled in places (`Magh` repeats). The `Mid-XXX` labels sit exactly
at the group anchors and reconcile to the permit (see below).

## Output row shape

One JSON object per non-empty cell. Every dimension this cut does not specify is
`null` (marginal/aggregate), per ADR-0026:

```json
{ "fiscalYearBs": "2078/79", "monthNum": 1,
  "destinationCountry": null, "destinationRegion": null,
  "originDistrict": "Achham", "skillClass": null, "permitCategory": null,
  "sex": "total", "permits": "24", "unit": "permits", "sourceSheet": "district" }
```

`permits` is a non-negative integer **string**; blank / non-numeric / fractional
cells are skipped (counts are never fabricated). `originDistrict` /
`destinationCountry` carry the **name string** — the ingest CLI resolves the name
to `origin_entity_id` later; the parser invents no UUIDs.

## Reconciliation gate (the correctness proof)

For a given `(fiscalYearBs, monthNum)`, the **sum of district `total` permits** ==
the **sum of country `total` permits** == the `Migrant Worker` sheet's
`Total Worker's Outflow` (New + Renew) for that month — all three are the same
national monthly outflow. Verified on the real file:

| FY (BS) | month | district | country | migrant | |
|---|---|---|---|---|---|
| 2078/79 | 1 (Mid-Aug) | 25,428 | 25,428 | 25,428 | exact |
| 2078/79 | 2 (Mid-Sep) | 36,040 | 36,040 | 36,040 | exact |
| 2078/79 | 3 (Mid-Oct) | 39,671 | 39,671 | 39,671 | exact |

Across all 51 fully-populated months, **district == country exactly in 46**; the
remaining handful differ by ≤6 permits (source rounding). **One** latest-FY month
(`2082/83` M2) is materially off because the two wide sheets populate a different
number of trailing months in the in-progress FY — a faithfully-reproduced source
artifact, not a parse error. The early, complete months reconcile to the exact
permit and are asserted with zero tolerance in the test.

## Usage

```bash
# JSON to stdout (the orchestrator input)
python scrapers/dofe_migrant_workers/parser.py <xlsx>

# Diagnostics + reconciliation table to stderr
python scrapers/dofe_migrant_workers/parser.py <xlsx> --verify
python scrapers/dofe_migrant_workers/parser.py <xlsx> --reconcile
```

Real-file extraction (current source): **~44,891 rows** —
district 11,820 · Country 32,752 · Migrant Worker 319.

## Tests

```bash
# run from the scrapers/ directory (pytest rootdir)
python -m pytest dofe_migrant_workers/tests/test_parser.py
```

Tests run against a committed copy of the real workbook in `tests/fixtures/`
(~270 KB) — the same real-file-fixture convention `nrb_dne` uses.
