# mof_whitebook — MoF White Book foreign-aid parser

Deterministic Python parser (ADR-0003) for the MoF **"Source Book for Projects
Financed with Foreign Assistance"** (the *White Book* / वैदेशिक सहायता आयोजनाहरुको
स्रोत पुस्तिका) — the annual budget-book record of foreign aid (grants + loans)
entering Nepal, by development partner and by ministry. The "Money In" external-
financing story.

- **Source id:** `mof-whitebook-foreign-aid` (PROPOSED — registry row pending Mother)
- **Corpus:** `Financial Data/mof_documents/whitebook/`
- **Output:** ADR-0017 **dimensional facts** → `foreign_aid_facts`. Emits a
  `dimensional_rows` JSON array; no single-series `staging_rows`.
- **Ingest CLI:** `scripts/ingest-whitebook.ts`
  (`pnpm ingest:whitebook` — script line pending Mother, see below).

## What it extracts

The two clean English summary tables (stable 12-/13-column geometry):

| caption | `dimension_kind` | member |
|---------|------------------|--------|
| Development Partnerwise Summary (older: "Donor Summary") | `donor`  | development partner |
| Summary of Ministrywise Development Partners            | `sector` | ministry / budget head |

Two base measures per member (the headline grant/loan totals):

| base_indicator_slug  | source column | meaning |
|----------------------|---------------|---------|
| `foreign-aid-grant`  | Total Grant   | cash + reimbursable + direct-payment + commodity |
| `foreign-aid-loan`   | Total Loan    | loan direct-payment + reimbursable + cash |

- `dimension_value` = kebab slug of the member name; `dimension_label` = raw name.
- `unit` = **detected per page, emitted verbatim** (ADR-0011): `npr_lakh` for
  `(Rs. in '00000')` (FY2020/21); `npr_thousand` for `(NRs'000s)` / `( Rs. 000 )`
  (FY2015/16, FY2013/14, FY2014/15). **NOT normalised** — consumers must read it.
- `reporting_period_type` = `annual`; AD fiscal year read from the cover/caption
  ("Fiscal Year 2020/21"); BS via the +57 offset (ADR-0013): AD 2020/21 → BS 2077/78.
- `confidence_grade` = `B`.

The ministrywise table has an extra leading **"GoN Budget"** column, so its
Total-Grant/Total-Loan columns sit one position later than the donor table's; the
parser uses table-specific column offsets (`_DONOR_SPEC` / `_SECTOR_SPEC`).

Real-PDF runs (`status=success`, 0 errors):

| edition | facts | donor g/l | sector g/l | unit | BS FY | donor total |
|---------|------:|-----------|------------|------|-------|-------------|
| FY 2020/21 | 134 | 44 / 44 | 23 / 23 | npr_lakh     | 2077/78 | NPR 360.0 bn |
| FY 2015/16 | 144 | 46 / 46 | 26 / 26 | npr_thousand | 2072/73 | NPR 205.9 bn |
| FY 2013/14 | 154 | 54 / 54 | 25 / 25 | npr_thousand | 2070/71 | NPR 113 bn |
| FY 2014/15 | 174 | 62 / 62 | 25 / 25 | npr_thousand | 2071/72 | NPR 123 bn |

The summed per-donor grant + loan reconciles to the published **Total** row in
each edition, and the **donor total equals the sector total** in each edition (the
two summary tables are two views of the same aid). Both anchors are asserted by
integration tests. (FY2013/14 sector member count rose 23→25 in v0.2.1 — see the
wrapped-row note below.)

## Why these tables / known breakage modes

- The REAL summary tables co-occur with the unit annotation on the page; the
  Table-of-Contents page carries the captions but no unit annotation and yields no
  extractable 12-col table — so the parser requires **caption + detected unit** to
  gate a page, which excludes the ToC deterministically.
- **Grant/loan sub-components** (cash / reimbursable / direct-payment / commodity)
  are present and clean but **deferred** — the two Total columns are the headline
  story (ADR-0017). Project-level detail tables are deferred too.
- **Wrapped-name row merge** (`wrapped-name-row-dumped-into-col0`, fixed v0.2.1):
  when a member name wraps to a second visual line, pdfplumber sometimes fails to
  split that row into the column grid and dumps the WHOLE row into col 0 as one
  space-joined blob with the other cells empty. The parser (`_expand_merged_row`)
  detects this exact artifact (col 0 a code-led blob, other cells empty, a
  contiguous money-token run of length `cols − 2`) and reconstructs
  `[code, name, *values]` deterministically. This was the **FY2070/71 donor≠sector**
  flag (DATA_AUDIT §5 G3): two ministry rows — *Ministry of Science Technology and
  Environment* (331) and *Ministry of Federal Affairs and Local Development* (365) —
  were silently dropped, so the sector total read 95,934,658 instead of the printed
  **113,240,000** npr_thousand (= the donor total). The source itself is internally
  consistent (both printed Totals equal 113,240,000); this was purely a parse bug.
- **Preeti editions** (FY 2062/63, 2064/65, 2065/66, 2067/68): text layer is a
  legacy Preeti byte-map (e.g. `dGqfnout`), not Unicode. We do **not** transliterate
  Preeti (reverse-engineering a font byte-map — effectively the OCR ADR-0003 forbids).
- **A mislabelled CID-broken file** (`...White Book FY 2021-22_azz4yjf.pdf`) is
  actually the **Intergovernmental Fiscal Transfer** book (Devanagari, `(cid:N)`).
  Not a White Book; the parser refuses it.
- For any edition without a clean caption+unit summary table, the parser emits a
  typed `PageLayoutChanged` (and `PeriodAmbiguous` if a table is found but no
  "Fiscal Year YYYY/YY" label exists anywhere) and returns `status=failure` — a
  documented infeasibility, never a fabricated value.

## Tests

`tests/test_parser.py` exercises the deterministic core
(`extract_dimensional_rows`) against **synthesized** tiny donor (12-col) and sector
(13-col) tables — covering the GoN-Budget column offset, a preserved zero, a
dropped dash, Total-row exclusion, unit detection, FY detection, a
`ValueUnparseable` for an all-garbage row, and the **wrapped-name row recovery**
(`_expand_merged_row`) on the verbatim FY2070/71 sector blobs. The real multi-MB
PDFs are **not committed** (ADR-0003 / source profile); optional integration tests
run against the FY 2020/21 and FY 2070/71 PDFs when present (donor-Total
reconciliation + donor==sector reconciliation) and are skipped otherwise.

```
cd scrapers
PYTHONPATH=<worktree>/scrapers <venv>/python -m pytest mof_whitebook/tests -q
```

36 tests; green (32 unit + 4 real-PDF integration when the FY2020/21 and FY2070/71
PDFs are on disk).

## Pending Mother (RETURN items — not edited here per scope fence)

- `src/lib/db/schema/index.ts`: re-export `./foreign-aid-facts` (barrel).
- `drizzle-kit generate` + apply the `foreign_aid_facts` migration, then run the
  live ingest.
- `scrapers/pyproject.toml`: add `"mof_whitebook*"` to
  `[tool.setuptools.packages.find].include` and `"mof_whitebook/tests"` to
  `[tool.pytest.ini_options].testpaths`.
- `package.json` scripts: `"ingest:whitebook": "node --env-file=.env.local --conditions=react-server --import tsx scripts/ingest-whitebook.ts"`.
- `seed-source-registry.ts`: add the `mof-whitebook-foreign-aid` row (see the
  source profile / the worker's FOR-MOTHER notes).
