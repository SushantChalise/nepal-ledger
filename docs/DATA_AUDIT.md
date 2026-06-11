# Data Audit — Nepal Ledger truth-layer inventory, coverage, accuracy & gaps

**Generated:** 2026-06-08 · **Partial update 2026-06-10:** + Economic Survey GVA-by-sector (§2/§5/§6, ADR-0023; broader counts not refreshed). · **Regenerate:** `pnpm audit:data` (`scripts/data-audit.ts`, read-only).

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
| `local_government_fiscal_transfers` | 30,104 | **5 FYs** (2078/79–2082/83) — 3 text-layer FYs pending layout adapters + 1 scanned (2077/78) pending OCR |
| `banking_sector_facts` | 2,088 | 58 months (Ashadh 2078 → Shrawan 2082) |
| `foreign_aid_facts` | 1,750 | 12 fiscal years (gaps — see §3) |
| `approved_indicator_values` | 877 | 103 single-series indicators |
| `entities` | 753 | local levels (palika crosswalk) |
| `staging_indicator_values` | 739 | in-flight (pre-promotion) |
| `data_quality_flags` | 399 | validator flags — REVIEW (see §6) |
| `source_documents` | 184 | archived source files (+2 intergovernmental, Stream 2) |
| `indicators` / `indicator_source_map` | 103 / 103 | catalogue |
| `source_registry` | 70 | 17 active, 53 paused (+`mof-intergovernmental`) |
| `parser_runs` / `parser_errors` | 14 / 2 | |
| `ocr_*` (tile/cell/stitch) | 0 / 0 / 0 | harness BANKED + 58 pytest (ADR-0022); 2 FYs ingested **text-layer-only** (honest `extraction_method=textlayer`) — Surya GPU cross-check pass pending (see §6) |
| `administrative_units`, `fact_ledger_*`, `leads` | 0 | not yet populated |

---

## 2. Coverage by domain — what we have, how far back

| Domain | Series / table | Coverage | Conf | Status |
|---|---|---|---|---|
| **Real sector** | `dne-gdp-nominal/real/per-capita/deflator` | **50 FY, 2031/32→2081/82** | B | ✅ deep |
| | `dne-gdp-real-growth` | 49 FY (2032/33→2081/82) | B | ✅ |
| | `dne-cpi` / `dne-inflation-rate` | 52 / 51 FY (2029/30→2080/81) | B | ✅ deep |
| **Trade (DNE)** | `dne-merchandise-{exports,imports}-{india,china,other}` × commodity | monthly, Ashadh 2069→Shrawan 2082 (~160 mo) | B | ✅ deep |
| **Trade (customs)** | `customs-merchandise-{imports,exports}` × {commodity, country, office, composite} | **7 periods** — annual FY2076/77–2081/82 (5 yrs) + Shrawan 2081 + YTD Jestha 2082 | A | ✅ deepened 2026-06-08 |
| **Migrant workers** | `dne-migrant-workers` × country | 234 countries, 51 months (Ashadh 2078→Shrawan 2082) | B | ✅ (headcounts, NOT remittance NPR) |
| **Remittance (NPR)** | `dne-remittance-inflow` | **only 3 FY (2079/80→2081/82)** | B | ⚠️ short — needs historical BoP |
| **Tourism** | `dne-tourist-arrival` | 407 months (Ashadh 2048→Shrawan 2082) | B | ✅ deep |
| **Foreign aid** | `foreign_aid_facts` (donor + sector) | **9 FY w/ gaps** (see §3) | B | ⚠️ gaps |
| **Public enterprises** | `soe-government-share`, `soe-loan-principal` | **1 FY (2080/81)**, equity+loan only | B | ⚠️ revenue/profit deferred |
| **Federal budget** | `budget-allocation-{total,recurrent,capital}` × budget-head | **1 FY (2074/75)**, 57 heads | B | ⚠️ single year |
| **Sectoral GVA** | `economic-survey-gva-current` (`industry` + `province-industry`) | **1 FY (2081/82)**, 18 industries × (national + 7 provinces) = 144 facts | B | ✅ new — Tier-2 OCR, render-verified (ADR-0023) |
| **Fiscal transfers** | `local_government_fiscal_transfers` | **5 FY (2078/79–2082/83)**, 30,104 rows | A/B | ✅ deepened 2026-06-08 (Stream 2 + deterministic multi-edition recovery); 3 text-layer FYs pending adapters + 1 scanned FY pending OCR |
| **Census** | `census_facts` | 531,618 rows, 753 palikas (NPHC 2021) | A | ✅ full |
| **Banking** | `banking_sector_facts` | 58 months (2078→2082) | A | ✅ |
| **CMEFs (NRB monthly)** | 78 NCPI categories + 7 headline | **1 snapshot only** (FY2082/83 9-month) | A | ⚠️ single period — monthly history not ingested |

