# Data Audit — Nepal Ledger truth-layer inventory, coverage, accuracy & gaps

**Generated:** 2026-06-08 · **Regenerate:** `pnpm audit:data` (`scripts/data-audit.ts`, read-only).

> **Mission context.** Nepal Ledger aims to be the most **comprehensive AND accurate**
> database of Nepal's financial data, for advanced reporting + AI applications.
> Completeness and accuracy are first-class. This document is the **authoritative,
> machine-verified inventory** of what data actually exists, how far back it goes,
> how it reconciles, and where the gaps are.

## How agents MUST use this document (anti-hallucination protocol)

1. **Never assert a number, series, or coverage exists without checking** — either this
   doc (for the shape) or the live DB (for the value). Do not infer "we have X back to
   year Y" from memory.
2. **Cite provenance.** Every fact carries `source_document_id`, a `confidence_grade`
   (A/B/C), and an extraction method. Report grade B/C data as such; never present
   OCR/transliteration-recovered data as if it were audited primary data.
3. **Trust the reconciliation gate, not the parse.** A recovered number is trustworthy
   only if it reconciles to the source's printed totals (see §5). Unreconciled rows are
   flagged here and MUST NOT be used in reporting until resolved.
4. **Re-run before relying.** This is a snapshot; `pnpm audit:data` regenerates it.

---

## 1. Table inventory (live row counts)

| Table | Rows | Notes |
|---|--:|---|
| `census_facts` | 531,618 | 753 palikas (full federal coverage; NPHC 2021) |
| `dne_facts` | 106,989 | dimensional facts (trade, customs, migrant, provincial GDP, SOE, budget) |
| `local_government_fiscal_transfers` | 6,008 | **only FY2082/83** — 8 historical FYs deferred (OCR) |
| `banking_sector_facts` | 2,088 | 58 months (Ashadh 2078 → Shrawan 2082) |
| `foreign_aid_facts` | 1,020 | 7 fiscal years (gaps — see §3) |
| `approved_indicator_values` | 877 | 103 single-series indicators |
| `entities` | 753 | local levels (palika crosswalk) |
| `staging_indicator_values` | 739 | in-flight (pre-promotion) |
| `data_quality_flags` | 399 | validator flags — REVIEW (see §6) |
| `source_documents` | 182 | archived source files |
| `indicators` / `indicator_source_map` | 103 / 103 | catalogue |
| `source_registry` | 69 | 16 active, 53 paused |
| `parser_runs` / `parser_errors` | 14 / 2 | |
| `ocr_*` (tile/cell/stitch) | 0 / 0 / 0 | **Tier-2 OCR not yet built** (ADR-0021) |
| `administrative_units`, `fact_ledger_*`, `leads` | 0 | not yet populated |

---

## 2. Coverage by domain — what we have, how far back

| Domain | Series / table | Coverage | Conf | Status |
|---|---|---|---|---|
| **Real sector** | `dne-gdp-nominal/real/per-capita/deflator` | **50 FY, 2031/32→2081/82** | B | ✅ deep |
| | `dne-gdp-real-growth` | 49 FY (2032/33→2081/82) | B | ✅ |
| | `dne-cpi` / `dne-inflation-rate` | 52 / 51 FY (2029/30→2080/81) | B | ✅ deep |
| **Trade (DNE)** | `dne-merchandise-{exports,imports}-{india,china,other}` × commodity | monthly, Ashadh 2069→Shrawan 2082 (~160 mo) | B | ✅ deep |
| **Trade (customs)** | `customs-merchandise-{imports,exports}` × {commodity, country, office, composite} | **3 periods only** (annual 2081/82 + Shrawan 2081 + YTD Jestha 2082) | A | ⚠️ shallow history |
| **Migrant workers** | `dne-migrant-workers` × country | 234 countries, 51 months (Ashadh 2078→Shrawan 2082) | B | ✅ (headcounts, NOT remittance NPR) |
| **Remittance (NPR)** | `dne-remittance-inflow` | **only 3 FY (2079/80→2081/82)** | B | ⚠️ short — needs historical BoP |
| **Tourism** | `dne-tourist-arrival` | 407 months (Ashadh 2048→Shrawan 2082) | B | ✅ deep |
| **Foreign aid** | `foreign_aid_facts` (donor + sector) | **7 FY w/ gaps** (see §3) | B | ⚠️ gaps |
| **Public enterprises** | `soe-government-share`, `soe-loan-principal` | **1 FY (2080/81)**, equity+loan only | B | ⚠️ revenue/profit deferred |
| **Federal budget** | `budget-allocation-{total,recurrent,capital}` × budget-head | **1 FY (2074/75)**, 57 heads | B | ⚠️ single year |
| **Fiscal transfers** | `local_government_fiscal_transfers` | **1 FY (2082/83)**, 6,008 rows | A | ⚠️ 8 historical FYs deferred (OCR) |
| **Census** | `census_facts` | 531,618 rows, 753 palikas (NPHC 2021) | A | ✅ full |
| **Banking** | `banking_sector_facts` | 58 months (2078→2082) | A | ✅ |
| **CMEFs (NRB monthly)** | 78 NCPI categories + 7 headline | **1 snapshot only** (FY2082/83 9-month) | A | ⚠️ single period — monthly history not ingested |

---

