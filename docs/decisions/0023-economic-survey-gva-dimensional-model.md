# ADR-0023: Economic Survey GVA-by-industry dimensional model (Tier-2 OCR recovery of the macro annex)

- **Status:** Accepted (user-approved 2026-06-10)
- **Date:** 2026-06-10
- **Deciders:** Mother Opus, user
- **Tags:** data-pipeline, data-model, dne_facts, ocr, economic-survey

## Context

[ADR-0016](0016-economic-survey-annex-only-parsing.md) **deferred** the Economic Survey's
macro annex (GDP / sectoral GVA / prices / fiscal) because, under the pre-OCR regime, the
English edition's macro annex is RTL-mirrored in its text layer and the Nepali editions are
CID-broken — neither deterministically parseable. [ADR-0021](0021-pdf-recovery-tiers-and-verification-gate.md)
then established **Tier-2 Surya OCR of the rendered page** as the sanctioned recovery route
for exactly such pages, and the overnight run (P2) OCR'd both Nepali editions cleanly.

This ADR records the first macro-annex recovery: **annex 13.1, प्रदेशगत कुल मूल्य अभिवृद्धि
(औद्योगिक वर्गीकरण अनुसार)** — provincial Gross Value Added by 18 industrial sectors, current
prices, रू करोडमा, from `Economic_Survey_2081-82.pdf` p475. This is the **GVA-by-sector gap**
DATA_AUDIT §6 names. It is genuinely new: `dne_facts` currently holds only `dne-provincial-gdp`
(province TOTALS, no sector breakdown).

The data is a **two-dimensional cross-tab** (province × industry) plus a national column —
it does not fit the one-dimension `dne_facts` contract directly, so it needs the
[ADR-0018](0018-composite-dimension-for-cross-tabs.md) composite-dimension treatment.

### Verification posture (the reason this is promotable at all)

Pure OCR of this dense landscape table has ~5–20 % digit errors. Per ADR-0021's gate, **no
value ships unless it reconciles AND was render-verified**. Mother render-verified the national
column AND all 7 province columns (full-column `Matrix(8)` strips, read off the printed page).
Reconciliation is multi-directional and over-determined:

- Σ(18 sectors) = कुल मूल्य अभिवृद्धि (GVA basic) per column;
- GVA + खुद कर (net product tax) = GDP per column;
- Σ(7 provinces) = नेपाल (national) per sector row;
- national GDP **= existing `dne-gdp-nominal`** (cross-source, ADR-0011 magnitude).

**Achieved (FY2081/82, `verified_matrix_2081_82.json`):** all three internal gates close with
worst residual **3 crore** (per-province Σsectors vs GVA 0…+3; per-sector Σprovinces vs national
−1…+2; GVA+tax=GDP ±1) — within the ~±9 rounding tolerance for 18 crore-rounded values. Cross-source:
Σ(7 provinces) GDP = national GDP = **610,722 = `dne-gdp-nominal` FY2081/82, to the rupee**. Every
cell was read from the rendered page; none computed-and-left-unread.

**FY2080/81 is excluded**: its national Σ(sectors)=506,864 vs printed GVA-basic 506,065 is a
**+799 source-internal discrepancy** (every cell render-verified correct-as-printed) — it cannot
be made to reconcile from this source, so it is documented as a known gap, never force-fit.
Only **FY2081/82**, which reconciles on all gates, is promoted.

## Decision

Model Economic Survey GVA-by-industry as facts in the existing `dne_facts` table (no schema
change — `dne_facts` already accepts arbitrary `dimension_kind`/`dimension_value`, ADR-0018):

- **`base_indicator_slug = 'economic-survey-gva-current'`** — the measure: Gross Value Added at
  basic prices, current (प्रचलित) prices. (A `-constant` sibling can follow for स्थिर-मूल्य tables.)
