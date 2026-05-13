# Calendar and Periods Doctrine

Date confusion will kill this project if not handled at the schema level. Nepal uses Bikram Sambat (BS) officially; the world uses Gregorian (AD). Fiscal year runs Shrawan–Ashadh (mid-July to mid-July). NRB CMEFs reports "nine months" cumulatively. Monthly NCPI rows are labeled by mid-month (Chait, Falgun, Baisakh, …). Publication date ≠ reporting period. Reporting period start ≠ end.

**This document is the canonical reference for how dates and periods are stored, displayed, and queried.** Every indicator row, every story, every chart obeys it.

---

## Core Principle

> **Every temporal data point stores BOTH BS and AD representations, BOTH the reporting period AND the publication date, AND its period type. No shortcuts.**

This costs ~5 extra columns per indicator row. The cost of NOT doing this is bugs that take days to find and Fact Ledger claims that are wrong about *when*.

---

## Required Fields on Every `indicator_values` Row

```typescript
{
  // What the value reports
  reporting_period_type:      'monthly' | 'quarterly' | 'annual' | 'nine_months_cumulative' | 'year_to_date';
  reporting_period_bs:        string;   // e.g. "2082/83 Chait" or "FY 2082/83" or "FY 2082/83 9-month"
  reporting_period_ad_start:  Date;     // e.g. 2026-03-14 (start of Chait 2082)
  reporting_period_ad_end:    Date;     // e.g. 2026-04-12 (end of Chait 2082)

  // When the value was published
  publication_date_ad:        Date;     // e.g. 2026-05-08
  publication_date_bs:        string;   // e.g. "2083 Baisakh 25" — display only

  // Fiscal-year anchors (for grouping/charting)
  fiscal_year_bs:             string;   // "2082/83"
  fiscal_year_ad_label:       string;   // "2025/26" — for international display only

  // The value itself + provenance
  value:                      number;
  unit:                       string;   // "NPR_billion", "percent", "months_of_imports", etc.
  source_document_id:         string;   // FK → source_documents
  confidence_grade:           'A' | 'B' | 'C';
  revision_number:            number;   // 0 for first; increments on each revision
}
```

The `reporting_period_*` and `publication_date_*` fields are non-nullable. The `fiscal_year_*` fields are non-nullable. Skipping them at schema time is rejected at PR review.

---

## Nepali Fiscal Year (BS)

The Nepali fiscal year runs Shrawan 1 to Ashadh 31:

- **FY 2082/83** = Shrawan 2082 → Ashadh 2083 (i.e., mid-July 2025 → mid-July 2026 in AD)
- **FY 2083/84** = Shrawan 2083 → Ashadh 2084 (mid-July 2026 → mid-July 2027)

Labels we use everywhere:
- **Storage:** `fiscal_year_bs = "2082/83"` (4-digit start year, slash, 2-digit end year)
- **Display (Nepali):** `"आ.व. 2082/83"`
- **Display (English):** `"FY 2082/83"` or `"FY 2082/83 (2025/26)"` when international context demands it

### Nepali months (mid-month labels used in NRB data)

| BS month | AD approx start | AD approx end | Common transliteration |
|----------|-----------------|---------------|------------------------|
| Shrawan | mid-July | mid-Aug | Shrawan / Saun |
| Bhadra | mid-Aug | mid-Sep | Bhadra / Bhadau |
| Ashwin | mid-Sep | mid-Oct | Ashwin / Asoj |
| Kartik | mid-Oct | mid-Nov | Kartik / Kartika |
| Mangsir | mid-Nov | mid-Dec | Mangsir |
| Poush | mid-Dec | mid-Jan | Poush / Push |
| Magh | mid-Jan | mid-Feb | Magh |
| Falgun | mid-Feb | mid-Mar | Falgun / Phagun |
| Chait | mid-Mar | mid-Apr | Chait / Chaitra |
| Baisakh | mid-Apr | mid-May | Baisakh / Vaishakha |
| Jestha | mid-May | mid-Jun | Jestha / Jeth |
| Ashadh | mid-Jun | mid-Jul | Ashadh / Asar |

**Storage convention:** always use the canonical English transliteration in the BS month component (`Shrawan`, `Bhadra`, `Ashwin`, `Kartik`, `Mangsir`, `Poush`, `Magh`, `Falgun`, `Chait`, `Baisakh`, `Jestha`, `Ashadh`). Display can localize.

### "Nine months" reporting

NRB's CMEFs reports cumulative "nine-months" data — the FY 2082/83 nine-month report covers Shrawan through Chait (8 months actually, since CMEFs labels "9th month" as Chait). The `reporting_period_type` for these rows is `nine_months_cumulative`. The `reporting_period_ad_start` and `_end` cover the full nine-month span.