---

## 3. Foreign-aid fiscal-year gaps (illustrative completeness analysis)

`foreign_aid_facts` has **12 of ~18** fiscal years since 2062/63 (updated 2026-06-11):

| Present (AD) | 2005/06 · 2007/08 · 2008/09 · 2009/10 · 2010/11 · 2013/14 · 2014/15 · 2015/16 · 2020/21 · **2023/24** · **2024/25** · **2025/26** |
|---|---|
| **Missing (gaps)** | 2006/07, 2011/12–2012/13, **2016/17–2019/20**, **2021/22–2022/23** |

The recent editions FY **2023/24, 2024/25, 2025/26** were acquired 2026-06-11 from the MoF **IERD "Source Book / सेतो किताब"** division section (`mof.gov.np/divisions/ierd/category/ierd--sourcebook--seto-kitab/`) — the White Book moved off the old `/category/whitebook/` listing (which dead-ends at FY 2021/22), which is why earlier catalog audits missed them. They use a new merged-code+name layout; parser v0.3.0 reads it via a word-positional path (donor==sector reconciled to the rupee).

Remaining gaps and why:
- **FY 2021/22 (BS 2078/79)** — no genuine White Book online; the only file under that label (`...FY 2021-22_azz4yjf.pdf`) is the mislabelled Intergovernmental Fiscal Transfer book. The IERD listing skips from FY 2020/21 to FY 2023/24.
- **FY 2022/23 (BS 2079/80)** — genuine publication gap; absent from the IERD listing (coincides with the 2022 government transitions). IERD `news/1703` holds only a "Foreign Aid Commitments" summary, not the project Source Book.
- **FY 2016/17–2019/20** — not on mof.gov.np (site skips FY 2015/16 → FY 2020/21); IECCD unreachable 2026-06-11. Need manual re-acquisition from IECCD or a donor archive.
- **FY 2006/07, 2011/12–2012/13** — older gaps; lower priority.

---

## 4. Source registry status (the backlog)

- **17 active** sources: **11 have ingested data** (+`mof-intergovernmental`, Stream 2); **6 registered-but-empty** — external benchmark feeds not yet ingested: `adb-ado-nepal`, `imf-article-iv`, `ndhs-survey`, `nlss-survey`, `npc-16th-plan`, `wb-wdi`.
- **53 paused** sources (the recovery backlog: OCR targets + future feeds). 2 paused sources carry stray documents (registry hygiene item).

---

## 5. Accuracy — machine-checked reconciliation (the verification baseline)

These are the cross-checks that prove a number is trustworthy. **All pass except one flag.**