- **Two `dimension_kind`s under that one measure** (the customs precedent: one measure, several
  dimension kinds):
  - `industry` — the **national** sectoral GVA. `dimension_value` = sector kebab slug
    (`agriculture-forestry-fishing`, `manufacturing`, `construction`, …, 18 members). This is the
    headline gap series.
  - `province-industry` — the **provincial** disaggregation (composite, ADR-0018).
    `dimension_value = '<province-slug>__<sector-slug>'` (both parts `__`-free); `dimension_label`
    = `<Province> → <Sector>`. 7 provinces × 18 sectors.
- **`unit = 'npr_crore'`** (ADR-0011 convention; source is रू करोडमा, no conversion).
- **Period:** `reporting_period_bs='2081/82'`, `fiscal_year_ad_label='2024/25'`, type `annual`.
- **Provenance:** `extraction_method='surya-ocr'`, `confidence_grade='B'` (render-verified +
  fully reconciled), `source_document_id` = the archived ES 2081-82 PDF.
- **NOT stored:** the GDP row (idx20) — it duplicates `dne-gdp-nominal` already in the DB. The
  GVA-basic total and net-tax are stored as national `industry`-kind rows only if useful as
  anchors; the *sectoral* GVA is the new payload.

### The reconciliation invariant (the safeguard, ADR-0018 style)

The composite `province-industry` facts disaggregate the `industry` facts: **Σ(province-industry
for a sector) == that sector's national `industry` value** — verified in the parser's tests
against the rendered, reconciled matrix, worst residual ≤ rounding. A composite that doesn't
reconcile has a read/geometry bug and MUST NOT ship.

### Idempotency / no double-count

The national `industry` rows and the `province-industry` composite rows are distinct
`dimension_kind`s under one `source_document_id`; the `dne_facts_unique_idx` keys on
`(base_indicator_slug, dimension_kind, dimension_value, reporting_period_bs, source_document_id)`,
so re-ingest is idempotent. Consumers summing GVA must pick ONE dimension_kind (national OR
provincial), never both, to avoid double-counting — documented in the source profile.

## Alternatives considered

- **Single-dimension only (national `industry`), drop provincial.** Rejected — the provincial
  GVA-by-sector is high-value (District MRI / Money Map) and reconciles cleanly for FY2081/82.
- **New province×sector matrix table + migration.** Rejected — the composite encoding reuses the
  proven `dne_facts` machinery with zero schema risk (ADR-0018 precedent), and the reconciliation
  invariant keeps it honest.
- **Promote FY2080/81 with a flagged discrepancy.** Rejected per the user's clean-only mandate —
  unreconciled data does not enter the truth layer; documented as a source-defect gap instead.

## Consequences

- The macro annex ADR-0016 deferred becomes partially recovered: national + provincial GVA by 18
  industries for FY2081/82, reconciled and cross-validated against `dne-gdp-nominal`.
- `dimension_kind` vocabulary grows: `industry`, `province-industry`.
- No schema migration. New ADR + ingest-path extension to `scripts/ingest-economic-survey.ts`
  (or a dimensional sibling) routing `dimensional_rows` → `dne_facts` (ADR-0015 generic path).
- FY2080/81 + the constant-price tables + the other editions remain documented follow-ups.

## References

- [ADR-0016](0016-economic-survey-annex-only-parsing.md) — deferred the macro annex (this revisits it via OCR)
- [ADR-0021](0021-pdf-recovery-tiers-and-verification-gate.md) / [ADR-0022](0022-surya-ocr-pipeline.md) — Tier-2 OCR + the verification gate
- [ADR-0015](0015-dne-dimensional-fact-model.md) — the `dne_facts` one-dimension model
- [ADR-0018](0018-composite-dimension-for-cross-tabs.md) — composite dimension + reconciliation invariant
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — npr_crore unit + magnitude reconciliation
- Artifacts: `scrapers/surya_ocr/_ai_pass/es2081_annex13_1/` (cells.json, reconciliation_report.md, MOTHER_VERIFICATION.md, verified_matrix_2081_82.json)
