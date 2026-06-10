# AI pass — structure, verify, reconcile & promote the Surya-OCR corpus

**How to use this doc.** This is a self-contained briefing for the "AI pass" over the
overnight Surya-OCR output. Start a fresh session in this repo and either paste this file's
body as the prompt, or tell the agent: _"Read `scrapers/surya_ocr/AI_PASS_BRIEF.md` and
execute it."_ It assumes the repo is present (so `CLAUDE.md` + `docs/` auto-load) but that
the session has **no memory of the run that produced the OCR** — so the run-specific
learnings are embedded below.

---

## TASK

You are Mother (Opus-class orchestrator) on the **Nepal Ledger** project. An overnight GPU
run extracted ~13,000 pages of scanned / font-corrupted Nepali financial PDFs to raw
per-page OCR JSON. Your job: turn that raw OCR into **clean, reconciled, provenance-tagged
facts** that are safe for downstream reporting/AI — **without fabricating anything**.

This is the **AI-as-QA / dev-assistant** role, NOT generative extraction. Read the rules
below before touching anything.

---

## 0. READ FIRST (do not skip — anti-hallucination + doctrine)

Run `/memory`, then read, in order:

1. `CLAUDE.md` (root) — agent doctrine, the Six Rules, verification gates.
2. `docs/CONTEXT_RULES.md` — anti-hallucination + anti-scope-drift (mandatory).
3. `docs/DATA_AUDIT.md` — the authoritative truth-layer inventory + the reconciliation
   baseline. Never assert a number/series/coverage exists without checking here or the live
   DB (`pnpm audit:data`). Report confidence grade + provenance always.
4. `docs/decisions/0003-ai-assisted-parsing-policy.md` — **AI may clean/verify/QA, but the
   shipped VALUE must be deterministically derivable + reconciled; no LLM-guessed numbers.**
5. `docs/decisions/0021-*pdf-recovery*` (verification gate) and
   `docs/decisions/0022-surya-ocr-pipeline.md` (dual-channel) — the trust model.
6. `docs/decisions/0011-*fiscal-data-units*` — **verify the printed unit; never assume.**
7. `docs/decisions/0015-*dne-facts*` — the dimensional fact model.
8. `docs/CALENDAR_AND_PERIODS.md` — BS/AD + fiscal-year handling.
9. `docs/DATA_PIPELINE.md` + `docs/INGEST_RUNBOOK.md` — staging → validate → approved; how
   ingest CLIs run (env, PYTHON venv, source_document archival).
10. `scrapers/surya_ocr/OVERNIGHT_OCR.md` — the OCR run + output schema + the AI-pass contract.
11. `docs/DOCUMENTATION_STANDARD.md` — the Documentation Gate you must satisfy.

---

## 1. WHERE THE DATA IS

- Raw OCR: `scrapers/surya_ocr/_ocr_output/P<tier>__<stem>_<sha8>/page_<NNNN>.json`
  (gitignored, ~13k files). Each page JSON:
  `{ path, page, n_pages, priority, tier, render_scale(=3.0), image_px[w,h], model_name,
model_version, ocr_ts, text_lines:[ {text, confidence(0–1), bbox:[x0,y0,x1,y1]} ] }`
  `text_lines` are in reading order; **bbox is pixel space at render_scale** (÷3 → PDF points).
- Run `python -m surya_ocr.batch_ocr status` (from `scrapers/`, env below) for tier/doc/page
  counts. `_ocr_output/_state/`: `manifest.json` (the queue), `progress.log`, `.error` markers.
- Source PDFs (for verification): the `path` field, relative to repo root. The data dirs
  (`Financial Data/`, `NRB Current/`, `Stastical Information/`) are symlinks to the main repo.
- Env for any Python/ingest:
  `PYTHON=C:\Users\ACER\AppData\Local\Programs\Python\Python312\python.exe`, `PYTHONUTF8=1`,
  `PYTHONPATH=<repo>/scrapers`. Ingest CLIs:
  `node --env-file=.env.local --conditions=react-server --import tsx scripts/ingest-*.ts`.

Tiers (value order): **P0** scanned/un-extractable (402-pg Yellow Book SOE review 2081,
intergovernmental FY2077/78, scanned agreements) · **P1** SOE yellowbooks · **P2** Nepali
economic surveys (macro annex) · **P3** whitebook foreign aid · **P4** redbooks (federal
budget detail, ~9.5k pages) · **P5** misc Devanagari.

---

## 2. HARD RULES (non-negotiable — these are the mission)

- **Never fabricate, zero-fill, interpolate, or forward-carry a value** (Data Continuity
  Protocol). If you can't recover it, leave it out + record why.
