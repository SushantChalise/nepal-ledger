# NRB BFI XLSX layout versions

Schema-discovery notes for `scrapers/nrb_bfi/parser.py` v0.1.0.
Sampled three snapshots:

- **Oldest** — `Shrawan-2078-2.xlsx` (BS 2078 Shrawan, AD Aug 2021)
- **Middle** — `Asar_2080_Publish.xlsx` (BS 2080 Ashadh, AD Jul 2023)
- **Latest** — `Bhadau_2082_Publish.xlsx` (BS 2082 Bhadra, AD Sep 2025)

Plus the corpus end-anchor `Saun-2082-Publish.xlsx` (BS 2082 Shrawan, AD Aug 2025).

## Variant axes that matter

### Sheet count

- BS 2078 files: 14 sheets (C1..C14). Per-bank C15..C25 not yet published.
- BS 2080+ files: 25 sheets (C1..C25). Per-bank breakdowns C15..C25.

Impact: v0.1.0 only ingests C4..C7 which exist in every file. No version
gating required.

### Unit annotation in row 3

- BS 2078 files: row 3 is blank in C5..C7.
- BS 2079+ files: row 3 carries `Amt in Mn of Rs` once per block.

Impact: parser falls back to `NPR_million` default when row-3 unit cells
are blank, so both variants produce the same canonical unit.

### Period-column header text on the latest snapshot

The column immediately right of the three historical Mid-July anchors
varies by reporting month:

- `Asar / Ashadh` files → `Mid-June` / `Mid-July` (the FY-close pair).
- `Saun / Shrawan` files → `Mid-July` / `Mid-Aug`.
- `Bhadau / Bhadra` files → `Mid-Aug` / `Mid-Sept`.
- ... and so on through the calendar.

Impact: `_periods.py` recognises every English month abbreviation +
full name; v0.1.0 passes 51/51 files with 0 errors.

### Block-title cell content

Sometimes the row-2 title cell is truncated to ~60 chars by openpyxl's
read-only mode (e.g. `Statement of  Assets and Liabilities of Banks &
Financial In`). Detection in `_sheets._find_block_starts` therefore
uses substring matching on lowercase needles, not equality.

## Layout invariants v0.1.0 relies on

For every C4..C7 sheet in every file in the 51-file corpus:

- **C4** — bank-class header row holds the literals `Class "A"`,
  `Class "B"`, `Class "C"`, `Overall` (column C..G or D..G).
- **C5/C6/C7** — exactly 4 bank-class blocks side-by-side, with row 2
  containing the block title that includes the substring of one of:
  - `banks & financial in...` -> `system_total`
  - `commercial banks` -> `commercial`
  - `development banks` -> `development`
  - `finance companies` -> `finance`
- The "Mid-..." period headers live in row 4 of every observed file.
- Period years live in row 5.

A future BFI file that violates any of these will trigger a
`PageLayoutChanged` ParserError rather than silent miscoding.

## Deferred for v0.2.0

- Sheets C8..C25 (per-bank breakdowns).
- "% Change" columns (3 per block; currently dropped).
- Microfinance + infrastructure bank classes (not present in C5..C7;
  appear in C13..C14 deferred sheets).
