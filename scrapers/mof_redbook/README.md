# mof_redbook — MoF Red Book (annual budget) parser

Deterministic Python parser (ADR-0003) for the MoF **"Estimates of Expenditure"
/ व्यय अनुमानको विवरण (रातो किताब — the *Red Book*)** — Nepal's annual federal
budget: the appropriation each ministry / budget head is PLANNED to spend, split
recurrent vs capital. The "what the government plans to spend" counterpart to
FCGO's audited actuals (Money Out pillar / Budget Watch).

- **Source id:** `mof-budget-redbook` (already registered in
  `seed-source-registry.ts`, status `paused` — Mother flips to `active` on first
  live ingest; see "Pending Mother" below)
- **Corpus:** `Financial Data/mof_documents/redbook/` (21 editions, BS 2059–2081/82)
- **Output:** ADR-0015 **dimensional facts** → `dne_facts`. Emits a
  `dimensional_rows` JSON array; no single-series `staging_rows`.
- **Ingest CLI:** `scripts/ingest-redbook.ts`
  (`pnpm ingest:redbook` — script line pending Mother, see below).

## What it extracts

The clean **appropriation (विनियोजन) summary** (खण्ड-१) of the one parseable
edition — **"Red Book Central 2074-75"** (BS 2074/75, PDF pages 25-30). Each row
is a अनुदान संख्या / appropriation head (mostly ministries; also constitutional
bodies, provinces `701`, local-level transfers `801`).

Three base measures per budget head (the FY0 appropriation columns):

| base_indicator_slug            | source column            | meaning |
|--------------------------------|--------------------------|---------|
| `budget-allocation-total`      | जम्मा रकम                | total appropriation |
| `budget-allocation-recurrent`  | चालु खर्च                 | recurrent |
| `budget-allocation-capital`    | पूँजीगत तथा वित्तीय व्यवस्था | **capital AND financial provision** (the summary fuses them in one column — consumers must read it as capital+financial, NOT capital alone) |

- `dimension_kind = budget-head`; `dimension_value` = kebab of **`<code>-<name>`**
  (the federal appropriation code prefixes the slug so two heads never collide on
  a glyph-mangled Devanagari name — ADR-0011 "identity from the code"); raw name
  kept as `dimension_label`.
- `unit` = **detected per page, emitted verbatim** (ADR-0011): `npr_thousand` for
  the `(रू.हजारमा)` annotation (हजार = thousand). **NOT normalised.**
- `reporting_period_type = annual`; BS fiscal year from the cover (`2074/75`);
  `fiscal_year_ad_label` = `2017/18` (BS − 57, ADR-0013).
- `confidence_grade = B` — budget ESTIMATES (plans, revised across the year and
  superseded by FCGO actuals), not audited outturn.

Real-PDF run (`Red Book Central 2074-75`):

| metric | value |
|--------|------:|
| status | success |
| budget heads | 57 |
| dimensional rows | 171 (57 heads × 3 measures) |
| parser errors | 0 |
| unit | `npr_thousand` |
| BS FY | 2074/75 |
| Σ `budget-allocation-total` | 1,195,378,131 thousand = **NPR 1,195.4 billion** |

Magnitude reconciliation (ADR-0011 Decision 2): the summed per-head total
appropriation equals the published appropriation-from-Consolidated-Fund grand
total (जम्मा row = NPR 1,195.4 bn); plus the charged-fund summary (NPR 83.6 bn)
= NPR 1,279.0 bn — the published FY 2074/75 budget (~NPR 1.28 trillion). A second
structural anchor: every parsed head satisfies **total == recurrent + capital**
(asserted by a test on both synthesized and real data — 57/57 heads, 0
mismatches on the real PDF).

## Why text-line regex, not `extract_tables`

The summary table's `page.extract_text()` is clean and stably ordered — each
budget-head row is one line `<code> <name> <8 numbers>` — whereas
`page.extract_tables()` mis-merges the चालु/पूँजीगत sub-rows and shifts columns.
We anchor on the line geometry (exactly like `fcgo_consolidated` anchors on
prose). The 8 trailing numbers per row are, in source order: FY-2 actual,
FY-1 revised, **FY0 total**, **recurrent**, **capital+financial**, then the
source split (GoN / foreign grant / foreign loan). We emit the three FY0 budget
measures; prior-year and source-split columns are deferred.

