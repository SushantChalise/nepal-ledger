# Source: Ministry of Finance — White Book (Source Book for Projects Financed with Foreign Assistance)

**source_id:** `mof-whitebook-foreign-aid`
**Status:** PROPOSED — registry row pending Mother (see "FOR MOTHER" / the parser docstring). Parser v0.1.0 built + run against 4 clean English editions.
**Tier:** 1 (Money In — external financing spine)
**Registered at:** _pending Mother seeds the row_
**Last verified:** 2026-06-07 (parser built; FY2015/16, FY2020/21, FY2013/14, FY2014/15 parse with `status=success`, 0 errors)

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
- **Preeti-encoded editions** — FY 2062/63, 2064/65, 2065/66, 2067/68. Their text
  layer is a legacy Preeti font byte-map (e.g. `dGqfnout` = "मन्त्रालयगत"), not
  Unicode. Un-mapping it is reverse-engineering a font (the OCR/translit ADR-0003
  forbids).
- **A mislabelled CID-broken file** — `Source Book  White Book FY 2021-22_azz4yjf.pdf`
  is actually the **Intergovernmental Fiscal Transfer** book (Devanagari, CID-broken,
  `(cid:N)` glyphs). Not a White Book; belongs to a different source.

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
- `preeti-and-cid-editions-unparseable` — pre-2013 editions render in Preeti/CID;
  deferred (ADR-0003).

## Revision policy

Annual. Figures are budget-book allocations that may be revised across editions; a
revised edition appears as a new file. Re-ingest is idempotent (unique index +
`ON CONFLICT DO NOTHING`), and `source_document_id` is part of the natural key so a
revised edition's facts coexist with the prior edition's.

## Parser

- Path: `scrapers/mof_whitebook/parser.py` (underscore dir — Python-importable; the
  on-disk folder is NOT the hyphenated profile name)
- Version: 0.1.0
- Owner: Mother Opus (built by Sonnet worker, batch #12, 2026-06-07)
- Output: ADR-0017 dimensional facts → `foreign_aid_facts` (emits `dimensional_rows`)
- Tested against: 4 clean English editions in
  `Financial Data/mof_documents/whitebook/` + synthesized donor/sector table
  fixtures in `scrapers/mof_whitebook/tests/`. Bundled real-PDF integration target:
  `Source Book White Book FY 2020-21_dkjqgrt.pdf` (176 pp → 134 facts).
- Ingest CLI: `scripts/ingest-whitebook.ts` (`pnpm ingest:whitebook` — script line
  pending Mother)

## Archive policy

- All downloaded files stored in Supabase Storage bucket `source-archive`
  ([ADR-0004](../decisions/0004-supabase-storage-instead-of-r2.md)) under key
  `mof-whitebook-foreign-aid/<yyyy-mm-dd>/<original-filename>`.
- Hash + downloaded URL recorded in `source_documents`. Never overwritten.

## Recent ingests

_Auto-populated once `parser_runs` is wired to a monitoring view._
