# Overnight AI-pass — session findings & strategic handoff (2026-06-10/11)

**Status:** Machinery built + validated; recovery started; **critical economics finding below needs a
human scope decision.** Recover + stage only — **nothing promoted** (your morning gate).

---

## 1. What was built + validated (committed on `claude/loving-wing-7bdcb4`)

| Build step                     | Artifact                                         | State                                                                             |
| ------------------------------ | ------------------------------------------------ | --------------------------------------------------------------------------------- |
| 1. Master Recovery Ledger      | `locate_tables.py` + `RECOVERY_LEDGER.json/.md`  | ✅ done (50 docs, 1,339 table candidates)                                         |
| 2. Multipage workflow + repair | `workflows/ocr_table_recovery_multipage.js`      | ✅ built + **validated live**                                                     |
| 2b. Engine gate fixes          | `workflows/ocr_table_recovery.js`                | ✅ 2 bugs fixed (see below)                                                       |
| 3. Nightly loop substrate      | `ledger_driver.py` + `run_ai_pass_overnight.ps1` | ✅ done (dry-run verified)                                                        |
| 4. Local-FS storage            | —                                                | ⏸️ **deferred** (wrong branch; schema migration = escalate; only gates promotion) |
| 5. Recovery runs               | `recovered/<id>/verified_matrix.json`            | 🔄 in progress                                                                    |

**Engine validated end-to-end:** GVA annex 13.1 re-run reproduced Nepal GDP **610,722 to the rupee**
(152 cells accepted; FY2080/81 correctly quarantined as the known +799 printed defect). The
multipage row-identity path reconciled intergovernmental FY2077/78 p20–22 (Σ4 grants = जम्मा, ±1).

**Two engine bugs caught by known-good canaries + fixed:**

1. Scope guard aborted when the agent left `reconciles_how=[]` despite a valid `total_row_idx`/`cross_groups`.
2. Gate quarantined **all** cells when `cross_groups=[]` (required cross-recon that's unevaluable for
   single-axis tables) — would have wrongly killed every column-footing table.

---

## 2. ⚠️ THE CRITICAL FINDING — token economics make full-corpus LLM recovery infeasible

The recovery work-unit is an LLM that **renders + reads every cell** of a page and reconciles. Measured cost/yield this run:

| Table                                | tokens | yield                                  |
| ------------------------------------ | -----: | -------------------------------------- |
| GVA 13.1 (clean macro)               | ~1.05M | 152 cells (full FY2081/82) ✅          |
| Intergovt FY2077/78 (scanned) p20–22 | ~2.13M | 36/99 rows (~36%) ⚠️                   |
| SOE ५.४ balance sheet                | ~0.32M | balance identity only; 2 corrupt cells |
| Econ ५.३ commodities                 | ~0.71M | 21 aggregate cells (selection table)   |
| Econ २.२४ foreign aid (degraded)     | ~0.94M | 36/345 cells ⚠️                        |
| Econ 13.7 prov. fund (degraded)      | ~1.06M | 33/400 cells ⚠️                        |

**~0.5–2M tokens per page, yield 30–100% depending on page OCR quality.** The corpus is **~11,000
pages**. At the requested ~60M tokens/night that is **~85 pages/night ⇒ ~130 nights** for the full
corpus, much of it at partial yield. **"Recover ALL OCR'd documents" via per-cell LLM render-verify is
not economically achievable.** The machinery is correct and honest; the _scale_ is the constraint.

### Corollary — route by source type, don't LLM everything

Per `DATA_AUDIT.md`, most of the corpus is **not** genuinely scanned:

- **Clean Preeti / text-layer** (whitebooks — all 14 already reconcile; many redbooks; some intergovt FYs)
  → **deterministic parsers** (cents per doc, exact). LLM-OCR here is wasted money.
- **Genuinely scanned (image-only)** — SOE review 2081 (`ksi3tbe`), scanned agreements, intergovt
  FY2077/78 — **no cheaper option ⇒ LLM-OCR is justified** (accept partial yield).
- **Broken/RTL-mirrored text layer** — Nepali economic surveys — LLM-OCR-of-visual is the proven route
  (but pick the _reconcilable levels_ tables; skip growth-rate/structure/selection tables — low/zero yield).

---

## 3. Recommended scope (my autonomous default unless you redirect)

Spend the LLM budget where it is the _only_ option **and** the table fully reconciles:

1. **`ksi3tbe` SOE review 2081** (scanned, high-value, ~250 table pages) — the SOE financial detail the
   DB lacks (revenue/profit/paid-up). Highest priority.
2. **Intergovt FY2077/78** (scanned) — chunked 4-page batches; accept ~36% yield + the ADR block.
3. **Economic-survey reconcilable levels annexes** (GVA-family levels, provincial fiscal) — skip
   growth-rate (13.4), structure/shares (13.2/13.3 — derivable), selection (5.x), and degraded pages.
4. **Defer text-layer redbooks/whitebooks to deterministic parsers** (cheaper + exact) — not LLM.

**Decision points for you (queued, not auto-decided):** (a) accept this prioritized/partial scope vs.
push for full-corpus; (b) whether to re-OCR degraded pages at higher DPI to lift yield before LLM
recovery; (c) the structural ADRs below.

---

## 4. Structural-decision queue (ADRs/enums needed before promotion — never auto-decided)

1. **Intergovernmental 4-aggregate grant types** (समानीकरण/सशर्त/विशेष/समपूरक, codes 26331–26334) vs the
   schema's 8 atomic types → enum ADR or aggregate→atomic mapping policy. (FY2074/75–2077/78.)
2. **Consolidated balance sheet** → new `consolidated_balance_sheet` measure + `side` enum
   (liab_equity/assets), unit `npr_lakh`. (SOE ५.४.)
3. **Foreign-aid flow matrix** → `aid_flow_stage × aid_instrument` dimension. (Econ २.२४.)
4. **Period enum** → `eight_months_cumulative` (or generic `first_n_months`). (Econ ५.३ 8-month cols.)
5. **Shares store-vs-derive** → provincial GDP composition is derivable from the absolute GVA table;
   likely derive, don't store. (Econ 13.3.)

---

## 5. How to continue

- **Unattended:** `run_ai_pass_overnight.ps1 -Execute` (walks the ledger via headless `claude`; safe/bounded).
- **Re-scan after OCR finishes:** `python scrapers/surya_ocr/_ai_pass/locate_tables.py` (idempotent; preserves statuses).
- **Morning report:** `python scrapers/surya_ocr/_ai_pass/ledger_driver.py report` → `REPORTS/<date>.md`.
- Staged matrices live in `recovered/<id>/verified_matrix.json` — review + promote the reconciled ones.