## Page gating (the look-alike-table traps)

Gated on two glyph-reordering-survivable anchors plus one negative anchor
(verified against the real `extract_text()` output — the 2074-75 Devanagari
extracts with conjunct reordering and `�` replacement glyphs, so literal
"विनियोजन"/"सारांश" do **not** match):

- positive `योजन` — the stable tail of "विनियोजन" (appropriation); excludes the
  **charged (व्ययभार) summary** on page 8 (no `योजन`).
- positive `जम्मा रकम` — the total-amount column caption; excludes the detailed
  शीर्षकगत section (total column is "जम्मा बजेट").
- negative `तलु नामा` — "तुलनामा" (growth comparison), unique to the **अनुसूची-१
  functional-classification annex** (~page 600+) which reuses the same जम्मा-रकम
  / चालु-खर्च captions and code-led ministry rows but is a different cut with 10
  number columns. Belt-and-suspenders: the row regex also requires **exactly 8**
  number columns, which independently rejects the 10-column annex rows.

## Known breakage modes / why one edition only

The 21-edition corpus splits four ways by text-layer encoding; **only "Red Book
Central 2074-75" is clean Devanagari-Unicode with a segmentable summary**:

- **Broken-Unicode / glyph substitution** (BS 2069/70-2072/73): a defective
  embedded-font ToUnicode map reorders conjuncts and swaps glyphs (header
  "(रू. हजारमा)" → "(रू. हजायभा)"); digits survive but labels are corrupted and
  columns do not segment. **Deferred** (no font reverse-engineering, ADR-0003).
- **CID-broken** (BS 2073/74, 2076, 2077, 2078/79, 2079/80, 2080/81, 2081/82):
  `(cid:N)` glyphs, no usable ToUnicode — the recent "plan now" editions are all
  here. **Deferred** (no OCR, ADR-0003).
- **Legacy Preeti** (BS 2059-2067/68): Preeti font byte-map, not Unicode.
  **Deferred.**

For any edition without a clean appropriation-summary page, the parser emits a
typed `PageLayoutChanged` (and `PeriodAmbiguous` if a summary is found but no
`YYYY/YY` cover label) and returns `status=failure` — a documented infeasibility,
never a fabricated value. When MoF re-publishes a clean-Unicode Red Book the same
anchors should pick it up unchanged.

## Tests

`tests/test_parser.py` exercises the deterministic core
(`extract_dimensional_rows`) against **synthesized** text-line fixtures that
reproduce the real summary geometry (code-led rows + चालु/पूँजीगत sub-rows + a
जम्मा total row): three-measures-per-head, the total==recurrent+capital invariant,
a preserved real `0` capital, total-row exclusion, sub-row exclusion, the
10-column annex rejection (via the exact-8 guard), unit + FY detection, and the
no-silent-failure guard — an **invariant violation** (total ≠ recurrent + capital,
i.e. mis-segmented columns) surfaces a typed `ValueUnparseable` and skips the row.
The real multi-MB PDF is **not committed** (ADR-0003 / source profile); four
optional integration tests run against the FY 2074/75 PDF when present (head
count, grand-total magnitude reconciliation, the per-head invariant, and CLI JSON)
and are skipped otherwise.

```
cd scrapers
PYTHONPATH=<worktree>/scrapers <venv>/python -m pytest mof_redbook/tests -q
```

## Pending Mother (RETURN items — not edited here per scope fence)

- `seed-source-registry.ts`: the `mof-budget-redbook` row already exists — flip
  `status: 'paused'` → `'active'` on first live ingest. **Also reconcile
  `confidenceDefault`**: it is currently `'A'`, but the Red Book is budget
  ESTIMATES (plans), so the parser emits `'B'`; recommend the registry default be
  changed to `'B'` to match (and to differ from FCGO's audited-actuals `'A'`).
- `package.json` scripts: add
  `"ingest:redbook": "node --env-file=.env.local --conditions=react-server --import tsx scripts/ingest-redbook.ts"`.
- `scrapers/pyproject.toml`: add `"mof_redbook*"` to
  `[tool.setuptools.packages.find].include` and `"mof_redbook/tests"` to
  `[tool.pytest.ini_options].testpaths`.
- No schema/migration: reuses `dne_facts` (ADR-0015) — nothing to generate.
