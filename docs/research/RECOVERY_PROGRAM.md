# Recovery Program — 3 parallel streams (control + tracking)

**Started:** 2026-06-08. **Owner:** Mother. **Status doc — update as streams land.**

> **Why this doc exists:** background workers do not survive idle/suspend gaps
> (several killed mid-session). This is the durable tracker so any worker death or
> context reset is recoverable: it records each stream's scope, worker id, the
> verification gate, the recovery procedure, and the mission guardrails. Pair with
> the task list (#51–#53) and `pnpm audit:data` (the regression gate).

## Mission guardrails (do NOT drift)

1. **Completeness AND accuracy are the product.** Every recovered fact must (a)
   reconcile to the source's printed total, (b) carry `confidence_grade` +
   `extraction_method` provenance, (c) never be fabricated/zero-filled.
2. **ADR-0021 verification gate** applies to all OCR/recovered data: reconcile →
   sample-verify vs rendered page → grade B/C + provenance. Unreconciled = do not ship.
3. **ADR-0003**: deterministic Python + Surya OCR (recognition) + AI-as-QA only.
   No generative-LLM-as-extractor.
4. **After every ingest, re-run `pnpm audit:data`** — a NEW reconciliation mismatch
   in `docs/DATA_AUDIT.md` §5 means the new data is wrong. Roll back, don't ship.
5. **Recovery on worker death:** the worker's code files persist. Run its module's
   pytest; if green, Mother finishes integration (seed/registry/package/pyproject +
   live ingest + commit). If red/partial, Mother finishes or re-dispatches.

## Environments

- Deterministic parsers + ingest CLIs: venv `C:/Users/ACER/Projects/Economy/scrapers/.venv/Scripts/python.exe` (py3.12, editable scrapers). Set `PYTHON` + `PYTHONPATH=<worktree>/scrapers`; ingest via `node --env-file=.env.local --conditions=react-server --import tsx scripts/...`.
- **Tier-2 Surya OCR: base py312** `C:/Users/ACER/AppData/Local/Programs/Python/Python312/python.exe` — RTX 4060 GPU, torch 2.10+cu128, surya-ocr 0.17.1, pymupdf, opencv. API: `FoundationPredictor()` → `RecognitionPredictor(foundation)`; `DetectionPredictor()`; `rec([pil_img], det_predictor=det)` → `[0].text_lines[].{text,confidence,bbox}`. Render `fitz.Matrix(3,3)`. (Validated — task #50.)
- Migrations (Mother only): `node --env-file=.env.local node_modules/drizzle-kit/bin.cjs migrate`.

---

## Stream 1 (#51) — Fix foreign-aid FY2070/71 reconciliation flag

- **Problem:** `foreign_aid_facts` FY2070/71 (AD2013/14) donor-total 113,240,000 ≠
  sector-total 95,934,658 npr_thousand (~15%). Every other edition reconciles exactly
  (DATA_AUDIT §5). One of that edition's two Preeti-decoded tables mis-captured rows.
- **Scope:** `scrapers/mof_whitebook/` (parser + tests). Diagnose which table is wrong
  (compare donor vs sector row sets for that edition), fix, re-ingest 2070/71, confirm
  donor==sector in the audit. If un-fixable, mark the edition unreconciled + exclude.
- **Verify:** `pnpm audit:data` G3 shows 2070/71 donor==sector.
- **Worker:** (pending dispatch) · **Status:** in progress.

## Stream 2 (#52) — Tier-2 Surya OCR: intergovernmental fiscal-transfer history (Phase B1)

- **Goal:** build `scrapers/surya_ocr/` harness (render→OpenCV preprocess→tile→Surya→
  stitch→`ocr_tracking`→`devanagari_normalization`→table-reconstruct→facts) and apply
  to the **intergovernmental fiscal-transfer PDFs** on disk
  (`Financial Data/mof_documents/intergovernmental/` — FY2074/75–2079/80, ~6 FYs) →
  `local_government_fiscal_transfers` (which currently has only FY2082/83).
- **Env:** base py312 GPU (above). **Gate:** per-FY transfer total reconciles to the
  published figure; populate `ocr_tile_manifests`/`ocr_cell_extractions`/
  `ocr_stitch_disagreements`; confidence B; `extraction_method='surya-ocr'`.
- **Migration:** NONE — reuses `local_government_fiscal_transfers` unchanged. OCR
  provenance lives in the `ocr_tracking` trio + row `notes`
  (`extraction_method=surya-ocr+textlayer-xcheck`).
- **Worker:** loving-wing-7bdcb4 · **Status:** ✅ INTEGRATED 2026-06-08 (harness banked; 2 FYs ingested text-layer; Surya GPU cross-check pass deferred — see below).
  - Harness `scrapers/surya_ocr/` (render→preprocess→tile→Surya→stitch→reconstruct
    + `ocr_tracking` trio). 57 pytest pass; ruff + mypy clean (mypy needs pyproject
    `fitz`/`cv2`/`surya` overrides — RETURNED to Mother). README + ADR-0022 written.
  - Parser `scrapers/surya_ocr/parsers/intergovernmental.py`; CLI
    `scripts/ingest-intergovernmental.ts`; repo `src/lib/db/repositories/ocr-tracking.ts`.
  - **Corpus reality (probed, not assumed):** only **FY2078/79 + FY2079/80** have a
    usable numeric text layer — both 753/753 rows reconcile AND the 753 grand totals
    sum to the printed `स्थानीय तह` document total TO THE RUPEE. The other 6 FYs are
    scanned / non-reconciling → **DEFERRED** (Surya-OCR-only; gate not yet met). Code
    crosswalk 9→8 digit verified 753/753. **Dual-channel:** values from the reconciling
    text layer; Surya as cross-check + label recovery + `ocr_tracking` provenance (ADR-0022).
  - **✅ INGESTED (text-layer)** — Mother applied pyproject overrides (`surya_ocr*` include +
    testpaths + `fitz`/`cv2`/`surya`/`PIL`/`numpy` mypy ignores), seeded `mof-intergovernmental`
    (registry 69→70, active), added `ingest:intergovernmental` to package.json, dry-ran both
    FYs (gate passed), then live-ingested: **FY2078/79 + FY2079/80 = 12,048 rows**
    (`local_government_fiscal_transfers` 6,008→**18,056**, 3 FYs), 0 unresolved, both reconcile.
    `pnpm audit:data` re-run: F3 shows 3 FYs, all G-checks still pass (no new mismatch).
  - **Provenance honesty fix (Mother):** the parser hardcoded `extraction_method=`
    `surya-ocr+textlayer-xcheck` on every row even in text-only mode. Changed to honest
    conditional: `textlayer` by default, `surya-ocr+textlayer-xcheck` only when `--surya`
    actually runs (`parse(..., surya_xcheck=run_surya)`). +1 test. The 2 ingested FYs carry
    `extraction_method=textlayer` (true — values are text-layer-derived, not OCR).
  - **DEFERRED — Surya GPU cross-check pass** (populate `ocr_tracking` for the 2 ingested FYs):
    the CLI invokes the parser as a **bare script** (`python .../intergovernmental.py …`), under
    which the lazy `from .. import HarnessConfig, …` in `cross_validate_with_surya` does NOT
    resolve (no parent package in `__main__`). Needs a small fix (absolute import +
    `sys.path` bootstrap of the `scrapers/` dir) before `--surya` runs end-to-end via the CLI,
    then a ~5–15 min/FY GPU run (31 detail pages each). **The DATA does not depend on it** —
    text-layer values already reconcile + shipped. Tracked as a follow-up below.

## Stream 3 (#53) — Deepen thin single-period domains (acquisition + ingest, no OCR)

- **Targets (DATA_AUDIT §2 thin domains):**
  - **Customs trade history** — only FY2081/82 on disk; acquire prior FYs from
    customs.gov.np (sandbox bypass) → `ingest:customs-trade` (idempotent per period).
  - **CMEFs monthly history** — only the latest 9-month snapshot; acquire the monthly
    NRB CMEFs releases → `ingest:cmefs`.
  - **Remittance-NPR history** — only 3 FY; find an older BoP/external-sector source
    with the remittance series (the current BoP file stops at FY2079/80).
- **Scope:** downloads under `Financial Data/...`; reuse EXISTING parsers/CLIs (no new
  parser unless a layout demands it). Return any seed/registry edits to Mother.
- **Gate:** magnitude + reconcile per source; audit shows extended coverage.
- **Worker:** (pending dispatch) · **Status:** in progress. Acquisition may be blocked
  for some sources — document blockers honestly, never fabricate.

---

## Integration log (append as streams land)

| When | Stream | Result | Audit re-run? | Commit |
|---|---|---|---|---|
| 2026-06-08 | **1 — aid FY2070/71** | ✅ root-caused (wrapped-name rows dropped from sector table = exact gap); fixed deterministically (mof_whitebook v0.2.1, no AI); re-ingested 154→158; **all 7 aid FYs reconcile** | ✅ G3 donor==sector | `8d482c7` |
| 2026-06-08 | **3 — deepen thin** | ✅ customs **1→7 periods** (5 annual FYs 2076/77–2081/82; +164,612 dne_facts); blank-description fix (v0.3.0) + `safeQueryWithRetry` (ECONNRESET resilience for all bulk inserts). ⚠️ CMEFs-monthly + remittance-NPR PARSER-blocked (acquired, documented in DATA_AUDIT §8) | ✅ customs 7 periods | `74c08ee` |
| 2026-06-08 | **2 — Tier-2 OCR** | ✅ harness `scrapers/surya_ocr/` BANKED (58 pytest, ruff+mypy clean) + ADR-0022. Intergovernmental **FY2078/79 + FY2079/80 INGESTED** (text-layer): `local_government_fiscal_transfers` 6,008→**18,056** (3 FYs), 12,048 rows, 753/753 reconcile to printed doc-total exactly, npr_crore, conf B, `extraction_method=textlayer` (honest). Registry 69→70 (`mof-intergovernmental` active). Provenance-honesty fix to parser (+1 test). Gates: typecheck 0, eslint 0-err, vitest 148, ruff clean, mypy 17 files, **pytest 604**. 6 scanned FYs + the `ocr_tracking` Surya GPU pass DEFERRED (CLI `--surya` invocation fix needed). | ✅ F3 3 FYs; all G-checks pass | _see commit below_ |

### Follow-ups surfaced (new scoped tasks, documented in DATA_AUDIT §8)
- **CMEFs period-aware parser fix** — `nrb_cmefs` hardcodes `_BS_FY_START=2082`; the whole monthly history is acquirable once it reads the FY+month-count from the PDF.
- **Remittance BPM5 route + discontinuity** — `Trade-and-Balance-of-Payments.xlsx` has Workers'-remittances from FY2000/01 (BPM5); needs a new route + a labelled methodology discontinuity vs the BPM6 series.
- **Surya GPU cross-check pass (Stream 2)** — fix the `--surya` CLI invocation (parser bare-script relative import → absolute import + `sys.path` bootstrap), then run the GPU OCR over the 2 ingested FYs' detail pages to populate `ocr_tracking` (tiles/cells/disagreements). Independently, run the harness over the **6 scanned transfer FYs** (2074/75, 2075/76, 2077/78, 2080/81, 2081/82, 2082/83-pdf) — Surya is the ONLY route there (no text layer); ship per-FY only when OCR reconciles (ADR-0021 gate).
- **Live DB after Streams 1+2+3:** dne_facts **271,601** · foreign_aid_facts **1,024** · `local_government_fiscal_transfers` **18,056** (3 FYs) · source_registry 70 (17 active) · approved 877.
