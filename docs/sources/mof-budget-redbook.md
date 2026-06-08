# Source: Ministry of Finance — Red Book (Estimates of Expenditure / annual budget)

**source_id:** `mof-budget-redbook`  
**Status:** paused (parser landed for the FY 2074/75 appropriation summary; flip to `active` on first live ingest — pending Mother)  
**Tier:** Tier 4  
**Registered at:** 2026-05-14  
**Last verified:** 2026-06-08 (parser PR — appropriation summary, "Red Book Central 2074-75" edition)

> Parser PR landed: `scrapers/mof_redbook/` emits ADR-0015 dimensional facts
> (dimension = budget head) from the **appropriation (विनियोजन) summary** (खण्ड-१)
> of the clean-Unicode "Red Book Central 2074-75" edition. Ingest via
> `scripts/ingest-redbook.ts` → `dne_facts`.

## Publication

- URL: https://mof.gov.np/
- Frequency: annual
- Format: pdf
- Reporting period type: annual
- Requires table extraction: yes

## Provenance

- Confidence default (registry): A — **but the parser emits `B`** (see Notes:
  Red Book figures are budget ESTIMATES/plans, not audited actuals; recommend the
  registry default be reconciled to `B`).
- License: gov_open
- Ingestion mode: manual_upload

## Notes

Budget Watch / Money Out pillar. In-repo corpus at
`Financial Data/mof_documents/redbook/` (21 editions, BS 2059–2081/82). The Red
Book is the "what the government PLANS to spend" counterpart to FCGO's audited
outturn.

### Extracted indicators (ADR-0015 dimensional, `dne_facts`)

From the **appropriation (विनियोजन) summary** (खण्ड-१, PDF pages 25-30) of the
"Red Book Central 2074-75" edition
(`Red Book Central 2074-75_20170530083940_00lqgwe.pdf`):

| base_indicator_slug           | source column               | unit          | confidence |
|-------------------------------|-----------------------------|---------------|:----------:|
| `budget-allocation-total`     | जम्मा रकम (total)            | `npr_thousand`| B          |
| `budget-allocation-recurrent` | चालु खर्च (recurrent)         | `npr_thousand`| B          |
| `budget-allocation-capital`   | पूँजीगत तथा वित्तीय व्यवस्था | `npr_thousand`| B          |

`dimension_kind = budget-head`; `dimension_value` = kebab of `<code>-<name>`
(the federal appropriation code prefixes the slug — ADR-0011 identity-from-code);
`reporting_period_type = annual`; BS FY 2074/75 (AD 2017/18). Real-PDF run:
57 budget heads → 171 dimensional rows (`status=success`, 0 errors).

**Capital column caveat:** `budget-allocation-capital` is **capital AND financial
provision** combined — the Red Book summary fuses पूँजीगत + वित्तीय व्यवस्था in a
single column. Consumers must not read it as capital alone.

**Unit (ADR-0011):** the summary page stamps "(रू.हजारमा)" = NPR **thousand**
(हजार = thousand). Verified: summed `budget-allocation-total` = 1,195,378,131
thousand = NPR 1,195.4 billion, matching the published FY 2074/75 appropriation-
from-Consolidated-Fund grand total; + the charged-fund summary (NPR 83.6 bn) =
NPR 1,279.0 bn = the published budget (~NPR 1.28 trillion). Second structural
anchor: every parsed head satisfies total == recurrent + capital.

## Known breakage modes

The 21-edition corpus splits four ways by text-layer encoding; **only "Red Book
Central 2074-75" is clean Devanagari-Unicode with a segmentable summary table.**

- **Broken-Unicode / glyph substitution** (BS 2069/70-2072/73, the "RB 20xx-xx" /
  "व्यय अनुमानको विवरण 207x" files): a defective embedded-font ToUnicode map
  reorders conjuncts and swaps glyphs (header "(रू. हजारमा)"→"(रू. हजायभा)");
  digits survive but labels are corrupted and the columns do not segment. **Not
  parsed** (font reverse-engineering = the OCR ADR-0003 forbids).
- **CID-broken** (BS 2073/74, 2076, 2077, 2078/79, 2079/80, 2080/81, 2081/82):
  `(cid:N)` glyphs, no usable ToUnicode. The recent "plan now" editions are all
  here. **Not parsed** (no OCR, ADR-0003).
- **Legacy Preeti** (BS 2059, 2060/61, 2061/62, 2062/63, 2065, 2066/67, 2067/68):
  Preeti font byte-map (e.g. "cfly{s" = आर्थिक), not Unicode. **Not parsed.**
- **Look-alike tables within the clean edition.** The charged-fund (व्ययभार)
  summary (page 8) and the अनुसूची-१ functional-classification annex (~page 600+)
  reuse the same जम्मा-रकम / चालु-खर्च captions and code-led rows. The parser gates
  the appropriation block on `योजन` + `जम्मा रकम` and excludes the annex via the
  `तलु नामा` (growth-comparison) anchor + an exact-8-number-column row check, so
  neither contaminates the totals (ADR-0011).
- **Glyph-reordering artifacts** in the clean edition's names (e.g. `रा�प�त` for
  राष्ट्रपति). `dimension_label` preserves the raw extracted text faithfully; we
  never fabricate. The code prefix in `dimension_value` guarantees distinct head
  identity even when names mangle.
- For any unparseable edition the parser emits a typed `PageLayoutChanged` (never
  silently empty) and returns `status=failure` — a documented infeasibility.

## Deferred (not yet extracted)

- The **charged-fund (व्ययभार) summary** (constitutional bodies + debt servicing,
  page 8) — a narrower 7-column table with different column semantics (no separate
  capital column); deferred to avoid cross-semantic unit confusion (ADR-0011).
- **Prior-year actual / revised** columns and the **source split** (GoN / foreign
  grant / foreign loan) — present and clean on the same rows; the three FY0 budget
  measures are the headline story.
- All editions other than FY 2074/75 (encoding-blocked, above).

## Revision policy

Annual editions supersede prior years' figures (and a single year has Original +
Revised + Mid-Term-Review variants). Each edition/document is a separate
`source_documents` row; `dne_facts` is keyed by `source_document_id`, so
re-ingesting the same document is idempotent (`ON CONFLICT DO NOTHING`) and a new
edition adds rows without overwriting — preserving the revision trail (Data
Continuity Protocol). Never merge across editions on `(slug, dimension, period)`
alone.
