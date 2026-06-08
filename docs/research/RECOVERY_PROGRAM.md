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
- **Migration:** likely none (reuse `local_government_fiscal_transfers`); if a schema
  change is needed, worker writes it + Mother applies.
- **Worker:** (pending dispatch) · **Status:** in progress. This is the largest stream;
  if the full harness+ingest doesn't land in one run, bank the harness first.

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
| _running_ | **2 — Tier-2 OCR** | intergovernmental fiscal-transfer history (GPU Surya) | — | — |

### Follow-ups surfaced (new scoped tasks, documented in DATA_AUDIT §8)
- **CMEFs period-aware parser fix** — `nrb_cmefs` hardcodes `_BS_FY_START=2082`; the whole monthly history is acquirable once it reads the FY+month-count from the PDF.
- **Remittance BPM5 route + discontinuity** — `Trade-and-Balance-of-Payments.xlsx` has Workers'-remittances from FY2000/01 (BPM5); needs a new route + a labelled methodology discontinuity vs the BPM6 series.
- **Live DB after Streams 1+3:** dne_facts **271,601** · foreign_aid_facts **1,024** · approved 877.
