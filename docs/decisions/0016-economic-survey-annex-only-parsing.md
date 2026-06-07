# ADR-0016: Economic Survey parser — annex-only scope (extract Annex 6.1; defer the RTL-mirrored macro annex and CID editions)

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, parsing, mof, scope, data-integrity

## Context

The MoF **Economic Survey** (आर्थिक सर्वेक्षण, `source_id:
mof-economic-survey-annual`) is Nepal's canonical annual macro compendium. Its
value for a data pipeline is the statistical **annex** — GDP & growth, sectoral
GVA, prices/CPI, fiscal revenue/expenditure, external trade, BoP, plus
social-sector tables (labour, tourism, health, education). The buildout roadmap
flagged this as the **hardest** ingest item: encoding is wildly mixed
page-to-page. The agreed policy was **annex-only parsing**: extract ONLY tables
that are cleanly, deterministically parseable; DEFER (document) the rest.

Three editions sit in-repo (`Financial Data/mof_documents/economic_survey/`):
`Economic_Survey_2023-24_EN.pdf` (536 pp, English "unofficial translation"),
`Economic_Survey_2080-81_NP.pdf` (547 pp, Nepali), `Economic_Survey_2081-82.pdf`
(517 pp).

STEP-0 real-PDF inspection (pdfplumber `extract_text` / `extract_tables` /
`chars`; page numbers are 0-based pdfplumber indices, EN edition) found **three**
encoding zones in the English edition, not one:

1. **CID-broken narrative chapters (pp ~3–298).** 15–50 `(cid:N)` glyphs per
   word, no ToUnicode map. Unusable.
2. **RTL-mirrored MACRO annex.** The "Macroeconomic Indicators" summary
   (pp 299–303) and the numbered Annex 1.1… macro tables (GDP/GVA/prices/fiscal,
   from p 313) are free of `(cid:N)` but **right-to-left mirrored**: every cell
   string is character-reversed (GDP `8.4075` = "5704.8" reversed; year
   `P42/3202` = "2023/24P"), the COLUMN order is reversed (row-label column lands
   LAST), the ROW order is reversed, and multi-line row labels are word-reversed
   AND line-wrap-fragmented (`"noitacifissalC\nlai"`). Confirmed at char level:
   the top annex line read left-to-right by x-coordinate is
   `*51040769410854912755477` — glyphs at genuinely reversed x-coordinates, a
   baked-in RTL layout artifact. The NUMBERS decode by string-reversal
   (`8.4075`→`5704.8` ⇒ nominal GDP FY2023/24 ≈ NPR 5.7 trillion, inside the
   ADR-0011 NPR 5–6 trillion band) but the row-label↔value GEOMETRY is **not
   deterministically reconstructable** — un-mirroring (transpose + reverse cells
   + reverse columns + reverse rows + reassemble scrambled mid-word-split
   reversed label fragments) is brittle and is, in spirit, the font/layout
   reverse-engineering ADR-0003 forbids. It is the failure class
   `fcgo_consolidated` DEFERRED for its reversed-glyph financial-statement tables.
3. **CLEAN social-sector annex tables (pp ~405–488).** A subset — foreign
   employment (Annex 6.1), hotels (Annex 8.14), medical specialists (Annex 11.7),
   education (Annex 11.x) — render as **clean, forward English tables** with
   stable column geometry. These ARE deterministically parseable.

The two Nepali editions' annex/English zone is **CID-broken** (the Devanagari
narrative body is clean Unicode but is prose — no parseable statistical tables),
so they yield no clean annex table.

## Decision

1. **Annex-only, scoped to the single highest-value clean table.** Extract
   **Annex 6.1: Number of Workers having Foreign Employment Permit** — a clean
   `Fiscal Year | Female | Male | Total` matrix. Labour migration is the
   front-end of Nepal's remittance economy — directly on-mission ("does Nepal's
   money become wealth"). Emit three single-series indicators (unit `count`),
   one value per **full** fiscal year:
   - `economic-survey-foreign-employment-permits-total`
   - `economic-survey-foreign-employment-permits-female`
   - `economic-survey-foreign-employment-permits-male`
   Cumulative rows ("Upto July 2015", "Upto Mid March 2024") and the partial,
   starred current-year row ("2023/24*") are **skipped** — they are not full
   annual values and emitting them as `annual` would mislead.

2. **Single-series `staging_rows`, not `dne_facts`.** Annex 6.1's three columns
   are clean single-value-per-year series; routing the headline Total + the
   Female/Male split through the standard staging→validation→approved path
   (ADR-0014) needs no dimensional machinery. (A future enrichment could model
   gender as a `dne_facts` dimension, but that is not warranted for three columns.)

3. **Anchor-based extraction.** The parser finds Annex 6.1 by its caption
   ("Annex 6.1 … Foreign Employment Permit") and validates the
   `Fiscal Year/Female/Male/Total` header before reading any value — the page
   number is never hard-coded (annex pagination drifts across editions).

