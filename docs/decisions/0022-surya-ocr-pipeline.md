# ADR-0022: Surya tile-OCR harness + the intergovernmental dual-channel recovery

- **Status:** Accepted
- **Date:** 2026-06-08
- **Deciders:** Mother Opus, Stream-2 worker
- **Tags:** data-pipeline, parsing, ocr, recovery

## Context

[ADR-0021](0021-pdf-recovery-tiers-and-verification-gate.md) adopted a tiered
recovery cascade and mandated, as Tier 2, the Surya tile-OCR pipeline that
`FINANCIAL_DATA_STRATEGY.md` §Phase B had specified but never built. The first
application (Phase B1) is the historical **intergovernmental fiscal-transfer**
books (`Financial Data/mof_documents/intergovernmental/<FY>.pdf`, FY2074/75–
2082/83), which extend the per-local-level `local_government_fiscal_transfers`
series that currently holds only FY2082/83 (from the cleaned XLSX).

This ADR records (a) the harness's design, (b) the validated Surya-0.17.1
behaviour on real Nepali fiscal tables, and (c) the dual-channel extraction
decision the intergovernmental corpus forced — so none of it is re-learned.

### What the corpus actually is (investigated, not assumed)

Probing the 9 in-repo PDFs (pymupdf text + image inventory) found **three**
distinct page types, not the uniform "scanned" assumption:

1. **Text-layer-clean numbers, font-corrupted labels** (FY2078/79, FY2079/80):
   the embedded text layer yields the NUMBERS exactly. Every local-level row's
   8 atomic grant components sum to its printed grand total, and the 753 grand
   totals sum to the document's printed `स्थानीय तह` (local-level) total — TO
   THE RUPEE (FY2079/80 = 3,003,716 lakh; FY2078/79 = 2,830,147 lakh). The
   Devanagari LABELS in that same text layer are font-corrupted (dropped
   matras: `ववरण` for `विवरण`), but the 9-digit local-level code is intact and
   is the join key, so labels are not needed.
2. **No usable numeric text layer** (FY2074/75, 2075/76, 2077/78, 2080/81):
   prose text exists but the table numbers/codes don't extract — genuine OCR
   territory.
3. **Fully scanned** (FY2081/82, FY2082/83-pdf: one image per page) — OCR-only.

A verified, deterministic **code crosswalk** links the books to the entity
seed: the PDF 9-digit local-level code is the canonical 8-digit federal code +
a trailing `3`. Stripping it maps all **753/753** codes onto the seeded
`entities.slug` set (`kind='local_level'`), zero misses.

### What Surya 0.17.1 actually does on these tables (validated, RTX 4060)

Running the harness on the FY2079/80 province + detail pages:

- **Labels: excellent.** Headers and entity names OCR correctly in Unicode
  Devanagari at confidence > 0.99 (`समानीकरण अनुदान (२६३३१)`, the budget-head
  codes, `प्रदेश नं. १`, `मधेश प्रदेश`, …). **OCR is the BETTER label source
  than the corrupted text layer.**
- **Numbers: mostly right, ~5–10% digit errors.** The dominant issues match
  `surya-ocr-findings`:
  - **Adjacent-column merging** — one bbox spans 2–3 numbers
    (`'९२,०० ११,५२,२७'`, `'७,७४,६६ | १०,०६,५१'`). Must be split + re-placed.
  - **Arabic-Indic digit leakage** — `٩` (U+0669) for `९` (U+096F).
  - **Spurious markup** — `<br>`, `<b>…</b>`, `<math>`.
  - **Low-confidence digit confusion** — e.g. `9,55,88` for `1,55,88`
    (confidence 0.63). These would make ~30–50 of 753 rows fail reconciliation
    if Surya were the value source.

## Decision

### 1. A reusable, domain-agnostic Surya harness — `scrapers/surya_ocr/`

Pipeline (one direction, factored into testable modules):

```
render (pymupdf Matrix(3,3)) → preprocess? (OpenCV, opt-in) → tile (overlap)
  → Surya detection+recognition per tile → page-global CellExtraction
  → normalize (_common.devanagari_normalization: both numeral systems)
  → stitch (IoU dedupe across tiles; log disagreements)
  ⇒ OcrPageResult  (mirrors the ocr_tracking trio)
```