| Check | Result | Verdict |
|---|---|---|
| Provincial GDP Σ vs national nominal GDP (FY2081/82) | 6,107,221 npr_M vs 6,107 npr_B | ✅ exact |
| Customs cross-tab (composite) Σ vs single-dim total (imports 2081/82) | 1,804,122,731.4 vs .5 | ✅ exact (rounding) |
| Redbook recurrent+capital = stated total (per head) | matches every head | ✅ exact |
| Foreign-aid donor-total = sector-total (per FY) | **all 12 FYs match exactly** (incl. modern FY 2023/24–2025/26, parser v0.3.0 word path) | ✅ |
| Intergovernmental transfers Σ(753 local levels) vs printed `स्थानीय तह` doc total | FY2078/79 2,830,147 lakh = printed; FY2079/80 3,003,716 lakh = printed | ✅ exact (to the rupee) |
| Economic Survey GVA Σ(province-industry) vs national `industry` per sector (FY2081/82, G5) | worst residual 2 npr_crore; 0 of 18 sectors >±9 | ✅ within rounding |
| Economic Survey GVA national GDP vs `dne-gdp-nominal` (FY2081/82) | 610,722 npr_crore = 6,107.221 npr_billion | ✅ exact (to the rupee) |

> **✅ RESOLVED (2026-06-08) — foreign-aid FY2070/71:** the earlier donor≠sector gap
> (113,240,000 vs 95,934,658) was a pdfplumber row-merge artifact — 2 ministries whose
> names wrap to a 2nd line were dropped from the sector table (their totals = 17,305,342
> = exactly the gap). Fixed by deterministic wrapped-name recovery (mof_whitebook v0.2.1,
> no AI/OCR); re-ingested (154→158 rows); donor==sector==113,240,000 now. Every White
> Book edition reconciles (clean, Preeti, and the modern FY 2023/24+ word path); no value
> was fabricated.

---

## 6. Known gaps & deferred corpus (what is NOT yet in the truth layer)

**Deferred PDFs (Tier-2 Surya OCR, ADR-0021/0022 — harness built + banked):**
- **Historical intergovernmental fiscal transfers** — ✅ **5 of the 8 historical FYs RECOVERED** (2026-06-08), all deterministic text-layer + reconciled to the rupee, 6,024 rows each, `npr_crore`, confidence B, `extraction_method=textlayer`:
  - FY2078/79 + FY2079/80 (Stream 2, 9-digit codes); FY2080/81 + FY2081/82 (8-digit codes, same 14-column model). (FY2082/83 already present via the XLSX feed; its PDF is a redundant copy, not re-ingested.)
  - **Correction to the earlier "6 scanned" claim** (a do-not-assume lesson): re-inspecting the bytes, **only FY2077/78 is genuinely scanned** (0 numeric tokens/page). The others all have rich text layers — the earlier worker mis-attributed "the template parser failed" as "scanned" without checking. The 3 still-pending FYs each hit a *characterized* blocker (deterministic data is recoverable, but not without a decision/build):
    - **FY2074/75 + FY2075/76 — schema-granularity blocker.** Visually verified (rendered page): the early books carry only **4 AGGREGATE grant columns** — वित्तीय समानीकरण (equalization), सशर्त (conditional), समपूरक (complementary), विशेष (special) + जम्मा (total) — NOT the schema's 8 *atomic* sub-types (the current/capital + min/formula/performance splits were introduced later). 3 of the 4 cannot map to atomic types without fabricating the split. Also: **unit is thousands** (not lakh — values ~`15,25,84`), and the code is **7-digit** (`8014893`) needing an old→federal crosswalk. → Recovering these honestly needs a **schema extension** (aggregate grant-type enum values) + an ADR + a code crosswalk — a structural decision, NOT just a parser tweak. Deferred pending that decision (never fabricate the atomic split).
    - **FY2076/77 — complex-layout blocker.** Landscape (842×595), every glyph **overprinted 4×**, and an apparently **transposed matrix** (≈24 local-level codes across one row). Deterministic but needs significant geometry reverse-engineering.
    - **FY2077/78 — genuinely scanned** → Surya OCR (harness built + validated end-to-end on real data; see below). Reconciliation of pure-OCR digits is the open risk.
