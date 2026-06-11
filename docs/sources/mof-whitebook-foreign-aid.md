# Source: Ministry of Finance — White Book (Source Book for Projects Financed with Foreign Assistance)

**source_id:** `mof-whitebook-foreign-aid`
**Status:** ACTIVE — source_registry seeded; FY 2062/63 (148 rows) + FY 2064/65 (136 rows) ingested 2026-06-11.
**Tier:** 1 (Money In — external financing spine)
**Registered at:** 2026-06-11 (seeded via `scripts/seed-source-registry.ts`)
**Last verified:** 2026-06-11 (FY 2062/63 + FY 2064/65 Preeti editions — donor==sector reconciliation ✅)

## What this is

The White Book ("Source Book for Projects Financed with Foreign Assistance" /
वैदेशिक सहायता आयोजनाहरुको स्रोत पुस्तिका) is MoF's annual budget-book record of foreign
aid — **grants and loans** — entering Nepal, broken out **by development partner
(donor)** and **by spending ministry (sector)**. It is the "Money In" external-
financing story: who funds Nepal, in what form (grant vs loan), to which
ministry. Published as an "Unofficial Translation (For Official Use Only)"
English edition alongside the budget.

## Publication

- URL: https://mof.gov.np/ (Budget / Source Book section)
- Frequency: annual (tabled with the budget, ~Jestha/Asar)
- Format: pdf
- Historical coverage in-repo: FY 2062/63 … FY 2020/21 (mixed encoding — see below)

## What we extract

Two clean English summary tables, both with a stable 12-/13-column geometry:

- **Development Partnerwise Summary** → `dimension_kind = donor`
- **Summary of Ministrywise Development Partners** → `dimension_kind = sector`
  (the ministrywise table has an extra leading "GoN Budget" column, so its
  value columns are offset by +1 vs the donor table)

Two base measures per dimension member (the headline grant/loan totals):

- `foreign-aid-grant` — **Total Grant** column (= cash + reimbursable + direct
  payment + commodity)
- `foreign-aid-loan` — **Total Loan** column (= loan direct-payment + reimbursable
  + cash)

> **UNIT (ADR-0011) — VARIES BY EDITION; carried verbatim, NOT normalised:**
> - FY 2020/21 : `(Rs. in '00000')` = Rs in 100,000 = **lakh** → `unit = npr_lakh`
> - FY 2015/16 / 2013/14 / 2014/15 : `(NRs'000s)` / `( Rs. 000 )` = Rs in 1,000 =
>   **thousand** → `unit = npr_thousand`
>
> The parser reads the annotation stamped on each summary-table page and emits the
> matching unit string. **Consumers must read `unit` before summing across
> editions.** Magnitude sanity (donor Total rows):
> - FY 2015/16: grants 110,929,407 + loans 94,964,704 thousand = **NPR 205.9 bn**
> - FY 2020/21: grants 605,277 + loans 2,994,993 lakh = **NPR 360.0 bn** (COVID-year
>   surge: IMF RCF, ADB-CARES, IDA DPC budget support all present)
> - FY 2013/14 ≈ NPR 113 bn; FY 2014/15 ≈ NPR 123 bn
> All in/around the NPR 100–250 bn/yr band for total annual assistance.