- **Reconcile before you trust.** A recovered number is shippable ONLY if it reconciles to
  the document's printed subtotal/grand total (exact for structured tables; within a stated,
  logged tolerance otherwise). Unreconciled → quarantine + flag; never promote.
- **Magnitude sanity (ADR-0011):** every total checked against a known order of magnitude +
  the printed unit (रु. हजारमा=thousand, लाखमा=lakh, करोडमा=crore — READ the header).
- **Provenance always:** promoted facts carry `confidence_grade` (OCR-derived ⇒ B or C),
  `extraction_method='surya-ocr'` (or `surya-ocr+repair` if you arithmetic-corrected), and
  `source_document_id`. Never present OCR data as audited primary data.
- **AI is QA, not the source of digits.** You may normalize, cluster, arithmetic-repair (see
  §4), and VERIFY against the rendered page. You may NOT invent a digit the OCR/the image
  doesn't support.
- **Escalate structural decisions** (schema/enum changes, migrations, new ADRs) to the user —
  do not unilaterally migrate. (Known live example: the earliest fiscal-transfer books use 4
  _aggregate_ grant types vs the schema's 8 _atomic_ — that needs an ADR.)

---

## 3. OCR-QUALITY LEARNINGS FROM THE RUN (apply these — they're hard-won)

- **Labels / headers / prose: near-perfect** (conf 0.95–1.00). Trust the textual layer: table
  titles, row labels, units, FY headers, entity names. This is the big win — these are the
  CORRECT strings the font-corrupted (Preeti/CID) text layers could not give.
- **Numbers are the weak spot.** ~10–20% of numeric lines are <0.75 confidence, concentrated
  in dense table cells. Failure modes observed:
  - **Devanagari↔Latin digit confusion** (a printed Devanagari `१२००००००००` came back as
    Latin `92000000` — a misread AND a script switch). **A single line mixing Devanagari
    (०–९) and Latin (0–9) digits is a strong red flag** (it's <1% of lines — treat each as suspect).
  - Confidence <0.75 is a reliable "scrutinize me" signal — but NOT a guarantee; some wrong
    numbers carry high confidence. Reconciliation, not confidence, is the final arbiter.
- **OCR is line-by-line, NOT row×column.** You MUST reconstruct table geometry from `bbox`:
  cluster by y (rows) and x (columns); the per-line x0 gives column order. Headers anchor columns.
- **Nepali numerals + grouping:** `० १ २ ३ ४ ५ ६ ७ ८ ९` = 0–9. Grouping is South-Asian
  (lakh/crore: `१२,३४,५६७` = 1234567), NOT thousands. Decimals use `.`.
- **Periods:** fiscal years are BS (e.g., `२०८०/८१` = FY2080/81 BS). Keep BS labels; map to AD
  only via the project's date utilities (CALENDAR_AND_PERIODS), never by hand-math.
- **Empty pages are genuinely blank** (section dividers / blank backs) — not failures; skip.
- A page with a `.error` sibling could not be OCR'd — note it, don't invent its content.

---

## 4. WORKFLOW (phased, value-first, reconciliation-gated)

Work **tier by tier in priority order (P0→P4)**, and **document by document** within a tier.
For each document you may dispatch a scope-fenced worker; cap parallelism per the doctrine.
For each logical table:

(a) **Reconstruct** structure from the page JSONs (bbox row/column clustering; headers →
column model). Identify the table's keys (entity/line-item) + value columns + the printed
subtotal/grand-total cells.

(b) **Normalize** deterministically: Nepali→Arabic digits, fix grouping, parse the printed
unit, parse the BS period. Keep the raw OCR text alongside each parsed value.

(c) **Flag suspects:** (i) any line conf <0.75; (ii) Devanagari/Latin digit mixing; (iii)
cells that break internal arithmetic (components ≠ subtotal; rec+cap ≠ total; row sum ≠
printed row total); (iv) magnitude outliers.

(d) **Arithmetic self-repair (deterministic only):** if exactly one cell breaks an otherwise-
consistent row/column identity and a single-digit correction makes it reconcile, propose that
correction — then CONFIRM it in step (e). Log every repair. Do NOT repair by guessing.

(e) **Verify suspects against the ORIGINAL PDF** (this is the AI-QA core): render the exact
source page (`fitz.open(path)[page].get_pixmap(matrix=fitz.Matrix(3,3))` → PNG) and READ it.
Compare the suspect cell to the image. Accept the value ONLY if the image clearly supports it;
otherwise mark unrecoverable. You are agree/disagree, never the extractor.

(f) **Reconcile** the table: per-row identities AND the document's printed grand total (e.g.,
the `स्थानीय तह` total, donor-total==sector-total, recurrent+capital==total). If it reconciles
→ eligible for promotion. If not → quarantine the table + log the gap.

---

## 5. PER-TIER RECONCILIATION KEYS (known structure)

- **Intergovernmental fiscal transfers** (P0 FY2077/78): 753 local levels × 8 grant types;
  per-row 8 atomic components sum to the row grand total; the 753 grand totals sum to the
  printed `स्थानीय तह` document total. Codes: 9-digit = federal-8 + trailing `3` (strip it);
  some editions print bare 8-digit. Unit usually lakh → store `npr_crore` (÷10). Target table:
  `local_government_fiscal_transfers` (via `scripts/ingest-intergovernmental.ts`). NOTE: early
  books (2074/75-style) use 4 _aggregate_ grants — escalate, don't force into 8 atomic.
- **SOE / Yellow Book** (P0 review-2081, P1): per-enterprise financial+physical tables (paid-up
  capital, govt share, loan principal, revenue, profit/loss, royalty/VAT/income-tax paid to
  GoN, etc.). Reconcile sub-components to the stated per-enterprise totals. Likely feeds
  `dne_facts` (SOE dimensions) — confirm against the existing `soe-*` series.
- **Economic survey macro annex** (P2): GDP-levels / GVA-by-sector / fiscal detail tables.
  Headline GDP/CPI is ALREADY in the DB from DNE — only add annex depth not already present;
  cross-check overlaps to the existing `dne-gdp-*` / `dne-cpi` series; flag discontinuities.
- **Whitebook foreign aid** (P3): donor + sector/ministrywise summaries → `foreign_aid_facts`
  (`scripts/ingest-whitebook.ts`). Gate: **donor-total == sector-total per FY** (exact). Aid
  years already present (per DATA_AUDIT §3) must NOT be duplicated — check first.
- **Redbook federal budget** (P4): budget-head × {total, recurrent, capital}; gate:
  **recurrent + capital == total per head**, and heads sum to the appropriation total. Target
  `dne_facts` budget dimensions (`scripts/ingest-redbook.ts`).

Always check what's ALREADY in the DB (`pnpm audit:data`, DATA_AUDIT) before ingesting — the
fact tables use idempotent ON CONFLICT keys; don't create duplicate source_documents needlessly.

---

## 6. PROMOTION + GATES + DOCUMENTATION

- Produce, per document, **two durable artifacts** before any DB write: (1) a cleaned/
  structured table (JSON/CSV with raw-OCR + parsed value + conf + bbox per cell), (2) a
  **reconciliation report** (what reconciled, what was repaired, what was quarantined, with the
  printed totals cited). Let these be reviewable.
- Promote ONLY reconciled rows to the fact tables, with `confidence_grade` B/C +
  `extraction_method` + `source_document_id`. Use the existing repositories / ingest CLIs; bulk
  inserts use `safeQueryWithRetry` (pooler ECONNRESET resilience). If you persist OCR
  provenance, use the `ocr_tracking` trio (`ocr_tile_manifests`/`ocr_cell_extractions`/
  `ocr_stitch_disagreements`).
- **After every ingest, re-run `pnpm audit:data`.** A NEW reconciliation mismatch in
  DATA_AUDIT §5 means the new data is wrong → ROLL BACK, don't ship.
- Pass the CI gates (`pnpm typecheck|lint|test|build`, `drizzle-kit check`, `gitleaks`).
- Satisfy the **Documentation Gate**: update `docs/DATA_AUDIT.md` (new coverage + recon rows),
  `docs/changes/CHANGELOG.md`, and write an ADR for any structural decision. Record the
  OCR-quality caveats (§3) as the standing provenance note for this data.

---

## 7. DEFINITION OF DONE

For each processed document: every shipped number reconciles to a printed total, carries B/C
confidence + surya-ocr provenance + source_document_id; suspects were verified against the
rendered page or quarantined (never guessed); duplicates avoided; `pnpm audit:data` green with
no new mismatch; artifacts + reconciliation report saved; docs updated. Anything that can't
reconcile is documented as a known gap — NOT fabricated.

---

## START HERE

1. Read the §0 docs + run `python -m surya_ocr.batch_ocr status` and `pnpm audit:data` to see
   current coverage.
2. Propose a short plan (tier order, per-doc approach, how you'll reconstruct tables + verify
   suspects + reconcile) and the artifacts you'll produce.
3. Start with the highest-value, smallest-risk document in P0 (e.g., intergovernmental
   FY2077/78 — it has the cleanest reconciliation key), prove the end-to-end loop
   (reconstruct→normalize→suspect→verify→reconcile→report→promote→audit), then scale.

Ask before any schema migration or if a source's structure isn't documented above.

```

```