Table reconstruction (`reconstruct.py`) is a SEPARATE importable step — the
harness doesn't know column semantics; the domain parser supplies them. The
key reconstruction fix is **splitting merged multi-number lines** and snapping
each token to its nearest column anchor (recovering Surya's merged cells
instead of losing them).

Validated parameters (recorded in the tile manifest for reproducibility):
render zoom `Matrix(3,3)` (≈216 DPI); tile `max_edge_px=2200`, `overlap_px=256`
(single-tile fast path below the threshold); Surya called with the detection
predictor (`rec([img], det_predictor=det)`); OpenCV preprocessing OFF for
born-digital pages, available (deskew→denoise→adaptive-threshold) for scanned
legacy pages. Confidence rides on every cell; `near_tile_seam_px` is the
spot-check sampling bias.

The harness imports torch/surya/cv2 only when its run functions execute; the
pure-logic modules (cleanup, tiling, stitch, reconstruct, types) are importable
and unit-tested without the GPU stack.

### 2. Dual-channel extraction for the text-layer-clean FYs

For FY2078/79 + FY2079/80 the parser takes the numeric VALUES from the text
layer (deterministic, exact, self-reconciling — ADR-0021 Tier 0/1) and uses the
Surya harness as an **independent cross-validation channel** that (a) recovers
the correct Devanagari labels, (b) confirms values cell-by-cell, and (c)
populates the `ocr_tracking` trio for inspectability. This maximizes BOTH
completeness (100% of rows ship; none lost to OCR digit errors) AND accuracy
(triple reconciliation), which is the mission guardrail. `extraction_method` is
recorded honestly as **`surya-ocr+textlayer-xcheck`**, confidence **B**.

Storing pure-Surya values was rejected: its digit-error rate would drop real,
reconciling rows. LLM-vision extraction is forbidden (ADR-0003). The text layer
is not "less rigorous than OCR" here — it is the EXACT source the printed
totals reconcile to; Surya is the second opinion that the gate requires.

### 3. The verification gate is enforced parser-side

The parser refuses (`status=failure`) to emit a FY whose per-row atomic sums or
whose document total don't reconcile, and refuses scanned-only FYs (deferred).
The ingest CLI refuses to persist a non-reconciling FY. Unreconciled = not
shipped (ADR-0021).

### 4. Scanned FYs are deferred, not faked

FY2074/75, 2075/76, 2077/78, 2080/81, 2081/82, 2082/83-pdf have no usable
numeric text layer. The harness is ready to OCR them, but per-FY reconciliation
is the gate and Surya's digit-error rate means substantial cells need
verification first. They are deferred (documented in the parser's `SCANNED_FYS`
+ the source profile), never fabricated.

## Consequences

- Two historical FYs (2078/79, 2079/80) of per-local-level fiscal transfers
  (753 × 8 grant types = 6024 rows each) become shippable, extending the
  `local_government_fiscal_transfers` series backward with triple reconciliation.
- The harness is reusable for the genuinely-scanned Phase B targets (Yellow
  Books, Red Books) — its real long-term value.
- New deps for the Tier-2 path: `surya-ocr==0.17.1`, `pymupdf`, `opencv` — used
  only on the GPU path; they need mypy `ignore_missing_imports` overrides
  (matching the existing `pdfplumber`/`openpyxl` overrides) and the
  `surya_ocr*` package include + testpaths in `scrapers/pyproject.toml`.
- Unit (lakh → crore) is converted on ingest so historical rows share
  `npr_crore` with the FY2082/83 XLSX rows.

## References

- [ADR-0021](0021-pdf-recovery-tiers-and-verification-gate.md) — the tier cascade + verification gate this implements
- [ADR-0003](0003-ai-assisted-parsing-policy.md) — OCR-as-recognition is allowed; no generative-LLM extractor
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — reconcile/verify by magnitude
- `docs/research/surya-ocr-findings.md` — Surya 0.17.1 behaviour catalogue (predicted, here confirmed)
- `src/lib/db/schema/ocr-tracking.ts` — the provenance trio the harness populates
- `scrapers/surya_ocr/README.md` — the harness's operational doc + parameter table
- `docs/sources/mof-intergovernmental.md` — the source profile