- **Surya GPU path VALIDATED end-to-end** (2026-06-08): the `--surya` CLI runs the full render→tile→detect→recognize→stitch→reconstruct pipeline on a real intergovernmental page in ~30s (incl. model load), emitting valid UTF-8 JSON `ocr_tracking` (e.g. FY2079/80 p.1: 2 tiles, 533 cells, 14 stitch disagreements, mean line-confidence 0.836). Enablement fixes landed (bare-script absolute import + `sys.path` bootstrap; UTF-8 stdout for Devanagari; `--max-pages` bound). Reserved for the one genuinely-scanned FY (2077/78) + optional `ocr_tracking` provenance passes; the 5 recovered FYs use exact text-layer values, not OCR.
- **Full Yellow Book SOE financials** — revenue, profit/loss, paid-up capital (we have only equity + loan, 1 FY).
- **Economic Survey macro annex** — ✅ **GVA-by-sector (annex 13.1) RECOVERED for FY2081/82** (2026-06-10): national 18 industries + 7 provinces × 18, Tier-2 Surya-OCR, Mother render-verified + dual-reconciled, promoted to `dne_facts` (`economic-survey-gva-current`, ADR-0023). **Still deferred:** FY2080/81 (a +799 printed-source Σ-vs-total defect — excluded, not faked), the constant-price (स्थिर मूल्य) tables, fiscal/revenue annex, and the other survey editions (RTL-mirrored text layer; OCR-of-visual-page is the proven route). Headline GDP/CPI already covered by DNE.
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

## 8. Bottom line (updated 2026-06-08 after the 3-stream recovery program)

- **Strong, deep, reconciled:** real-sector (GDP/CPI 50yr), DNE trade-by-commodity, tourism,
  census, banking, **customs (now 5 annual FYs + monthly + cumulative)**, the macro money-flow,
  **foreign aid (7 FYs, all reconciled)**, **intergovernmental fiscal transfers (3 FYs — 753
  local levels × 8 grant types, every FY reconciles to the printed document total)**.
- **Accuracy flags:** ✅ none open — the FY2070/71 aid flag is RESOLVED (§5).
- **Resilience hardened:** `safeQueryWithRetry` now protects all large bulk ingests from the
  pooler's transient ECONNRESETs (a 42k-row customs ingest had failed mid-stream; now retries).
- **Still thin (deepen next):** SOE financials (1 FY), federal budget (1 FY); fiscal-transfer
  history is now **3 FYs** (Stream 2 recovered FY2078/79 + FY2079/80; 6 scanned FYs await the
  Surya-OCR-only path, harness ready), and two PARSER-blocked (not data-blocked) gaps
  surfaced by Stream 3:
  - **CMEFs monthly history** — fully acquirable (NRB sitemap→direct-PDF), but `nrb_cmefs`
    parser HARDCODES the period (`_BS_FY_START=2082`) → would mis-date every non-current
    edition. **Needs a period-aware parser fix** before the monthly back-history can ingest.
  - **Remittance-NPR history** — BPM6 only goes back to FY2022/23 (3 FY); a longer series
    exists in `Trade-and-Balance-of-Payments.xlsx` (`BOP 2000-`, Workers' remittances from
    FY2000/01) but it is **BPM5 (different definition)** → needs a new parser route + a
    labelled methodology discontinuity (Data Continuity), not a silent splice.
- **The path is proven:** Tier-1 deterministic recovery done; Tier-2 GPU Surya OCR harness
  built + banked (58 pytest, ADR-0022); intergovernmental fiscal-transfer history (Stream 2)
  shipped its 2 text-layer-reconcilable FYs. Remaining OCR-only work: 6 scanned transfer FYs +
  the `ocr_tracking` cross-check pass for the 2 ingested FYs (both gated on the same Surya GPU run).

Data currently spans **AD 2005 → 2025**. The mission's bar is completeness + accuracy;
this audit makes both measurable and keeps the agents honest.