## 3. Foreign-aid fiscal-year gaps (illustrative completeness analysis)

`foreign_aid_facts` has **7 of ~17** fiscal years since 2062/63:

| Present (AD) | 2008/09 · 2009/10 · 2010/11 · 2013/14 · 2014/15 · 2015/16 · 2020/21 |
|---|---|
| **Missing (gaps)** | 2005/06–2007/08, 2011/12–2012/13, **2016/17–2019/20**, 2021/22–2023/24 |

The 2016/17–2019/20 + 2021/22–2024/25 gaps matter most (recent years). Filling them needs the corresponding White Book editions (some Preeti — recoverable via Tier-1a; some may need re-acquisition).

---

## 4. Source registry status (the backlog)

- **16 active** sources: **10 have ingested data**; **6 registered-but-empty** — external benchmark feeds not yet ingested: `adb-ado-nepal`, `imf-article-iv`, `ndhs-survey`, `nlss-survey`, `npc-16th-plan`, `wb-wdi`.
- **53 paused** sources (the recovery backlog: OCR targets + future feeds). 2 paused sources carry stray documents (registry hygiene item).

---

## 5. Accuracy — machine-checked reconciliation (the verification baseline)

These are the cross-checks that prove a number is trustworthy. **All pass except one flag.**

| Check | Result | Verdict |
|---|---|---|
| Provincial GDP Σ vs national nominal GDP (FY2081/82) | 6,107,221 npr_M vs 6,107 npr_B | ✅ exact |
| Customs cross-tab (composite) Σ vs single-dim total (imports 2081/82) | 1,804,122,731.4 vs .5 | ✅ exact (rounding) |
| Redbook recurrent+capital = stated total (per head) | matches every head | ✅ exact |
| Foreign-aid donor-total = sector-total (per FY) | 6 of 7 FYs match exactly | ⚠️ **see flag** |

> **🚩 ACCURACY FLAG — foreign-aid FY2070/71 (2013/14):** donor-total **113,240,000** ≠
> sector-total **95,934,658** npr_thousand (~15% gap). Every other edition reconciles
> exactly, so one of this edition's two tables (donor vs sector) was mis-parsed (likely
> a Preeti-decode or row-capture issue). **Do not use FY2070/71 aid figures in reporting
> until re-parsed + reconciled.** All other aid FYs are reconciled and safe.

---

## 6. Known gaps & deferred corpus (what is NOT yet in the truth layer)

**Deferred PDFs (Tier-2 Surya OCR, ADR-0021 — feasibility proven, build pending):**
- **Historical intergovernmental fiscal transfers** — 8 FYs of per-local-level grants (the entire history beyond FY2082/83).
- **Full Yellow Book SOE financials** — revenue, profit/loss, paid-up capital (we have only equity + loan, 1 FY).
- **Economic Survey macro annex** — GDP-levels / GVA-by-sector / fiscal detail (RTL-mirror; OCR-of-visual-page is the route — headline GDP/CPI already covered by DNE).
- **Preeti/CID redbook + remaining whitebook editions** — more budget years + the aid-year gaps.

**Other gaps:**
- Remittance NPR history (only 3 FY; pre-2079/80 needs historical BoP files).
- CMEFs monthly history (only the latest 9-month snapshot; the monthly series is not back-filled).
- Customs trade history (only FY2081/82; prior years need acquisition).
- 6 external benchmark sources (ADB/IMF/WB/NLSS/NDHS/NPC) registered, not ingested.

**`data_quality_flags` (399 rows):** the validator's own warn/block flags on staging
rows — should be reviewed as a standing quality worklist (not yet triaged here).

---

## 7. OCR-verification protocol (for Tier-2, ADR-0021)

Every OCR-recovered fact must pass, before promotion:
1. **Reconcile** the OCR'd subtotals to the document's **printed grand-total** (exact for
   structured tables; within a stated tolerance otherwise). A run that fails reconciliation
   is a parse/geometry bug — fix or defer, never ship.
2. **Sample-verify** low-confidence + near-tile-seam cells (via `ocr_cell_extractions`)
   against the **rendered PDF page** (Read renders PDFs; or pymupdf) — AI-as-QA, agree/
   disagree only, never as the extractor.
3. **Grade + provenance**: OCR-derived → confidence B/C, `extraction_method='surya-ocr'`.
4. **Magnitude sanity** (ADR-0011): every total checked against a known order of magnitude.

This document's §5 reconciliation checks are the **regression suite** for that protocol —
re-run `pnpm audit:data` after any OCR ingest; a new mismatch means the OCR is wrong.

---

## 8. Bottom line

- **Strong, deep, reconciled:** real-sector (GDP/CPI 50yr), DNE trade-by-commodity, tourism,
  census, banking, customs (current year), the macro money-flow.
- **Thin / single-period (priority to deepen):** customs history, remittance-NPR history,
  SOE financials, federal budget, fiscal-transfer history, CMEFs monthly.
- **One accuracy flag to fix:** foreign-aid FY2070/71 donor≠sector.
- **The path is proven:** Tier-1 deterministic recovery is done; Tier-2 GPU Surya OCR is
  validated and scoped (task #50) to close the historical PDF gaps.

Data currently spans **AD 2005 → 2025**. The mission's bar is completeness + accuracy;
this audit makes both measurable and keeps the agents honest.