4. **DEFER the RTL-mirrored macro annex and the CID editions, documented.** The
   GDP/inflation/revenue/trade macro series the brief prioritised live in the
   RTL-mirrored macro annex; the Nepali editions are CID-broken. Neither is
   parseable without the reverse-engineering / OCR ADR-0003 forbids. The parser
   attaches typed diagnostics naming the breakage modes and affected page ranges
   (`PageLayoutChanged` for the mirrored macro annex, `EncodingError` for CID
   pages) so the deferral is auditable, never silent (Rule 6). The other ~10
   clean social-sector tables (hotels/health/education) have heterogeneous
   merged-cell / multi-row-header geometry; a robust extractor spanning them
   would exceed the ≤300-line diff budget and be fragile, so they are
   **deferred** too (documented in the source profile as the future scope).

5. **Status semantics.** The EN edition yields `partial` (Annex-6.1 rows
   extracted + macro/CID pages deferred). The two Nepali editions yield `failure`
   with a `NoCleanAnnexTable` `Other` error — a documented per-edition
   infeasibility, never a fabricated value.

6. **Unit & magnitude (ADR-0011).** Unit is `count` (people holding permits).
   Verified by magnitude: FY2022/23 total = 494,224 permits — the right order
   for Nepal's annual labour outflow; Female + Male reconcile to Total in the
   source. The deferred macro numbers were also decoded (GDP ≈ NPR 5.7 trillion)
   to confirm the deferral is a geometry problem, not a masked parse bug.

7. **Registry: reference-only posture retained, no flip.** The registered row
   `mof-economic-survey-annual` is `status: 'active'`, `ingestionMode:
   'reference_only'`. The headline MACRO series are NOT ingested (deferred), so
   the source remains primarily a narrative reference; the Annex-6.1 labour
   series is a bonus clean extraction. No status flip required.

8. **Future-proof.** The diagnostic classifier recognises a Unicode-clean macro
   annex (forward GDP/Indicators vocabulary) as `clean`; a future re-typeset
   edition, or a follow-up coordinate-based (`extract_words` x/y-clustering)
   un-mirror, would let the macro tables be added without changing the Annex-6.1
   path, the registry id, or the CLI contract.

## Alternatives Considered

- **Un-mirror the RTL macro annex (reverse cells + columns + rows + reassemble
  labels).** Rejected — fragile multi-stage geometric reconstruction; breaks on
  any merged-cell/wrap drift; the reverse-engineering ADR-0003 forbids. (Numbers
  decode, but row-label identity does not survive deterministically.)
- **Extract all ~11 clean social-sector tables now.** Rejected for this PR —
  heterogeneous geometries (hotels has AD/BS + star-level multi-headers; health
  repeats per-FY blocks; education is subject×year matrices) push well past the
  diff budget and raise fragility. Deferred as a documented follow-up.
- **Model Annex 6.1 gender as a `dne_facts` dimension.** Considered; rejected as
  over-engineering for three clean columns. Single-series is simpler and the
  Total is the headline.
- **OCR the CID-broken / mirrored pages.** Rejected — ADR-0003 (no production AI/OCR).
- **Pure documented-infeasibility (emit nothing).** Rejected once a clean,
  on-mission table (Annex 6.1) was found — extracting what IS clean beats a blanket
  deferral.

## Consequences

- The EN edition yields **24 approved-bound rows** (8 full fiscal years 2015/16–
  2022/23 × 3 measures), provenance-tracked and idempotent — the *Money In* /
  remittance-adjacent story gains a clean labour-migration series.
- The RTL-mirrored macro annex (GDP/prices/fiscal/trade) and the ~10 other clean
  social-sector tables are **explicitly deferred and documented** with page
  ranges — not silently dropped. Follow-ups have a clear starting point.
- The two Nepali editions return a documented `failure` (their annex is
  CID-broken); re-running is idempotent and honest.
- `seed-indicators.ts` gains three slugs (returned to Mother). The registry stays
  reference-only.

## References

- [ADR-0003](0003-ai-assisted-parsing-policy.md) — no production AI/OCR/transliteration
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — verify magnitudes; unit `count`
- [ADR-0013](0013-dne-ad-fiscal-year-periods.md) — AD→BS fiscal-year mapping (+57)
- [ADR-0020](0020-yellowbook-soe-annex1-scope.md) — sibling "annex-only, scope to one clean table, defer the rest" decision (Yellow Book)
- `scrapers/mof_economic_survey/` (parser + README + tests)
- `scripts/ingest-economic-survey.ts` — ingest CLI (mirrors `ingest-fcgo-cfs.ts`)
- `docs/sources/mof-economic-survey-annual.md` — source profile + breakage modes
- `scrapers/fcgo_consolidated/parser.py` — prior art (anchor-based + deferring reversed-glyph tables)