The first existing dataset (`CMEFs_Table_Nine-Months_2082.83`) is exactly this type.

---

## BS ↔ AD Conversion

Use a single, vetted conversion utility. Never inline a formula.

- **Library:** `nepali-date-converter` (npm) — small, well-tested, MIT licensed.
- **Wrapper:** `src/lib/dates/index.ts` provides `bsToAd(year, month, day): Date` and `adToBs(date: Date): { year, month, day }`.
- **Conversion is one-way per call.** Never round-trip — accumulated rounding causes off-by-one-day bugs.
- **Mid-month convention:** for indicators reported "Mid-Chait" we store the AD date as the 15th of the equivalent AD month (approximation). Where exactness matters (e.g., daily FCGO), convert the actual BS day.

---

## Period Type Definitions

| Type | Semantics | Example |
|------|-----------|---------|
| `monthly` | Single Nepali month | "Chait 2082" (mid-Mar to mid-Apr 2026) |
| `quarterly` | Three Nepali months. Q1 = Shrawan–Ashwin, Q2 = Kartik–Poush, Q3 = Magh–Chait, Q4 = Baisakh–Ashadh | "Q3 FY 2082/83" |
| `annual` | Full fiscal year, Shrawan–Ashadh | "FY 2082/83" |
| `nine_months_cumulative` | Shrawan–Chait (first nine months) of a fiscal year | "FY 2082/83 (9M)" |
| `year_to_date` | Shrawan to specified end month within an FY (less common) | "FY 2082/83 YTD Falgun" |
| `daily` | Single calendar day; rare (FCGO only) | "2026-04-12 / 2082-12-30" |
| `seasonal` | Crop season (Kharif/Rabi) | "Kharif 2082" |

---

## Display Rules

| Context | Format |
|---------|--------|
| English UI body text | "FY 2082/83 — Chait" or "Mid-Chait 2082 (mid-Mar 2026)" |
| Nepali UI body text | "आ.व. 2082/83 — चैत" |
| Chart axis label | "FY 2082/83" or "Chait '82" (short) |
| Table column header (English) | "FY 2082/83 Chait" |
| Table column header (Nepali) | "चैत 2082/83" |
| Fact Ledger claim metadata | "Published: Baisakh 25, 2083 BS (May 8, 2026 AD). Period: FY 2082/83 9M (Shrawan–Chait)." |

Display logic lives in `src/lib/dates/format.ts`. Never inline date strings in components.

---

## Publication Date vs Reporting Period

A common Fact Ledger error: confusing *when a value was reported* with *when it was published*.

Example: NRB CMEFs for the FY 2082/83 nine-month period reports on Shrawan 2082 → Chait 2082 (mid-July 2025 → mid-April 2026). The report itself was published around Baisakh 25, 2083 (May 8, 2026).

- `reporting_period_*` fields → the time the value describes.
- `publication_date_*` fields → the time the data was released.

**Charts and Pulse cards show the reporting period.** **Fact Ledger metadata shows both.** **Newsletter copy can say "as of Chait 2082 (released May 2026)."**

---

## Revisions

When NRB or NSO revises a historical value:

1. Insert a NEW row in `indicator_values` with the same `reporting_period_*` and the new value, with `revision_number = prior + 1`.
2. The prior row is NEVER updated or deleted. Revisions are append-only.
3. Queries default to "latest revision per period" via a view: `indicator_values_latest`.
4. The indicator page shows the revision trail when the user expands the "history" panel.

See [DATA_PIPELINE.md](DATA_PIPELINE.md) for the revision-detection logic in the parser pipeline.

---

## Forbidden Patterns

- Storing dates as strings without parsing. Always `Date` (Postgres `timestamptz`) for AD, structured string for BS.
- Computing BS from AD inline anywhere except the `src/lib/dates/` wrapper.
- Using `new Date()` for "today" without a clock injection in tests. Tests pass an explicit `now`.
- Charting with raw mid-month dates and expecting axis labels to look right — always use the formatter.
- Saying "this month" in editorial copy without naming the BS month. Ambiguity rots a Fact Ledger fast.

---

## Cross-Reference

- Drizzle schema for these fields: `src/lib/db/schema/indicators.ts` (Day 4–10).
- Date utilities: `src/lib/dates/` (added with the schema).
- Source-registry per-source reporting period type: [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md).
- Display formats in UI: `src/lib/dates/format.ts`.
- Tests: `src/lib/dates/tests/` — required cases include FY boundary, leap-year edge, nine-month cumulative.
