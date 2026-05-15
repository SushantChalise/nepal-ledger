# Worker P3 follow-up — CBS NPHC 2021 remaining 84 CSVs

**Status:** queued
**Predecessor:** the initial P3 PR shipped the two-mode reader + parser
infrastructure + a first batch of 5 CSVs (`Hhld01`, `Hhld02`, `Hhld05`,
`Hhld10`, `Indv01`).
**Source:** [docs/sources/cbs-nphc-2021.md](../sources/cbs-nphc-2021.md)
**Audit:** [docs/research/cbs-nphc-2021-audit.md](../research/cbs-nphc-2021-audit.md)

---

## What's left

The 84 CSVs not in the first batch, grouped by topic. Each batch should be
its own PR with diff cap ≤ 500 source lines: roughly one new
`_TABLE_REGISTRY` entry + one new `_TABLE_VALUE_COLUMNS` entry per CSV,
plus one fixture and at least one parametric test row per CSV.

### Batch B — household housing remainder (Mode A + Mode B mix, 8 CSVs)

| CSV stem                        | Mode | Family               |
|---------------------------------|------|----------------------|
| `Hhld03_OuterwallOfHouse`       | A    | `household_housing`  |
| `Hhld04_RoofOfHouse`            | A    | `household_housing`  |
| `Hhld06_SourceOfDrinkingWater`  | B    | `household_facility` |
| `Hhld07_TypeOfCookingFuel`      | B    | `household_facility` |
| `Hhld08_SourceOfLighting`       | B    | `household_facility` |
| `Hhld09_TypeOfToiletUsed`       | B    | `household_facility` |
| `Hhld11_FemaleOwnershipOfFixedAsset` | B | `household_economic` |
| `Hhld12_SmallScaleBusiness`     | B    | `household_economic` |

### Batch C — household mortality & migration (Mode B, ~10 CSVs)

`Hhld13_HouseholdHavingDeath` through `Hhld23_AbsentPopnByLevelOfEdu`.
These include long-format files with an `agegrp` dimension (e.g.
`Hhld14_NumberOfDeathBySex`) — the parser will need a small extension to
preserve the breakdown axis as part of the indicator slug.

### Batch D — individual demographics core (Mode B, ~10 CSVs)

`Indv02..Indv11` (size, age bands, household head, relationship,
nationality, marital status, age at first marriage). These are mostly long
format and will exercise the long-format handling.

### Batch E — individual education (Mode B, ~6 CSVs)

`Indv16..Indv21`. Disability is one-off; the rest are education-domain.

### Batch F — individual migration (Mode B, ~6 CSVs)

`Indv22..Indv30` range (place of birth, previous residence, duration).

### Batch G — individual economic & fertility (Mode B, ~10 CSVs)

`Indv31..Indv50` range. Industry / occupation / activity status / fertility.

### Batch H — Indv56 + the wide-table tail (Mode B, ~10 CSVs)

`Indv51..Indv71`. `Indv56_PopulationByIndustry` (the 8.5 MB widest file)
needs special attention: 23 columns including a full age-band breakdown.

### Batch I — DEGURBA XLSX (out of scope for the initial follow-up)

`degurba-report/DegurbaUrbanRural.xlsx` is the sole ward-grain file in the
corpus. It requires a *separate* parser (`scrapers/cbs_degurba_2021/`) and
a separate `entities.kind` lookup (`ward` instead of `local_level`).
Schedule after Batch H.

### Batch J — Listing XLSX/XLS (deferred per audit §6)

The 7 `Listing*` files publish percentages only. They can only be
meaningfully ingested AFTER their corresponding `Hhld*` denominator files
are loaded so the percentages can be back-multiplied into counts. Schedule
after Batches B and C.

---

## Per-batch acceptance criteria

For each batch:

- [ ] One fixture per new CSV (≤ 10 rows each, schema-faithful)
- [ ] Extend `_TABLE_REGISTRY` and `_TABLE_VALUE_COLUMNS`
- [ ] Parametric test row per new CSV in `test_parser.py`
- [ ] Source profile updated with the new batch list
- [ ] Ingest script invocation tested end-to-end with `--dry-run`
- [ ] `pnpm typecheck && pnpm lint && pnpm test` green
- [ ] `pytest scrapers/cbs_nphc/tests` green
- [ ] Diff cap ≤ 500 source lines

## Open questions for Mother before Batch B starts

1. The `Indv01` audit note flagged 830 palika-level rows vs the canonical
   753. The parser currently treats every non-aggregate row as a palika;
   if the extra 77 rows are urban/rural sub-rollups within a palika, the
   parser will emit `Other` errors on duplicate `(entity, indicator)`
   keys. Decide before Batch D whether to (a) filter the sub-grain rows
   out, (b) split them into a secondary fact table, or (c) treat them as
   a separate ward-like entity kind.
2. The long-format files (`Hhld14`, `Indv03`, etc.) carry an `agegrp` or
   `cause` dimension. The current slug convention `<table>-<column>`
   collapses this axis. Decide whether to (a) extend the slug to
   `<table>-<dim>-<col>` or (b) move the dimension into a structured
   sidecar (`census_fact_breakdowns`).