Period: `annual`. The AD fiscal year is read from the cover/caption ("Fiscal Year
2020/21") and mapped to BS via +57 on the lead year (ADR-0013): AD 2020/21 →
BS 2077/78. The AD start/end bound the BS-fiscal-year span (mid-Shrawan..mid-Ashadh).

## What we DEFER (documented infeasibility — never fabricated)

- **Grant/loan SUB-components** (cash / reimbursable / direct-payment / commodity)
  per member — present and clean, but out of scope for the first cut (the two
  Total columns are the headline story). A follow-up can add them on the same
  contract.
- **Project-level detail tables** (per-budget-head project lists) — large and
  heterogeneous; deferred.
- **CID-broken Preeti editions** — FY 2065/66, 2067/68 remain unverified; if their
  text layer is broken `(cid:N)` rather than valid Preeti bytes the parser will
  emit `status=failure`. FY 2062/63 and FY 2064/65 are **parseable and ingested**
  (donor==sector reconciliation ✅ on both — see "Recent ingests").
- **A mislabelled CID-broken file** — `Source Book  White Book FY 2021-22_azz4yjf.pdf`
  is actually the **Intergovernmental Fiscal Transfer** book (Devanagari, CID-broken,
  `(cid:N)` glyphs). Not a White Book; belongs to a different source.
- **FY 2016/17–2019/20 gap** — these editions are **not on mof.gov.np** (confirmed
  2026-06-11: site skips from FY 2015/16 directly to FY 2020/21). IECCD
  (ieccd.gov.np) was unreachable. Flag for manual re-acquisition.

The parser scans every page and emits typed `PageLayoutChanged` / `PeriodAmbiguous`
diagnostics for these, with `status=failure` — a documented infeasibility, not a
value.

## Provenance

- Confidence default: **B** — MoF "unofficial translation" budget source book;
  figures are budgeted/disbursement allocations revised across editions.
- License: gov-open
- Reporting period type: annual

## Known breakage modes

- `unit-annotation-varies-by-edition-lakh-vs-thousand` — the money unit is
  `(Rs. in '00000')` (lakh) in some editions and `(NRs'000s)` (thousand) in
  others. The parser detects it per page; never assume.
- `mislabelled-files-in-whitebook-folder` — at least one file in the corpus is a
  different document (intergovernmental transfer) under a White-Book-looking name.
  The parser refuses it (no clean summary table + unit) rather than mis-parsing.
- `donor-caption-varies` — newer editions caption the donor table "Development
  Partnerwise Summary"; older ones use a bare "Donor Summary". The parser matches
  both.
- `wrapped-name-row-dumped-into-col0` (fixed v0.2.1) — when a member name wraps to a
  second visual line, pdfplumber sometimes fails to split that row into the column
  grid and dumps the whole row into col 0 as one space-joined blob (other cells
  empty), silently dropping it. The parser (`_expand_merged_row`) detects this exact
  artifact and reconstructs `[code, name, *values]` deterministically (the value
  columns are the contiguous money-token run of length `cols − 2`). This was the
  **FY2070/71 donor≠sector** flag (DATA_AUDIT §5 G3): two ministry rows (codes 331
  *Science Technology and Environment* and 365 *Federal Affairs and Local
  Development*) were dropped, so the sector total read 95,934,658 instead of the
  printed **113,240,000** npr_thousand (= the donor total). The source is internally
  consistent — both the donor and sector printed Totals are 113,240,000 — so this
  was a parse bug, not a source-level difference.
- `preeti-editions-parseable-cid-editions-are-not` — FY 2062/63 and FY 2064/65
  are legacy Preeti/Siddhi font editions and ARE parseable by the parser's
  `_common/preeti.py` transliteration (ADR-0003 permits deterministic font-map
  reversal). CID-broken editions (`(cid:N)` glyphs) are still infeasible.

## Revision policy

Annual. Figures are budget-book allocations that may be revised across editions; a
revised edition appears as a new file. Re-ingest is idempotent (unique index +
`ON CONFLICT DO NOTHING`), and `source_document_id` is part of the natural key so a
revised edition's facts coexist with the prior edition's.

## Parser

- Path: `scrapers/mof_whitebook/parser.py` (underscore dir — Python-importable; the
  on-disk folder is NOT the hyphenated profile name)
- Version: 0.2.1
- Owner: Mother Opus (built by Sonnet worker, batch #12, 2026-06-07)
- Output: ADR-0017 dimensional facts → `foreign_aid_facts` (emits `dimensional_rows`)
- Tested against: 4 clean English editions in
  `Financial Data/mof_documents/whitebook/` + synthesized donor/sector table
  fixtures in `scrapers/mof_whitebook/tests/`. Bundled real-PDF integration target:
  `Source Book White Book FY 2020-21_dkjqgrt.pdf` (176 pp → 134 facts).
- Ingest CLI: `scripts/ingest-whitebook.ts` (`pnpm ingest:whitebook` — script line
  pending Mother)

## Archive policy

- Files stored under `$SOURCE_ARCHIVE_DIR/mof-whitebook-foreign-aid/<yyyy-mm-dd>/<sanitized-filename>`
  (local filesystem, [ADR-0006](../decisions/0006-local-storage-year1.md); Supabase
  Storage is wired when `SUPABASE_URL` is set instead).
- Hash + file URL recorded in `source_documents`. Never overwritten.

## Recent ingests

| Date       | Edition      | FY (AD)  | Rows | Status        |
|------------|--------------|----------|------|---------------|
| 2026-06-11 | BS 2062/63   | 2005/06  | 148  | ✅ reconciled |
| 2026-06-11 | BS 2064/65   | 2007/08  | 136  | ✅ reconciled |
