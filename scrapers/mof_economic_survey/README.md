# mof_economic_survey — MoF Economic Survey statistical-annex parser

Deterministic Python parser (ADR-0003) for the **Economic Survey** (आर्थिक
सर्वेक्षण), the Ministry of Finance's canonical annual macro compendium.

- **Source id:** `mof-economic-survey-annual` (registered; `status: active`,
  `ingestionMode: reference_only`)
- **Corpus:** `Financial Data/mof_documents/economic_survey/` (3 editions)
- **Output:** `_common` `ParserResult` with `staging_rows` (same contract as
  `fcgo_consolidated`).
- **Ingest CLI:** `scripts/ingest-economic-survey.ts`
  (`pnpm ingest:economic-survey` — script line pending Mother, see below).

## What it extracts (ADR-0016)

The English 2023/24 edition has **three** encoding zones; only a subset is
clean. This parser scopes to the single highest-value clean table —
**Annex 6.1: Number of Workers having Foreign Employment Permit** (a clean
`Fiscal Year | Female | Male | Total` matrix). Labour migration is the front-end
of Nepal's remittance economy — directly on-mission. Three single-series
indicators, one value per **full** fiscal year (unit `count`):

| indicator slug | source column |
|----------------|---------------|
| `economic-survey-foreign-employment-permits-total`  | Total  |
| `economic-survey-foreign-employment-permits-female` | Female |
| `economic-survey-foreign-employment-permits-male`   | Male   |

- `reporting_period_type` = `annual`; the source labels rows by AD fiscal year
  (`2022/23`), mapped to BS via +57 (ADR-0013): AD 2022/23 → BS 2079/80.
- `confidence_grade` = `B` (PDF table extraction).
- Cumulative rows ("Upto July 2015", "Upto Mid March 2024") and the partial,
  starred current-year row ("2023/24*") are **skipped** — not full annual values.
- Real-PDF dry-run (EN 2023/24): **24 rows** = 8 full fiscal years (2015/16–
  2022/23) × 3 measures, `status=partial`. ADR-0011 magnitude check: FY2022/23
  total = 494,224 permits (right order for Nepal); Female + Male = Total ✓.

Extraction is **anchor-based**: the parser finds Annex 6.1 by its caption +
`Fiscal Year/Female/Male/Total` header, so the page number is never hard-coded.

## What it DEFERS (documented breakage modes)

Page numbers are 0-based pdfplumber indices for the EN edition.

- **RTL-mirrored MACRO annex (EN, pp 299–303 + 313+).** The "Macroeconomic
  Indicators" summary and numbered Annex 1.1… macro tables (GDP/GVA/prices/
  fiscal/trade) are free of `(cid:N)` but right-to-left mirrored: every cell is
  character-reversed (GDP `8.4075` = "5704.8" reversed), the column order is
  reversed (row-label column lands LAST), the row order is reversed, and
  multi-line labels are word-reversed AND line-wrap-fragmented. Numbers decode by
  string-reversal (`8.4075`→`5704.8` ⇒ nominal GDP ≈ NPR 5.7 trillion, ADR-0011
  band ✓) but the label↔value geometry is not deterministically reconstructable;
  un-mirroring is the reverse-engineering ADR-0003 forbids. **Deferred** — this
  is where the brief's headline GDP/inflation/revenue series live. The parser
  emits a typed `PageLayoutChanged` naming the page ranges.
- **CID-broken narrative chapters (EN, pp ~3–298) and the entire Nepali editions'
  annex.** `(cid:N)` glyphs, no ToUnicode map → gibberish. Not parseable without
  OCR (forbidden, ADR-0003). The parser emits a typed `EncodingError`. The two
  Nepali editions (2080-81, 2081-82) therefore have **no clean Annex 6.1** and
  return `status=failure` with a `NoCleanAnnexTable` error — a documented
  per-edition infeasibility.
- **The other ~10 clean social-sector annex tables (EN: hotels/Annex 8.14,
  medical specialists/Annex 11.7, education/Annex 11.x).** Genuinely clean but
  with heterogeneous merged-cell / multi-row-header geometry; a robust extractor
  spanning them would exceed the ≤300-line diff budget and be fragile.
  **Deferred** as a documented follow-up (coordinate-based per-table extraction).

## Status semantics

- `partial` — Annex-6.1 rows extracted AND macro/CID pages deferred (the EN
  outcome).
- `failure` — Annex 6.1 absent (the Nepali editions: CID-broken annex) →
  documented infeasibility for that edition; no values fabricated.

## Tests

`tests/test_parser.py` exercises the deterministic core
(`extract_foreign_employment_rows` + `_full_year_lead` / `_parse_count` /
`_ad_fy_to_bs_start` + the diagnostic `classify_annex_text`) against a
**synthesized** Annex-6.1 table mirroring the real page-405 geometry (full-year
rows, cumulative + starred rows that must be skipped, a preserved zero, a dropped
blank, a typed `ValueUnparseable`), plus an ADR-0011 magnitude check. Optional
integration tests run the full `parse` (and the `__main__` CLI) against the real
PDFs when present (EN → `partial` with Annex-6.1 rows + deferral errors; Nepali
editions → documented `failure`); skipped otherwise so CI stays green.

```
cd scrapers
PYTHONPATH=<worktree>/scrapers <venv>/python -m pytest mof_economic_survey/tests -q
```

## Pending Mother (RETURN items — not edited here per scope fence)

- `scrapers/pyproject.toml`: add `"mof_economic_survey*"` to
  `[tool.setuptools.packages.find].include` and `"mof_economic_survey/tests"` to
  `[tool.pytest.ini_options].testpaths`.
- `package.json` scripts:
  `"ingest:economic-survey": "tsx scripts/ingest-economic-survey.ts"`.
- `seed-indicators.ts`: add the **three** Annex-6.1 slugs (Total/Female/Male) —
  see the worker report for the exact rows.
- `seed-source-registry.ts`: the `mof-economic-survey-annual` row is already
  `status: 'active'` (`ingestionMode: reference_only`). **No flip needed**
  (the headline macro series remain deferred; only the Annex-6.1 labour series is
  extracted). Optionally append a note that Annex 6.1 is now parsed (ADR-0016).
